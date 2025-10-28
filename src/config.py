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
    LINKEDIN_REST_VERSION: str = os.getenv("LINKEDIN_REST_VERSION", "202409")
    LINKEDIN_REST_VERSION_FALLBACKS: str = os.getenv("LINKEDIN_REST_VERSION_FALLBACKS", "202407,202405")
    LINKEDIN_ENABLE_REST: bool = os.getenv("LINKEDIN_ENABLE_REST", "false").lower() == "true"

    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
    GEMINI_RETRY_STEP: int = int(os.getenv("GEMINI_RETRY_STEP", "600"))

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

    # Invites (disabled by default for safety)
    INVITES_ENABLED: bool = os.getenv("INVITES_ENABLED", "false").lower() == "true"
    # Desired daily invites (user requested ~20)
    INVITES_MAX_PER_DAY: int = int(os.getenv("INVITES_MAX_PER_DAY", "20"))
    # How many invites at most to process in a single batch
    INVITES_BATCH_SIZE: int = int(os.getenv("INVITES_BATCH_SIZE", "3"))
    # Invite scheduling (controls / soft caps)
    # Default per-hour cap (scheduler will compute per-hour quota to average daily target)
    INVITES_PER_HOUR: int = int(os.getenv("INVITES_PER_HOUR", "3"))
    INVITES_HOUR_START: int = int(os.getenv("INVITES_HOUR_START", "7"))
    INVITES_HOUR_END: int = int(os.getenv("INVITES_HOUR_END", "21"))
    # Campaign duration in days (when started via manage command)
    INVITES_CAMPAIGN_DAYS: int = int(os.getenv("INVITES_CAMPAIGN_DAYS", "7"))
    # Proactive posting: when discovered items lack a LinkedIn URN, optionally post them as new shares
    AUTO_POST_DISCOVERED_AS_SHARE: bool = os.getenv("AUTO_POST_DISCOVERED_AS_SHARE", "true").lower() == "true"
    # Failed actions / retry behavior
    FAILED_ACTIONS_ENABLED: bool = os.getenv("FAILED_ACTIONS_ENABLED", "true").lower() == "true"
    FAILED_ACTIONS_MAX_RETRIES: int = int(os.getenv("FAILED_ACTIONS_MAX_RETRIES", "5"))
    FAILED_ACTION_RETRY_BASE_SECONDS: int = int(os.getenv("FAILED_ACTION_RETRY_BASE_SECONDS", "60"))
    # Tagging
    TAGS_MAX_PER_POST: int = int(os.getenv("TAGS_MAX_PER_POST", "9"))


# Export a single config instance
config = Config()

# Backward-compatible alias used by some modules
cfg = config
