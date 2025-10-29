# interactive_login.py
import sys
import json
import argparse
from linkedin_api import Linkedin
from linkedin_api.client import ChallengeException

COOKIE_PATH = "linkedin_cookies.json"

def main(email, password):
    """
    Performs a robust interactive login. If a security challenge is raised,
    it prompts the user to enter the PIN from the terminal.
    """
    print("🚀 Attempting to authenticate with LinkedIn...")
    print("If a security challenge (like a PIN) is required, you will be prompted to enter it below.")

    # Instantiate the client without authenticating
    api = Linkedin(email, password, refresh_cookies=True, authenticate=False)

    try:
        # Attempt to login
        api.client.authenticate()

    except ChallengeException:
        print("\n🔒 LinkedIn Security Challenge Detected.")
        pin = input("Please enter the PIN sent to your device: ")
        try:
            # Submit the PIN to resolve the challenge
            api.client.answer_challenge(pin)
        except Exception as e:
            print(f"\n❌ ERROR: Failed to answer the challenge. Details: {e}")
            sys.exit(1)

    except Exception as e:
        # A general exception will catch authentication errors if credentials are wrong
        print(f"\n❌ ERROR: An unexpected error occurred. This could be due to wrong credentials or a network issue.")
        print(f"   Details: {e}")
        sys.exit(1)

    # If authentication is successful (either directly or via challenge)
    print("\n✅ Authentication successful!")
    with open(COOKIE_PATH, "w") as f:
        json.dump(api.client.cookies.get_dict(), f)
    print(f"   Session cookies have been saved to '{COOKIE_PATH}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform an interactive LinkedIn login.")
    parser.add_argument("email", help="LinkedIn email address")
    parser.add_argument("password", help="LinkedIn password")
    args = parser.parse_args()

    main(args.email, args.password)
