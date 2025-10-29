# src/worker.py
import asyncio
import feedparser
import random
from .database import SessionLocal
from .models import ActionLog
from .ai_core import generate_text
from .linkedin_api_client import LinkedInApiClient

# --- Client Factory ---
def get_api_client():
    """Initializes the API client, which loads the token from the DB."""
    try:
        return LinkedInApiClient()
    except ValueError as e:
        log_action("Client Initialization Failed", str(e))
        return None

# --- Configuration ---
RSS_FEEDS = [
    "http://feeds.feedburner.com/TechCrunch/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "http://feeds.arstechnica.com/arstechnica/index/",
]

# --- Helper Functions ---

def log_action(action_type: str, details: str, url: str = None):
    """Logs an action to the database."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(action_type=action_type, details=details, result_url=url)
        db.add(log_entry)
        db.commit()
    finally:
        db.close()

def find_shareable_article():
    """Finds a random article from RSS feeds."""
    try:
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        if feed.entries:
            return random.choice(feed.entries)
        return None
    except Exception as e:
        log_action("Article Search Failed", f"Error: {e}")
        return None

def find_profile_to_invite():
    """Placeholder for a more complex profile discovery logic."""
    # This is a placeholder and should be replaced with real logic.
    return {"urn_id": "ACoAADf-c-4B1v2XqZ_rY_z_wX_qZ_rY_z_w", "public_id": "in/kürşatyılmaz"}

def log_system_health():
    """Logs a simple health check message."""
    log_action("System Health Check", "Scheduler is running.")

# --- Core Action Triggers ---

async def trigger_post_creation_async():
    """Full logic for creating a new post."""
    log_action("Post Creation Triggered", "Process initiated.")
    api_client = get_api_client()
    if not api_client: 
        return {"success": False, "message": "API client initialization failed"}

    article = find_shareable_article()
    if not article:
        log_action("Post Creation Failed", "Could not find an article.")
        return {"success": False, "message": "Could not find an article to share"}

    post_prompt = f"Write a short, engaging, witty LinkedIn post in English about this article titled '{article.title}'. Reflect a 21-year-old product builder's persona. End with the link: {article.link}"
    post_text = generate_text(post_prompt)

    summary_prompt = f"Summarize the key points of this article titled '{article.title}' in Turkish, for a follow-up comment."
    summary_text = generate_text(summary_prompt)

    if not post_text or not summary_text:
        log_action("Post Creation Failed", "AI content generation failed.")
        return {"success": False, "message": "AI content generation failed"}

    try:
        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        if not user_urn:
            log_action("Post Creation Failed", "Could not get user URN.")
            return {"success": False, "message": "Could not get user profile"}

        post = await api_client.share_post(user_urn, post_text)
        post_urn = post.get("id")
        if not post_urn:
            log_action("Post Creation Failed", "Did not get post URN after sharing.")
            return {"success": False, "message": "Failed to share post"}

        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
        log_action("Post Created", f"Shared post: {article.title}", url=post_url)

        await asyncio.sleep(45)
        await api_client.add_reaction(user_urn, post_urn)
        log_action("Post Liked", "Liked our own post after 45 seconds.", url=post_url)

        await asyncio.sleep(45)
        await api_client.submit_comment(user_urn, post_urn, summary_text)
        log_action("Summary Comment Added", "Added Turkish summary after 90 seconds total.", url=post_url)

        return {
            "success": True, 
            "message": f"Post shared successfully: {article.title}",
            "url": post_url,
            "actions": [
                f"✅ Gönderi paylaşıldı: {article.title[:50]}...",
                f"✅ 45 saniye sonra beğenildi",
                f"✅ 90 saniye sonra Türkçe özet eklendi"
            ]
        }

    except Exception as e:
        log_action("Post Creation Failed", f"Unexpected error: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}

def trigger_post_creation():
    return asyncio.run(trigger_post_creation_async())

async def trigger_commenting_async():
    """Full logic for proactive commenting."""
    log_action("Commenting Triggered", "Process initiated.")
    api_client = get_api_client()
    if not api_client: 
        return {"success": False, "message": "API client initialization failed"}

    try:
        keywords = "teknoloji or yazılım or girişimcilik"
        posts = await api_client.search_for_posts(keywords, count=1)
        if not posts:
            log_action("Commenting Failed", "No relevant posts found.")
            return {"success": False, "message": "No relevant posts found to comment on"}

        target_post = posts[0]
        post_urn = target_post.get("id")
        post_text = target_post.get("text", "")

        if not post_urn or not post_text:
            log_action("Commenting Failed", "Found post is missing URN or content.")
            return {"success": False, "message": "Found post is incomplete"}

        comment_prompt = f"Write a short, insightful, and witty comment in Turkish for a LinkedIn post with this content: '{post_text}'"
        comment_text = generate_text(comment_prompt)
        if not comment_text:
            log_action("Commenting Failed", "AI failed to generate a comment.")
            return {"success": False, "message": "AI comment generation failed"}

        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        if not user_urn:
            log_action("Commenting Failed", "Could not get user URN.")
            return {"success": False, "message": "Could not get user profile"}

        await api_client.submit_comment(user_urn, post_urn, comment_text)
        post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
        log_action("Proactive Comment Added", "Successfully commented on a post.", url=post_url)

        return {
            "success": True,
            "message": "Comment posted successfully",
            "url": post_url,
            "actions": [
                f"✅ Yorum paylaşıldı",
                f"✅ Hedef gönderi: {post_text[:50]}...",
                f"✅ Yorum: {comment_text[:80]}..."
            ]
        }

    except Exception as e:
        log_action("Commenting Failed", f"Unexpected error: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}

def trigger_commenting():
    return asyncio.run(trigger_commenting_async())

async def trigger_invitation_async():
    """Full logic for sending a connection invitation."""
    log_action("Invitation Triggered", "Process initiated.")
    api_client = get_api_client()
    if not api_client: 
        return {"success": False, "message": "API client initialization failed"}

    profile_to_invite = find_profile_to_invite()
    if not profile_to_invite:
        log_action("Invitation Failed", "Could not find a profile to invite.")
        return {"success": False, "message": "Could not find a profile to invite"}

    try:
        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        if not user_urn:
            log_action("Invitation Failed", "Could not get user URN.")
            return {"success": False, "message": "Could not get user profile"}

        invitee_urn = profile_to_invite["urn_id"]
        invitation_message = "Merhaba, ağınızı genişletmek ve potansiyel işbirlikleri hakkında konuşmak isterim."

        await api_client.send_invitation(user_urn, invitee_urn, invitation_message)
        profile_url = f"https://www.linkedin.com/in/{profile_to_invite['public_id']}/"
        log_action("Invitation Sent", f"Sent invitation to {profile_to_invite['public_id']}", url=profile_url)

        return {
            "success": True,
            "message": "Invitation sent successfully",
            "url": profile_url,
            "actions": [
                f"✅ Bağlantı daveti gönderildi",
                f"✅ Hedef profil: {profile_to_invite['public_id']}",
                f"✅ Mesaj: {invitation_message[:80]}..."
            ]
        }

    except Exception as e:
        log_action("Invitation Failed", f"Unexpected error: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}

def trigger_invitation():
    return asyncio.run(trigger_invitation_async())
