import time
from . import bp
import logging
import uuid
import json
from datetime import datetime
from flask import render_template, jsonify, request, session, make_response, redirect, url_for, Response, stream_with_context
from ..extensions import supabase
logger = logging.getLogger("dsa-mentor")

from ..services.intent import (
    classify_query_with_groq, generate_response_by_intent,
    QueryProcessor, enhanced_summarize_with_context
)
from ..services.embeddings import fetch_text_df, fetch_qa_df, _to_array
from ..services.search import best_text_for_query, top_qa_for_query
from ..services.videos import get_videos
from ..services.pdf import generate_pdf_from_html

def is_authenticated():
    return 'google_id' in session

def get_current_user_id():
    return session.get('google_id')

def get_current_user():
    return {
        'is_authenticated': is_authenticated(),
        'name': session.get('name'),
        'email': session.get('email'),
        'google_id': session.get('google_id')
    }

@bp.route("/")
def index():
    user_data = get_current_user()
    logger.info(f"Index route accessed - User authenticated: {user_data['is_authenticated']}, Name: {user_data.get('name', 'N/A')}")
    return render_template("index.html", user=user_data, is_shared_view=False, shared_thread_id=None)

@bp.route("/chat/<thread_id>")
def shared_chat(thread_id):
    """Render the chat UI in shared view mode with a preselected thread_id.

    The frontend will use this to populate the share link and optionally load
    messages if the user is authenticated.
    """
    user_data = get_current_user()
    logger.info(f"Shared chat route accessed - Thread: {thread_id}, User authenticated: {user_data['is_authenticated']}")
    # Validate basic thread_id format
    if not thread_id or not thread_id.startswith("thread_"):
        thread_id = None
    return render_template(
        "index.html",
        user=user_data,
        is_shared_view=True,
        shared_thread_id=thread_id,
    )

# ... thread helpers unchanged ...

