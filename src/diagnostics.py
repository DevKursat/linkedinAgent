"""Quick diagnostics for environment and auth status."""
import os
from .config import config
from . import db


def check_env() -> dict:
    return {
        "DRY_RUN": config.DRY_RUN,
        "TZ": config.TZ,
        "GOOGLE_API_KEY_set": bool(config.GOOGLE_API_KEY),
        "LINKEDIN_CLIENT_ID_set": bool(config.LINKEDIN_CLIENT_ID),
        "LINKEDIN_CLIENT_SECRET_set": bool(config.LINKEDIN_CLIENT_SECRET),
        "INTERESTS": config.INTERESTS,
        "DB_PATH": config.DB_PATH,
    }


def check_oauth() -> dict:
    token = db.get_token()
    return {
        "authenticated": token is not None,
        "token_preview": (token.get("access_token", "")[:6] + "…") if token else None,
    }


def doctor() -> dict:
    return {
        "env": check_env(),
        "oauth": check_oauth(),
    }
