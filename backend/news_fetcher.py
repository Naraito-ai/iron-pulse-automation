"""
news_fetcher.py — Multi-source AI news fetcher with intelligent ranking.
Fetches from RSS feeds + NewsAPI, deduplicates, scores, and returns top 5.
"""

import re
import time
import math
import logging
import hashlib
import feedparser
import requests
from datetime import datetime, timezone
from typing import Optional
from config import RSS_FEEDS, AI_KEYWORDS, NEWSAPI_KEY, DEMO_MODE

logger = logging.getLogger(__name__)


# ─── Demo Data ────────────────────────────────────────────────────────────────

DEMO_STORIES = [
    {
        "title": "New Study Reveals Optimal Protein Intake for Maximum Hypertrophy",
        "summary": "Researchers have discovered that consuming 1.6g to 2.2g of protein per kg of body weight maximizes muscle protein synthesis, with diminishing returns beyond that threshold.",
        "source": "Men's Health",
        "url": "https://menshealth.com/fitness/protein-study",
        "published_at": datetime.utcnow().isoformat(),
        "virality_score": 9.8,
        "keywords": ["protein", "hypertrophy", "muscle", "nutrition"],
        "selected": True,
    },
    {
        "title": "Why Zone 2 Cardio is the Secret to Elite Endurance and Fat Loss",
        "summary": "Training in Zone 2 (60-70% of max heart rate) builds mitochondrial density and improves metabolic flexibility, making it the most effective way to burn fat and build stamina.",
        "source": "Healthline Fit",
        "url": "https://healthline.com/nutrition/zone-2-cardio",
        "published_at": datetime.utcnow().isoformat(),
        "virality_score": 9.5,
        "keywords": ["cardio", "fat loss", "endurance", "metabolism"],
        "selected": True,
    },
    {
        "title": "Creatine Monohydrate: The Most Studied Supplement Proven to Boost Strength",
        "summary": "Decades of research confirm that 5g of creatine daily increases ATP regeneration, leading to significant strength gains and improved cognitive function.",
        "source": "Bodybuilding.com",
        "url": "https://bodybuilding.com/creatine-guide",
        "published_at": datetime.utcnow().isoformat(),
        "virality_score": 9.2,
        "keywords": ["creatine", "strength", "supplements", "lifting"],
        "selected": True,
    },
    {
        "title": "The Perfect Push/Pull/Legs Routine for Natural Lifters",
        "summary": "A 6-day PPL split allows for optimal training frequency, ensuring each muscle group is hit twice a week with adequate recovery time for natural athletes.",
        "source": "BarBend",
        "url": "https://barbend.com/ppl-routine",
        "published_at": datetime.utcnow().isoformat(),
        "virality_score": 8.9,
        "keywords": ["workout", "training", "bodybuilding", "recovery"],
        "selected": True,
    },
    {
        "title": "How Sleep Deprivation Kills Your Testosterone and Muscle Growth",
        "summary": "Getting less than 7 hours of sleep can plummet testosterone levels by 15% and significantly impair muscle recovery, rendering intense workouts ineffective.",
        "source": "Breaking Muscle",
        "url": "https://breakingmuscle.com/sleep-testosterone",
        "published_at": datetime.utcnow().isoformat(),
        "virality_score": 8.7,
        "keywords": ["recovery", "testosterone", "muscle", "fitness"],
        "selected": True,
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _story_hash(title: str) -> str:
    return hashlib.md5(title.lower().strip().encode()).hexdigest()


def _keyword_score(text: str) -> float:
    """Score text based on AI keyword density."""
    text_lower = text.lower()
    hits = sum(1 for kw in AI_KEYWORDS if kw.lower() in text_lower)
    return min(hits / 3.0, 3.0)   # cap at 3.0


def _recency_score(published_str: str) -> float:
    """Higher score for more recent articles (max 1 within past 24h)."""
    try:
        if not published_str:
            return 0.5
        pub = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_ago = (now - pub).total_seconds() / 3600
        return max(0.0, 1.0 - (hours_ago / 48.0))
    except Exception:
        return 0.5


def _length_score(text: str) -> float:
    """Score based on content length (prefers more substantive articles)."""
    length = len(text or "")
    return min(length / 500.0, 1.0)


def _compute_virality(title: str, summary: str, published_at: str) -> float:
    kw  = _keyword_score(f"{title} {summary}")
    rec = _recency_score(published_at)
    lng = _length_score(summary)
    # Weighted formula
    score = (kw * 3.5) + (rec * 4.0) + (lng * 2.5)
    return round(min(score, 10.0), 2)


def _parse_entry(entry, source_name: str) -> Optional[dict]:
    """Parse a feedparser entry into a normalized story dict."""
    try:
        title   = entry.get("title", "").strip()
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", entry.get("description", ""))).strip()
        url     = entry.get("link", "")
        if not title or not url:
            return None

        # Parse date
        published_at = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()

        # Extract matched keywords
        combined = f"{title} {summary}".lower()
        matched_kw = [kw for kw in AI_KEYWORDS if kw.lower() in combined]

        return {
            "title":        title,
            "summary":      summary[:600],
            "source":       source_name,
            "url":          url,
            "published_at": published_at,
            "keywords":     matched_kw,
            "virality_score": _compute_virality(title, summary, published_at),
            "selected":     False,
        }
    except Exception as e:
        logger.debug("Failed to parse entry: %s", e)
        return None


# ─── Fetchers ─────────────────────────────────────────────────────────────────

def _fetch_rss_stories() -> list[dict]:
    """Fetch stories from all configured RSS feeds."""
    stories = []
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            logger.info("Fetching RSS: %s", source_name)
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                story = _parse_entry(entry, source_name)
                if story:
                    stories.append(story)
            time.sleep(0.3)   # be polite
        except Exception as e:
            logger.warning("RSS fetch failed for %s: %s", source_name, e)
    return stories


def _fetch_newsapi_stories() -> list[dict]:
    """Fetch stories from NewsAPI.org as supplementary source."""
    if not NEWSAPI_KEY:
        return []
    stories = []
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "fitness OR bodybuilding OR muscle OR workout OR nutrition OR gym",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": NEWSAPI_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for art in data.get("articles", []):
            title     = art.get("title", "").strip()
            summary   = art.get("description", "").strip()
            url_link  = art.get("url", "")
            source    = art.get("source", {}).get("name", "NewsAPI")
            pub_at    = art.get("publishedAt", "")
            if not title or not url_link:
                continue
            combined  = f"{title} {summary}".lower()
            matched_kw = [kw for kw in AI_KEYWORDS if kw.lower() in combined]
            stories.append({
                "title":          title,
                "summary":        summary[:600],
                "source":         source,
                "url":            url_link,
                "published_at":   pub_at,
                "keywords":       matched_kw,
                "virality_score": _compute_virality(title, summary, pub_at),
                "selected":       False,
            })
    except Exception as e:
        logger.warning("NewsAPI fetch failed: %s", e)
    return stories


# ─── Main Fetch Function ──────────────────────────────────────────────────────

def fetch_top_ai_news() -> list[dict]:
    """
    Fetch, deduplicate, and rank fitness news.
    Returns the top 5 stories with virality scores.
    """
    if DEMO_MODE:
        logger.info("[DEMO MODE] Returning mock fitness news stories")
        stories = DEMO_STORIES.copy()
        for i, s in enumerate(stories):
            s["rank"] = i + 1
            s["selected"] = True
        return stories

    logger.info("Fetching fitness news from all sources...")

    # Gather from all sources
    all_stories: list[dict] = []
    all_stories.extend(_fetch_rss_stories())
    all_stories.extend(_fetch_newsapi_stories())

    logger.info("Collected %d raw stories", len(all_stories))

    # Filter: must contain at least one fitness keyword
    filtered = [s for s in all_stories if s.get("keywords")]

    import database as db
    recent_titles = db.get_recent_story_titles(days=7)
    
    # Deduplicate by title hash and skip already processed
    seen_hashes: set[str] = set()
    unique: list[dict] = []
    for s in filtered:
        h = _story_hash(s["title"])
        if h not in seen_hashes and s["title"] not in recent_titles:
            seen_hashes.add(h)
            unique.append(s)

    logger.info("After dedup: %d unique fitness stories", len(unique))

    # Sort by virality_score descending
    ranked = sorted(unique, key=lambda x: x["virality_score"], reverse=True)

    # Take top 5
    top5 = ranked[:5]
    for i, s in enumerate(top5):
        s["rank"] = i + 1
        s["selected"] = True

    logger.info("Selected top %d stories", len(top5))
    for s in top5:
        logger.info("  #%d [%.1f] %s — %s", s["rank"], s["virality_score"], s["source"], s["title"][:60])

    return top5
