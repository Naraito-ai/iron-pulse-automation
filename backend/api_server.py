"""
api_server.py — FastAPI REST + WebSocket server for the dashboard.
Exposes all data the dashboard needs and streams live logs via WebSocket.
"""

import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import database as db
from config import (
    API_HOST, API_PORT, DEMO_MODE, SCHEDULE_HOUR, SCHEDULE_MINUTE,
    TIMEZONE, BRAND_NAME, GENERATED_DIR, THUMBNAIL_DIR
)
from analytics import get_performance_summary

logger = logging.getLogger(__name__)

app = FastAPI(title=f"{BRAND_NAME} API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for image serving
app.mount("/images", StaticFiles(directory=str(Path(__file__).parent / "assets")), name="images")
app.mount("/generated", StaticFiles(directory=str(Path(__file__).parent / "assets/generated")), name="generated")

@app.on_event("startup")
async def startup_event():
    from image_server import start_image_server
    from main import start_scheduler
    import database as db
    db.init_db()
    start_image_server()
    _scheduler = start_scheduler()
    app.state.scheduler = _scheduler
    logger.info("✅ Scheduler started — 5 posts daily at peak IST times")

# ─── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info("WebSocket client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        msg = json.dumps(data)
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()


def sync_broadcast(data: dict):
    """Called from sync main.py pipeline to broadcast to WebSocket clients."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast(data))
        else:
            loop.run_until_complete(manager.broadcast(data))
    except Exception:
        pass


# Register the broadcast function with main.py
try:
    from main import set_ws_broadcast
    set_ws_broadcast(sync_broadcast)
except Exception:
    pass


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    # Send initial status on connect
    await ws.send_text(json.dumps({
        "type": "connected",
        "message": f"Connected to {BRAND_NAME} Live Feed",
        "timestamp": datetime.utcnow().isoformat(),
    }))
    try:
        while True:
            await ws.receive_text()   # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ─── REST endpoints ───────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """System status: scheduler, Instagram connection, demo mode."""
    from datetime import timedelta
    import os
    now = datetime.now(TIMEZONE)
    next_run = now.replace(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    seconds_until = int((next_run - now).total_seconds())

    run_history = db.get_run_history(limit=1)
    last_run = run_history[0] if run_history else None

    # Check Instagram token validity via real API call
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    ig_connected = False
    ig_user_id = ""
    if token:
        try:
            import requests as _req
            r = _req.get(
                f"https://graph.facebook.com/me",
                params={"access_token": token, "fields": "id,name"},
                timeout=5
            )
            data = r.json()
            if "id" in data and "error" not in data:
                ig_connected = True
                ig_user_id = data.get("id", "")
        except Exception:
            ig_connected = False

    # Check ElevenLabs configured
    elevenlabs_configured = bool(os.environ.get("ELEVENLABS_API_KEY", ""))

    return {
        "brand_name":               BRAND_NAME,
        "demo_mode":                DEMO_MODE,
        "instagram_connected":      ig_connected,
        "instagram_user_id":        ig_user_id,
        "elevenlabs_configured":    elevenlabs_configured,
        "scheduler_active":         True,
        "next_run_at":              next_run.isoformat(),
        "seconds_until_next":       seconds_until,
        "schedule_time":            f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}",
        "last_run":                 last_run,
        "ws_clients":               len(manager.active),
        "server_time":              now.isoformat(),
    }


@app.get("/api/news")
async def get_news():
    """Latest fetched AI news stories."""
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    stories = db.get_latest_news(today) or db.get_latest_news()
    return {"stories": stories, "count": len(stories)}


@app.get("/api/posts")
async def get_posts():
    """Generated carousel posts with slide paths and captions."""
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    posts = db.get_generated_posts(today) or db.get_generated_posts()
    return {"posts": posts, "count": len(posts)}


@app.get("/api/published")
async def get_published():
    """All published Instagram posts."""
    published = db.get_published_posts(limit=30)
    return {"published": published, "count": len(published)}


import time
_analytics_cache = {"data": None, "time": 0}

@app.get("/api/analytics")
def get_analytics():
    """Performance analytics and engagement summary."""
    now = time.time()
    if _analytics_cache["data"] and now - _analytics_cache["time"] < 300:
        return _analytics_cache["data"]
        
    summary = get_performance_summary()
    _analytics_cache["data"] = summary
    _analytics_cache["time"] = now
    return summary


@app.get("/api/logs")
async def get_logs(limit: int = 100, run_date: str = None):
    """Automation log entries."""
    logs = db.get_logs(limit=limit, run_date=run_date)
    return {"logs": logs, "count": len(logs)}


@app.get("/api/history")
async def get_history():
    """Run history records."""
    history = db.get_run_history(limit=20)
    return {"history": history}


@app.get("/api/drafts")
async def get_drafts():
    """Today's pre-generated drafts pending approval."""
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    posts = db.get_generated_posts(today)
    drafts = [p for p in posts if p["status"] in ("draft", "approved", "rejected")]
    return {"drafts": drafts, "count": len(drafts)}

@app.post("/api/drafts/{post_id}/approve")
async def approve_draft(post_id: int):
    db.update_post_status(post_id, "approved")
    return {"status": "success", "message": f"Draft {post_id} approved"}

@app.post("/api/drafts/{post_id}/reject")
async def reject_draft(post_id: int):
    db.update_post_status(post_id, "rejected")
    return {"status": "success", "message": f"Draft {post_id} rejected"}

@app.put("/api/drafts/{post_id}")
async def edit_draft(post_id: int, body: dict):
    """Update draft content directly."""
    allowed_keys = {"headline", "caption", "hashtags"}
    updates = {k: v for k, v in body.items() if k in allowed_keys}
    if updates:
        db.update_draft_content(post_id, updates)
    return {"status": "success"}

@app.post("/api/generate-custom")
async def generate_custom(body: dict, background_tasks: BackgroundTasks):
    """Manually generate a post from a custom prompt."""
    prompt = body.get("prompt")
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Prompt required"})
    from main import run_custom_post
    logger.info("Custom post trigger via API: %s", prompt)
    background_tasks.add_task(run_custom_post, prompt)
    return {"status": "triggered", "message": "Custom post generation started..."}

@app.post("/api/force-post/{post_id}")
async def force_post(post_id: int, background_tasks: BackgroundTasks):
    """Instantly publish a specific draft to Instagram, bypassing the schedule."""
    # Mark as pending so the publisher picks it up
    db.update_post_status(post_id, "pending")
    from instagram_publisher import publish_pending_posts
    logger.info("Force publishing post %d", post_id)
    background_tasks.add_task(publish_pending_posts)
    return {"status": "triggered", "message": f"Publishing post {post_id} to Instagram..."}

@app.post("/api/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger the pre-generation pipeline."""
    from main import run_daily_pregeneration
    logger.info("Manual pre-generation trigger via API")
    background_tasks.add_task(run_daily_pregeneration)
    return {"status": "triggered", "message": "Pre-generation starting in background..."}


@app.get("/api/schedule")
async def get_schedule():
    """Return the daily posting schedule with next fire times."""
    from main import POST_SCHEDULE
    now = datetime.now(TIMEZONE)
    schedule = []
    for slot in POST_SCHEDULE:
        h, m = slot["hour"], slot["minute"]
        fire_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if fire_time < now:
            from datetime import timedelta
            fire_time += timedelta(days=1)
        schedule.append({
            "rank": slot["rank"],
            "content_type": slot["content_type"],
            "time": f"{h:02d}:{m:02d} IST",
            "next_fire": fire_time.isoformat(),
            "seconds_until": int((fire_time - now).total_seconds()),
        })
    return {"schedule": schedule}


@app.get("/api/images/thumbnails")
async def list_thumbnails():
    """List all generated thumbnail images."""
    thumbs = list(THUMBNAIL_DIR.glob("*.jpg"))
    return {
        "thumbnails": [
            {"name": t.name, "url": f"/images/thumbnails/{t.name}"}
            for t in sorted(thumbs, reverse=True)[:20]
        ]
    }


@app.get("/api/token-status")
async def get_token_status():
    """Check Instagram access token health and days remaining."""
    from token_refresher import get_token_info
    import os
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    if not token:
        return {"status": "missing", "days_remaining": 0, "message": "No token configured"}
    info = get_token_info(token)
    if not info["is_valid"]:
        return {"status": "expired", "days_remaining": 0, "message": "Token expired — paste a new one below"}
    days = info["days_remaining"]
    if days == 9999:
        return {"status": "permanent", "days_remaining": 9999, "message": "System User token — never expires"}
    status = "healthy" if days > 15 else ("warning" if days > 5 else "critical")
    return {
        "status": status,
        "days_remaining": days,
        "expires_at": info["expires_at"].isoformat() if info["expires_at"] else None,
        "message": f"Token valid — {days} days remaining",
    }


@app.post("/api/update-token")
async def update_token(body: dict):
    """Update the Instagram access token from the dashboard."""
    import os
    from dotenv import set_key
    from pathlib import Path
    new_token = (body.get("token") or "").strip()
    if not new_token or len(new_token) < 50:
        return JSONResponse(status_code=400, content={"error": "Invalid token"})
    env_file = Path(__file__).parent.parent / ".env"
    try:
        set_key(str(env_file), "INSTAGRAM_ACCESS_TOKEN", new_token)
        # Also update in-process env
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = new_token
        # Reload config
        import importlib, config
        importlib.reload(config)
        logger.info("Access token updated via dashboard API")
        return {"status": "updated", "message": "Token saved successfully! Pipeline will use new token."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/")
async def root():
    return {"message": f"{BRAND_NAME} API running", "docs": "/docs"}


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import uvicorn
    db.init_db()

    # Railway sets PORT dynamically — fall back to API_PORT for local dev
    port = int(os.environ.get("PORT", API_PORT))

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
