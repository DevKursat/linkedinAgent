# src/linkedin_client.py
import os
from linkedin_api import Linkedin
from linkedin_api.client import ChallengeException
import json
# Import credentials directly from the secure file
from . import credentials

# --- Configuration ---
COOKIE_PATH = "linkedin_cookies.json"

# --- Custom Exception ---
class LinkedInAuthenticationError(Exception):
    pass

# --- Client Holder ---
_linkedin_api_client = None

def get_linkedin_api():
    """
    Authenticates with LinkedIn using session cookies if available, otherwise
    falls back to the credentials in credentials.py.
    """
    global _linkedin_api_client
    if _linkedin_api_client:
        return _linkedin_api_client

    try:
        print("Attempting to authenticate with LinkedIn...")

        if os.path.exists(COOKIE_PATH):
            print(f"Found session cookie file at '{COOKIE_PATH}'. Authenticating with cookies.")
            api = Linkedin("", "", cookies=COOKIE_PATH)
        else:
            print("No cookie file found. Authenticating with credentials from credentials.py.")
            api = Linkedin(credentials.LINKEDIN_EMAIL, credentials.LINKEDIN_PASSWORD, refresh_cookies=True)
            with open(COOKIE_PATH, "w") as f:
                json.dump(api.client.cookies.get_dict(), f)
            print(f"New session cookies saved to '{COOKIE_PATH}'.")

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
    return get_linkedin_api()
