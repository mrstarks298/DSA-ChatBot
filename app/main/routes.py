# FIXED app/main/routes.py - Input Validation and Error Handling

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

# ADDED: Input validation and security functions
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
        logger.warning(f"Potentially malicious query blocked: {query[:50]}...")
        return False, "Query contains potentially unsafe content"
    
    # Check for excessive special characters (might indicate injection attempt)
    special_char_count = len(re.findall(r'[<>"\'\(\)\{\}\[\];]', query))
    if special_char_count > len(query) * 0.3:  # More than 30% special chars
        logger.warning(f"Query with excessive special characters: {query[:50]}...")
        return False, "Query format appears suspicious"
    
    # SQL injection pattern detection (basic)
    sql_patterns = [
        r'\b(union|select|insert|update|delete|drop|create|alter)\b',
        r'--|\*\/|\*\*',
        r'\bor\s+1=1\b|\band\s+1=1\b'
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential SQL injection attempt: {query[:50]}...")
            return False, "Query contains suspicious patterns"
    
    return True, query

def validate_thread_id(thread_id):
    """Validate thread ID format"""
    if not thread_id:
        return True, f"thread_{str(uuid.uuid4())}"  # Generate new one
    
    if not isinstance(thread_id, str):
        return False, "Invalid thread ID format"
    
    if not thread_id.startswith('thread_'):
        return False, "Invalid thread ID prefix"
    
    if len(thread_id) > 50:  # Reasonable length limit
        return False, "Thread ID too long"
    
    # Check for valid UUID part
    uuid_part = thread_id[7:]  # Remove 'thread_' prefix
    if not re.match(r'^[a-f0-9-]+$', uuid_part):
        return False, "Invalid thread ID format"
    
    return True, thread_id

def is_authenticated():
    """Check if user is authenticated"""
    return 'google_id' in session

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('google_id')

def get_current_user():
    """Get current user data"""
    return {
        'is_authenticated': is_authenticated(),
        'name': session.get('name'),
        'email': session.get('email'),
        'google_id': session.get('google_id')
    }

# IMPROVED: Better message saving with error handling
def save_message(user_id, thread_id, role, content):
    """Save message to database with improved error handling"""
    if not supabase:
        logger.error("Cannot save message - Supabase not initialized")
        return False
    
    try:
        # Serialize content if it's not a string
        if not isinstance(content, str):
            content = json.dumps(content)
        
        message_data = {
            'user_id': user_id,
            'thread_id': thread_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        result = supabase.table('messages').insert(message_data).execute()
        logger.info(f"Message saved for user {user_id}, thread {thread_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return False

# ROUTES
@bp.route("/")
def index():
    """Main index route"""
    user_data = get_current_user()
    logger.info(f"Index accessed - User: {user_data.get('email', 'anonymous')}")
    
    return render_template("index.html", 
                         user=user_data, 
                         is_shared_view=False, 
                         shared_thread_id=None)

@bp.route("/chat/<thread_id>")
def shared_chat(thread_id):
    """Shared chat view with thread ID validation"""
    user_data = get_current_user()
    logger.info(f"Shared chat accessed - Thread: {thread_id}, User: {user_data.get('email', 'anonymous')}")
    
    # Validate thread ID format
    is_valid, validated_thread_id = validate_thread_id(thread_id)
    if not is_valid:
        logger.warning(f"Invalid thread ID format: {thread_id}")
        thread_id = None
    else:
        thread_id = validated_thread_id
    
    return render_template("index.html",
                         user=user_data,
                         is_shared_view=True,
                         shared_thread_id=thread_id)

@bp.route("/query", methods=["POST"])
def handle_query():
    """IMPROVED: Main query handler with comprehensive validation"""
    try:
        # Authentication check
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        # Input validation
        data = request.get_json() or {}
        is_valid, result = validate_and_sanitize_query(data)
        
        if not is_valid:
            logger.warning(f"Query validation failed: {result}")
            return jsonify({"error": result}), 400
        
        raw_query = result
        
        # Thread ID validation
        thread_id = data.get('thread_id', '')
        is_valid_thread, validated_thread = validate_thread_id(thread_id)
        
        if not is_valid_thread:
            logger.warning(f"Thread ID validation failed: {validated_thread}")
            return jsonify({'error': 'Invalid thread ID'}), 400
        
        thread_id = validated_thread

        # Database availability check
        if not supabase:
            logger.error("Database not available")
            return jsonify({"error": "Database service unavailable"}), 503

        # Process query
        user_id = get_current_user_id()
        
        # Save user message
        save_message(user_id, thread_id, 'user', raw_query)
        
        # Classify query with error handling
        try:
            classification = classify_query_with_groq(raw_query)
        except Exception as e:
            logger.error(f"Classification error: {e}")
            classification = {"type": "dsa_specific", "confidence": 0.5, "is_dsa": True}
        
        logger.info(f"Query: '{raw_query[:50]}...' -> Classification: {classification.get('type')}")

        # Handle contextual responses (greetings, etc.)
        contextual = generate_response_by_intent(classification, raw_query)
        if contextual:
            save_message(user_id, thread_id, 'assistant', contextual)
            response_data = {
                **contextual,
                "query_info": {
                    "original_query": raw_query,
                    "classification": classification
                },
                "thread_id": thread_id
            }
            return jsonify(response_data)

        # Handle DSA-specific queries
        if classification.get("is_dsa", False):
            try:
                processor = QueryProcessor()
                cleaned = processor.clean_and_normalize_query(raw_query)
                ctx = processor.extract_dsa_context(cleaned)
                
                # Fetch data with error handling
                text_df = fetch_text_df()
                qa_df = fetch_qa_df()
                
                if text_df.empty:
                    logger.warning("No text embeddings available")
                
                if qa_df.empty:
                    logger.warning("No QA resources available")
                
                # Search for best content
                best_content = best_text_for_query(cleaned, text_df)
                if "error" in best_content:
                    logger.warning(f"Content search error: {best_content['error']}")
                    best_content = {"content": "No relevant content found", "similarity": 0.0}
                
                # Generate summary
                summary = enhanced_summarize_with_context(
                    best_content.get("content", ""), ctx, raw_query
                )
                
                # Get related Q&A
                top_qa = top_qa_for_query(cleaned, qa_df, k=5) or []
                
                # Get video suggestions
                videos = get_videos(cleaned, limit=3) or []
                
                # Fallback video search if no results
                if not videos and ctx.get('topics'):
                    for topic in ctx['topics'][:2]:
                        videos.extend(get_videos(topic, limit=2) or [])
                        if len(videos) >= 3:
                            break
                
                # Final fallback for videos
                if not videos:
                    for keyword in ['algorithm', 'data structure', 'programming', 'coding']:
                        if keyword in cleaned.lower():
                            videos.extend(get_videos(keyword, limit=2) or [])
                            break
                
                videos = videos[:3]  # Limit to 3 videos
                
                response_data = {
                    "best_book": {
                        "title": (best_content.get("content", "DSA Content")[:50] + "...") 
                                if best_content.get("content") else "DSA Learning Content",
                        "content": best_content.get("content", "Content not found"),
                        "similarity": best_content.get("similarity", 0.0)
                    },
                    "summary": summary or "Based on your query about DSA concepts, here's the most relevant information.",
                    "top_dsa": top_qa if isinstance(top_qa, list) else [],
                    "video_suggestions": videos if isinstance(videos, list) else [],
                    "query_info": {
                        "original_query": raw_query,
                        "cleaned_query": cleaned,
                        "classification": classification,
                        "context": ctx
                    },
                    "thread_id": thread_id
                }
                
                save_message(user_id, thread_id, 'assistant', response_data)
                return jsonify(response_data)
                
            except Exception as e:
                logger.exception(f"DSA query processing error: {e}")
                # Return graceful error response
                error_response = {
                    "best_book": {
                        "title": "Processing Error 🔧",
                        "content": "I encountered an error while processing your DSA query. Please try rephrasing your question or try again."
                    },
                    "summary": "Error occurred while processing your request.",
                    "top_dsa": [],
                    "video_suggestions": [],
                    "query_info": {
                        "original_query": raw_query,
                        "classification": classification
                    },
                    "thread_id": thread_id
                }
                save_message(user_id, thread_id, 'assistant', error_response)
                return jsonify(error_response)

        # Non-DSA queries
        response_data = {
            "best_book": {
                "title": "I'm not sure how to help with that 🤔",
                "content": "I specialize in DSA (Data Structures & Algorithms). Try asking: 'Explain binary search' or 'How do sorting algorithms work?'"
            },
            "summary": "Please ask me about a specific DSA topic!",
            "top_dsa": [],
            "video_suggestions": [],
            "query_info": {
                "original_query": raw_query,
                "classification": classification
            },
            "thread_id": thread_id
        }
        
        save_message(user_id, thread_id, 'assistant', response_data)
        return jsonify(response_data)

    except Exception as e:
        logger.exception("Unexpected error in handle_query")
        
        # Return user-friendly error
        return jsonify({
            "error": "Internal server error",
            "best_book": {
                "title": "Oops! Something went wrong 😅",
                "content": "I encountered an unexpected error. Please try again, and if the problem persists, contact support."
            },
            "summary": "An unexpected error occurred while processing your request.",
            "top_dsa": [],
            "video_suggestions": []
        }), 500

# ADDED: Rate limiting helper (basic implementation)
_request_counts = {}  # In production, use Redis or similar

def check_rate_limit():
    """Basic rate limiting implementation"""
    if not current_app.config.get('DEBUG'):
        user_id = get_current_user_id()
        now = time.time()
        minute_key = f"{user_id}_{int(now // 60)}"
        
        count = _request_counts.get(minute_key, 0)
        max_requests = current_app.config.get('RATE_LIMIT_PER_MINUTE', 30)
        
        if count >= max_requests:
            return False
        
        _request_counts[minute_key] = count + 1
        
        # Clean old entries
        for key in list(_request_counts.keys()):
            if int(key.split('_')[-1]) < int(now // 60) - 5:  # Keep last 5 minutes
                del _request_counts[key]
    
    return True

@bp.route("/query-stream", methods=["POST"])
def handle_query_stream():
    """IMPROVED: Streaming query handler with rate limiting"""
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    # Rate limiting
    if not check_rate_limit():
        return jsonify({'error': 'Rate limit exceeded. Please wait before making another request.'}), 429
    
    data = request.get_json() or {}
    
    # Input validation
    is_valid, result = validate_and_sanitize_query(data)
    if not is_valid:
        return jsonify({"error": result}), 400
    
    raw_query = result
    
    # Thread validation
    thread_id = data.get("thread_id") or f"thread_{str(uuid.uuid4())}"
    is_valid_thread, validated_thread = validate_thread_id(thread_id)
    
    if not is_valid_thread:
        return jsonify({"error": "Invalid thread ID"}), 400
    
    thread_id = validated_thread

    if not supabase:
        return jsonify({"error": "Database not available"}), 500

    user_id = get_current_user_id()
    save_message(user_id, thread_id, 'user', raw_query)

    def generate():
        try:
            classification = classify_query_with_groq(raw_query)
            yield _sse_event("meta", json.dumps({
                "thread_id": thread_id, 
                "classification": classification
            }))

            if classification.get("is_dsa", False):
                # DSA processing with streaming
                processor = QueryProcessor()
                cleaned = processor.clean_and_normalize_query(raw_query)
                ctx = processor.extract_dsa_context(cleaned)
                
                text_df = fetch_text_df()
                qa_df = fetch_qa_df()
                
                best_content = best_text_for_query(cleaned, text_df)
                summary = enhanced_summarize_with_context(
                    best_content.get("content", ""), ctx, raw_query
                )
                
                summary_text = summary or "Based on your DSA query, here's relevant information."
                
                # Stream summary
                yield _sse_event("chunk", json.dumps({
                    "text": f"📝 Summary:\n{summary_text}\n\n"
                }))
                
                # Stream detailed content
                detail = best_content.get("content", "") or ""
                for para in (detail.split("\n\n") or [detail]):
                    p = para.strip()
                    if p:
                        yield _sse_event("chunk", json.dumps({"text": p + "\n\n"}))
                
                # Stream Q&A suggestions
                top_qa = top_qa_for_query(cleaned, qa_df, k=5)
                if isinstance(top_qa, list) and top_qa:
                    yield _sse_event("chunk", json.dumps({
                        "text": "📝 Related Practice Problems:\n"
                    }))
                    
                    for qa in top_qa:
                        line = f"- {qa.get('section', 'DSA')}: {qa.get('question', '')}\n"
                        yield _sse_event("chunk", json.dumps({"text": line}))
                    
                    yield _sse_event("chunk", json.dumps({"text": "\n"}))
                
                # Stream video suggestions
                videos = get_videos(cleaned, limit=3) or []
                if not videos and ctx.get('topics'):
                    for topic in ctx['topics'][:2]:
                        videos.extend(get_videos(topic, limit=2) or [])
                        if len(videos) >= 3:
                            break
                
                videos = videos[:3]
                
                if videos:
                    yield _sse_event("chunk", json.dumps({
                        "text": "🎥 Recommended Videos:\n"
                    }))
                    
                    for v in videos:
                        title = v.get('title', 'Video')
                        difficulty = v.get('difficulty', '')
                        duration = v.get('duration', '')
                        
                        video_line = f"- {title}"
                        if difficulty:
                            video_line += f" - {difficulty}"
                        if duration:
                            video_line += f" - {duration}"
                        video_line += "\n"
                        
                        yield _sse_event("chunk", json.dumps({"text": video_line}))
                    
                    yield _sse_event("chunk", json.dumps({"text": "\n"}))
                
                # Final response data
                response_data = {
                    "best_book": {
                        "title": (best_content.get("content", "DSA Content")[:50] + "...") 
                                if best_content.get("content") else "DSA Learning Content",
                        "content": best_content.get("content", "Content not found"),
                        "similarity": best_content.get("similarity", 0.0)
                    },
                    "summary": summary_text,
                    "top_dsa": top_qa if isinstance(top_qa, list) else [],
                    "video_suggestions": videos if isinstance(videos, list) else [],
                    "query_info": {
                        "original_query": raw_query,
                        "cleaned_query": cleaned,
                        "classification": classification,
                        "context": ctx
                    },
                    "thread_id": thread_id
                }
            else:
                # Non-DSA response
                response_data = {
                    "best_book": {
                        "title": "I'm not sure how to help with that 🤔",
                        "content": "I specialize in DSA. Try: 'Explain binary search'."
                    },
                    "summary": "Please ask me about a specific DSA topic!",
                    "top_dsa": [],
                    "video_suggestions": [],
                    "query_info": {
                        "original_query": raw_query,
                        "classification": classification
                    },
                    "thread_id": thread_id
                }
                
                yield _sse_event("chunk", json.dumps({
                    "text": "I specialize in DSA. Try: 'Explain binary search'.\n"
                }))

            # Send final JSON data
            yield _sse_event("final_json", json.dumps(response_data))
            
            # Save assistant message
            save_message(user_id, thread_id, 'assistant', response_data)
            
            yield _sse_event("done", "{}")

        except Exception as e:
            logger.exception("Streaming error")
            yield _sse_event("error", json.dumps({"error": "Internal server error"}))
            yield _sse_event("done", "{}")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }

    return Response(stream_with_context(generate()), headers=headers)

def _sse_event(name, data):
    """Helper for Server-Sent Events formatting"""
    return f"event: {name}\ndata: {data}\n\n"

@bp.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    """IMPROVED: PDF generation with validation"""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json() or {}
        html_content = data.get("html")
        thread_id = data.get('thread_id', 'unknown')

        if not html_content:
            return jsonify({"error": "Missing HTML content"}), 400

        if not html_content.strip():
            return jsonify({"error": "Empty HTML content"}), 400

        # Basic HTML validation
        if len(html_content) > 1000000:  # 1MB limit
            return jsonify({"error": "HTML content too large"}), 400

        # Clean HTML content (remove potential XSS)
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'javascript:', '', html_content, flags=re.IGNORECASE)
        html_content = html_content.replace('@import url(', '')

        # Generate PDF
        try:
            pdf_bytes = generate_pdf_from_html(html_content)
            
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="dsa_chat_{thread_id}.pdf"'
            
            logger.info(f"PDF generated for thread {thread_id}")
            return response
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return jsonify({"error": "PDF generation failed"}), 500

    except Exception as e:
        logger.exception("PDF generation error")
        return jsonify({"error": "Internal server error"}), 500
