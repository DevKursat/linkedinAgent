"""Configuration management for LinkedIn Agent."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # LinkedIn API
    LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:5000/callback")
    LINKEDIN_SCOPES = os.getenv("LINKEDIN_SCOPES", "w_member_social r_member_social r_liteprofile")
    
    # Google Gemini
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Timezone and Scheduling
    TZ = os.getenv("TZ", "Europe/Istanbul")
    POST_WINDOWS = os.getenv("POST_WINDOWS", "weekday:09:30-11:00,17:30-19:30")
    
    # Posting Configuration
    DAILY_POSTS = int(os.getenv("DAILY_POSTS", "1"))
    MAX_DAILY_PROACTIVE = int(os.getenv("MAX_DAILY_PROACTIVE", "9"))
    DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
    RARE_EMOJI = os.getenv("RARE_EMOJI", "true").lower() == "true"
    
    # Content Moderation
    BLOCK_POLITICS = os.getenv("BLOCK_POLITICS", "true").lower() == "true"
    BLOCK_SPECULATIVE_CRYPTO = os.getenv("BLOCK_SPECULATIVE_CRYPTO", "true").lower() == "true"
    REQUIRE_APPROVAL_SENSITIVE = os.getenv("REQUIRE_APPROVAL_SENSITIVE", "true").lower() == "true"
    
    # Persona Configuration
    PERSONA_NAME = os.getenv("PERSONA_NAME", "Kürşat")
    PERSONA_AGE = int(os.getenv("PERSONA_AGE", "21"))
    PERSONA_ROLE = os.getenv("PERSONA_ROLE", "Product Builder")
    
    # Flask Configuration
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "./data/bot.db")


config = Config()
