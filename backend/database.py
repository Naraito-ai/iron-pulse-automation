"""
database.py — SQLite persistence layer for the AI Instagram Automation System
All modules read/write through this interface.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS news_stories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date    TEXT NOT NULL,
            rank        INTEGER NOT NULL,
            title       TEXT NOT NULL,
            summary     TEXT,
            source      TEXT,
            url         TEXT,
            published_at TEXT,
            virality_score REAL DEFAULT 0.0,
            keywords    TEXT,
            selected    INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS generated_posts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date        TEXT NOT NULL,
            story_id        INTEGER REFERENCES news_stories(id),
            rank            INTEGER NOT NULL,
            headline        TEXT,
            subheadline     TEXT,
            caption         TEXT,
            hashtags        TEXT,
            cta             TEXT,
            bullet_points   TEXT,
            slide_paths     TEXT,
            thumbnail_path  TEXT,
            reel_thumb_path TEXT,
            image_urls      TEXT,
            reel_url        TEXT,
            status          TEXT DEFAULT 'draft',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS published_posts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id         INTEGER REFERENCES generated_posts(id),
            ig_media_id     TEXT,
            ig_permalink    TEXT,
            published_at    TEXT,
            status          TEXT DEFAULT 'published',
            error_message   TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analytics_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            published_post_id INTEGER REFERENCES published_posts(id),
            ig_media_id     TEXT,
            likes           INTEGER DEFAULT 0,
            comments        INTEGER DEFAULT 0,
            shares          INTEGER DEFAULT 0,
            saves           INTEGER DEFAULT 0,
            reach           INTEGER DEFAULT 0,
            impressions     INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0.0,
            viral_score     REAL DEFAULT 0.0,
            snapshot_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS automation_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date    TEXT,
            level       TEXT NOT NULL,
            module      TEXT,
            message     TEXT NOT NULL,
            details     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS run_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date    TEXT NOT NULL,
            status      TEXT DEFAULT 'running',
            stories_fetched INTEGER DEFAULT 0,
            posts_generated INTEGER DEFAULT 0,
            posts_published INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0.0,
            started_at  TEXT DEFAULT (datetime('now')),
            finished_at TEXT
        );
        """)
    logger.info("Database initialized at %s", DB_PATH)


# ─── News Stories ─────────────────────────────────────────────────────────────

def save_news_stories(run_date: str, stories: list[dict]) -> list[int]:
    ids = []
    with get_db() as conn:
        for story in stories:
            cur = conn.execute("""
                INSERT INTO news_stories
                    (run_date, rank, title, summary, source, url, published_at,
                     virality_score, keywords, selected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_date, story.get("rank", 0), story["title"],
                story.get("summary", ""), story.get("source", ""),
                story.get("url", ""), story.get("published_at", ""),
                story.get("virality_score", 0.0),
                json.dumps(story.get("keywords", [])),
                1 if story.get("selected") else 0,
            ))
            ids.append(cur.lastrowid)
    return ids


def get_latest_news(run_date: str = None) -> list[dict]:
    with get_db() as conn:
        if run_date:
            rows = conn.execute(
                "SELECT * FROM news_stories WHERE run_date=? ORDER BY rank",
                (run_date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM news_stories ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
        return [dict(r) for r in rows]


# ─── Generated Posts ──────────────────────────────────────────────────────────

def save_generated_post(run_date: str, story_id: int, data: dict) -> int:
    with get_db() as conn:
        # Add reel_thumb_path column if it doesn't exist (migration)
        try:
            conn.execute("ALTER TABLE generated_posts ADD COLUMN reel_thumb_path TEXT DEFAULT ''")
        except Exception:
            pass  # Column already exists
        cur = conn.execute("""
            INSERT INTO generated_posts
                (run_date, story_id, rank, headline, subheadline, caption,
                 hashtags, cta, bullet_points, slide_paths, thumbnail_path,
                 reel_thumb_path, image_urls, reel_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_date, story_id, data.get("rank", 0),
            data.get("headline", ""), data.get("subheadline", ""),
            data.get("caption", ""), data.get("hashtags", ""),
            data.get("cta", ""),
            json.dumps(data.get("bullet_points", [])),
            json.dumps(data.get("slide_paths", [])),
            data.get("thumbnail_path", ""),
            data.get("reel_thumb_path", ""),
            json.dumps(data.get("image_urls", [])),
            data.get("reel_url", ""),
            "draft",
        ))
        return cur.lastrowid


