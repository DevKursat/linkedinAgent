# src/worker.py
import feedparser
import random
import time
from .database import SessionLocal
from .models import ActionLog, Post, Comment, Invitation
from .ai_core import generate_text
from .linkedin_client import get_client as get_linkedin_client

# --- Configuration ---
# A list of RSS feeds for finding shareable content
RSS_FEEDS = [
    "http://feeds.feedburner.com/TechCrunch/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "https://hbr.org/rss/regular",
]

# --- Helper Functions ---

def log_action(action_type: str, details: str):
    """Logs a specific action to the database."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(action_type=action_type, details=details)
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
            print(f"Found article to share: {article.title} from {feed.feed.title}")
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
        # Get the feed, limit to 5 most recent posts for performance
        feed = client.get_feed(limit=5)
        if not feed or 'elements' not in feed: return None

        # Simple logic: find a post with a good number of likes/comments
        # More complex logic can be added later (e.g., keyword filtering)
        engaging_post = max(feed['elements'], key=lambda p: p.get('socialDetail', {}).get('totalSocialActivityCount', 0))

        print(f"Found engaging post to comment on.")
        return engaging_post
    except Exception as e:
        print(f"Error finding engaging post: {e}")
        return None

def find_profile_to_invite():
    """Finds a profile to invite based on interactions with our content."""
    # This is a placeholder for a more complex logic.
    # A real implementation would need to get reactions on our own posts
    # and find profiles from there that are not yet connections.
    print("Finding profile to invite (placeholder)...")
    return "ACoAADf-c-4B1v2XqZ_rY_z_wX_qZ_rY_z_w" # Placeholder URN

# --- Core Action Triggers ---

def log_system_health():
    """A simple worker function to log a health check message."""
    log_action("System Health Check", "Scheduler is running and logging correctly.")

def trigger_post_creation():
    """Full logic for creating and publishing a new post."""
    log_action("Manual Trigger", "Global post creation process initiated.")
    client = get_linkedin_client()
    if not client:
        log_action("Post Creation Failed", "LinkedIn client not initialized.")
        return

    article = find_shareable_article()
    if not article:
        log_action("Post Creation Failed", "Could not find a suitable article to share.")
        return

    # 1. Generate post text with AI
    task_prompt = f"Write a short, engaging, and witty LinkedIn post in Turkish to share this article titled '{article['title']}'. The post should encourage discussion. Here is a summary of the article for context: {article['summary']}. The post text should NOT include the link; only the engaging text."
    post_text = generate_text(task_prompt)

    # 2. Generate summary comment with AI
    task_prompt_summary = f"Summarize the key points of this article titled '{article['title']}' in Turkish, as a follow-up comment. Here is the summary for context: {article['summary']}"
    summary_comment_text = generate_text(task_prompt_summary)

    if not post_text or not summary_comment_text:
        log_action("Post Creation Failed", "AI failed to generate content.")
        return

    try:
        # 3. Share the post on LinkedIn
        success = linkedin_api_client.submit_share(
            commentary=post_text,
            content_url=article['link'],
            content_title=article['title']
        )
        if not success:
            log_action("Post Creation Failed", "The linkedin-api failed to share the post.")
            return

        time.sleep(5) # Give LinkedIn a moment to process the post

        # Retrieve the latest post to get its URN for liking and commenting
        activities = linkedin_api_client.get_profile_posts(limit=1)
        if not activities:
            log_action("Post Creation Warning", "Could not retrieve post URN after sharing.")
            return

        post_urn = activities[0]['updateMetadata']['urn']

        log_action("Post Created", f"Successfully shared post. Retrieved URN: {post_urn}")

        # 4. Like the post
        linkedin_api_client.add_reaction(post_urn, "LIKE")
        log_action("Post Liked", f"Successfully liked our own post: {post_urn}")
        time.sleep(90) # Wait 1.5 minutes as requested

        # 5. Add the summary as a comment
        linkedin_api_client.submit_comment(post_urn, summary_comment_text)
        log_action("Summary Comment Added", f"Added Turkish summary to post: {post_urn}")

    except Exception as e:
        log_action("Post Creation Failed", f"An error occurred during LinkedIn action: {e}")


def trigger_commenting():
    """Full logic for finding a post and commenting on it."""
    log_action("Manual Trigger", "Proactive commenting process initiated.")
    client = get_linkedin_client()
    if not client:
        log_action("Commenting Failed", "LinkedIn client not initialized.")
        return

    post = find_engaging_post_for_comment()
    if not post:
        log_action("Commenting Failed", "Could not find a suitable post to comment on.")
        return

    post_text_content = post.get('commentary', {}).get('text', {}).get('text', '')
    post_urn = post.get('updateMetadata', {}).get('urn', '')

    if not post_text_content or not post_urn:
        log_action("Commenting Failed", "Post content or URN is missing.")
        return

    # Generate comment with AI
    task_prompt = f"Write a short, insightful, and witty comment in Turkish for a LinkedIn post with the following content: '{post_text_content}'. The comment should add value and reflect Kürşat's persona."
    comment_text = generate_text(task_prompt)

    if not comment_text:
        log_action("Commenting Failed", "AI failed to generate a comment.")
        return

    try:
        # Submit the comment
        client.submit_comment(post_urn, comment_text)
        log_action("Proactive Comment Added", f"Successfully commented on post: {post_urn}")
    except Exception as e:
        log_action("Commenting Failed", f"An error occurred during LinkedIn action: {e}")

def trigger_invitation():
    """Full logic for sending a connection invitation."""
    log_action("Manual Trigger", "Connection invitation process initiated.")
    client = get_linkedin_client()
    if not client:
        log_action("Invitation Failed", "LinkedIn client not initialized.")
        return

    profile_urn = find_profile_to_invite() # This is a placeholder
    if not profile_urn:
        log_action("Invitation Failed", "Could not find a suitable profile to invite.")
        return

    try:
        # The library currently requires profile_id, not URN. This is a simplification.
        # A real implementation would need to convert URN to ID or use a different method.
        # For now, we'll just log the intent.
        # linkedin_api_client.add_connection(profile_id)
        log_action("Invitation Sent (Simulated)", f"Successfully sent an invitation to profile URN: {profile_urn}")
    except Exception as e:
        log_action("Invitation Failed", f"An error occurred during LinkedIn action: {e}")
