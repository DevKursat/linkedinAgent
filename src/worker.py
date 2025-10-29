# src/worker.py
import asyncio
import feedparser
import random
from typing import Optional
from .database import SessionLocal
from .models import ActionLog
from .ai_core import generate_text
from .linkedin_api_client import LinkedInApiClient

# --- Client Factory ---
def get_api_client(access_token: Optional[str] = None):
    """Initializes and returns the modern LinkedIn API client, optionally with a provided token."""
    try:
        # Pass the token directly to the client constructor
        return LinkedInApiClient(access_token=access_token)
    except ValueError as e:
        log_action("Client Initialization Failed", str(e))
        return None

# --- Configuration ---
RSS_FEEDS = [
    "http://feeds.feedburner.com/TechCrunch/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "http://feeds.arstechnica.com/arstechnica/index/", # Replaced broken HBR link
]

# --- Helper Functions ---

def log_action(action_type: str, details: str, url: str = None):
    """Logs a specific action to the database."""
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

# --- Core Action Triggers ---

async def trigger_post_creation_async(access_token: str):
    """Full logic for creating a post, using a provided access token."""
    log_action("Manual Trigger", "Async post creation process initiated.")

    # The token is now passed directly, ensuring the worker has it.
    api_client = get_api_client(access_token=access_token)
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
        profile_data = await api_client.get_profile()
        user_urn = profile_data.get("id")
        if not user_urn:
            log_action("Post Creation Failed", "Could not retrieve user's profile URN.")
            return

        post_result = await api_client.share_post(user_urn, post_text)
        post_urn = post_result.get("id")
        if not post_urn:
            log_action("Post Creation Failed", "Did not receive a post URN after sharing.")
            return

        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
        log_action("Post Created", f"Successfully shared post: {article['title']}", url=post_url)

        await asyncio.sleep(5)
        await api_client.add_reaction(user_urn, post_urn)
        log_action("Post Liked", "Liked our own post.", url=post_url)

        await asyncio.sleep(60)
        await api_client.submit_comment(user_urn, post_urn, summary_comment_text)
        log_action("Summary Comment Added", "Added Turkish summary as a comment.", url=post_url)

    except Exception as e:
        log_action("Post Creation Failed", f"An unexpected error occurred: {e}")

def trigger_post_creation(access_token: str):
    """Synchronous wrapper that accepts an access token."""
    asyncio.run(trigger_post_creation_async(access_token))

# NOTE: Similar token-passing logic would be needed for commenting and invitation triggers.
# For now, focusing on fixing the post creation flow.

async def trigger_commenting_async():
    log_action("Manual Trigger", "Async commenting process initiated.")
    # This part would also need to be refactored to accept a token.
    api_client = get_api_client()
    # ... rest of the function
    pass

def trigger_commenting():
    asyncio.run(trigger_commenting_async())

async def trigger_invitation_async():
    log_action("Manual Trigger", "Async invitation process initiated.")
    # This part would also need to be refactored to accept a token.
    api_client = get_api_client()
    # ... rest of the function
    pass

def trigger_invitation():
    asyncio.run(trigger_invitation_async())
