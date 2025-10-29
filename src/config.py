# src/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file at the earliest opportunity
load_dotenv()

class Settings(BaseSettings):
    """
    Centralized application settings using Pydantic for validation.
    Reads variables from environment/.env file.
    """
    # Gemini API
    GEMINI_API_KEY: str

    # Database
    DATABASE_URL: str = "sqlite:///./linkedin_agent.db"

    # LinkedIn OAuth 2.0 Credentials
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str

    class Config:
        # This allows pydantic to read from a .env file if load_dotenv() is called
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a single, importable instance of the settings
settings = Settings()
