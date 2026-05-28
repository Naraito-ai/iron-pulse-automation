"""
image_server.py — Local HTTP server for hosting generated carousel images.
Makes images accessible at public URLs for Instagram Graph API.
"""

import os
import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from config import IMAGE_SERVER_PORT, GENERATED_DIR, BACKEND_DIR

logger = logging.getLogger(__name__)

_server_instance: HTTPServer | None = None
_server_thread: threading.Thread | None = None


class QuietHandler(SimpleHTTPRequestHandler):
    """Silent file handler — serves files without request log spam."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BACKEND_DIR / "assets"), **kwargs)

    def log_message(self, format, *args):
        pass   # suppress per-request logging


def start_image_server():
    """Start the image HTTP server in a background daemon thread."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        logger.info("Image server already running on port %d", IMAGE_SERVER_PORT)
        return

    try:
        _server_instance = HTTPServer(("0.0.0.0", IMAGE_SERVER_PORT), QuietHandler)
        _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        _server_thread.start()
        logger.info("Image server started → http://localhost:%d", IMAGE_SERVER_PORT)
    except OSError as e:
        logger.error("Failed to start image server: %s", e)


def stop_image_server():
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance = None
        logger.info("Image server stopped")


def get_image_urls(slide_paths: list[str]) -> list[str]:
    """Upload images to Catbox to ensure public HTTP URLs without warning screens."""
    import requests
    urls = []
    logger.info("Uploading %d slides to Catbox...", len(slide_paths))
    for i, path in enumerate(slide_paths):
        try:
            with open(path, 'rb') as f:
                r = requests.post('https://catbox.moe/user/api.php', files={'fileToUpload': f}, data={'reqtype': 'fileupload'}, timeout=30)
                url = r.text.strip()
                if not url.startswith('http'):
                    logger.warning("Catbox returned non-URL: %s. Falling back to local.", url)
                    from config import IMAGE_HOST_URL
                    filename = Path(path).name
                    url = f"{IMAGE_HOST_URL}/generated/{filename}"
                urls.append(url)
                logger.debug("Uploaded slide %d/%d -> %s", i + 1, len(slide_paths), url)
        except Exception as e:
            logger.error("Failed to upload %s: %s", path, e)
            from config import IMAGE_HOST_URL
            filename = Path(path).name
            urls.append(f"{IMAGE_HOST_URL}/generated/{filename}")
    return urls


def get_reel_url(reel_path: str) -> str:
    """Upload MP4 to Catbox to ensure public HTTP URLs without warning screens."""
    import requests
    logger.info("Uploading reel to Catbox...")
    try:
        with open(reel_path, 'rb') as f:
            r = requests.post('https://catbox.moe/user/api.php', files={'fileToUpload': f}, data={'reqtype': 'fileupload'}, timeout=60)
            url = r.text.strip()
            if not url.startswith('http'):
                logger.warning("Catbox returned non-URL: %s. Falling back to local.", url)
                from config import IMAGE_HOST_URL
                filename = Path(reel_path).name
                url = f"{IMAGE_HOST_URL}/generated/{filename}"
            logger.debug("Uploaded reel -> %s", url)
            return url
    except Exception as e:
        logger.error("Failed to upload %s: %s", reel_path, e)
        from config import IMAGE_HOST_URL
        filename = Path(reel_path).name
        return f"{IMAGE_HOST_URL}/generated/{filename}"


def get_reel_thumb_url(thumb_path: str) -> str:
    """Return a public URL for the reel thumbnail JPEG (served via local image server)."""
    if not thumb_path:
        return ""
    from config import IMAGE_HOST_URL
    filename = Path(thumb_path).name
    return f"{IMAGE_HOST_URL}/generated/{filename}"
