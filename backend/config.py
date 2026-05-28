"""
config.py — Central configuration manager for AI Instagram Automation System
Loads all environment variables and provides typed constants.
"""

import os
import pytz
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# ─── Paths ────────────────────────────────────────────────────────────────────
BACKEND_DIR   = Path(__file__).parent
ASSETS_DIR    = BACKEND_DIR / "assets"
GENERATED_DIR = ASSETS_DIR / "generated"
THUMBNAIL_DIR = ASSETS_DIR / "thumbnails"
FONTS_DIR     = ASSETS_DIR / "fonts"
DATA_DIR      = BACKEND_DIR / "data"
MUSIC_DIR     = ASSETS_DIR / "music"
GYM_BG_DIR    = ASSETS_DIR / "gym_backgrounds"

for d in [GENERATED_DIR, THUMBNAIL_DIR, FONTS_DIR, DATA_DIR, MUSIC_DIR, GYM_BG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "automation.db"

# ─── Mode ─────────────────────────────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# ─── News Sources ─────────────────────────────────────────────────────────────
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

RSS_FEEDS = {
    "Bodybuilding.com": "https://www.bodybuilding.com/rss/articles",
    "Men's Health":     "https://www.menshealth.com/rss/all.xml",
    "Breaking Muscle":  "https://breakingmuscle.com/feed/",
    "BarBend":          "https://barbend.com/feed/",
    "Healthline Fit":   "https://www.healthline.com/nutrition/feed",
}

AI_KEYWORDS = [
    "workout", "muscle", "hypertrophy", "protein", "fitness", "gym", "nutrition",
    "strength", "lifting", "bodybuilding", "diet", "cardio", "recovery", "supplements",
    "creatine", "training", "exercise", "weight loss", "fat loss", "metabolism",
    "testosterone", "endurance", "powerlifting", "crossfit", "calisthenics",
]

# ─── AI Writer ────────────────────────────────────────────────────────────────
AI_PROVIDER   = os.getenv("AI_PROVIDER", "gemini")   # gemini | openai
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJcg") # Default voice Adam

# ─── Instagram / Meta ─────────────────────────────────────────────────────────
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.getenv("INSTAGRAM_USER_ID", "")
FACEBOOK_PAGE_ID       = os.getenv("FACEBOOK_PAGE_ID", "")
GRAPH_API_VERSION      = "v21.0"
GRAPH_API_BASE         = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# ─── Image Hosting ────────────────────────────────────────────────────────────
IMAGE_HOST_URL       = os.getenv("IMAGE_HOST_URL", "http://localhost:8888")
IMAGE_SERVER_PORT    = int(os.getenv("IMAGE_SERVER_PORT", "8888"))

# ─── Image Dimensions ────────────────────────────────────────────────────────
# Carousel: 4:5 portrait
IMG_WIDTH    = 1080
IMG_HEIGHT   = 1350
# Reel: 9:16 full vertical
REEL_WIDTH   = 720
REEL_HEIGHT  = 1280
SLIDES_COUNT = 5

# ─── Scheduler ────────────────────────────────────────────────────────────────
SCHEDULE_HOUR   = int(os.getenv("SCHEDULE_HOUR", "9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
TIMEZONE        = pytz.timezone("Asia/Kolkata")   # IST — change as needed

# ─── API Server ───────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ─── Design Tokens ────────────────────────────────────────────────────────────
BRAND_NAME = ""

COLORS = {
    "bg_primary":    (10,  10,  10),      # Deep black
    "bg_secondary":  (20,  20,  20),      # Dark charcoal
    "bg_card":       (25,  25,  28),      # Card bg
    "accent_cyan":   (255, 85,  0),       # Neon orange
    "accent_violet": (255, 40,  0),       # Deep red
    "accent_magenta":(255, 120, 0),       # Bright orange
    "accent_gold":   (255, 196, 0),       # Premium gold
    "text_primary":  (255, 255, 255),     # Pure white
    "text_secondary":(180, 180, 180),     # Muted grey
    "text_dim":      (100, 100, 100),     # Dim
    "success":       (0,   255, 136),     # Neon green
    "warning":       (255, 165, 0),       # Orange
    "error":         (255, 50,  80),      # Red
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
