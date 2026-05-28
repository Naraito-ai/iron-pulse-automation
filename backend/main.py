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
from image_server import start_image_server, get_image_urls, get_reel_url
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

def run_daily_pipeline():
    """
    Full autonomous pipeline:
    1. Fetch top 5 AI news
    2. Generate AI content (captions, hashtags, headlines)
    3. Generate carousel images
    4. Host images via local server
    5. Publish to Instagram
    6. Fetch analytics
    """
    run_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    start_time = time.time()

    _broadcast("INFO", "Orchestrator", f"🚀 Daily pipeline starting for {run_date}", run_date)
    run_id = db.start_run(run_date)

    stats = {
        "stories_fetched": 0,
        "posts_generated": 0,
        "posts_published": 0,
        "error_count": 0,
    }

    try:
        # ── Step 1: Fetch News ──────────────────────────────────────────────
        _broadcast("INFO", "NewsFetcher", "📡 Fetching latest AI news from multiple sources...", run_date)
        stories = fetch_top_ai_news()
        stats["stories_fetched"] = len(stories)
        story_ids = db.save_news_stories(run_date, stories)
        _broadcast("SUCCESS", "NewsFetcher", f"✅ Fetched {len(stories)} top AI stories", run_date)

        # ── Step 2: Generate Content ────────────────────────────────────────
        _broadcast("INFO", "AIWriter", "✍️  Generating AI captions and content...", run_date)
        content_list = generate_all_content(stories)
        _broadcast("SUCCESS", "AIWriter", f"✅ Content generated for {len(content_list)} posts", run_date)

        # ── Step 3: Generate Carousel Images ────────────────────────────────
        _broadcast("INFO", "ImageEngine", "🎨 Rendering carousel slides...", run_date)
        content_list = generate_all_carousels(content_list, run_date)
        _broadcast("SUCCESS", "ImageEngine", f"✅ Carousels & Reels generated for {len(content_list)} posts", run_date)

        # ── Step 4: Host Images & Videos ──────────────────────────────────────────────
        _broadcast("INFO", "ImageServer", "🌐 Generating public media URLs...", run_date)
        for i, content in enumerate(content_list):
            image_urls = get_image_urls(content.get("slide_paths", []))
            content["image_urls"] = image_urls
            
            # Upload Reel
            reel_path = content.get("reel_path")
            if reel_path:
                content["reel_url"] = get_reel_url(reel_path)

            # Save to DB
            story_id = story_ids[i] if i < len(story_ids) else None
            post_id = db.save_generated_post(run_date, story_id, {
                **content,
                "rank": i + 1,
            })
            content["db_post_id"] = post_id

        stats["posts_generated"] = len(content_list)
        _broadcast("SUCCESS", "ImageServer", "✅ Media URLs ready", run_date)

        # ── Step 5: Publish to Instagram ────────────────────────────────────
        mode_tag = "[DEMO]" if DEMO_MODE else "[LIVE]"
        carousel_count = sum(1 for c in content_list if c.get("post_format") == "carousel")
        reel_count     = sum(1 for c in content_list if c.get("post_format") != "carousel")
        _broadcast("INFO", "Publisher",
                   f"📲 {mode_tag} Publishing {len(content_list)} posts "
                   f"({reel_count} Reels + {carousel_count} Carousels)...", run_date)
        _broadcast("INFO", "Publisher",
                   "💡 TIP: After posting, open each Reel in Instagram and add a TRENDING SOUND for 3-5x more reach!", run_date)

        published = publish_all_posts(content_list)
        for pub in published:
            db_post_id = pub.get("db_post_id")
            ig_id      = pub.get("ig_media_id", "")
            permalink  = pub.get("ig_permalink", "")
            error      = pub.get("error", "")

            db.save_published_post(db_post_id, ig_id, permalink, error)
            db.update_post_status(db_post_id, "published" if ig_id else "failed")

            if ig_id:
                stats["posts_published"] += 1
                _broadcast("SUCCESS", "Publisher",
                           f"✅ Post #{pub.get('rank', '?')} published → {permalink or ig_id}", run_date)
            else:
                stats["error_count"] += 1
                _broadcast("ERROR", "Publisher",
                           f"❌ Post #{pub.get('rank', '?')} failed: {error}", run_date)

        # ── Step 6: Analytics ────────────────────────────────────────────────
        _broadcast("INFO", "Analytics", "📊 Fetching post analytics...", run_date)
        poll_analytics_for_run(run_date)
        _broadcast("SUCCESS", "Analytics", "✅ Analytics snapshot saved", run_date)

        # ── Done ─────────────────────────────────────────────────────────────
        duration = round(time.time() - start_time, 1)
        stats["duration_seconds"] = duration
        db.finish_run(run_id, "completed", stats)

        _broadcast("SUCCESS", "Orchestrator",
                   f"🎉 Pipeline complete in {duration}s | "
                   f"{stats['posts_published']}/{stats['posts_generated']} posts published", run_date)

        if _ws_broadcast:
            _ws_broadcast({"type": "pipeline_complete", "run_date": run_date, "stats": stats})

    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        stats["error_count"] += 1
        stats["duration_seconds"] = round(time.time() - start_time, 1)
        db.finish_run(run_id, "failed", stats)
        _broadcast("ERROR", "Orchestrator", f"💥 Pipeline failed: {e}", run_date)
        if _ws_broadcast:
            _ws_broadcast({"type": "pipeline_error", "error": str(e)})


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


