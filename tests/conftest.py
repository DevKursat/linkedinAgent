"""Pytest configuration and shared fixtures."""
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "test_client_id")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
os.environ.setdefault("GEMINI_API_KEY", "test_api_key")
os.environ.setdefault("FLASK_SECRET_KEY", "test_secret_key")
