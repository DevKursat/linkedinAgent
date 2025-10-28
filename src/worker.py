# src/worker.py
import feedparser
import random
import time
from .database import SessionLocal
from .models import ActionLog
from .ai_core import generate_text
from .linkedin_client import get_client as get_linkedin_client

# --- Configuration ---
RSS_FEEDS = [
    "http://feeds.feedburner.com/TechCrunch/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "https://hbr.org/rss/regular",
]

# --- Helper Functions ---

def log_action(action_type: str, details: str, url: str = None):
    """Logs a specific action to the database, optionally including a result URL."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(action_type=action_type, details=details, result_url=url)
        db.add(log_entry)
        db.commit()
        print(f"Logged action: {action_type}")
    except Exception as e:
        print(f"Error logging action: {e}")
        db.rollback()
    finally:
        db.close()

def find_shareable_article():
    """Finds a recent, relevant article from the RSS feeds."""
    try:
        feed_url = random.choice(RSS_FEEDS)
        feed = feedparser.parse(feed_url)
        if feed.entries:
            article = random.choice(feed.entries)
            print(f"Found article to share: {article.title}")
            return {"title": article.title, "link": article.link, "summary": article.summary}
        return None
    except Exception as e:
        print(f"Error finding shareable article: {e}")
        return None

def find_engaging_post_for_comment():
    """Finds a high-engagement post from the LinkedIn feed to comment on."""
    try:
        client = get_linkedin_client()
        if not client: return None
        feed = client.get_feed(limit=5)
        if not feed or 'elements' not in feed: return None
        engaging_post = max(feed['elements'], key=lambda p: p.get('socialDetail', {}).get('totalSocialActivityCount', 0))
        print("Found engaging post to comment on.")
        return engaging_post
    except Exception as e:
        print(f"Error finding engaging post: {e}")
        return None

def find_profile_to_invite():
    """Finds a profile to invite."""
    # This is a placeholder for a more complex logic.
    print("Finding profile to invite (placeholder)...")
    # Returning a dictionary with URN and public ID for URL generation
    return {"urn_id": "ACoAADf-c-4B1v2XqZ_rY_z_wX_qZ_rY_z_w", "public_id": "in/kürşatyılmaz"}

# --- Core Action Triggers ---

def log_system_health():
    """A simple worker function to log a health check message."""
    log_action("System Health Check", "Scheduler is running.")

from .linkedin_client import LinkedInAuthenticationError

def trigger_post_creation():
    """Full logic for creating and publishing a new post."""
    log_action("Manual Trigger", "Global post creation process initiated.")
    try:
        client = get_linkedin_client()
    except LinkedInAuthenticationError as e:
        log_action("Post Creation Failed", f"Authentication Error: {e}")
        return

    article = find_shareable_article()
    if not article:
        log_action("Post Creation Failed", "Could not find an article.")
        return

    task_prompt = f"Write a short, engaging, and witty LinkedIn post in Turkish to share this article titled '{article['title']}'. The post should encourage discussion. Here is a summary: {article['summary']}. The post should NOT include the link."
    post_text = generate_text(task_prompt)
    task_prompt_summary = f"Summarize the key points of this article titled '{article['title']}' in Turkish, as a follow-up comment. Here is the summary for context: {article['summary']}"
    summary_comment_text = generate_text(task_prompt_summary)

    if not post_text or not summary_comment_text:
        log_action("Post Creation Failed", "AI failed to generate content.")
        return

    try:
        success = client.submit_share(commentary=post_text, content_url=article['link'], content_title=article['title'])
        if not success:
            log_action("Post Creation Failed", "The linkedin-api failed to share the post.")
            return

        time.sleep(5)
        activities = client.get_profile_posts(limit=1)
        if not activities:
            log_action("Post Creation Warning", "Could not retrieve post URN after sharing.")
            return

        post_urn = activities[0]['updateMetadata']['urn']
        post_id = post_urn.split(':')[-1]
        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"

        log_action("Post Created", f"Successfully shared post: {article['title']}", url=post_url)

        client.add_reaction(post_urn, "LIKE")
        log_action("Post Liked", "Liked our own post.", url=post_url)
        time.sleep(90)

        client.submit_comment(post_urn, summary_comment_text)
        log_action("Summary Comment Added", "Added Turkish summary.", url=post_url)

    except Exception as e:
        log_action("Post Creation Failed", f"An error occurred: {e}")

def trigger_commenting():
    """Full logic for finding a post and commenting on it."""
    log_action("Manual Trigger", "Proactive commenting process initiated.")
    try:
        client = get_linkedin_client()
    except LinkedInAuthenticationError as e:
        log_action("Commenting Failed", f"Authentication Error: {e}")
        return

    post = find_engaging_post_for_comment()
    if not post:
        log_action("Commenting Failed", "Could not find a post to comment on.")
        return

    post_text_content = post.get('commentary', {}).get('text', {}).get('text', '')
    post_urn = post.get('updateMetadata', {}).get('urn', '')
    post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"

    if not post_text_content or not post_urn:
        log_action("Commenting Failed", "Post content or URN is missing.")
        return

    task_prompt = f"Write a short, insightful, and witty comment in Turkish for a LinkedIn post with this content: '{post_text_content}'"
    comment_text = generate_text(task_prompt)
    if not comment_text:
        log_action("Commenting Failed", "AI failed to generate a comment.")
        return

    try:
        client.submit_comment(post_urn, comment_text)
        log_action("Proactive Comment Added", f"Successfully commented on post.", url=post_url)
    except Exception as e:
        log_action("Commenting Failed", f"An error occurred: {e}", url=post_url)

def trigger_invitation():
    """Full logic for sending a connection invitation."""
    log_action("Manual Trigger", "Connection invitation process initiated.")
    try:
        client = get_linkedin_client()
    except LinkedInAuthenticationError as e:
        log_action("Invitation Failed", f"Authentication Error: {e}")
        return

    profile_data = find_profile_to_invite()
    if not profile_data:
        log_action("Invitation Failed", "Could not find a profile to invite.")
        return

    profile_url = f"https://www.linkedin.com/{profile_data['public_id']}"

    try:
        # The library's add_connection is often unreliable. We simulate and log.
        # client.add_connection(profile_id)
        log_action("Invitation Sent (Simulated)", f"Sent invitation to {profile_data['public_id']}", url=profile_url)
    except Exception as e:
        log_action("Invitation Failed", f"An error occurred: {e}", url=profile_url)
