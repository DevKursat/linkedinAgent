"""Configuration management for LinkedIn Agent."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:5000/callback")
    # Varsayılanı OIDC + w_member_social yapıyoruz
    LINKEDIN_SCOPES: str = os.getenv("LINKEDIN_SCOPES", "w_member_social openid profile email")

    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    TZ: str = os.getenv("TZ", "Europe/Istanbul")
    POST_WINDOWS: str = os.getenv("POST_WINDOWS", "weekday:09:30-11:00,17:30-19:30")
    DAILY_POSTS: int = int(os.getenv("DAILY_POSTS", "1"))
    MAX_DAILY_PROACTIVE: int = int(os.getenv("MAX_DAILY_PROACTIVE", "9"))
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    RARE_EMOJI: bool = os.getenv("RARE_EMOJI", "true").lower() == "true"

    BLOCK_POLITICS: bool = os.getenv("BLOCK_POLITICS", "true").lower() == "true"
    BLOCK_SPECULATIVE_CRYPTO: bool = os.getenv("BLOCK_SPECULATIVE_CRYPTO", "true").lower() == "true"
    REQUIRE_APPROVAL_SENSITIVE: bool = os.getenv("REQUIRE_APPROVAL_SENSITIVE", "true").lower() == "true"

    PERSONA_NAME: str = os.getenv("PERSONA_NAME", "Kürşat")
    PERSONA_AGE: str = os.getenv("PERSONA_AGE", "21")
    PERSONA_ROLE: str = os.getenv("PERSONA_ROLE", "Product Builder")

cfg = Config()
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "./data/bot.db")


config = Config()
