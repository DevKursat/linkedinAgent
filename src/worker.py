# src/worker.py
import asyncio
import feedparser
import random
import httpx
import os
from .database import SessionLocal
from .models import ActionLog
from .ai_core import generate_text
from .linkedin_api_client import LinkedInApiClient
from .post_discovery import PostDiscovery, ProfileDiscovery

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

async def find_profile_to_invite():
    """
    Find a profile to invite using safe automated discovery.
    Returns None if no safe profile can be found or daily/weekly limit reached.
    """
    # Get user interests
    interests_str = os.getenv('INTERESTS', 'ai,llm,product,saas,startup')
    interests = [i.strip() for i in interests_str.split(',')]
    
    # Initialize profile discovery with conservative limits
    # max_daily_invites=2, max_weekly_invites=12 (conservative to avoid hitting LinkedIn's weekly limit)
    discovery = ProfileDiscovery(interests, max_daily_invites=2, max_weekly_invites=12)
    
    # Check if we can send invites today/this week
    if not discovery.can_send_invite():
        # Don't log if weekly limit - it will log in the ProfileDiscovery class
        return None
    
    # Attempt to discover a profile
    profile = await discovery.discover_profiles_safe()
    
    if profile:
        discovery.record_invite_sent()
    
    return profile

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

    post_prompt = f"""Write a LinkedIn post about this article: '{article.title}'. 
Write as Kürşat: 21-year-old solo entrepreneur who builds massive projects alone, skilled in software, music, boxing, and design. 
A Turkish nationalist following Atatürk's path. Be authentic and insightful. End with: {article.link}"""
    post_text = generate_text(post_prompt)

    summary_prompt = f"""Write a Turkish follow-up comment about '{article.title}'. 
Write as Kürşat: solo entrepreneur, developer, musician, boxer, designer. Turkish nationalist following Atatürk. 
Be concise and add value. Maximum 280 characters."""
    summary_text = generate_text(summary_prompt)

    if post_text is None or summary_text is None:
        error_msg = "AI content generation is not available. Please check GEMINI_API_KEY configuration."
        log_action("Post Creation Skipped", error_msg)
        return {"success": False, "message": error_msg}

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

async def trigger_post_creation():
    return await trigger_post_creation_async()

async def trigger_commenting_async():
    """Full logic for proactive commenting with automated post discovery."""
    api_client = get_api_client()
    if not api_client:
        return {"success": False, "message": "API client initialization failed"}
    
    # Get user interests from environment
    interests_str = os.getenv('INTERESTS', 'ai,llm,product,saas,startup')
    interests = [i.strip() for i in interests_str.split(',')]
    
    # Initialize post discovery
    discovery = PostDiscovery(interests)
    
    try:
        # Discover relevant posts
        discovered_posts = await discovery.discover_posts_smart(max_posts=5)
        
        if not discovered_posts:
            log_action("Commenting Skipped", "No relevant posts discovered")
            return {
                "success": False,
                "message": "Could not discover any relevant posts to comment on",
                "actions": [
                    "ℹ️ Otomatik post keşfi çalıştırıldı",
                    "⚠️ İlgi alanlarınıza uygun post bulunamadı"
                ]
            }
        
        # Select a random post from discovered ones
        selected_post = random.choice(discovered_posts)
        post_url = selected_post['url']
        
        # Extract post URN from URL
        import re
        urn_match = re.search(r'urn:li:(activity|share|ugcPost):(\d+)', post_url)
        if not urn_match:
            activity_match = re.search(r'activity-(\d+)', post_url)
            if activity_match:
                post_urn = f"urn:li:activity:{activity_match.group(1)}"
            else:
                log_action("Commenting Failed", f"Could not extract URN from: {post_url}")
                return {"success": False, "message": "Invalid post URL format"}
        else:
            post_urn = f"urn:li:{urn_match.group(1)}:{urn_match.group(2)}"
        
        # Get user profile
        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        
        if not user_urn:
            log_action("Commenting Failed", "Could not get user profile")
            return {"success": False, "message": "Could not get user profile"}
        
        # Generate AI comment
        comment_prompt = f"""Write a LinkedIn comment for a post about {selected_post.get('title', 'technology')}. 
Write as Kürşat: 21-year-old solo entrepreneur who builds massive projects alone, skilled in software, music, boxing, and design. 
A Turkish nationalist following Atatürk's path. Match the post's language. Be authentic and add value. Maximum 280 characters."""
        comment_text = generate_text(comment_prompt)
        
        if not comment_text:
            log_action("Commenting Failed", "AI comment generation failed")
            return {"success": False, "message": "Could not generate comment text"}
        
        # Submit comment
        await api_client.submit_comment(user_urn, post_urn, comment_text)
        
        # Log success
        log_action("Auto Comment Added", f"Commented on: {selected_post.get('title', 'post')}", url=post_url)
        
        return {
            "success": True,
            "message": "Comment posted successfully via automated discovery!",
            "url": post_url,
            "actions": [
                "✅ Otomatik post keşfi yapıldı",
                f"📝 Yorum: {comment_text[:100]}...",
                f"🔗 Post: {selected_post.get('title', 'LinkedIn Post')}"
            ]
        }
        
    except Exception as e:
        log_action("Commenting Failed", f"Error: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

async def trigger_commenting():
    return await trigger_commenting_async()

async def trigger_invitation_async():
    """Full logic for sending a connection invitation with safe automated discovery."""
    api_client = get_api_client()
    if not api_client: 
        return {"success": False, "message": "API client initialization failed"}

    profile_to_invite = await find_profile_to_invite()
    if not profile_to_invite:
        # Don't log - this is expected when no profiles are found or daily limit reached
        return {
            "success": False, 
            "message": "Could not find a safe profile to invite today",
            "actions": [
                "ℹ️ Otomatik profil keşfi aktif",
                "⚠️ Güvenli davet limiti veya uygun profil yok"
            ]
        }

    try:
        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        if not user_urn:
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
        error_message = str(e)
        
        # Check if it's a 403 Forbidden error - this is expected without proper permissions
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 403:
            # Don't log this error - it's a known limitation documented in LINKEDIN_API_MIGRATION.md
            # Only return the message if manually triggered, scheduler will skip silently
            error_message = "LinkedIn invitations API requires special permissions. Please request 'invitations' permission in your LinkedIn Developer app. See LINKEDIN_API_MIGRATION.md for details."
            return {"success": False, "message": error_message, "skip_log": True}
        else:
            # Only log unexpected errors
            log_action("Invitation Failed", f"Error: {error_message}")
        
        return {"success": False, "message": error_message}

async def trigger_invitation():
    return await trigger_invitation_async()
