"""
instagram_publisher.py — Meta Graph API publisher.
Supports: Carousel feed posts (save-worthy content) + Reels (viral short content).
"""

import time
import logging
import os
import requests
from config import (
    INSTAGRAM_USER_ID, FACEBOOK_PAGE_ID,
    GRAPH_API_BASE, GRAPH_API_VERSION, DEMO_MODE
)

logger = logging.getLogger(__name__)

def _get_token() -> str:
    """Always read the latest token from env — picks up updates without restart."""
    return os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")

MAX_POLL_ATTEMPTS   = 30
POLL_INTERVAL_SECONDS = 4


# ─── Demo publisher ───────────────────────────────────────────────────────────

def _demo_publish(post_rank: int, post_format: str = "reel") -> dict:
    import random, string
    fake_id = "17841" + "".join(random.choices(string.digits, k=11))
    suffix  = "reel" if post_format == "reel" else "p"
    fake_link = f"https://www.instagram.com/{suffix}/{''.join(random.choices(string.ascii_letters + string.digits, k=11))}/"
    logger.info("[DEMO] Simulated %s publish #%d → %s", post_format, post_rank + 1, fake_id)
    return {"ig_media_id": fake_id, "ig_permalink": fake_link, "status": "published"}


# ─── Graph API helpers ────────────────────────────────────────────────────────

def _api_post(endpoint: str, params: dict) -> dict:
    params["access_token"] = _get_token()
    url  = f"{GRAPH_API_BASE}/{endpoint}"
    resp = requests.post(url, data=params, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API error: {data['error']}")
    return data


def _api_get(endpoint: str, params: dict = None) -> dict:
    p = params or {}
    p["access_token"] = _get_token()
    url  = f"{GRAPH_API_BASE}/{endpoint}"
    resp = requests.get(url, params=p, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API error: {data['error']}")
    return data


def _wait_for_container(container_id: str) -> bool:
    for attempt in range(MAX_POLL_ATTEMPTS):
        data   = _api_get(container_id, {"fields": "status_code,status"})
        status = data.get("status_code", "")
        logger.debug("Container %s status: %s (attempt %d)", container_id, status, attempt + 1)
        if status == "FINISHED":
            return True
        elif status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} failed: {status}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Container {container_id} timed out")


def _publish_container(container_id: str) -> str:
    for attempt in range(3):
        try:
            data     = _api_post(f"{INSTAGRAM_USER_ID}/media_publish", {"creation_id": container_id})
            media_id = data.get("id")
            if not media_id:
                raise RuntimeError(f"No media ID returned: {data}")
            return media_id
        except Exception as e:
            if attempt < 2 and "unknown error" in str(e).lower():
                logger.warning("Meta API error. Retrying in 20s...")
                time.sleep(20)
            else:
                raise
    raise RuntimeError("Failed to publish after retries")


def _create_reel_container(video_url: str, caption: str, cover_url: str = "") -> str:
    """Create a REELS media container with proper thumbnail (first frame = headline)."""
    logger.info("Creating REELS container")
    params = {
        "media_type":  "REELS",
        "video_url":   video_url,
        "caption":     caption[:2200],
        "thumb_offset": "0",   # Use frame at 0ms = first frame = headline overlay
    }
    data = _api_post(f"{INSTAGRAM_USER_ID}/media", params)
    logger.info("Raw Meta API response for REELS creation: %s", data)
    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"No reels container ID returned: {data}")
    return container_id


def _get_permalink(media_id: str) -> str:
    try:
        data = _api_get(media_id, {"fields": "permalink"})
        return data.get("permalink", "")
    except Exception:
        return ""


# ─── Carousel Feed Post ───────────────────────────────────────────────────────

def _create_child_container(image_url: str) -> str:
    """Create a child container for one carousel slide."""
    data = _api_post(f"{INSTAGRAM_USER_ID}/media", {
        "image_url":        image_url,
        "is_carousel_item": "true",
    })
    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"No child container ID: {data}")
    return container_id


