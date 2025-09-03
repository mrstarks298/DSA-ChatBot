# Updated app/main/routes.py - Enhanced to match frontend expectations

import time
import uuid
import json
import re
from datetime import datetime
from flask import (
    render_template, jsonify, request, session, make_response,
    redirect, url_for, Response, stream_with_context, current_app
)
from . import bp
from ..extensions import supabase
from ..services.intent import (
    classify_query_with_groq, generate_response_by_intent,
    QueryProcessor, enhanced_summarize_with_context
)
from ..services.embeddings import fetch_text_df, fetch_qa_df, _to_array
from ..services.search import best_text_for_query, top_qa_for_query
from ..services.videos import get_videos
from ..services.pdf import generate_pdf_from_html
import logging

logger = logging.getLogger("dsa-mentor")

# ===== INPUT VALIDATION AND SECURITY =====

def validate_and_sanitize_query(data):
    """Validate and sanitize user input with comprehensive checks"""
    if not data or not isinstance(data, dict):
        return False, "Invalid request format"
    
    query = data.get("query", "").strip() if data.get("query") else ""
    if not query:
        return False, "Query cannot be empty"
    
    # Get max length from config
    max_length = current_app.config.get('MAX_QUERY_LENGTH', 2000)
    if len(query) > max_length:
        return False, f"Query too long (max {max_length} characters)"
    
    # Basic security checks
    if re.search(r'<script|javascript:|data:|vbscript:', query, re.IGNORECASE):
        return False, "Invalid characters detected"
    
    # SQL injection basic check
    if re.search(r'(union|select|insert|update|delete|drop|create|alter)\s', query, re.IGNORECASE):
        return False, "Invalid query format"
    
    return True, query

def is_authenticated():
    """Check if user is authenticated"""
    return 'google_id' in session and 'login_time' in session

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ===== MAIN ROUTES =====

@bp.route('/')
def index():
    """Main page with user data injection for frontend"""
    try:
        # Get current user info for frontend
        user_data = {
            'is_authenticated': is_authenticated(),
            'user_id': session.get('google_id'),
            'name': session.get('name'),
            'email': session.get('email'),
            'picture': session.get('picture')
        }
        
        logger.info(f"Index route - User authenticated: {user_data['is_authenticated']}")
        return render_template('index.html', user=user_data)
        
    except Exception as e:
        logger.error(f"Index route error: {e}")
        # Fallback user data
        user_data = {'is_authenticated': False}
        return render_template('index.html', user=user_data)

@bp.route('/auth-status')
def auth_status():
    """API endpoint for checking authentication status - Required by frontend"""
    try:
        authenticated = is_authenticated()
        
        user_data = {
            'is_authenticated': authenticated,
            'user_id': session.get('google_id') if authenticated else None,
            'name': session.get('name') if authenticated else None,
            'email': session.get('email') if authenticated else None,
            'picture': session.get('picture') if authenticated else None
        }
        
        logger.debug(f"Auth status check: {user_data['is_authenticated']} for user {user_data.get('email', 'anonymous')}")
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return jsonify({
            'is_authenticated': False,
            'error': 'Failed to check authentication status'
        }), 500

@bp.route('/query', methods=['POST'])
@require_auth
def query():
    """Enhanced query endpoint with proper response format for frontend"""
    try:
        # Validate input
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided", "code": "NO_DATA"}), 400
        
        is_valid, result = validate_and_sanitize_query(data)
        if not is_valid:
            return jsonify({"error": result, "code": "INVALID_INPUT"}), 400
        
        query_text = result
        thread_id = data.get('thread_id') or f"thread_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Query received: '{query_text[:50]}...' from user {session.get('email')}")
        
        # Process query
        response_data = process_dsa_query(query_text, thread_id)
        
        # Ensure required format for frontend
        formatted_response = {
            'best_book': response_data.get('best_book', {
                'title': 'DSA Insights',
                'content': response_data.get('content', 'I can help you with DSA concepts. Please ask a specific question.')
            }),
            'top_dsa': response_data.get('top_dsa', []),
            'video_suggestions': response_data.get('video_suggestions', []),
            'summary': response_data.get('summary', 'Ask me about any DSA topic!'),
            'thread_id': thread_id
        }
        
        return jsonify(formatted_response)
        
    except Exception as e:
        logger.error(f"Query endpoint error: {e}")
        return jsonify({
            "error": "An error occurred processing your request",
            "code": "PROCESSING_ERROR"
        }), 500

