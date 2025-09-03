# app/main/routes.py - Enhanced Main Routes with Chat Functionality
import time
import uuid
import json
import re
import logging
from datetime import datetime
from flask import (
    render_template, jsonify, request, session, make_response,
    redirect, url_for, Response, stream_with_context, current_app
)

from . import bp
from ..extensions import supabase_service, limiter
from ..services.intent import (
    classify_query_with_groq, generate_response_by_intent,
    QueryProcessor, enhanced_summarize_with_context
)
from ..services.embeddings import fetch_text_df, fetch_qa_df
from ..services.search import best_text_for_query, top_qa_for_query
from ..services.videos import get_videos
from ..services.pdf import generate_pdf_from_html

logger = logging.getLogger("dsa-mentor")


def validate_and_sanitize_query(data):
    """Comprehensive input validation and sanitization"""
    if not data or not isinstance(data, dict):
        return False, "Invalid request format"
    
    query = data.get("query", "").strip() if data.get("query") else ""
    if not query:
        return False, "Query cannot be empty"
    
    # Length validation
    max_length = current_app.config.get('MAX_QUERY_LENGTH', 2000)
    if len(query) > max_length:
        return False, f"Query too long (max {max_length} characters)"
    
    # Security checks
    dangerous_patterns = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script tags
        r'javascript:',  # JavaScript protocols
        r'data:text/html',  # Data URLs
        r'vbscript:',  # VBScript
        r'onload\s*=',  # Event handlers
        r'onerror\s*=',
        r'onclick\s*=',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Suspicious input detected: {pattern}")
            return False, "Invalid input detected"
    
    # SQL injection prevention
    sql_patterns = [
        r'\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b',
        r'[\'"];?\s*--',  # SQL comments
        r'\/\*.*?\*\/',  # SQL block comments
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential SQL injection attempt: {query[:100]}...")
            return False, "Invalid input format"
    
    # Sanitize the query
    sanitized_query = re.sub(r'[<>"\']', '', query)  # Remove dangerous characters
    sanitized_query = re.sub(r'\s+', ' ', sanitized_query)  # Normalize whitespace
    
    return True, sanitized_query


def require_authentication(f):
    """Decorator to require authentication for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'google_id' not in session:
            return jsonify({
                "error": "Authentication required",
                "message": "Please sign in to access this feature"
            }), 401
        
        # Check session validity
        login_time = session.get('login_time', 0)
        max_age = current_app.config.get('PERMANENT_SESSION_LIFETIME')
        
        if hasattr(max_age, 'total_seconds'):
            max_age = max_age.total_seconds()
        else:
            max_age = 7200  # 2 hours default
        
        if time.time() - login_time > max_age:
            session.clear()
            return jsonify({
                "error": "Session expired",
                "message": "Please sign in again"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


@bp.route('/')
def index():
    """Main application page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Failed to render index template: {e}")
        return jsonify({
            "message": "DSA Mentor is running",
            "version": "2.0.0",
            "status": "healthy"
        })


@bp.route('/chat', methods=['POST'])
@require_authentication
@limiter.limit("30 per minute")  # Rate limiting for chat endpoint
def chat():
    """Enhanced chat endpoint with comprehensive error handling"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"🔍 Chat request {request_id} started")
    
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({
                "error": "Invalid content type",
                "message": "Request must be JSON"
            }), 400
        
        # Validate and sanitize input
        is_valid, result = validate_and_sanitize_query(request.json)
        if not is_valid:
            logger.warning(f"Invalid query in request {request_id}: {result}")
            return jsonify({
                "error": "Invalid input",
                "message": result
            }), 400
        
        user_query = result
        user_id = session.get('google_id')
        user_email = session.get('email', 'unknown')
        
        logger.info(f"📝 Processing query for {user_email}: {user_query[:50]}...")
        
        # Step 1: Classify user intent
        classification = classify_query_with_groq(user_query)
        logger.debug(f"Intent classification: {classification}")
        
        # Step 2: Check for special intent responses
        special_response = generate_response_by_intent(classification, user_query)
        if special_response:
            logger.info(f"✨ Special response generated for {classification.get('type')}")
            processing_time = time.time() - start_time
            
            return jsonify({
                **special_response,
                "query": user_query,
                "intent": classification,
                "processing_time": round(processing_time, 2),
                "request_id": request_id
            })
        
        # Step 3: Fetch relevant data from database
        try:
            text_df = fetch_text_df()
            qa_df = fetch_qa_df()
            
            if text_df.empty and qa_df.empty:
                logger.warning("No knowledge base data available")
                return jsonify({
                    "error": "Service unavailable",
                    "message": "Knowledge base is currently unavailable"
                }), 503
                
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            return jsonify({
                "error": "Database error",
                "message": "Unable to access knowledge base"
            }), 503
        
        # Step 4: Find best matching content
        best_text = best_text_for_query(user_query, text_df) if not text_df.empty else {}
        top_qa = top_qa_for_query(user_query, qa_df, k=3) if not qa_df.empty else []
        
        # Step 5: Get relevant videos
        try:
            videos = get_videos(user_query, limit=3)
        except Exception as e:
            logger.warning(f"Video fetch failed: {e}")
            videos = []
        
        # Step 6: Generate response
        processor = QueryProcessor()
        context = processor.extract_dsa_context(user_query)
        
        # Create response structure
        response_data = {
            "query": user_query,
            "intent": classification,
            "context": context,
            "best_book": {},
            "top_dsa": top_qa[:3],  # Limit to top 3
            "video_suggestions": videos,
            "summary": "",
            "processing_time": 0,
            "request_id": request_id
        }
        
        # Format best text content
        if best_text and "content" in best_text:
            similarity_score = best_text.get("similarity", 0)
            
            if similarity_score > 0.7:  # High confidence threshold
                content = best_text["content"]
                
                # Enhance content with context
                enhanced_summary = enhanced_summarize_with_context(
                    content, context, user_query
                )
                
                response_data["best_book"] = {
                    "title": f"DSA Concept: {context.get('topics', ['General'])[0].title()}",
                    "content": enhanced_summary or content,
                    "similarity": round(similarity_score, 3)
                }
                
                response_data["summary"] = f"Found highly relevant content about {', '.join(context.get('topics', ['DSA']))}"
            
            else:  # Lower confidence - provide general guidance
                response_data["best_book"] = {
                    "title": "DSA Learning Guide",
                    "content": f"I found some information related to your query about {user_query}. Here are some resources that might help you learn more about this topic.",
                    "similarity": round(similarity_score, 3)
                }
                
                response_data["summary"] = "Here are some resources that might be helpful for your DSA learning journey."
        
        else:
            # No relevant content found
            response_data["best_book"] = {
                "title": "Explore DSA Topics",
                "content": "I'd be happy to help you learn about Data Structures and Algorithms! Try asking about specific topics like arrays, trees, graphs, sorting algorithms, or complexity analysis.",
                "similarity": 0.0
            }
            
            response_data["summary"] = "Ask me about specific DSA topics for more targeted help!"
        
        # Calculate final processing time
        processing_time = time.time() - start_time
        response_data["processing_time"] = round(processing_time, 2)
        
        logger.info(f"✅ Chat request {request_id} completed in {processing_time:.2f}s")
        
        return jsonify(response_data)
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Chat request {request_id} failed after {processing_time:.2f}s: {e}")
        
        return jsonify({
            "error": "Processing failed",
            "message": "An error occurred while processing your request",
            "request_id": request_id,
            "processing_time": round(processing_time, 2)
        }), 500


@bp.route('/download-chat', methods=['POST'])
@require_authentication
def download_chat():
    """Generate PDF download of chat conversation"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type"}), 400
        
        html_content = request.json.get('html_content', '')
        if not html_content:
            return jsonify({"error": "No content provided"}), 400
        
        # Generate PDF
        pdf_bytes = generate_pdf_from_html(html_content)
        
        if not pdf_bytes:
            return jsonify({"error": "PDF generation failed"}), 500
        
        # Create response with PDF
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="dsa_chat_{int(time.time())}.pdf"'
        response.headers['Content-Length'] = len(pdf_bytes)
        
        return response
        
    except Exception as e:
        logger.error(f"PDF download error: {e}")
        return jsonify({
            "error": "Download failed",
            "message": "Unable to generate PDF"
        }), 500


