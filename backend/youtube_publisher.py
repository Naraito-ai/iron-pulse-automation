"""
youtube_publisher.py — YouTube Data API v3 integration for YouTube Shorts.

NOTE: YouTube requires Google Cloud Console OAuth App setup and approval.
Once you have your credentials.json, implement the google-api-python-client logic here.
"""

import logging
from config import DEMO_MODE

logger = logging.getLogger(__name__)

def publish_to_youtube_shorts(video_path: str, title: str, description: str) -> dict:
    if DEMO_MODE:
        logger.info("[DEMO] Simulated YouTube Short publish: %s", title[:30])
        return {"youtube_url": "https://youtube.com/shorts/123", "status": "published"}
        
    logger.warning("YouTube API is not yet configured. Skipping cross-post.")
    return {"youtube_url": "", "status": "skipped", "error": "API not configured"}