def publish_carousel_post(image_urls: list, caption: str, hashtags: str, rank: int) -> dict:
    """
    Publish a multi-image carousel as an Instagram feed post.
    Best for: save-worthy lists, myth busters, transformation tips.
    """
    if DEMO_MODE or not _get_token() or not INSTAGRAM_USER_ID:
        return _demo_publish(rank, "carousel")

    full_caption = f"{caption}\n\n{hashtags}"

    try:
        # Step 1: Create child containers for each slide
        child_ids = []
        for url in image_urls[:10]:  # Instagram max 10 carousel items
            cid = _create_child_container(url)
            child_ids.append(cid)
            time.sleep(1)

        logger.info("Created %d child containers for carousel post #%d", len(child_ids), rank + 1)

        # Step 2: Create carousel container
        data = _api_post(f"{INSTAGRAM_USER_ID}/media", {
            "media_type":   "CAROUSEL",
            "children":     ",".join(child_ids),
            "caption":      full_caption[:2200],
        })
        container_id = data.get("id")
        if not container_id:
            raise RuntimeError(f"No carousel container ID: {data}")

        # Step 3: Wait for processing
        _wait_for_container(container_id)

        # Step 4: Publish
        media_id  = _publish_container(container_id)
        permalink = _get_permalink(media_id)

        logger.info("✅ Published CAROUSEL post #%d → %s", rank + 1, media_id)
        return {"ig_media_id": media_id, "ig_permalink": permalink, "status": "published"}

    except Exception as e:
        logger.error("❌ Failed carousel post #%d: %s", rank + 1, e)
        return {"ig_media_id": "", "ig_permalink": "", "status": "failed", "error": str(e)}


# ─── Reel Post ────────────────────────────────────────────────────────────────

def publish_reel_post(video_url: str, caption: str, hashtags: str, rank: int, cover_url: str = "") -> dict:
    """
    Publish a Reel with optional custom thumbnail cover.
    NOTE: No background music added — user should add trending audio in Instagram app.
    """
    if DEMO_MODE or not _get_token() or not INSTAGRAM_USER_ID:
        return _demo_publish(rank, "reel")

    full_caption = f"{caption}\n\n{hashtags}"

    try:
        # Create reel container (NO share_to_feed — Reels get more reach in Reels tab)
        container_id = _create_reel_container(video_url, full_caption, cover_url)

        # Wait for processing
        logger.info("Waiting for reel to process...")
        _wait_for_container(container_id)

        # Publish
        media_id  = _publish_container(container_id)
        permalink = _get_permalink(media_id)

        logger.info("✅ Published REEL post #%d → %s", rank + 1, media_id)
        return {"ig_media_id": media_id, "ig_permalink": permalink, "status": "published"}

    except Exception as e:
        logger.error("❌ Failed reel post #%d: %s", rank + 1, e)
        return {"ig_media_id": "", "ig_permalink": "", "status": "failed", "error": str(e)}


# ─── Smart Router — picks carousel or reel based on content type ──────────────

def publish_post(content: dict, rank: int) -> dict:
    """
    Route to the right publisher based on content format.
    - hot_take, quick_tip, meme_relatable → REEL
    - save_list, myth_buster, transformation → CAROUSEL feed post
    """
    post_format   = content.get("post_format", "reel")
    caption       = content.get("caption", "")
    hashtags      = content.get("hashtags", "")
    reel_thumb    = content.get("reel_thumb_path", "")
    image_server  = content.get("_image_server_base", "")

    # Build a public URL for the reel thumbnail if available
    cover_url = ""
    if reel_thumb and image_server:
        import os
        fname = os.path.basename(reel_thumb)
        cover_url = f"{image_server}/generated/{fname}"

    if post_format == "carousel":
        image_urls = content.get("image_urls", [])
        if not image_urls:
            logger.warning("No image URLs for carousel post #%d, falling back to reel", rank + 1)
            return publish_reel_post(content.get("reel_url", ""), caption, hashtags, rank)
        logger.info("Publishing CAROUSEL post #%d (save-worthy content)...", rank + 1)
        return publish_carousel_post(image_urls, caption, hashtags, rank)
    else:
        reel_url = content.get("reel_url", "")
        if not reel_url:
            logger.warning("No reel URL for reel post #%d, falling back to carousel", rank + 1)
            return publish_carousel_post(content.get("image_urls", []), caption, hashtags, rank)
        logger.info("Publishing REEL post #%d (viral content)...", rank + 1)
        return publish_reel_post(reel_url, caption, hashtags, rank, cover_url=cover_url)


def publish_all_posts(content_list: list[dict]) -> list[dict]:
    """Publish all posts using the smart router (carousel or reel per content type)."""
    results = []
    for i, content in enumerate(content_list):
        result = publish_post(content, i)
        results.append({**content, **result})
        if i < len(content_list) - 1:
            time.sleep(8)  # Rate limit buffer
    return results
