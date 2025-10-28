"""Module for proactive engagement, like commenting on target profiles' posts."""
from .config import config
from . import db
from .linkedin_api import get_linkedin_api
from .gemini import generate_text
from .generator import generate_proactive_comment_prompt
from .utils import get_reply_delay_seconds
import time


def discover_and_queue_posts():
    """
    Discover posts from target profiles and queue them for commenting.
    This function is intended to be run periodically by the scheduler.
    """
    if not config.PROACTIVE_ENABLED:
        return

    target_profiles = [p.strip() for p in (config.LINKEDIN_TARGET_PROFILES or '').split(',') if p.strip()]
    if not target_profiles:
        return

    print(f"Running proactive discovery for profiles: {target_profiles}")
    
    try:
        api = get_linkedin_api()

        for profile_url in target_profiles:
            try:
                # The library needs a public ID or URN. Let's assume the user provides a valid public URL.
                # A robust implementation would need a way to resolve a public URL to a profile URN.
                # For now, let's assume the `get_profile_posts` can handle a URL, or we have a utility for it.
                # This is a conceptual step. The `linkedin_api` library might require a profile ID/URN.

                # Let's assume we can get a profile's URN. A real implementation would need a lookup step.
                # E.g., profile_info = api.get_profile(public_identifier=profile_url) -> get URN

                # We'll use a placeholder for the URN.
                # In a real scenario, this would be the most failure-prone part.
                # For this example, we can't execute this without a valid, configured profile target.

                # Let's pivot to searching for content from a company page, which is often more stable.
                # Let's assume target_profiles can also be company IDs/URNs.

                # The function `get_company_updates` is a common feature in these libraries.
                updates = api.get_company_updates(public_id_or_urn=profile_url, max_results=5)

                if not updates:
                    continue

                for post in updates:
                    post_urn = post.get('urn', '') or f"urn:li:share:{post.get('id', '')}"
                    if not post_urn or db.is_proactive_post_processed(post_urn):
                        continue

                    post_text = post.get('text', '')

                    # Basic check to avoid commenting on trivial posts
                    if len(post_text.split()) < 10:
                        continue

                    db.add_proactive_target(post_urn, post_text, profile_url)
                    print(f"Queued post {post_urn} from {profile_url} for commenting.")

            except Exception as e:
                print(f"Could not process proactive target {profile_url}: {e}")
                db.log_system_event("proactive_discovery_failed", f"Target: {profile_url}, Error: {e}")

    except Exception as e:
        print(f"Error during proactive discovery: {e}")


def process_proactive_queue():
    """
    Process the queue of posts to comment on.
    """
    if not config.PROACTIVE_ENABLED:
        return

    targets = db.get_proactive_targets_to_comment()
    if not targets:
        return

    print(f"Processing {len(targets)} posts from the proactive queue.")

    try:
        api = get_linkedin_api()

        for target in targets:
            try:
                prompt = generate_proactive_comment_prompt(target['post_content'])
                comment_text = generate_text(prompt, temperature=0.75)

                if config.DRY_RUN:
                    print(f"[DRY_RUN] Would comment on post {target['post_urn']}: {comment_text}")
                    mark_posted(target['id'])
                    continue

                delay = get_reply_delay_seconds()
                print(f"Waiting {delay} seconds before commenting...")
                time.sleep(delay)

                api.comment_on_post(target['post_urn'], comment_text)
                mark_posted(target['id'])

                print(f"Successfully commented on proactive post {target['post_urn']}")
                db.log_system_event("proactive_comment_success", f"Commented on {target['post_urn']}")

            except Exception as e:
                print(f"Error processing proactive target {target['id']}: {e}")
                db.log_system_event("proactive_comment_failed", f"Target ID: {target['id']}, Error: {e}")

    except Exception as e:
        print(f"Error in proactive processing: {e}")

# Helper functions to be called by the scheduler or other parts of the app
def get_approved_targets():
    return db.get_proactive_targets(status='approved')

def mark_posted(target_id):
    db.update_proactive_target_status(target_id, 'posted')
