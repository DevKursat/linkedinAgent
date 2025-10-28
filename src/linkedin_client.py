# src/linkedin_client.py
import os
from dotenv import load_dotenv
from linkedin_api import Linkedin
from linkedin_api.client import ChallengeException
import json

# --- Configuration ---
load_dotenv()
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
COOKIE_PATH = "linkedin_cookies.json"

# --- Custom Exception ---
class LinkedInAuthenticationError(Exception):
    pass

# --- Client Holder ---
_linkedin_api_client = None

def get_linkedin_api():
    """
    Authenticates with LinkedIn using session cookies if available, otherwise
    falls back to username/password. Raises LinkedInAuthenticationError on failure.
    """
    global _linkedin_api_client
    if _linkedin_api_client:
        return _linkedin_api_client

    try:
        print("Attempting to authenticate with LinkedIn...")

        # Prioritize using saved session cookies for authentication
        if os.path.exists(COOKIE_PATH):
            print(f"Found session cookie file at '{COOKIE_PATH}'. Authenticating with cookies.")
            api = Linkedin("", "", cookies=COOKIE_PATH)

        # Fallback to username/password if cookies are not available/valid
        elif LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
            print("No valid cookie file found. Falling back to username/password authentication.")
            api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, refresh_cookies=True)

        else:
            raise LinkedInAuthenticationError("LinkedIn credentials (or a cookie file) not found.")

        print("✅ Successfully authenticated with LinkedIn.")
        _linkedin_api_client = api
        return _linkedin_api_client

    except ChallengeException as e:
        error_message = (
            "LinkedIn requires a security check (CHALLENGE). "
            "Please run the interactive login process via the dashboard button."
        )
        print(f"❌ ERROR: {error_message}")
        raise LinkedInAuthenticationError(error_message)
    except Exception as e:
        error_message = f"An unexpected error occurred during LinkedIn authentication: {e}"
        print(f"❌ ERROR: {error_message}")
        raise LinkedInAuthenticationError(error_message)

def get_client():
    """A getter that ensures the client is initialized before use."""
    # This architecture ensures we only try to authenticate once per session.
    return get_linkedin_api()
