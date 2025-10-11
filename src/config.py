"""Configuration management for LinkedIn Agent."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # LinkedIn
    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:5000/callback")
    # Varsayılanı OIDC + w_member_social yapıyoruz
    LINKEDIN_SCOPES: str = os.getenv("LINKEDIN_SCOPES", "w_member_social openid profile email")

    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # General
    TZ: str = os.getenv("TZ", "Europe/Istanbul")
    POST_WINDOWS: str = os.getenv("POST_WINDOWS", "weekday:09:30-11:00,17:30-19:30")
    DAILY_POSTS: int = int(os.getenv("DAILY_POSTS", "1"))
    MAX_DAILY_PROACTIVE: int = int(os.getenv("MAX_DAILY_PROACTIVE", "9"))
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    RARE_EMOJI: bool = os.getenv("RARE_EMOJI", "true").lower() == "true"
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    # Moderation
    BLOCK_POLITICS: bool = os.getenv("BLOCK_POLITICS", "true").lower() == "true"
    BLOCK_SPECULATIVE_CRYPTO: bool = os.getenv("BLOCK_SPECULATIVE_CRYPTO", "true").lower() == "true"
    REQUIRE_APPROVAL_SENSITIVE: bool = os.getenv("REQUIRE_APPROVAL_SENSITIVE", "true").lower() == "true"

    # Persona
    PERSONA_NAME: str = os.getenv("PERSONA_NAME", "Kürşat")
    PERSONA_AGE: str = os.getenv("PERSONA_AGE", "21")
    PERSONA_ROLE: str = os.getenv("PERSONA_ROLE", "Product Builder")

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "./data/bot.db")

    # Personalization & interests
    INTERESTS: str = os.getenv("INTERESTS", "ai,llm,product,saas,startup,founder,ux,devtools,infra")
    ABOUT_ME_PATH: str = os.getenv("ABOUT_ME_PATH", "./data/about_me.md")
    POST_STYLE_FILE: str = os.getenv("POST_STYLE_FILE", "./data/style.md")
    COMMENT_STYLE_FILE: str = os.getenv("COMMENT_STYLE_FILE", "./data/style_comment.md")
    AB_TESTING: bool = os.getenv("AB_TESTING", "true").lower() == "true"
    MAX_POST_LENGTH: int = int(os.getenv("MAX_POST_LENGTH", "1200"))


# Export a single config instance
config = Config()

# Backward-compatible alias used by some modules
cfg = config
