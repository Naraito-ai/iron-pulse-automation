"""
main.py — Orchestrator and scheduler for the AI Instagram Automation System.
Runs the complete daily pipeline and manages APScheduler.
"""

import os
import sys
import time
import logging
import logging.config
from datetime import datetime
from pathlib import Path

# Ensure backend is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SCHEDULE_HOUR, SCHEDULE_MINUTE, TIMEZONE, DEMO_MODE, LOG_LEVEL, BRAND_NAME
import database as db
from news_fetcher import fetch_top_ai_news
from ai_writer import generate_all_content
from image_engine import generate_all_carousels, download_fonts
from image_server import start_image_server, get_image_urls, get_reel_url, get_reel_thumb_url
from instagram_publisher import publish_all_posts
from analytics import poll_analytics_for_run
from token_refresher import check_and_refresh_token

# ─── Logging setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)-25s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent / "data" / "automation.log",
            mode="a", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("main")

# WebSocket broadcast callback (set by api_server.py)
_ws_broadcast = None

def set_ws_broadcast(fn):
    global _ws_broadcast
    _ws_broadcast = fn

def _broadcast(level: str, module: str, message: str, run_date: str = ""):
    """Log to DB, file logger, and broadcast via WebSocket."""
    log_fn = {
        "INFO":    logger.info,
        "SUCCESS": logger.info,
        "WARNING": logger.warning,
        "ERROR":   logger.error,
    }.get(level, logger.info)
    log_fn("[%s] %s", module, message)
    db.log_event(level, module, message, run_date=run_date)
    if _ws_broadcast:
        try:
            _ws_broadcast({
                "type": "log",
                "level": level,
                "module": module,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def run_daily_pregeneration():
    """
    Full autonomous pipeline pre-generation (4:00 AM):
    1. Fetch top 5 AI news
    2. Generate AI content
    3. Generate carousel/reels
    4. Host images & save to DB as 'draft'
    """
    run_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    start_time = time.time()

    _broadcast("INFO", "Orchestrator", f"🚀 Daily Pre-generation starting for {run_date}", run_date)
    run_id = db.start_run(run_date)

    stats = {
        "stories_fetched": 0,
        "posts_generated": 0,
        "posts_published": 0,
        "error_count": 0,
    }

    try:
        # ── Step 1: Fetch News
        _broadcast("INFO", "NewsFetcher", "📡 Fetching latest AI news from multiple sources...", run_date)
        stories = fetch_top_ai_news()
        stats["stories_fetched"] = len(stories)
        story_ids = db.save_news_stories(run_date, stories)
        _broadcast("SUCCESS", "NewsFetcher", f"✅ Fetched {len(stories)} top AI stories", run_date)

        # ── Step 2: Generate Content
        _broadcast("INFO", "AIWriter", "✍️  Generating AI captions and content...", run_date)
        content_list = generate_all_content(stories)
        _broadcast("SUCCESS", "AIWriter", f"✅ Content generated for {len(content_list)} posts", run_date)

        # ── Step 3: Generate Carousel Images
        _broadcast("INFO", "ImageEngine", "🎨 Rendering carousels & reels...", run_date)
        content_list = generate_all_carousels(content_list, run_date)
        _broadcast("SUCCESS", "ImageEngine", f"✅ Media generated for {len(content_list)} posts", run_date)

        # ── Step 4: Host Images & Save Drafts
        _broadcast("INFO", "ImageServer", "🌐 Generating public media URLs...", run_date)
        for i, content in enumerate(content_list):
            image_urls = get_image_urls(content.get("slide_paths", []))
            content["image_urls"] = image_urls
            
            reel_path = content.get("reel_path")
            reel_thumb = content.get("reel_thumb_path", "")
            if reel_path:
                content["reel_url"] = get_reel_url(reel_path)
            if reel_thumb:
                content["reel_thumb_url"] = get_reel_thumb_url(reel_thumb)
            else:
                content["reel_thumb_url"] = ""

            story_id = story_ids[i] if i < len(story_ids) else None
            post_id = db.save_generated_post(run_date, story_id, {
                **content,
                "rank": i,
            })
            content["db_post_id"] = post_id

        stats["posts_generated"] = len(content_list)
        _broadcast("SUCCESS", "ImageServer", "✅ Media URLs ready and Drafts saved", run_date)

        duration = round(time.time() - start_time, 1)
        stats["duration_seconds"] = duration
        db.finish_run(run_id, "completed", stats)
        _broadcast("SUCCESS", "Orchestrator", f"🎉 Pre-generation complete in {duration}s", run_date)

    except Exception as e:
        logger.exception("Pre-generation failed: %s", e)
        stats["error_count"] += 1
        stats["duration_seconds"] = round(time.time() - start_time, 1)
        db.finish_run(run_id, "failed", stats)
        _broadcast("ERROR", "Orchestrator", f"💥 Pre-generation failed: {e}", run_date)


# ─── Staggered Post Times (IST) ─────────────────────────────────────────────
# Research-backed peak times for Indian fitness audience:
# 7:00 AM  — Hot Take Reel       (morning scroll before gym)
# 12:00 PM — Quick Tip Reel      (lunch break)
# 3:00 PM  — Save List Carousel  (mid-afternoon)
# 6:00 PM  — Myth Buster Carousel (post-gym golden hour)
# 9:00 PM  — Gym Meme Reel       (peak evening usage)

POST_SCHEDULE = [
    {"hour": 7,  "minute": 0,  "rank": 0, "content_type": "hot_take"},
    {"hour": 12, "minute": 0,  "rank": 1, "content_type": "quick_tip"},
    {"hour": 15, "minute": 0,  "rank": 2, "content_type": "save_list"},
    {"hour": 18, "minute": 0,  "rank": 3, "content_type": "myth_buster"},
    {"hour": 21, "minute": 0,  "rank": 4, "content_type": "meme_relatable"},
]


def run_custom_post(prompt: str):
    """Bypasses news and generates a single custom post immediately."""
    from ai_writer import generate_fitness_content
    from image_engine import generate_carousel
    
    run_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    _broadcast("INFO", "Custom", f"🚀 Generating custom post: {prompt[:40]}...", run_date)

    story = {
        "title": prompt,
        "summary": "Custom prompt by user",
        "source": "Custom",
        "url": "",
        "published_at": run_date,
        "rank": 999
    }
    story_ids = db.save_news_stories(run_date, [story])
    story_id = story_ids[0]

    try:
        content = generate_fitness_content(story, rank=999)
        _broadcast("INFO", "Custom", "Content generated, rendering media...", run_date)

        post_data = generate_carousel(content, story, 999, run_date)
        post_data.update(content)
        post_data["rank"] = 999

        # Get public URLs
        image_urls = get_image_urls(post_data.get("slide_paths", []))
        post_data["image_urls"] = image_urls
        reel_path = post_data.get("reel_path")
        reel_thumb = post_data.get("reel_thumb_path", "")
        if reel_path:
            post_data["reel_url"] = get_reel_url(reel_path)
        if reel_thumb:
            post_data["reel_thumb_url"] = get_reel_thumb_url(reel_thumb)
        else:
            post_data["reel_thumb_url"] = ""

        post_id = db.save_generated_post(run_date, story_id, post_data)
        _broadcast("SUCCESS", "Custom", f"✅ Custom post #{post_id} saved to Drafts!", run_date)
    except Exception as e:
        logger.error(f"Custom post failed: {e}")
        _broadcast("ERROR", "Custom", f"❌ Custom post failed: {str(e)}", run_date)



def run_single_post(rank: int, scheduled_time: str):
    """
    Publish a single post by rank (0-4).
    Checks if the draft is approved or pending. Rejects if user explicitly rejected.
    """
    run_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    slot     = POST_SCHEDULE[rank]
    ctype    = slot["content_type"]

    _broadcast("INFO", "Orchestrator", f"⏰ Scheduled post #{rank+1} ({ctype}) starting...", run_date)

    try:
        # Check token first
        token_info = check_and_refresh_token()
        if token_info["action"] == "expired":
            _broadcast("ERROR", "Orchestrator", "🔴 Token expired — skipping post.", run_date)
            return

        # Fetch draft from DB
        drafts = db.get_generated_posts(run_date)
        draft = next((d for d in drafts if d["rank"] == rank), None)

        if not draft:
            _broadcast("ERROR", "Orchestrator", f"No draft found for post #{rank+1}. Did pre-gen run?", run_date)
            return
            
        if draft["status"] == "rejected":
            _broadcast("WARNING", "Orchestrator", f"Post #{rank+1} was REJECTED by user. Skipping.", run_date)
            return

        _broadcast("INFO", "Orchestrator", f"Post #{rank+1} status is '{draft['status']}'. Proceeding to publish.", run_date)

        # We must format the draft back into the 'content' dict expected by publish_post
        content = {
            "db_post_id": draft["id"],
            "headline": draft["headline"],
            "caption": draft["caption"],
            "image_urls": draft["image_urls"],
            "reel_url": draft.get("reel_url", ""),
            "post_format": "reel" if draft.get("reel_url") else "carousel"
        }

        # Publish
        from instagram_publisher import publish_post
        result  = publish_post(content, rank)
        ig_id   = result.get("ig_media_id", "")
        link    = result.get("ig_permalink", "")
        error   = result.get("error", "")

        db.save_published_post(draft["id"], ig_id, link, error)
        db.update_post_status(draft["id"], "published" if ig_id else "failed")

        if ig_id:
            _broadcast("SUCCESS", "Orchestrator", f"✅ [{ctype}] Post #{rank+1} live → {link}", run_date)
        else:
            _broadcast("ERROR", "Orchestrator", f"❌ Post #{rank+1} failed: {error}", run_date)

    except Exception as e:
        logger.exception("Single post %d failed: %s", rank, e)
        _broadcast("ERROR", "Orchestrator", f"💥 Post #{rank+1} error: {e}", run_date)


def run_comment_engagement():
    """Polls recent posts for new comments and uses Gemini to automatically reply."""
    from instagram_publisher import get_recent_comments, reply_to_comment
    from ai_writer import get_gemini_client
    import google.generativeai as genai
    
    _broadcast("INFO", "Engagement", "Checking for new comments to reply to...")
    
    # Get last 3 published posts
    recent_posts = db.get_published_posts(limit=3)
    replied_count = 0
    
    genai_client = get_gemini_client()
    if not genai_client:
        return
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    sys_prompt = (
        "You are the Iron Pulse fitness brand social media manager. "
        "CRITICAL RULE: We only want to reply to a FEW high-value comments. "
        "If the user's comment is just a single emoji, generic praise (e.g., 'fire', 'good video'), "
        "or not a question, you MUST reply with EXACTLY the word: SKIP. "
        "Only generate a reply if it's a question, a substantial comment, or a debate. "
        "Keep replies very short (1-2 sentences) and encouraging."
    )

    for post in recent_posts:
        media_id = post.get("ig_media_id")
        if not media_id:
            continue
            
        comments = get_recent_comments(media_id)
        for c in comments[:5]: # Max 5 comments per post to avoid spamming
            username = c.get("username", "user")
            text = c.get("text", "")
            comment_id = c.get("id")
            
            try:
                prompt = f"{sys_prompt}\n\nUser @{username} commented: '{text}'\n\nReply (or output SKIP):"
                resp = model.generate_content(prompt)
                reply_text = resp.text.strip()
                
                if reply_text.upper() != "SKIP" and reply_text != "":
                    if reply_to_comment(comment_id, reply_text):
                        replied_count += 1
            except Exception as e:
                logger.error("Failed to generate/send reply for comment %s: %s", comment_id, e)
                
    if replied_count > 0:
        _broadcast("SUCCESS", "Engagement", f"✅ Automatically replied to {replied_count} comments!")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    # ── 4:00 AM Daily Pre-Generation ─────────────────────────────────────────
    scheduler.add_job(
        run_daily_pregeneration,
        trigger=CronTrigger(hour=4, minute=0, timezone=TIMEZONE),
        id="daily_pregeneration",
        name="Daily Pre-gen @ 4:00 AM IST",
        replace_existing=True,
    )
    logger.info("  📅 Pre-generation scheduled at 04:00 IST")

    # ── 5 staggered daily posts at peak Instagram times ───────────────────────
    for slot in POST_SCHEDULE:
        h, m, rank, ctype = slot["hour"], slot["minute"], slot["rank"], slot["content_type"]
        scheduled_time = f"{h:02d}:{m:02d}"
        scheduler.add_job(
            run_single_post,
            args=[rank, scheduled_time],
            trigger=CronTrigger(hour=h, minute=m, timezone=TIMEZONE),
            id=f"post_{rank}_{ctype}",
            name=f"{ctype} @ {h:02d}:{m:02d} IST",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        logger.info("  📅 Publishing Slot %d: %s at %02d:%02d IST", rank + 1, ctype, h, m)


    # ── Analytics refresh every 6 hours ──────────────────────────────────────
    scheduler.add_job(
        lambda: poll_analytics_for_run(datetime.now(TIMEZONE).strftime("%Y-%m-%d")),
        trigger=CronTrigger(hour="*/6", timezone=TIMEZONE),
        id="analytics_refresh",
        name="Analytics Refresh (6h)",
        replace_existing=True,
    )

    # ── Token health check at 8am ─────────────────────────────────────────────
    def _token_check():
        result = check_and_refresh_token()
        level  = "SUCCESS" if result["action"] in ("ok", "refreshed") else "WARNING"
        if result["action"] == "expired":
            level = "ERROR"
        _broadcast(level, "TokenRefresher", result["message"])

    scheduler.add_job(
        _token_check,
        trigger=CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        id="token_check",
        name="Daily Token Health Check",
        replace_existing=True,
    )
    
    # ── Automated Comment Replies (Every 15 mins) ─────────────────────────────
    scheduler.add_job(
        run_comment_engagement,
        trigger=CronTrigger(minute="*/15", timezone=TIMEZONE),
        id="comment_engagement",
        name="Comment Auto-Replies",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler active — 5 posts daily at peak IST times")
    return scheduler


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=f"{BRAND_NAME} Automation System")
    parser.add_argument("--run-now", action="store_true", help="Run the pipeline immediately")
    parser.add_argument("--no-scheduler", action="store_true", help="Skip the daily scheduler")
    args = parser.parse_args()

    # Initialize database
    db.init_db()
    logger.info("=" * 60)
    logger.info("  %s — AI Instagram Automation System", BRAND_NAME)
    logger.info("  Mode: %s", "DEMO" if DEMO_MODE else "LIVE")
    logger.info("  Schedule: Daily at %02d:%02d %s", SCHEDULE_HOUR, SCHEDULE_MINUTE, TIMEZONE.zone)
    logger.info("=" * 60)

    # Download fonts
    download_fonts()

    # Start image server
    start_image_server()

    if args.run_now:
        logger.info("Running pre-generation immediately (--run-now flag)")
        run_daily_pregeneration()

    if not args.no_scheduler:
        scheduler = start_scheduler()
        try:
            import time as _time
            while True:
                _time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("Scheduler stopped. Goodbye.")
