"""
image_engine.py — Premium Instagram carousel generator using Pillow.
Creates 5-slide dark neon carousels per post with enterprise-grade design.
"""

import os
import math
import logging
import random
import urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from config import (
    IMG_WIDTH, IMG_HEIGHT, GENERATED_DIR, THUMBNAIL_DIR,
    FONTS_DIR, COLORS, BRAND_NAME, SLIDES_COUNT
)

logger = logging.getLogger(__name__)

# ─── Font URLs (Google Fonts TTF) ─────────────────────────────────────────────
FONT_URLS = {
    "bold":       "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bslnt%2Cwght%5D.ttf",
    "montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
}

# Alternative direct static font URLs
FONT_URLS_ALT = {
    "Inter-Bold.ttf":        "https://cdn.jsdelivr.net/npm/@fontsource/inter@5/files/inter-latin-700-normal.woff2",
    "Inter-Regular.ttf":     "https://cdn.jsdelivr.net/npm/@fontsource/inter@5/files/inter-latin-400-normal.woff2",
    "Montserrat-Bold.ttf":   "https://cdn.jsdelivr.net/npm/@fontsource/montserrat@5/files/montserrat-latin-800-normal.woff2",
    "Montserrat-Regular.ttf":"https://cdn.jsdelivr.net/npm/@fontsource/montserrat@5/files/montserrat-latin-400-normal.woff2",
}

FALLBACK_FONT = None   # PIL default


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load font from FONTS_DIR, falling back to PIL default."""
    names = ["Montserrat-Bold.ttf", "Inter-Bold.ttf"] if bold else ["Inter-Regular.ttf", "Montserrat-Regular.ttf"]
    for name in names:
        path = FONTS_DIR / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    # Try system fonts on Windows
    system_fonts = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for sf in system_fonts:
        if os.path.exists(sf):
            try:
                return ImageFont.truetype(sf, size)
            except Exception:
                pass
    return ImageFont.load_default()


def download_fonts():
    """Attempt to download Google Fonts for better rendering."""
    targets = {
        "Inter-Bold.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Bold.ttf",
        "Inter-Regular.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Regular.ttf",
        "Montserrat-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
        "Montserrat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Regular.ttf",
    }
    for fname, url in targets.items():
        target = FONTS_DIR / fname
        if not target.exists():
            try:
                logger.info("Downloading font: %s", fname)
                urllib.request.urlretrieve(url, str(target))
                logger.info("Font downloaded: %s", fname)
            except Exception as e:
                logger.warning("Font download failed for %s: %s", fname, e)


# ─── Drawing Primitives ────────────────────────────────────────────────────────

def _rgba(color_key: str, alpha: int = 255) -> tuple:
    rgb = COLORS.get(color_key, (255, 255, 255))
    return (*rgb, alpha)


def _draw_gradient_bg(img: Image.Image, color1_key: str, color2_key: str, direction: str = "vertical"):
    """Draw a smooth gradient background."""
    draw = ImageDraw.Draw(img)
    c1 = COLORS[color1_key]
    c2 = COLORS[color2_key]
    w, h = img.size
    if direction == "vertical":
        for y in range(h):
            t = y / h
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
    else:
        for x in range(w):
            t = x / w
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))


def _draw_glow_circle(overlay: Image.Image, cx: int, cy: int, radius: int, color: tuple, alpha_max: int = 60):
    """Draw a soft glowing circle on an RGBA overlay."""
    draw = ImageDraw.Draw(overlay)
    for r in range(radius, 0, -max(1, radius // 30)):
        t = 1 - (r / radius)
        a = int(alpha_max * t * t)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, a),
        )


def _draw_neon_line(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int,
                    color: tuple, width: int = 2, glow: bool = True):
    """Draw a neon-glowing line."""
    if glow:
        for w in range(width + 6, width - 1, -2):
            a = max(20, 180 - w * 25)
            draw.line([(x1, y1), (x2, y2)], fill=(*color, a), width=w)
    draw.line([(x1, y1), (x2, y2)], fill=(*color, 255), width=width)


def _draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill: tuple = None, outline: tuple = None, width: int = 1):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)


def _safe_text(text: str) -> str:
    """Sanitize text for ffmpeg drawtext: remove special chars, limit length."""
    import re
    # Remove emojis and non-ASCII
    text = text.encode("ascii", "ignore").decode("ascii")
    # Escape ffmpeg special chars
    text = text.replace("\\", "").replace("'", "").replace(":", " ").replace("%", "pct")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:60]


def _make_caption_overlay(title: str, body: str, slug: str, clip_idx: int,
                           W: int = 1080, H: int = 1920) -> str:
    """
    Use PIL to render a transparent PNG overlay with:
    - Bottom scrim (dark gradient)
    - Orange accent bar
    - Title text (white, bold)
    - Body text (orange)
    - Brand badge (top left)
    Returns path to the PNG overlay.
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    scrim_y = int(H * 0.62)

    # Gradient scrim: fade from transparent to black
    for y in range(scrim_y, H):
        t = (y - scrim_y) / (H - scrim_y)
        alpha = int(180 * min(1.0, t * 1.5))
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

    # Orange accent bar
    draw.rectangle([(0, scrim_y), (W, scrim_y + 8)], fill=(255, 80, 0, 255))

    font_title  = _load_font(72, bold=True)
    font_body   = _load_font(48)
    font_badge  = _load_font(36, bold=True)

    # Title — centered, white
    if title:
        title_lines = _wrap_text(title, font_title, W - 80, draw)
        y = scrim_y + 30
        for line in title_lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=font_title)
            lw = bbox[2] - bbox[0]
            x = (W - lw) // 2
            # Shadow
            draw.text((x + 3, y + 3), line, font=font_title, fill=(0, 0, 0, 200))
            draw.text((x, y), line, font=font_title, fill=(255, 255, 255, 255))
            y += bbox[3] - bbox[1] + 10

    # Body — centered, orange
    if body:
        body_lines = _wrap_text(body, font_body, W - 80, draw)
        y_body = scrim_y + 180
        for line in body_lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=font_body)
            lw = bbox[2] - bbox[0]
            x = (W - lw) // 2
            draw.text((x + 2, y_body + 2), line, font=font_body, fill=(0, 0, 0, 180))
            draw.text((x, y_body), line, font=font_body, fill=(255, 136, 0, 255))
            y_body += bbox[3] - bbox[1] + 6

    # Brand badge removed — no brand name on reels

    overlay_path = str(GENERATED_DIR / f"{slug}_overlay{clip_idx}.png")
    overlay.save(overlay_path, "PNG")
    return overlay_path


