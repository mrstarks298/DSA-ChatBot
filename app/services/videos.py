import re
from typing import List, Dict, Optional
from ..extensions import supabase, logger

def extract_youtube_id(url: str) -> Optional[str]:
    if not url or not isinstance(url, str) or url == '#':
        return None
    url = url.strip()
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match and match.group(1):
            return match.group(1)
    logger.warning(f"Could not extract YouTube ID from URL: {url}")
    return None

def get_videos(topic: str, limit: int = 5) -> List[Dict]:
    if not topic or not topic.strip():
        logger.warning("Empty topic provided to get_videos")
        return []

    if not supabase:
        logger.error("Supabase client not initialized")
        return []

    try:
        # Sanitize topic to prevent injection
        sanitized_topic = topic.strip().replace("'", "''").replace('"', '""')
        
        query = (
            supabase.table("video_suggestions")
            .select("*")
            .or_(
                f"topic.ilike.%{sanitized_topic}%,title.ilike.%{sanitized_topic}%,subtopic.ilike.%{sanitized_topic}%,description.ilike.%{sanitized_topic}%"
            )
            .limit(limit)
        )
        result = query.execute()
        videos = result.data or []
        out = []

        for v in videos:
            video_url = v.get('video_url') or v.get('youtube_link') or '#'
            vid = extract_youtube_id(video_url)
            embed_url = f"https://www.youtube.com/embed/{vid}" if vid else '#'
            thumbnail_url = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg" if vid else 'https://via.placeholder.com/320x180/cccccc/666666?text=Video'

            out.append({
                'id': v.get('id'),
                'title': v.get('title', 'DSA Tutorial'),
                'topic': v.get('topic', 'DSA'),
                'subtopic': v.get('subtopic', ''),
                'description': v.get('description') or v.get('subtopic') or 'Learn this DSA concept',
                'difficulty': v.get('difficulty', 'Beginner'),
                'duration': v.get('duration', '10:00'),
                'embed_url': embed_url,
                'video_url': video_url,
                'thumbnail_url': thumbnail_url,
            })
        return out

    except Exception as e:
        logger.error(f"Supabase videos error: {e}")
        return []