@bp.route('/api/stats')
@require_authentication
def api_stats():
    """Get API usage statistics for the current user"""
    try:
        user_id = session.get('google_id')
        
        # This would typically query a usage tracking database
        # For now, return mock statistics
        stats = {
            "user_id": user_id,
            "total_queries": 0,  # Would be fetched from database
            "queries_today": 0,
            "favorite_topics": [],  # Would be computed from query history
            "last_active": session.get('login_time')
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Stats fetch error: {e}")
        return jsonify({
            "error": "Unable to fetch statistics"
        }), 500


@bp.route('/api/feedback', methods=['POST'])
@require_authentication
@limiter.limit("10 per hour")  # Rate limit feedback submissions
def submit_feedback():
    """Submit user feedback"""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type"}), 400
        
        feedback_data = request.json
        feedback_text = feedback_data.get('feedback', '').strip()
        rating = feedback_data.get('rating')
        
        if not feedback_text:
            return jsonify({"error": "Feedback text is required"}), 400
        
        if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        
        user_id = session.get('google_id')
        user_email = session.get('email')
        
        # Store feedback (this would typically go to a database)
        feedback_record = {
            "user_id": user_id,
            "user_email": user_email,
            "feedback": feedback_text[:1000],  # Limit feedback length
            "rating": rating,
            "timestamp": datetime.utcnow().isoformat(),
            "user_agent": request.headers.get('User-Agent', '')
        }
        
        logger.info(f"📝 Feedback received from {user_email}: {rating}/5 stars")
        
        # In a real application, save to database here
        # supabase_service.get_table('feedback').insert(feedback_record).execute()
        
        return jsonify({
            "message": "Thank you for your feedback!",
            "feedback_id": str(uuid.uuid4())  # Would be real ID from database
        })
        
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return jsonify({
            "error": "Failed to submit feedback"
        }), 500


# Error handlers specific to main blueprint
@bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle file upload size limit exceeded"""
    return jsonify({
        "error": "Request too large",
        "message": "The request size exceeds the maximum allowed limit"
    }), 413


@bp.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limit exceeded for main routes"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "You're sending requests too quickly. Please slow down.",
        "retry_after": getattr(error, 'retry_after', None)
    }), 429