def run_single_post(rank: int):
    """
    Publish a single post by rank (0-4).
    Called by the staggered scheduler at each peak time.
    Generates content fresh if not already done today, or publishes pre-generated.
    """
    run_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    slot     = POST_SCHEDULE[rank]
    ctype    = slot["content_type"]

    _broadcast("INFO", "Orchestrator",
               f"⏰ Scheduled post #{rank+1} ({ctype}) starting...", run_date)

    try:
        # Check token first
        token_info = check_and_refresh_token()
        if token_info["action"] == "expired":
            _broadcast("ERROR", "Orchestrator",
                       "🔴 Token expired — skipping post. Paste new token in dashboard.", run_date)
            return

        # Run the full pipeline for this single slot
        stories      = fetch_top_ai_news()
        all_content  = generate_all_content(stories)

        # Pick just this slot's content
        content = all_content[rank % len(all_content)]
        content = generate_all_carousels([content], run_date)[0]

        # Get public URLs
        content["image_urls"] = get_image_urls(content.get("slide_paths", []))
        reel_path = content.get("reel_path")
        if reel_path:
            content["reel_url"] = get_reel_url(reel_path)

        # Save to DB
        run_id  = db.start_run(run_date)
        post_id = db.save_generated_post(run_date, None, {**content, "rank": rank + 1})
        content["db_post_id"] = post_id

        # Publish
        from instagram_publisher import publish_post
        result  = publish_post(content, rank)
        ig_id   = result.get("ig_media_id", "")
        link    = result.get("ig_permalink", "")
        error   = result.get("error", "")

        db.save_published_post(post_id, ig_id, link, error)
        db.update_post_status(post_id, "published" if ig_id else "failed")
        db.finish_run(run_id, "completed" if ig_id else "failed", {"posts_published": 1 if ig_id else 0})

        if ig_id:
            _broadcast("SUCCESS", "Orchestrator",
                       f"✅ [{ctype}] Post #{rank+1} live → {link}", run_date)
            if slot["content_type"] in ("hot_take", "quick_tip", "meme_relatable"):
                _broadcast("INFO", "Orchestrator",
                           f"🎵 Open the Reel in Instagram app → tap ♪ → add a TRENDING SOUND for 5x more reach!",
                           run_date)
        else:
            _broadcast("ERROR", "Orchestrator",
                       f"❌ Post #{rank+1} failed: {error}", run_date)

    except Exception as e:
        logger.exception("Single post %d failed: %s", rank, e)
        _broadcast("ERROR", "Orchestrator", f"💥 Post #{rank+1} error: {e}", run_date)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    # ── 5 staggered daily posts at peak Instagram times ───────────────────────
    for slot in POST_SCHEDULE:
        h, m, rank, ctype = slot["hour"], slot["minute"], slot["rank"], slot["content_type"]
        scheduler.add_job(
            run_single_post,
            args=[rank],
            trigger=CronTrigger(hour=h, minute=m, timezone=TIMEZONE),
            id=f"post_{rank}_{ctype}",
            name=f"{ctype} @ {h:02d}:{m:02d} IST",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        logger.info("  📅 Slot %d: %s at %02d:%02d IST", rank + 1, ctype, h, m)

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
        logger.info("Running pipeline immediately (--run-now flag)")
        run_daily_pipeline()

    if not args.no_scheduler:
        scheduler = start_scheduler()
        try:
            import time as _time
            while True:
                _time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("Scheduler stopped. Goodbye.")