def get_generated_posts(run_date: str = None) -> list[dict]:
    with get_db() as conn:
        if run_date:
            rows = conn.execute(
                "SELECT * FROM generated_posts WHERE run_date=? ORDER BY rank",
                (run_date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM generated_posts ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for field in ("bullet_points", "slide_paths", "image_urls"):
                try:
                    d[field] = json.loads(d[field] or "[]")
                except Exception:
                    d[field] = []
            # Derive reel_thumb_url from the stored path
            rtp = d.get("reel_thumb_path", "")
            if rtp:
                from pathlib import Path as _Path
                from config import IMAGE_HOST_URL
                d["reel_thumb_url"] = f"{IMAGE_HOST_URL}/generated/{_Path(rtp).name}"
            else:
                d["reel_thumb_url"] = ""
            result.append(d)
        return result


def update_post_status(post_id: int, status: str):
    with get_db() as conn:
        conn.execute("UPDATE generated_posts SET status=? WHERE id=?", (status, post_id))

def update_draft_content(post_id: int, updates: dict):
    with get_db() as conn:
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values())
        values.append(post_id)
        conn.execute(f"UPDATE generated_posts SET {set_clause} WHERE id=?", tuple(values))


# ─── Published Posts ──────────────────────────────────────────────────────────

def save_published_post(post_id: int, ig_media_id: str, permalink: str = "", error: str = "") -> int:
    status = "published" if ig_media_id else "failed"
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO published_posts
                (post_id, ig_media_id, ig_permalink, published_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (post_id, ig_media_id, permalink, datetime.utcnow().isoformat(), status, error))
        return cur.lastrowid


def get_published_posts(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM published_posts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Analytics ────────────────────────────────────────────────────────────────

def save_analytics(pub_post_id: int, ig_media_id: str, metrics: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO analytics_snapshots
                (published_post_id, ig_media_id, likes, comments, shares, saves,
                 reach, impressions, engagement_rate, viral_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pub_post_id, ig_media_id,
            metrics.get("likes", 0), metrics.get("comments", 0),
            metrics.get("shares", 0), metrics.get("saves", 0),
            metrics.get("reach", 0), metrics.get("impressions", 0),
            metrics.get("engagement_rate", 0.0), metrics.get("viral_score", 0.0),
        ))


def get_analytics(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM analytics_snapshots ORDER BY snapshot_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Automation Logs ──────────────────────────────────────────────────────────

def log_event(level: str, module: str, message: str, details: str = "", run_date: str = ""):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO automation_logs (run_date, level, module, message, details)
            VALUES (?, ?, ?, ?, ?)
        """, (run_date or datetime.utcnow().strftime("%Y-%m-%d"), level, module, message, details))


def get_logs(limit: int = 100, run_date: str = None) -> list[dict]:
    with get_db() as conn:
        if run_date:
            rows = conn.execute(
                "SELECT * FROM automation_logs WHERE run_date=? ORDER BY created_at DESC LIMIT ?",
                (run_date, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM automation_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ─── Run History ──────────────────────────────────────────────────────────────

def start_run(run_date: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO run_history (run_date, status) VALUES (?, 'running')", (run_date,)
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str, stats: dict):
    with get_db() as conn:
        conn.execute("""
            UPDATE run_history SET
                status=?, stories_fetched=?, posts_generated=?, posts_published=?,
                error_count=?, duration_seconds=?, finished_at=datetime('now')
            WHERE id=?
        """, (
            status, stats.get("stories_fetched", 0), stats.get("posts_generated", 0),
            stats.get("posts_published", 0), stats.get("error_count", 0),
            stats.get("duration_seconds", 0.0), run_id,
        ))


def get_run_history(limit: int = 10) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM run_history ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
