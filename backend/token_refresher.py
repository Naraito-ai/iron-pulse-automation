"""
token_refresher.py — Auto-refreshes the Meta long-lived access token.

Meta long-lived tokens last 60 days. This module:
1. Checks the token expiry
2. Refreshes it every 50 days automatically (before it expires)
3. Saves the new token back to the .env file
4. Sends a log alert so you know it happened
"""

import os
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / ".env"

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

# Refresh when less than this many days remain
REFRESH_THRESHOLD_DAYS = 15


def get_token_info(access_token: str) -> dict:
    """
    Check the current token's validity and expiry.
    Returns dict with: is_valid, expires_at (datetime or None), days_remaining
    """
    import os
    app_id = os.getenv("META_APP_ID", "")
    app_secret = os.getenv("META_APP_SECRET", "")
    
    # Facebook requires an App Token to inspect a User Token
    auth_token = f"{app_id}|{app_secret}" if (app_id and app_secret) else access_token

    try:
        # Use debug_token endpoint to inspect the token
        app_token_url = f"{GRAPH_API_BASE}/debug_token"
        resp = requests.get(app_token_url, params={
            "input_token": access_token,
            "access_token": auth_token,
        }, timeout=15)
        data = resp.json().get("data", {})
        error_info = resp.json().get("error", {})

        # If it's a rate limit error, optimistically assume token is still valid
        if error_info.get("code") in [4, 17, 32, 613] or "limit reached" in error_info.get("message", "").lower():
            logger.warning("Meta rate limit reached on debug_token. Optimistically assuming token is valid.")
            return {"is_valid": True, "expires_at": None, "days_remaining": 60, "rate_limited": True}

        if not data.get("is_valid"):
            # Fallback check using /me in case App Token fails or is missing
            me_resp = requests.get(f"{GRAPH_API_BASE}/me", params={"access_token": access_token})
            me_error = me_resp.json().get("error", {})
            
            if me_error.get("code") in [4, 17, 32, 613] or "limit reached" in me_error.get("message", "").lower():
                logger.warning("Meta rate limit reached on /me. Optimistically assuming token is valid.")
                return {"is_valid": True, "expires_at": None, "days_remaining": 60, "rate_limited": True}

            if me_resp.status_code == 200:
                # Token works, but we can't inspect expiry. Assume short-lived (0 days) to force refresh.
                return {"is_valid": True, "expires_at": None, "days_remaining": 0}
            return {"is_valid": False, "expires_at": None, "days_remaining": 0}

        expires_at_ts = data.get("expires_at")
        if expires_at_ts and expires_at_ts > 0:
            expires_at = datetime.fromtimestamp(expires_at_ts)
            days_remaining = (expires_at - datetime.now()).days
        else:
            # Never-expiring token (System User token)
            expires_at = None
            days_remaining = 9999

        return {
            "is_valid": True,
            "expires_at": expires_at,
            "days_remaining": days_remaining,
        }
    except Exception as e:
        logger.error("Failed to check token info: %s", e)
        return {"is_valid": False, "expires_at": None, "days_remaining": 0}


def refresh_long_lived_token(current_token: str, app_id: str, app_secret: str) -> str | None:
    """
    Exchange current long-lived token for a new one (extends by 60 days).
    Returns new token string, or None if failed.
    """
    try:
        resp = requests.get(f"{GRAPH_API_BASE}/oauth/access_token", params={
            "grant_type":        "fb_exchange_token",
            "client_id":         app_id,
            "client_secret":     app_secret,
            "fb_exchange_token": current_token,
        }, timeout=15)
        data = resp.json()

        if "error" in data:
            logger.error("Token refresh failed: %s", data["error"])
            return None

        new_token = data.get("access_token")
        expires_in = data.get("expires_in", 5183944)  # ~60 days in seconds
        logger.info("Token refreshed successfully. Expires in %d days", expires_in // 86400)
        return new_token

    except Exception as e:
        logger.error("Token refresh exception: %s", e)
        return None


def save_token_to_env(new_token: str) -> bool:
    """Save the new token to the database."""
    import database as db
    try:
        db.set_ig_token(new_token)
        logger.info("New token saved to DB persistently")
        return True
    except Exception as e:
        logger.error("Failed to save token to DB: %s", e)
        return False


def check_and_refresh_token() -> dict:
    """
    Main function: check token expiry and refresh if needed.
    Returns status dict with action taken.
    Called by the scheduler every day.
    """
    import database as db
    current_token = db.get_ig_token()
    app_id        = os.getenv("META_APP_ID", "")
    app_secret    = os.getenv("META_APP_SECRET", "")

    if not current_token:
        return {"action": "no_token", "message": "No access token found in .env"}

    # Check current token status
    info = get_token_info(current_token)

    if not info["is_valid"]:
        logger.error("🔴 Token is INVALID or EXPIRED. Please paste a new token in the dashboard.")
        return {
            "action": "expired",
            "message": "Token expired. Please get a new token from Meta and paste it in the dashboard.",
            "days_remaining": 0,
        }

    days_left = info["days_remaining"]
    logger.info("Token status: valid, %d days remaining", days_left)

    # Only refresh if we have app credentials AND token is expiring soon
    if days_left <= REFRESH_THRESHOLD_DAYS:
        if app_id and app_secret:
            logger.info("Token expiring in %d days — attempting auto-refresh...", days_left)
            new_token = refresh_long_lived_token(current_token, app_id, app_secret)
            if new_token:
                save_token_to_env(new_token)
                # Reload the env
                load_dotenv(ENV_FILE, override=True)
                return {
                    "action": "refreshed",
                    "message": f"Token auto-refreshed successfully. Valid for another 60 days.",
                    "days_remaining": 60,
                }
            else:
                return {
                    "action": "refresh_failed",
                    "message": f"Token expires in {days_left} days. Auto-refresh failed. Please paste a new token.",
                    "days_remaining": days_left,
                }
        else:
            logger.warning(
                "Token expires in %d days but META_APP_ID/META_APP_SECRET not set in .env. "
                "Cannot auto-refresh. Please add them or paste a new token.",
                days_left
            )
            return {
                "action": "needs_refresh",
                "message": (
                    f"⚠️ Token expires in {days_left} days! "
                    "To enable auto-refresh, add META_APP_ID and META_APP_SECRET to .env. "
                    "Or paste a new token in the dashboard."
                ),
                "days_remaining": days_left,
            }

    return {
        "action": "ok",
        "message": f"Token is healthy. {days_left} days remaining.",
        "days_remaining": days_left,
    }
