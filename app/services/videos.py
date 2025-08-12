import re
from ..extensions import supabase, logger

def extract_youtube_id(url: str) -> str | None:
    if not url or url == '#':
        return None
    url = url.strip()
    pats = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)'
    ]
    for p in pats:
        m = re.search(p, url)
        if m and m.group(1):
            return m.group(1)
    logger.warning(f"Could not extract YouTube ID from URL: {url}")
    return None

def get_videos(topic: str, limit: int = 5):
    try:
        result = supabase.table("video_suggestions").select("*").or_(
            f"topic.ilike.%{topic}%,title.ilike.%{topic}%,subtopic.ilike.%{topic}%,description.ilike.%{topic}%"
        ).limit(limit).execute()
        videos = result.data or []
        out = []
        for v in videos:
            video_url = v.get('video_url', v.get('youtube_link', '#'))
            vid = extract_youtube_id(video_url)
            embed_url = f"https://www.youtube.com/embed/{vid}" if vid else '#'
            out.append({
                'id': v.get('id'),
                'title': v.get('title', 'DSA Tutorial'),
                'topic': v.get('topic', 'DSA'),
                'subtopic': v.get('subtopic', ''),
                'description': v.get('description', v.get('subtopic', 'Learn this DSA concept')),
                'difficulty': v.get('difficulty', 'Beginner'),
                'duration': v.get('duration', '10:00'),
                'embed_url': embed_url,
                'video_url': video_url,
                'youtube_link': video_url,
                'thumbnail_url': f"https://img.youtube.com/vi/{vid}/mqdefault.jpg" if vid else 'https://via.placeholder.com/320x180/cccccc/666666?text=Video',
            })
        return out
    except Exception as e:
        logger.error(f"Supabase videos error: {e}")
        return []