@bp.route('/query-stream', methods=['POST'])
@require_auth  
def query_stream():
    """Streaming endpoint for real-time responses - Required by frontend"""
    try:
        # Validate input
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        is_valid, result = validate_and_sanitize_query(data)
        if not is_valid:
            return jsonify({"error": result}), 400
            
        query_text = result
        thread_id = data.get('thread_id') or f"thread_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Streaming query: '{query_text[:50]}...' from user {session.get('email')}")
        
        def generate_stream():
            try:
                # Send metadata first
                yield f"event: meta\ndata: {json.dumps({'thread_id': thread_id})}\n\n"
                
                # Process query and stream response
                response_data = process_dsa_query(query_text, thread_id)
                content = response_data.get('best_book', {}).get('content', '')
                
                # Stream content in chunks
                if content:
                    chunk_size = 50
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        chunk_data = {'text': chunk}
                        yield f"event: chunk\ndata: {json.dumps(chunk_data)}\n\n"
                        time.sleep(0.05)  # Small delay for streaming effect
                
                # Send final complete data
                formatted_response = {
                    'best_book': response_data.get('best_book', {}),
                    'top_dsa': response_data.get('top_dsa', []),
                    'video_suggestions': response_data.get('video_suggestions', []),
                    'summary': response_data.get('summary', ''),
                    'thread_id': thread_id
                }
                
                yield f"event: final_json\ndata: {json.dumps(formatted_response)}\n\n"
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                error_data = {'error': 'Stream processing failed'}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # Disable nginx buffering
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Query stream error: {e}")
        return jsonify({"error": "Streaming failed"}), 500

def process_dsa_query(query_text, thread_id):
    """Process DSA query and return structured response"""
    try:
        # Classify the query
        classification = classify_query_with_groq(query_text)
        logger.debug(f"Query classification: {classification}")
        
        # Check if intent handler can respond
        intent_response = generate_response_by_intent(classification, query_text)
        if intent_response:
            return intent_response
        
        # Main DSA processing
        processor = QueryProcessor()
        clean_query = processor.clean_and_normalize_query(query_text)
        context = processor.extract_dsa_context(clean_query)
        
        # Fetch data
        text_df = fetch_text_df()
        qa_df = fetch_qa_df()
        
        response_data = {
            'best_book': {
                'title': 'DSA Insights',
                'content': 'Let me help you with that DSA concept.'
            },
            'top_dsa': [],
            'video_suggestions': [],
            'summary': 'DSA learning assistance provided.'
        }
        
        # Get best matching content
        if not text_df.empty:
            best_match = best_text_for_query(clean_query, text_df)
            if best_match and 'error' not in best_match:
                content = best_match.get('content', '')
                if content:
                    # Enhanced summarization with context
                    summary = enhanced_summarize_with_context(content, context, query_text)
                    response_data['best_book'] = {
                        'title': f"DSA Concept: {context.get('topics', ['General'])[0].replace('_', ' ').title()}",
                        'content': summary or content[:1000] + "..." if len(content) > 1000 else content
                    }
        
        # Get related Q&A
        if not qa_df.empty:
            qa_results = top_qa_for_query(clean_query, qa_df, k=3)
            response_data['top_dsa'] = qa_results
        
        # Get video suggestions
        if context.get('topics'):
            main_topic = context['topics'][0]
            videos = get_videos(main_topic, limit=2)
            response_data['video_suggestions'] = videos
        
        # Generate summary
        topic_names = [t.replace('_', ' ').title() for t in context.get('topics', [])]
        if topic_names:
            response_data['summary'] = f"Explored {', '.join(topic_names)} concepts with examples and practice resources."
        
        return response_data
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return {
            'best_book': {
                'title': 'Processing Error',
                'content': 'I encountered an issue processing your query. Please try rephrasing your question.'
            },
            'top_dsa': [],
            'video_suggestions': [],
            'summary': 'Please try your question again.'
        }


@bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages - CRITICAL MISSING ENDPOINT"""
    try:
        # Check authentication first
        if 'google_id' not in session:
            return jsonify({
                "error": "Authentication required",
                "requires_auth": True
            }), 401
        
        # Get and validate request data
        data = request.get_json()
        is_valid, error_msg = validate_and_sanitize_query(data)
        
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        query = data.get("query", "").strip()
        logger.info(f"Processing chat query: {query[:50]}...")
        
        # Process the query using your existing logic
        try:
            # Classify query intent
            classification = classify_query_with_groq(query)
            logger.info(f"Query classified as: {classification.get('type')}")
            
            # Generate response based on intent
            intent_response = generate_response_by_intent(classification, query)
            
            if intent_response:
                # Return intent-based response (greetings, etc.)
                return jsonify({
                    "response": intent_response.get("summary", ""),
                    "best_book": intent_response.get("best_book", {}),
                    "top_dsa": intent_response.get("top_dsa", []),
                    "video_suggestions": intent_response.get("video_suggestions", []),
                    "classification": classification
                })
            
            # For DSA-specific queries, fetch relevant content
            text_df = fetch_text_df()
            qa_df = fetch_qa_df()
            
            best_text = best_text_for_query(query, text_df)
            top_qa = top_qa_for_query(query, qa_df, k=3)
            videos = get_videos(query, limit=3)
            
            # Prepare response
            response_data = {
                "response": "Here's what I found about your question:",
                "best_book": {
                    "title": "DSA Information",
                    "content": best_text.get("content", "No specific content found.") if not best_text.get("error") else "No content available."
                },
                "top_dsa": top_qa[:3],
                "video_suggestions": videos,
                "classification": classification
            }
            
            # Add summary if content found
            if not best_text.get("error"):
                processor = QueryProcessor()
                ctx = processor.extract_dsa_context(query)
                summary = enhanced_summarize_with_context(
                    best_text.get("content", ""), ctx, query
                )
                if summary:
                    response_data["response"] = summary
            
            return jsonify(response_data)
            
        except Exception as processing_error:
            logger.error(f"Query processing error: {processing_error}")
            return jsonify({
                "response": "I encountered an error processing your question. Please try asking in a different way.",
                "error": "processing_failed",
                "best_book": {
                    "title": "Error",
                    "content": "Sorry, I couldn't process your request at the moment."
                },
                "top_dsa": [],
                "video_suggestions": []
            })
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": "Please try again later"
        }), 500


@bp.route('/chat/<thread_id>')
def shared_chat(thread_id):
    """Handle shared chat links - supports public viewing"""
    try:
        # Validate thread ID format
        if not re.match(r'^thread_\d+_[a-zA-Z0-9]+$', thread_id):
            return render_template('index.html', error="Invalid chat link"), 404
        
        # For shared chats, pass limited user data
        user_data = {
            'is_authenticated': is_authenticated(),
            'shared_view': True,
            'thread_id': thread_id
        }
        
        if user_data['is_authenticated']:
            user_data.update({
                'user_id': session.get('google_id'),
                'name': session.get('name'),
                'email': session.get('email')
            })
        
        logger.info(f"Shared chat access: {thread_id} by {user_data.get('email', 'anonymous')}")
        return render_template('index.html', user=user_data)
        
    except Exception as e:
        logger.error(f"Shared chat error: {e}")
        return render_template('index.html', error="Chat not found"), 404

@bp.route('/logout', methods=['POST'])
def logout():
    """Enhanced logout endpoint"""
    try:
        user_email = session.get('email', 'anonymous')
        
        # Clear all session data
        session.clear()
        
        logger.info(f"User logged out: {user_email}")
        return jsonify({"success": True, "message": "Logged out successfully"})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@bp.route('/download', methods=['POST'])
@require_auth
def download_chat():
    """Download chat as PDF"""
    try:
        data = request.get_json()
        html_content = data.get('html_content', '')
        
        if not html_content:
            return jsonify({"error": "No content to download"}), 400
        
        # Generate PDF
        pdf_bytes = generate_pdf_from_html(html_content)
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="dsa-mentor-chat-{int(time.time())}.pdf"'
        
        logger.info(f"Chat downloaded by {session.get('email')}")
        return response
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({"error": "Download failed"}), 500

@bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Basic system checks
        checks = {
            'database': 'ok' if supabase else 'error',
            'session': 'ok' if session else 'error',
            'timestamp': time.time(),
            'version': '2.0.0'
        }
        
        status_code = 200 if all(v == 'ok' for v in checks.values() if v != checks['timestamp'] and v != checks['version']) else 500
        
        return jsonify(checks), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ===== ERROR HANDLERS =====

@bp.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "code": "BAD_REQUEST"}), 400

@bp.errorhandler(401) 
def unauthorized(error):
    return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401

@bp.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Access forbidden", "code": "FORBIDDEN"}), 403

@bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found", "code": "NOT_FOUND"}), 404

@bp.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({"error": "Rate limit exceeded", "code": "RATE_LIMIT"}), 429

@bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500
