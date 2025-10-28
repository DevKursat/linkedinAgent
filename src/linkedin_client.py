# src/linkedin_client.py
import os
from dotenv import load_dotenv
from linkedin_api import Linkedin

# Load environment variables from .env file
load_dotenv()

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# This will hold our authenticated client instance.
_linkedin_api_client = None

def get_linkedin_api():
    """
    Authenticates with LinkedIn on the first call and returns the client.
    Subsequent calls will return the existing authenticated client.
    Returns None if authentication fails.
    """
    global _linkedin_api_client

    # If already authenticated, return the existing client.
    if _linkedin_api_client:
        return _linkedin_api_client

    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print("❌ ERROR: LinkedIn email or password not found in .env file.")
        return None

    try:
        # Authenticate with LinkedIn
        print("Attempting to authenticate with LinkedIn...")
        api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, refresh_cookies=True)
        print("✅ Successfully authenticated with LinkedIn.")
        _linkedin_api_client = api
        return _linkedin_api_client
    except Exception as e:
        print(f"❌ ERROR: Failed to authenticate with LinkedIn: {e}")
        return None

# We don't call get_linkedin_api() here anymore to prevent blocking startup.
# It will be called by worker functions when they need it.
linkedin_api_client = None # This will be initialized on first use.

# Modify worker functions to use the getter function
def get_client():
    """A getter to ensure the client is initialized before use."""
    global linkedin_api_client
    if not linkedin_api_client:
        linkedin_api_client = get_linkedin_api()
    return linkedin_api_client