def generate_reel_video(slide_paths: list[str], slug: str, content: dict = None) -> str:
    """
    Generate a cinematic fitness Reel:
    - Uses content-type specific background image (hot take = intense cardio, etc.)
    - Pass 1: Ken Burns zoom + fade on background
    - Pass 2: PIL caption overlay composited via ffmpeg
    - Final: Concat all clips, mix in lo-fi background music
    Returns (video_path, thumbnail_path) tuple.
    """
    import subprocess, shutil
    from config import REEL_WIDTH, REEL_HEIGHT, GYM_BG_DIR, MUSIC_DIR

    content_type = content.get("content_type", "hot_take") if content else "hot_take"
    video_path   = GENERATED_DIR / f"{slug}_reel.mp4"
    tmp_clips    = []

    # ── Pick content-type specific background ─────────────────────────────────
    # Map each content type to a dedicated background for visual relevance
    TYPE_BG_MAP = {
        "hot_take":       "hot_take_bg.png",
        "quick_tip":      "quick_tip_bg.png",
        "save_list":      "save_list_bg.png",
        "myth_buster":    "myth_buster_bg.png",
        "meme_relatable": "meme_relatable_bg.png",
        "transformation": "transformation_bg.png",
    }
    primary_bg = GYM_BG_DIR / TYPE_BG_MAP.get(content_type, "hot_take_bg.png")
    if not primary_bg.exists():
        # Fallback to any available gym background
        fallbacks = sorted(GYM_BG_DIR.glob("gym_bg_*.png")) + sorted(GYM_BG_DIR.glob("*.png"))
        primary_bg = fallbacks[0] if fallbacks else Path(slide_paths[0])

    # Use the primary bg for ALL slides so the visual is consistent per post
    # But vary pan direction per slide for dynamic feel
    bg_images = [primary_bg] * len(slide_paths)

    # Build per-slide text
    if content:
        headline = content.get("headline", "")
        bullets  = content.get("bullet_points", [])
        stat     = content.get("stat_highlight", "")
        cta      = content.get("cta", "Follow  for daily fitness")
        slides_text = [
            {"title": headline[:70],                              "body": ""},
            {"title": bullets[0][:60] if bullets else "",         "body": stat[:60]},
            {"title": bullets[1][:60] if len(bullets) > 1 else "", "body": ""},
            {"title": bullets[2][:60] if len(bullets) > 2 else "", "body": ""},
            {"title": cta[:70],                                   "body": "#  #Fitness  #GymLife"},
        ]
    else:
        slides_text = [{"title": "", "body": ""} for _ in slide_paths]

    FPS, DURATION = 30, 4
    FRAMES = FPS * DURATION
    W, H   = REEL_WIDTH, REEL_HEIGHT

    # Pan directions cycle per slide: center, left→right, right→left, zoom-out, center
    pan_configs = [
        {"z": "1+0.05*on/{F}", "x": "iw/2-(iw/zoom/2)",            "y": "ih/2-(ih/zoom/2)"},
        {"z": "1+0.04*on/{F}", "x": "0",                            "y": "ih/2-(ih/zoom/2)"},
        {"z": "1+0.04*on/{F}", "x": "iw-(iw/zoom)",                 "y": "ih/2-(ih/zoom/2)"},
        {"z": "1+0.03*on/{F}", "x": "iw/2-(iw/zoom/2)",            "y": "0"},
        {"z": "1+0.06*on/{F}", "x": "iw/2-(iw/zoom/2)",            "y": "ih-(ih/zoom)"},
    ]

    W, H   = REEL_WIDTH, REEL_HEIGHT

    for i, (src_path, txt) in enumerate(zip(slide_paths, slides_text)):
        pan    = pan_configs[i % len(pan_configs)]
        z_expr = pan["z"].replace("{F}", str(FRAMES))
        x_expr = pan["x"]
        y_expr = pan["y"]
        bg_path   = str(bg_images[i % len(bg_images)])
        zoom_clip = GENERATED_DIR / f"{slug}_zoom{i}.mp4"
        tmp_clip  = GENERATED_DIR / f"{slug}_clip{i}.mp4"
        tmp_clips.append(str(tmp_clip))

        # ── PASS 1: Ken Burns zoom on content-specific background ─────────────
        zoom_vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={FRAMES}:s={W}x{H}:fps={FPS},"
            f"fade=t=in:st=0:d=0.4,"
            f"fade=t=out:st={DURATION - 0.4}:d=0.4"
        )
        try:
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", bg_path,
                "-t", str(DURATION), "-vf", zoom_vf,
                "-fps_mode", "cfr", "-r", str(FPS),
                "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                str(zoom_clip),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            # Fallback: static
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", bg_path, "-t", str(DURATION),
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                "-fps_mode", "cfr", "-r", str(FPS),
                "-pix_fmt", "yuv420p", "-c:v", "libx264",
                str(zoom_clip),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # ── PASS 2: PIL caption overlay ───────────────────────────────────────
        overlay_path = None
        if txt.get("title"):
            try:
                overlay_path = _make_caption_overlay(
                    txt["title"], txt.get("body", ""), slug, i, W, H
                )
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", str(zoom_clip),
                    "-i", overlay_path,
                    "-filter_complex", "[0:v][1:v]overlay=0:0",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    str(tmp_clip),
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                logger.warning("Caption overlay failed for clip %d: %s — using zoom only", i, e)
                shutil.copy(str(zoom_clip), str(tmp_clip))
        else:
            shutil.copy(str(zoom_clip), str(tmp_clip))

        # Cleanup temp files
        for f in [str(zoom_clip), overlay_path]:
            if f:
                try: os.remove(f)
                except Exception: pass

    # ── Concatenate all clips ─────────────────────────────────────────────────
    concat_file = GENERATED_DIR / f"{slug}_concat.txt"
    with open(concat_file, "w") as f:
        for cp in tmp_clips:
            f.write(f"file '{cp.replace(chr(92), '/')}'\n")

    silent_video = GENERATED_DIR / f"{slug}_silent.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(silent_video),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ── NO background music — keep reel silent so Instagram allows trending audio ──
    # Instagram only lets you add trending sounds to reels that have NO baked-in audio.
    # Adding trending sounds in the app gives 3-5x more reach via the algorithm boost.
    shutil.copy(str(silent_video), str(video_path))
    logger.info("Reel saved silent — add trending sound in Instagram app for max reach")

    # ── Cleanup + return ──────────────────────────────────────────────────────
    for cp in tmp_clips:
        try: os.remove(cp)
        except Exception: pass
    for f in [str(silent_video), str(concat_file)]:
        try: os.remove(f)
        except Exception: pass

    # ── Generate reel thumbnail from the primary background + slide 1 overlay ─
    reel_thumb_path = str(GENERATED_DIR / f"{slug}_reel_thumb.jpg")
    try:
        thumb_overlay = _make_caption_overlay(
            slides_text[0].get("title", ""), "", slug + "_thumb", 99, W, H
        )
        bg_img = Image.open(str(primary_bg)).convert("RGB")
        bg_img = bg_img.resize((W, H), Image.LANCZOS)
        overlay_img = Image.open(thumb_overlay).convert("RGBA")
        bg_rgba = bg_img.convert("RGBA")
        composited = Image.alpha_composite(bg_rgba, overlay_img).convert("RGB")
        composited.save(reel_thumb_path, "JPEG", quality=95)
        try: os.remove(thumb_overlay)
        except Exception: pass
        logger.info("Reel thumbnail saved: %s", reel_thumb_path)
    except Exception as e:
        logger.warning("Reel thumbnail generation failed: %s", e)
        reel_thumb_path = ""

    return str(video_path), reel_thumb_path


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text_with_shadow(draw: ImageDraw.Draw, xy: tuple, text: str, font, fill: tuple,
                            shadow_color: tuple = (0, 0, 0, 180), shadow_offset: int = 3):
    """Draw text with a drop shadow for depth."""
    x, y = xy
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_circuit_pattern(draw: ImageDraw.Draw, width: int, height: int, color: tuple, alpha: int = 15):
    """Draw subtle circuit-board-like grid lines for tech aesthetic."""
    c = (*color, alpha)
    step = 80
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=c, width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=c, width=1)


