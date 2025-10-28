# src/linkedin_client.py
import os
from dotenv import load_dotenv
from linkedin_api import Linkedin
from linkedin_api.client import ChallengeException

# Load environment variables from .env file
load_dotenv()

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Custom Exception for better error handling
class LinkedInAuthenticationError(Exception):
    pass

# This will hold our authenticated client instance.
_linkedin_api_client = None

def get_linkedin_api():
    """
    Authenticates with LinkedIn on the first call and returns the client.
    Subsequent calls will return the existing authenticated client.
    Raises LinkedInAuthenticationError if authentication fails.
    """
    global _linkedin_api_client

    if _linkedin_api_client:
        return _linkedin_api_client

    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        raise LinkedInAuthenticationError("LinkedIn email or password not found in .env file.")

    try:
        print("Attempting to authenticate with LinkedIn...")
        # Note: setting refresh_cookies=True is important for long-running sessions
        api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, refresh_cookies=True)
        print("✅ Successfully authenticated with LinkedIn.")
        _linkedin_api_client = api
        return _linkedin_api_client
    except ChallengeException as e:
        # Catch the specific challenge exception and re-raise it as our custom error
        error_message = f"LinkedIn requires a security check (CHALLENGE): {e}"
        print(f"❌ ERROR: {error_message}")
        raise LinkedInAuthenticationError(error_message)
    except Exception as e:
        # Catch any other authentication errors
        error_message = f"An unexpected error occurred during LinkedIn authentication: {e}"
        print(f"❌ ERROR: {error_message}")
        raise LinkedInAuthenticationError(error_message)

# We define a simple getter here for the worker to use.
def get_client():
    """A getter that ensures the client is initialized before use."""
    return get_linkedin_api()
