"""
tiktok_publisher.py — TikTok Content Posting API integration.

NOTE: TikTok requires a registered Developer App and OAuth approval.
Once you get your Developer App approved by TikTok, add the API keys to config.py
and implement the direct upload logic here.
"""

import logging
from config import DEMO_MODE

logger = logging.getLogger(__name__)

def publish_to_tiktok(video_url: str, caption: str, hashtags: str) -> dict:
    if DEMO_MODE:
        logger.info("[DEMO] Simulated TikTok publish: %s", caption[:30])
        return {"tiktok_url": "https://tiktok.com/@demo/video/123", "status": "published"}
        
    logger.warning("TikTok API is not yet configured. Skipping cross-post.")
    return {"tiktok_url": "", "status": "skipped", "error": "API not configured"}
