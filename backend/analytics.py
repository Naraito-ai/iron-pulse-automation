"""
analytics.py — Instagram engagement tracker and trend analyzer.
Polls the Meta Graph API for post metrics and stores snapshots.
"""

import time
import logging
import random
import requests
from datetime import datetime
from config import INSTAGRAM_ACCESS_TOKEN, GRAPH_API_BASE, DEMO_MODE
import database as db

logger = logging.getLogger(__name__)


# ─── Demo Analytics ───────────────────────────────────────────────────────────

def _demo_metrics(ig_media_id: str, hours_since_post: float = 24) -> dict:
    """Generate realistic demo analytics based on time since posting."""
    seed = hash(ig_media_id) % 1000
    random.seed(seed)

    base_likes     = random.randint(800, 3500)
    base_comments  = random.randint(40, 250)
    base_shares    = random.randint(150, 900)
    base_saves     = random.randint(200, 1200)
    base_reach     = random.randint(8000, 45000)
    base_impressions = int(base_reach * random.uniform(1.5, 3.0))

    # Simulate growth over time (peaks at ~12h, tapers after 48h)
    growth = min(1.0, hours_since_post / 12.0) * max(0.3, 1.0 - (hours_since_post - 12) / 200.0)

    likes       = int(base_likes * growth)
    comments    = int(base_comments * growth)
    shares      = int(base_shares * growth)
    saves       = int(base_saves * growth)
    reach       = int(base_reach * growth)
    impressions = int(base_impressions * growth)

    engagement_rate = round((likes + comments + shares + saves) / max(reach, 1) * 100, 2)
    viral_score     = round(min(10.0, (shares * 3 + saves * 2 + likes) / max(reach, 1) * 100), 2)

    return {
        "likes":           likes,
        "comments":        comments,
        "shares":          shares,
        "saves":           saves,
        "reach":           reach,
        "impressions":     impressions,
        "engagement_rate": engagement_rate,
        "viral_score":     viral_score,
    }


# ─── Live API fetcher ─────────────────────────────────────────────────────────

METRICS_FIELDS = "like_count,comments_count,saved,reach,impressions,shares"


def _fetch_live_metrics(ig_media_id: str) -> dict:
    """Fetch real metrics from Instagram Graph API."""
    try:
        url = f"{GRAPH_API_BASE}/{ig_media_id}"
        params = {
            "fields": METRICS_FIELDS,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if "error" in data:
            raise RuntimeError(data["error"])

        likes       = data.get("like_count", 0)
        comments    = data.get("comments_count", 0)
        saves       = data.get("saved", 0)
        reach       = data.get("reach", 0)
        impressions = data.get("impressions", 0)
        shares      = data.get("shares", {}).get("count", 0) if isinstance(data.get("shares"), dict) else 0

        engagement_rate = round((likes + comments + shares + saves) / max(reach, 1) * 100, 2)
        viral_score     = round(min(10.0, (shares * 3 + saves * 2 + likes) / max(reach, 1) * 100), 2)

        return {
            "likes":           likes,
            "comments":        comments,
            "shares":          shares,
            "saves":           saves,
            "reach":           reach,
            "impressions":     impressions,
            "engagement_rate": engagement_rate,
            "viral_score":     viral_score,
        }
    except Exception as e:
        logger.error("Failed to fetch metrics for %s: %s", ig_media_id, e)
        return {}


# ─── Main Analytics Engine ────────────────────────────────────────────────────

def poll_analytics_for_run(run_date: str):
    """Fetch and store analytics for all published posts from a run."""
    published = db.get_published_posts(limit=50)
    today_published = [p for p in published if p.get("status") == "published" and p.get("ig_media_id")]

    if not today_published:
        logger.info("No published posts found for analytics")
        return

    logger.info("Polling analytics for %d posts...", len(today_published))

    for pub in today_published:
        ig_id = pub["ig_media_id"]
        pub_id = pub["id"]

        # Estimate hours since posting for demo realism
        try:
            pub_time = datetime.fromisoformat(pub.get("published_at", datetime.utcnow().isoformat()))
            hours = (datetime.utcnow() - pub_time).total_seconds() / 3600
        except Exception:
            hours = 24

        if DEMO_MODE or not INSTAGRAM_ACCESS_TOKEN:
            metrics = _demo_metrics(ig_id, hours_since_post=hours)
        else:
            metrics = _fetch_live_metrics(ig_id)
            if not metrics:
                metrics = _demo_metrics(ig_id, hours_since_post=hours)

        db.save_analytics(pub_id, ig_id, metrics)
        logger.info(
            "Analytics for %s: likes=%d reach=%d engagement=%.1f%% viral=%.1f",
            ig_id, metrics["likes"], metrics["reach"],
            metrics["engagement_rate"], metrics["viral_score"]
        )
        time.sleep(0.5)


def get_performance_summary() -> dict:
    """Compute aggregate performance summary from all analytics snapshots."""
    snapshots = db.get_analytics(limit=200)
    if not snapshots:
        return _empty_summary()

    total_likes      = sum(s["likes"] for s in snapshots)
    total_comments   = sum(s["comments"] for s in snapshots)
    total_shares     = sum(s["shares"] for s in snapshots)
    total_saves      = sum(s["saves"] for s in snapshots)
    total_reach      = sum(s["reach"] for s in snapshots)
    total_impressions = sum(s["impressions"] for s in snapshots)
    avg_engagement   = round(sum(s["engagement_rate"] for s in snapshots) / max(len(snapshots), 1), 2)
    avg_viral        = round(sum(s["viral_score"] for s in snapshots) / max(len(snapshots), 1), 2)
    best_viral       = max((s["viral_score"] for s in snapshots), default=0)

    return {
        "total_posts":       len(set(s["ig_media_id"] for s in snapshots)),
        "total_likes":       total_likes,
        "total_comments":    total_comments,
        "total_shares":      total_shares,
        "total_saves":       total_saves,
        "total_reach":       total_reach,
        "total_impressions": total_impressions,
        "avg_engagement_rate": avg_engagement,
        "avg_viral_score":   avg_viral,
        "best_viral_score":  best_viral,
        "snapshots":         snapshots[-30:],  # recent 30 for chart
    }


def _empty_summary() -> dict:
    """Return empty summary structure when no data exists."""
    return {
        "total_posts": 0, "total_likes": 0, "total_comments": 0,
        "total_shares": 0, "total_saves": 0, "total_reach": 0,
        "total_impressions": 0, "avg_engagement_rate": 0.0,
        "avg_viral_score": 0.0, "best_viral_score": 0.0, "snapshots": [],
    }