@bp.route("/query", methods=["POST"])
def handle_query():
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json() or {}
        raw_query = (data.get("query") or "").strip()
        thread_id = data.get('thread_id', '')
        
        if not raw_query:
            return jsonify({"error": "Missing query"}), 400
            
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        if thread_id and not (thread_id := thread_id).startswith('thread_'):
            return jsonify({'error': 'Invalid thread ID'}), 400
        if not thread_id:
            thread_id = f"thread_{str(uuid.uuid4())}"

        user_id = get_current_user_id()
        save_message(user_id, thread_id, 'user', raw_query)

        classification = classify_query_with_groq(raw_query)
        logger.info(f"Query: '{raw_query}' -> Classification: {classification}")

        contextual = generate_response_by_intent(classification, raw_query)
        if contextual:
            save_message(user_id, thread_id, 'assistant', contextual)
            response_data = {**contextual, "query_info": {"original_query": raw_query, "classification": classification}, "thread_id": thread_id}
            return jsonify(response_data)

        if classification.get("is_dsa", False):
            processor = QueryProcessor()
            cleaned = processor.clean_and_normalize_query(raw_query)
            ctx = processor.extract_dsa_context(cleaned)
            text_df = fetch_text_df()
            qa_df = fetch_qa_df()
            best_content = best_text_for_query(cleaned, text_df)
            summary = enhanced_summarize_with_context(best_content.get("content",""), ctx, raw_query)
            top_qa = top_qa_for_query(cleaned, qa_df, k=5)
            videos = get_videos(cleaned, limit=3) or []
            if not videos and ctx.get('topics'):
                for topic in ctx['topics'][:2]:
                    videos.extend(get_videos(topic, limit=2))
                    if len(videos) >= 3:
                        break
            if not videos:
                for kw in ['algorithm','data structure','programming','coding']:
                    if kw in cleaned:
                        videos.extend(get_videos(kw, limit=2))
                        break
            videos = videos[:3]

            response_data = {
                "best_book": {
                    "title": (best_content.get("content","DSA Content")[:50] + "...") if best_content.get("content") else "DSA Learning Content",
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

        response_data = {
            "best_book": {"title": "I'm not sure how to help with that 🤔",
                          "content": "I specialize in DSA. Try: 'Explain binary search'."},
            "summary": "Please ask me about a specific DSA topic!",
            "top_dsa": [], "video_suggestions": [],
            "query_info": {"original_query": raw_query, "classification": classification},
            "thread_id": thread_id
        }
        save_message(user_id, thread_id, 'assistant', response_data)
        return jsonify(response_data)

    except Exception as e:
        logger.exception("Error handling query")
        return jsonify({
            "error":"Internal server error",
            "best_book":{"title":"Error","content":"Sorry, something went wrong. Please try again."},
            "summary":"An error occurred processing your request.",
            "top_dsa": [], "video_suggestions":[]
        }), 500

# NEW: streaming endpoint
def _sse_event(name, data):
    return f"event: {name}\ndata: {data}\n\n"

@bp.route("/query-stream", methods=["POST"])
def handle_query_stream():
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json() or {}
    raw_query = (data.get("query") or "").strip()
    thread_id = data.get("thread_id") or f"thread_{str(uuid.uuid4())}"
    
    if not raw_query:
        return jsonify({"error":"Missing query"}), 400
        
    if not supabase:
        return jsonify({"error": "Database not available"}), 500
    if thread_id and not (thread_id := thread_id).startswith("thread_"):
        return jsonify({"error":"Invalid thread ID"}), 400

    user_id = get_current_user_id()
    save_message(user_id, thread_id, 'user', raw_query)

    def generate():
        try:
            classification = classify_query_with_groq(raw_query)
            yield _sse_event("meta", json.dumps({"thread_id": thread_id, "classification": classification}))

            if classification.get("is_dsa", False):
                processor = QueryProcessor()
                cleaned = processor.clean_and_normalize_query(raw_query)
                ctx = processor.extract_dsa_context(cleaned)
                text_df = fetch_text_df()
                qa_df = fetch_qa_df()
                best_content = best_text_for_query(cleaned, text_df)
                summary = enhanced_summarize_with_context(best_content.get("content",""), ctx, raw_query)
                summary_text = summary or "Based on your query about DSA concepts, here's the most relevant information."

                # stream summary
                yield _sse_event("chunk", json.dumps({"text": f"📝 Summary:\n{summary_text}\n\n"}))

                # stream detailed content in paragraphs
                detail = best_content.get("content", "") or ""
                for para in (detail.split("\n\n") or [detail]):
                    p = para.strip()
                    if p:
                        yield _sse_event("chunk", json.dumps({"text": p + "\n\n"}))

                top_qa = top_qa_for_query(cleaned, qa_df, k=5)
                if isinstance(top_qa, list) and top_qa:
                    yield _sse_event("chunk", json.dumps({"text": "📝 Related Practice Problems:\n"}))
                    for qa in top_qa:
                        line = f"- {qa.get('section','DSA')}: {qa.get('question','')}\n"
                        yield _sse_event("chunk", json.dumps({"text": line}))
                    yield _sse_event("chunk", json.dumps({"text": "\n"}))

                videos = get_videos(cleaned, limit=3) or []
                if not videos and ctx.get('topics'):
                    for topic in ctx['topics'][:2]:
                        videos.extend(get_videos(topic, limit=2))
                        if len(videos) >= 3: 
                            break
                videos = videos[:3]
                if videos:
                    yield _sse_event("chunk", json.dumps({"text": "🎥 Recommended Videos:\n"}))
                    for v in videos:
                        t = v.get('title','Video')
                        d = v.get('difficulty','')
                        u = v.get('duration','')
                        yield _sse_event("chunk", json.dumps({"text": f"- {t} {('-  ' + d) if d else ''} {('-  ' + u) if u else ''}\n"}))
                    yield _sse_event("chunk", json.dumps({"text": "\n"}))

                response_data = {
                    "best_book": {
                        "title": (best_content.get("content","DSA Content")[:50] + "...") if best_content.get("content") else "DSA Learning Content",
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
                response_data = {
                    "best_book": {"title": "I'm not sure how to help with that 🤔",
                                  "content": "I specialize in DSA. Try: 'Explain binary search'."},
                    "summary": "Please ask me about a specific DSA topic!",
                    "top_dsa": [], "video_suggestions": [],
                    "query_info": {"original_query": raw_query, "classification": classification},
                    "thread_id": thread_id
                }
                yield _sse_event("chunk", json.dumps({"text": "I specialize in DSA. Try: 'Explain binary search'.\n"}))

            # send final json for rich render
            yield _sse_event("final_json", json.dumps(response_data))

            # persist assistant message (store JSON)
            save_message(user_id, thread_id, 'assistant', response_data)

            yield _sse_event("done", "{}")

        except Exception as e:
            logger.exception("Streaming error")
            yield _sse_event("error", json.dumps({"error":"Internal server error"}))
            yield _sse_event("done", "{}")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return Response(stream_with_context(generate()), headers=headers)

@bp.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json() or {}
        html_content = data.get("html")
        thread_id = data.get('thread_id', 'unknown')

        if not html_content:
            return jsonify({"error":"Missing HTML content"}), 400
            
        if not html_content.strip():
            return jsonify({"error":"Empty HTML content"}), 400

        html_content = html_content.replace('@import url(', '<!-- @import url(')
        pdf = generate_pdf_from_html(html_content)

        resp = make_response(pdf)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'attachment; filename=dsa-mentor-{thread_id}-{int(time.time())}.pdf'
        return resp
    except Exception as e:
        logger.exception("PDF generation error")
        return jsonify({"error": f"PDF generation failed: {e}"}), 500

def save_message(user_id, thread_id, sender, content):
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return None
            
        # ensure JSON serializable
        stored = content
        if not isinstance(stored, (dict, list, str, int, float, type(None))):
            stored = json.loads(json.dumps(content, default=str))
        result = supabase.table('chat_messages').insert({
            'user_id': user_id,
            'thread_id': thread_id,
            'sender': sender,
            'content': stored
        }).execute()
        if result.data:
            logger.info(f"Message saved to thread {thread_id}")
            return result.data
        logger.error(f"Failed to save message: {result}")
        return None
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return None
        
def load_chat_thread(user_id, thread_id):
    """Load a chat thread from Supabase database"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return []
            
        result = supabase.table('chat_messages')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('thread_id', thread_id)\
            .order('timestamp')\
            .execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"Error loading chat thread: {e}")
        return []

def get_user_threads(user_id):
    """Get all thread IDs for a user from Supabase with better performance"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return []
            
        # Get distinct thread_ids with their latest timestamp
        result = supabase.table('chat_messages')\
            .select('thread_id, timestamp')\
            .eq('user_id', user_id)\
            .order('timestamp', desc=True)\
            .execute()
        
        if result.data:
            # Get unique thread_ids while preserving latest-first order
            seen = set()
            unique_threads = []
            for row in result.data:
                thread_id = row['thread_id']
                if thread_id not in seen:
                    seen.add(thread_id)
                    unique_threads.append(thread_id)
            return unique_threads
        return []
    except Exception as e:
        logger.error(f"Error getting user threads: {e}")
        return []
def get_thread_summary(user_id, thread_id):
    """Get thread summary for display in thread list"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return {
                'thread_id': thread_id,
                'created_at': None,
                'updated_at': None,
                'message_count': 0,
                'preview': 'Error loading preview'
            }
            
        # Get first user message for preview
        first_msg = supabase.table('chat_messages')\
            .select('content, timestamp')\
            .eq('user_id', user_id)\
            .eq('thread_id', thread_id)\
            .eq('sender', 'user')\
            .order('timestamp')\
            .limit(1)\
            .execute()
        
        # Get message count and last timestamp
        stats = supabase.table('chat_messages')\
            .select('timestamp')\
            .eq('user_id', user_id)\
            .eq('thread_id', thread_id)\
            .execute()
        
        preview_content = ""
        created_at = None
        
        if first_msg.data:
            msg = first_msg.data[0]
            created_at = msg['timestamp']
            content = msg['content']
            
            if isinstance(content, str):
                preview_content = content
            elif isinstance(content, dict):
                preview_content = content.get('query', '') or str(content)
        
        message_count = len(stats.data) if stats.data else 0
        updated_at = max([msg['timestamp'] for msg in stats.data]) if stats.data else created_at
        
        return {
            'thread_id': thread_id,
            'created_at': created_at,
            'updated_at': updated_at,
            'message_count': message_count,
            'preview': (preview_content[:100] + '...') if len(preview_content) > 100 else preview_content
        }
        
    except Exception as e:
        logger.error(f"Error getting thread summary: {e}")
        return {
            'thread_id': thread_id,
            'created_at': None,
            'updated_at': None,
            'message_count': 0,
            'preview': 'Error loading preview'
        }

# API endpoints for thread management
@bp.route('/api/thread/<thread_id>')
def get_thread(thread_id):
    """Get messages for a specific thread"""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
            
        if not thread_id or not thread_id.strip():
            return jsonify({'error': 'Invalid thread ID'}), 400
            
        user_id = get_current_user_id()
        messages = load_chat_thread(user_id, thread_id)
        
        return jsonify({
            'thread_id': thread_id,
            'messages': messages
        })
        
    except Exception as e:
        logger.error(f"Error getting thread: {e}")
        return jsonify({'error': 'Failed to load thread'}), 500

@bp.route('/api/threads')
def get_user_thread_list():
    """Get all threads for the current user - UPDATED VERSION"""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
            
        user_id = get_current_user_id()
        thread_ids = get_user_threads(user_id)
        
        # Get summary info for each thread
        threads = []
        for thread_id in thread_ids:
            thread_summary = get_thread_summary(user_id, thread_id)
            threads.append(thread_summary)
        
        # Already sorted by latest first from get_user_threads()
        return jsonify({'threads': threads})
        
    except Exception as e:
        logger.error(f"Error getting threads: {e}")
        return jsonify({'error': 'Failed to load threads'}), 500

# Your existing routes remain the same
# Debug routes removed for production security

@bp.route("/videos/<topic>")
def videos_topic(topic):
    if not topic or not topic.strip():
        return jsonify({"error": "Invalid topic"}), 400
        
    vids = get_videos(topic, limit=5)
    if not vids:
        general = get_videos("introduction", limit=3)
        return jsonify({"topic": topic, "videos": general, "message": f"No specific videos for '{topic}', showing general."})
    return jsonify({"topic": topic, "videos": vids, "total_count": len(vids)})

@bp.route("/videos/search")
def videos_search():
    q = (request.args.get("q") or "").strip()
    difficulty = (request.args.get("difficulty") or "").strip()
    limit = int(request.args.get("limit", 10))
    
    if not q:
        return jsonify({"error":"Missing search query"}), 400
        
    if limit <= 0 or limit > 50:
        return jsonify({"error":"Invalid limit parameter"}), 400
    vids = get_videos(q, limit=limit)
    if difficulty:
        vids = [v for v in vids if v.get("difficulty") == difficulty]
    return jsonify({"query": q, "difficulty_filter": difficulty, "videos": vids, "total_count": len(vids)})

@bp.route("/test-videos")
def test_videos():
    try:
        vids = get_videos("algorithm", limit=3)
        return jsonify({"status":"success","video_count": len(vids),"sample_videos": vids[:2] if vids else []})
    except Exception as e:
        logger.error(f"Test videos error: {e}")
        return jsonify({"status":"error","error": str(e)}), 500

# Debug routes removed for production security
