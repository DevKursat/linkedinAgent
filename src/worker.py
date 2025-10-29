# src/worker.py
import asyncio
import feedparser
import random
import time
from .database import SessionLocal
from .models import ActionLog
from .ai_core import generate_text
from .linkedin_api_client import LinkedInApiClient

# --- Client Factory ---
def get_api_client():
    """Initializes and returns the modern LinkedIn API client."""
    try:
        return LinkedInApiClient()
    except ValueError as e:
        log_action("Client Initialization Failed", str(e))
        return None

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

async def trigger_post_creation_async():
    """Full logic for creating and publishing a new post using the modern API client."""
    log_action("Manual Trigger", "Async post creation process initiated.")

    api_client = get_api_client()
    if not api_client:
        return

    article = find_shareable_article()
    if not article:
        log_action("Post Creation Failed", "Could not find an article to share.")
        return

    post_task_prompt = f"Write a short, engaging, and witty LinkedIn post in Turkish to share this article titled '{article['title']}'. The post should encourage discussion and end with the article link: {article['link']}"
    post_text = generate_text(post_task_prompt)

    summary_task_prompt = f"Summarize the key points of this article titled '{article['title']}' in Turkish, to be posted as a follow-up comment."
    summary_comment_text = generate_text(summary_task_prompt)

    if not post_text or not summary_comment_text:
        log_action("Post Creation Failed", "AI failed to generate necessary content.")
        return

    try:
        # 1. Get user's profile URN for authoring and actions
        profile_data = await api_client.get_profile()
        user_urn = profile_data.get("id")
        if not user_urn:
            log_action("Post Creation Failed", "Could not retrieve user's profile URN.")
            return

        # 2. Share the post
        post_result = await api_client.share_post(user_urn, post_text)
        post_urn = post_result.get("id")
        if not post_urn:
            log_action("Post Creation Failed", "Did not receive a post URN after sharing.")
            return

        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
        log_action("Post Created", f"Successfully shared post: {article['title']}", url=post_url)

        # Allow time for post to be processed by LinkedIn
        await asyncio.sleep(5)

        # 3. Like the new post
        await api_client.add_reaction(user_urn, post_urn)
        log_action("Post Liked", "Liked our own post.", url=post_url)

        # Wait a bit longer before commenting to seem more natural
        await asyncio.sleep(60)

        # 4. Add the summary comment
        await api_client.submit_comment(user_urn, post_urn, summary_comment_text)
        log_action("Summary Comment Added", "Added Turkish summary as a comment.", url=post_url)

    except Exception as e:
        log_action("Post Creation Failed", f"An unexpected error occurred: {e}")

def trigger_post_creation():
    """Synchronous wrapper for the async post creation trigger."""
    asyncio.run(trigger_post_creation_async())

async def trigger_commenting_async():
    """Full logic for finding a post and commenting on it using the modern API client."""
    log_action("Manual Trigger", "Async commenting process initiated.")

    api_client = get_api_client()
    if not api_client:
        return

    try:
        # 1. Search for relevant posts
        keywords = "teknoloji or (yazılım geliştirme) or (girişimcilik)"
        posts = await api_client.search_for_posts(keywords, count=1)
        if not posts:
            log_action("Commenting Failed", "No relevant posts found to comment on.")
            return

        # For simplicity, comment on the first post found
        target_post = posts[0]
        post_urn = target_post.get("id")
        post_text_content = target_post.get("text", "") # Adjust based on actual post object structure

        if not post_urn or not post_text_content:
            log_action("Commenting Failed", "Found post is missing URN or content.")
            return

        # 2. Generate an insightful comment
        comment_task_prompt = f"Write a short, insightful, and witty comment in Turkish for a LinkedIn post with this content: '{post_text_content}'"
        comment_text = generate_text(comment_task_prompt)
        if not comment_text:
            log_action("Commenting Failed", "AI failed to generate a comment.")
            return

        # 3. Get user's URN and submit the comment
        profile_data = await api_client.get_profile()
        user_urn = profile_data.get("id")
        if not user_urn:
            log_action("Commenting Failed", "Could not retrieve user's profile URN.")
            return

        await api_client.submit_comment(user_urn, post_urn, comment_text)

        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
        log_action("Proactive Comment Added", f"Successfully commented on a post.", url=post_url)

    except Exception as e:
        log_action("Commenting Failed", f"An unexpected error occurred: {e}")

def trigger_commenting():
    """Synchronous wrapper for the async commenting trigger."""
    asyncio.run(trigger_commenting_async())

async def trigger_invitation_async():
    """Full logic for sending a connection invitation using the modern API client."""
    log_action("Manual Trigger", "Async invitation process initiated.")

    api_client = get_api_client()
    if not api_client:
        return

    profile_to_invite = find_profile_to_invite()
    if not profile_to_invite:
        log_action("Invitation Failed", "Could not find a suitable profile to invite.")
        return

    try:
        profile_data = await api_client.get_profile()
        user_urn = profile_data.get("id")
        if not user_urn:
            log_action("Invitation Failed", "Could not retrieve user's profile URN.")
            return

        invitee_urn = profile_to_invite["urn_id"]
        # In a real scenario, you'd generate a personalized message
        invitation_message = "Merhaba, ağınızı genişletmek ve potansiyel işbirlikleri hakkında konuşmak isterim."

        await api_client.send_invitation(user_urn, invitee_urn, invitation_message)

        profile_url = f"https://www.linkedin.com/in/{profile_to_invite['public_id']}/"
        log_action("Invitation Sent", f"Successfully sent invitation to {profile_to_invite['public_id']}", url=profile_url)

    except Exception as e:
        log_action("Invitation Failed", f"An unexpected error occurred: {e}")

def trigger_invitation():
    """Synchronous wrapper for the async invitation trigger."""
    asyncio.run(trigger_invitation_async())
