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

    # Database
    DATABASE_URL: str = "sqlite:///./linkedin_agent.db"

    # LinkedIn OAuth 2.0 Credentials
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str

    @model_validator(mode='before')
    @classmethod
    def coalesce_api_keys(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Use GOOGLE_API_KEY as a fallback for GEMINI_API_KEY.
        Ensure that at least one of them is provided.
        """
        if 'GEMINI_API_KEY' not in values and 'GOOGLE_API_KEY' in values:
            values['GEMINI_API_KEY'] = values['GOOGLE_API_KEY']

        if not values.get('GEMINI_API_KEY'):
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) must be set in the environment or .env file.")

        return values

    class Config:
        # This allows pydantic to read from a .env file if load_dotenv() is called
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow and ignore extra fields from the .env file
        extra = "ignore"

# Create a single, importable instance of the settings
settings = Settings()