def _add_noise_texture(img: Image.Image, intensity: float = 0.04) -> Image.Image:
    """Add very subtle noise for a premium printed texture feel."""
    import random as rnd
    pixels = img.load()
    w, h = img.size
    for _ in range(int(w * h * intensity)):
        x = rnd.randint(0, w - 1)
        y = rnd.randint(0, h - 1)
        p = pixels[x, y]
        d = rnd.randint(-15, 15)
        pixels[x, y] = (
            max(0, min(255, p[0] + d)),
            max(0, min(255, p[1] + d)),
            max(0, min(255, p[2] + d)),
        ) if len(p) == 3 else (
            max(0, min(255, p[0] + d)),
            max(0, min(255, p[1] + d)),
            max(0, min(255, p[2] + d)),
            p[3],
        )
    return img


# ─── Slide Templates ──────────────────────────────────────────────────────────

ACCENT_PALETTE = [
    COLORS["accent_cyan"],
    COLORS["accent_violet"],
    COLORS["accent_magenta"],
    COLORS["accent_gold"],
]


def _get_accent(rank: int) -> tuple:
    return ACCENT_PALETTE[rank % len(ACCENT_PALETTE)]


def _create_base_image(accent_color: tuple) -> Image.Image:
    """Create the base dark gradient canvas with ambient glow."""
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
    _draw_gradient_bg(img, "bg_primary", "bg_secondary", "vertical")

    # Ambient glow overlay
    overlay = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0, 0))
    _draw_glow_circle(overlay, IMG_WIDTH // 2, IMG_HEIGHT // 4, 500, accent_color, alpha_max=30)
    _draw_glow_circle(overlay, IMG_WIDTH // 4, IMG_HEIGHT - 200, 300, COLORS["accent_violet"], alpha_max=20)
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)

    # Circuit pattern
    draw_tmp = ImageDraw.Draw(img_rgba)
    _draw_circuit_pattern(draw_tmp, IMG_WIDTH, IMG_HEIGHT, accent_color, alpha=8)

    return img_rgba.convert("RGB")


def _draw_header_bar(draw: ImageDraw.Draw, rank: int, source: str, accent: tuple, slide_num: int, total: int):
    """Draw top header with source badge + slide indicator (no brand name)."""
    # Accent pill top-left (design only, no text)
    _draw_rounded_rect(draw, (32, 28, 80, 68), radius=20, fill=(*accent, 30), outline=(*accent, 120), width=1)
    font_sm = _load_font(18, bold=True)

    # Source badge
    if source:
        src_text = source[:20]
        bbox = draw.textbbox((0, 0), src_text, font=font_sm)
        sw = bbox[2] - bbox[0]
        sx = IMG_WIDTH - sw - 60
        _draw_rounded_rect(draw, (sx - 12, 28, sx + sw + 12, 68), radius=20,
                           fill=(255, 255, 255, 12), outline=(255, 255, 255, 40), width=1)
        draw.text((sx, 36), src_text, font=font_sm, fill=COLORS["text_secondary"])

    # Slide indicator dots
    dot_size = 8
    dot_spacing = 18
    total_dots_w = total * dot_spacing
    dot_start_x = (IMG_WIDTH - total_dots_w) // 2
    for i in range(total):
        dx = dot_start_x + i * dot_spacing + dot_size // 2
        dy = 48
        if i == slide_num:
            draw.ellipse([dx - dot_size // 2, dy - dot_size // 2,
                          dx + dot_size // 2, dy + dot_size // 2],
                         fill=(*accent, 255))
        else:
            draw.ellipse([dx - dot_size // 2, dy - dot_size // 2,
                          dx + dot_size // 2, dy + dot_size // 2],
                         fill=(255, 255, 255, 50))


def _draw_rank_badge(draw: ImageDraw.Draw, rank: int, accent: tuple):
    """Draw #N ranking badge."""
    font_rank = _load_font(64, bold=True)
    font_label = _load_font(16)
    label = "TODAY'S TOP STORY"
    rank_text = f"#{rank}"
    draw.text((40, 100), label, font=font_label, fill=(*accent, 150))
    draw.text((40, 118), rank_text, font=font_rank, fill=(*accent, 255))
    # Accent line below badge
    draw.line([(40, 210), (IMG_WIDTH - 40, 210)], fill=(*accent, 60), width=1)


def _draw_footer(draw: ImageDraw.Draw, accent: tuple):
    """Draw bottom footer bar."""
    # Neon separator
    draw.line([(40, IMG_HEIGHT - 90), (IMG_WIDTH - 40, IMG_HEIGHT - 90)], fill=(*accent, 80), width=1)
    # Footer: just swipe hint, no follow text
    # Swipe hint
    swipe_text = "Swipe for more →"
    swipe_font = _load_font(20)
    bbox = draw.textbbox((0, 0), swipe_text, font=swipe_font)
    sw = bbox[2] - bbox[0]
    draw.text((IMG_WIDTH - sw - 40, IMG_HEIGHT - 75), swipe_text, font=swipe_font, fill=(*accent, 160))


# ─── Slide 1: Cover ───────────────────────────────────────────────────────────

def _create_cover_slide(content: dict, story: dict, rank: int) -> Image.Image:
    accent = _get_accent(rank)
    img = _create_base_image(accent)
    draw = ImageDraw.Draw(img)

    _draw_header_bar(draw, rank, story.get("source", ""), accent, 0, SLIDES_COUNT)
    _draw_rank_badge(draw, rank + 1, accent)

    # Headline — large, bold
    font_headline = _load_font(72, bold=True)
    font_sub      = _load_font(32)
    font_stat     = _load_font(26, bold=True)

    headline = content.get("headline", story["title"])
    subline  = content.get("subheadline", "")
    stat     = content.get("stat_highlight", "")

    # Wrap headline
    lines = _wrap_text(headline, font_headline, IMG_WIDTH - 80, draw)
    y = 240
    for line in lines[:3]:
        _draw_text_with_shadow(draw, (40, y), line, font_headline, COLORS["text_primary"])
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        y += bbox[3] - bbox[1] + 10

    # Neon accent line after headline
    y += 18
    draw.line([(40, y), (int(IMG_WIDTH * 0.4), y)], fill=(*accent, 200), width=3)
    y += 30

    # Subheadline
    sub_lines = _wrap_text(subline, font_sub, IMG_WIDTH - 80, draw)
    for sl in sub_lines[:2]:
        draw.text((40, y), sl, font=font_sub, fill=COLORS["text_secondary"])
        bbox = draw.textbbox((0, 0), sl, font=font_sub)
        y += bbox[3] - bbox[1] + 8

    # Stat highlight box
    if stat:
        y += 40
        stat_text = f"⚡  {stat}"
        bbox = draw.textbbox((0, 0), stat_text, font=font_stat)
        sw = bbox[2] - bbox[0]
        _draw_rounded_rect(draw, (38, y - 12, sw + 80, y + 48), radius=12,
                           fill=(*accent, 18), outline=(*accent, 100), width=2)
        draw.text((52, y), stat_text, font=font_stat, fill=(*accent, 230))

    _draw_footer(draw, accent)
    return img


# ─── Slides 2–4: Detail ───────────────────────────────────────────────────────

def _create_detail_slide(content: dict, story: dict, rank: int, slide_num: int) -> Image.Image:
    accent = _get_accent(rank)
    img = _create_base_image(accent)
    draw = ImageDraw.Draw(img)

    _draw_header_bar(draw, rank, story.get("source", ""), accent, slide_num, SLIDES_COUNT)

    bullets = content.get("bullet_points", [])
    font_title = _load_font(48, bold=True)
    font_body  = _load_font(34)
    font_num   = _load_font(80, bold=True)
    font_label = _load_font(20)

    # Big section number
    section_labels = ["", "KEY INSIGHT", "WHAT IT MEANS", "WHY IT MATTERS"]
    label = section_labels[slide_num] if slide_num < len(section_labels) else "DETAILS"
    draw.text((40, 100), label, font=font_label, fill=(*accent, 140))
    draw.text((40, 120), str(slide_num), font=font_num, fill=(*accent, 220))

    # Separator
    draw.line([(40, 230), (IMG_WIDTH - 40, 230)], fill=(*accent, 60), width=1)

    y = 265
    # Bullet for this slide (slide 1→bullet 0, slide 2→bullet 1, slide 3→bullet 2)
    bullet_idx = slide_num - 1
    bullets_to_show = bullets[bullet_idx:bullet_idx + 1] if bullet_idx < len(bullets) else []

    if bullets_to_show:
        bullet_text = bullets_to_show[0]
        # Large featured bullet
        font_featured = _load_font(52, bold=True)
        lines = _wrap_text(bullet_text, font_featured, IMG_WIDTH - 100, draw)
        # Glassmorphism panel
        panel_h = len(lines) * 70 + 80
        _draw_rounded_rect(draw, (30, y - 20, IMG_WIDTH - 30, y + panel_h), radius=24,
                           fill=(255, 255, 255, 6), outline=(*accent, 50), width=1)
        # Accent dot
        draw.ellipse([50, y + 14, 72, y + 36], fill=(*accent, 220))
        for line in lines:
            draw.text((90, y), line, font=font_featured, fill=COLORS["text_primary"])
            bbox = draw.textbbox((0, 0), line, font=font_featured)
            y += bbox[3] - bbox[1] + 12
        y += 60

    # Show remaining bullets smaller
    remaining_bullets = [b for i, b in enumerate(bullets) if i != bullet_idx]
    font_mini = _load_font(28)
    for bullet in remaining_bullets[:2]:
        bullet_lines = _wrap_text(f"→  {bullet}", font_mini, IMG_WIDTH - 90, draw)
        for bl in bullet_lines[:1]:
            draw.text((50, y), bl, font=font_mini, fill=COLORS["text_dim"])
            y += 40

    _draw_footer(draw, accent)
    return img


# ─── Slide 5: CTA ─────────────────────────────────────────────────────────────

def _create_cta_slide(content: dict, story: dict, rank: int) -> Image.Image:
    accent = _get_accent(rank)

    # Special gradient for CTA
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
    draw_bg = ImageDraw.Draw(img)
    # Diagonal gradient via manual fill
    c1 = COLORS["bg_primary"]
    c2 = (accent[0] // 6, accent[1] // 6, accent[2] // 6)
    for y in range(IMG_HEIGHT):
        t = y / IMG_HEIGHT
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw_bg.line([(0, y), (IMG_WIDTH, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0, 0))
    _draw_glow_circle(overlay, IMG_WIDTH // 2, IMG_HEIGHT // 2, 600, accent, alpha_max=40)
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)
    _draw_header_bar(draw, rank, story.get("source", ""), accent, 4, SLIDES_COUNT)
    _draw_circuit_pattern(draw, IMG_WIDTH, IMG_HEIGHT, accent, alpha=10)

    font_big   = _load_font(90, bold=True)
    font_med   = _load_font(44, bold=True)
    font_small = _load_font(30)
    font_cta   = _load_font(36, bold=True)

    # "STAY AHEAD OF THE PACK"
    label1 = "STAY AHEAD"
    label2 = "OF THE PACK."
    y = 280
    draw.text((40, y), label1, font=font_big, fill=COLORS["text_primary"])
    y += 105
    draw.text((40, y), label2, font=font_big, fill=(*accent, 255))
    y += 120

    # Divider
    draw.line([(40, y), (IMG_WIDTH - 40, y)], fill=(*accent, 80), width=2)
    y += 40

    # Sub text
    cta_sub = "Every day. First thing. Free."
    draw.text((40, y), cta_sub, font=font_small, fill=COLORS["text_secondary"])
    y += 60

    # CTA pill button — uses AI-generated CTA, no brand name fallback
    cta_text = content.get("cta", "Follow for daily fitness tips →")
    bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    px, py = 50, 20
    _draw_rounded_rect(draw, (40, y, 40 + bw + px * 2, y + bh + py * 2),
                       radius=50, fill=(*accent, 220), outline=(*accent, 255), width=2)
    draw.text((40 + px, y + py), cta_text, font=font_cta, fill=COLORS["bg_primary"])

    # Hashtag strip at bottom
    y_hash = IMG_HEIGHT - 120
    draw.line([(40, y_hash), (IMG_WIDTH - 40, y_hash)], fill=(*accent, 40), width=1)
    font_hash = _load_font(20)
    hash_text = "#Fitness #Workout #Bodybuilding #GymMotivation #Hypertrophy"
    draw.text((40, y_hash + 15), hash_text, font=font_hash, fill=COLORS["text_dim"])

    return img


# ─── Post Generator ───────────────────────────────────────────────────────────

def generate_carousel(content: dict, story: dict, rank: int, run_date: str) -> dict:
    """
    Generate all 5 carousel slides for one post.
    Returns dict with slide_paths and thumbnail_path.
    """
    slug = f"{run_date}_post{rank + 1}"
    slide_paths = []

    try:
        logger.info("Generating carousel for post #%d: %s", rank + 1, content.get("headline", "")[:40])

        slides = [
            _create_cover_slide(content, story, rank),
            _create_detail_slide(content, story, rank, 1),
            _create_detail_slide(content, story, rank, 2),
            _create_detail_slide(content, story, rank, 3),
            _create_cta_slide(content, story, rank),
        ]

        for i, slide in enumerate(slides):
            path = GENERATED_DIR / f"{slug}_slide{i + 1}.jpg"
            slide.save(str(path), "JPEG", quality=95, optimize=True)
            slide_paths.append(str(path))
            logger.debug("Saved slide %d → %s", i + 1, path)

        # Thumbnail = first slide, resized to 400×500
        thumb = slides[0].copy()
        thumb.thumbnail((400, 500), Image.LANCZOS)
        thumb_path = THUMBNAIL_DIR / f"{slug}_thumb.jpg"
        thumb.save(str(thumb_path), "JPEG", quality=85)

        logger.info("Carousel generated: %d slides for post #%d", len(slide_paths), rank + 1)
        
        # Generate Reel — returns (video_path, reel_thumb_path)
        reel_result   = generate_reel_video(slide_paths, slug, content=content)
        reel_path     = reel_result[0] if isinstance(reel_result, tuple) else reel_result
        reel_thumb    = reel_result[1] if isinstance(reel_result, tuple) and len(reel_result) > 1 else ""
        logger.info("Reel generated: %s (thumb: %s)", reel_path, reel_thumb)

        return {
            "slide_paths":      slide_paths,
            "thumbnail_path":   str(thumb_path),
            "reel_path":        reel_path,
            "reel_thumb_path":  reel_thumb,
        }

    except Exception as e:
        logger.error("Carousel generation failed for post #%d: %s", rank + 1, e)
        raise


def generate_all_carousels(content_list: list[dict], run_date: str) -> list[dict]:
    """Generate carousels for all 5 posts."""
    results = []
    for i, content_item in enumerate(content_list):
        story = content_item.get("story", {})
        paths = generate_carousel(content_item, story, i, run_date)
        content_item.update(paths)
        results.append(content_item)
    return results
