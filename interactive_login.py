# interactive_login.py
import os
from dotenv import load_dotenv
from linkedin_api.interactive import InteractiveLogin

# Load environment variables from .env file
load_dotenv()
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
COOKIE_PATH = "linkedin_cookies.json"

def main():
    """
    Performs an interactive login to LinkedIn, handles challenges,
    and saves the session cookies to a file.
    """
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print("❌ ERROR: Please ensure LINKEDIN_EMAIL and LINKEDIN_PASSWORD are set in your .env file.")
        return

    print("🚀 Starting interactive LinkedIn login...")
    print("Please follow the instructions in the terminal.")

    # This will prompt for challenge responses in the terminal
    InteractiveLogin(
        LINKEDIN_EMAIL,
        LINKEDIN_PASSWORD,
        cookie_path=COOKIE_PATH,
    )

    print(f"\n✅ Login successful! Session cookies have been saved to '{COOKIE_PATH}'.")
    print("You can now restart the main application.")

if __name__ == "__main__":
    main()
