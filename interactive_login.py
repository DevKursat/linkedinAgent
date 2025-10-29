# interactive_login.py
import os
import sys
import json
from dotenv import load_dotenv
from linkedin_api import Linkedin
from linkedin_api.client import ChallengeException

# Define constants at the module level
COOKIE_PATH = "linkedin_cookies.json"

def main():
    """
    Performs an interactive login to LinkedIn. It loads credentials at runtime,
    prompts for challenges, and saves session cookies.
    """
    # --- Load environment variables inside main() ---
    # This ensures that the script finds the .env file correctly
    # even when called as a subprocess from a different working directory.
    load_dotenv()
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
    # --- End of loading ---

    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print("❌ ERROR: Please ensure LINKEDIN_EMAIL and LINKEDIN_PASSWORD are set in your .env file.")
        sys.exit(1)

    print("🚀 Attempting to authenticate with LinkedIn...")
    print("If a security challenge (like a PIN) is required, you will be prompted to enter it below.")

    try:
        api = Linkedin(
            LINKEDIN_EMAIL,
            LINKEDIN_PASSWORD,
            refresh_cookies=True,
        )

        with open(COOKIE_PATH, "w") as f:
            json.dump(api.client.cookies.get_dict(), f)

        print(f"\n✅ Login successful! Session cookies have been saved to '{COOKIE_PATH}'.")
        print("You can now restart the main application if it's running.")

    except ChallengeException as e:
        print(f"\n❌ ERROR: Login failed due to a security challenge that could not be resolved.")
        print(f"   Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: An unexpected error occurred during login: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
