# src/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional, Any

# Load .env file at the earliest opportunity
load_dotenv()

class Settings(BaseSettings):
    """
    Centralized application settings using Pydantic for validation.
    Reads variables from environment/.env file.
    """
    # Gemini API - Allow both names for backward compatibility
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None  # Legacy support
    GEMINI_MODEL: str = "gemini-1.5-flash"  # Primary model
    GEMINI_FALLBACK_MODELS: str = "gemini-1.5-flash-8b,gemini-1.0-pro"  # Comma-separated fallback models

    # Database
    DATABASE_URL: str = "sqlite:///./linkedin_agent.db"

    # LinkedIn OAuth 2.0 Credentials
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str
    
    # Operating Hours Configuration
    OPERATING_HOURS_START: int = 7  # 7 AM
    OPERATING_HOURS_END: int = 22  # 10 PM (22:00)

    @model_validator(mode='before')
    @classmethod
    def coalesce_api_keys(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Use GOOGLE_API_KEY as a fallback for GEMINI_API_KEY for backward compatibility.
        The API key is optional; AI features will be disabled if not provided.
        """
        if 'GEMINI_API_KEY' not in values and 'GOOGLE_API_KEY' in values:
            values['GEMINI_API_KEY'] = values['GOOGLE_API_KEY']

        return values

    class Config:
        # This allows pydantic to read from a .env file if load_dotenv() is called
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow and ignore extra fields from the .env file
        extra = "ignore"

# Create a single, importable instance of the settings
settings = Settings()
