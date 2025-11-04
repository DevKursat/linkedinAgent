from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from . import models
from .database import engine, SessionLocal
from .config import settings
import pytz
import os
import datetime
import httpx
from typing import List
from pydantic import BaseModel
import urllib.parse
from pathlib import Path

# Create all tables
models.Base.metadata.create_all(bind=engine)

from .scheduler import setup_scheduler, shutdown_scheduler, scheduler

app = FastAPI()

# --- Dependency to get a DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- OAuth 2.0 Authentication Flow ---

@app.get("/login")
async def linkedin_login():
    """Redirects the user to LinkedIn's authorization page."""
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": "some_random_string",
        "scope": "openid profile w_member_social",
    }
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def linkedin_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handles the callback, exchanges the code for a token, and stores it in the database."""
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)

    if response.status_code != 200:
        return HTMLResponse(f"<h1>Error</h1><p>Could not retrieve access token: {response.text}</p>")

    token_data = response.json()
    access_token = token_data.get("access_token")

    # Validate token is not None, empty, or whitespace-only
    if not access_token or not access_token.strip():
        return HTMLResponse("<h1>Error</h1><p>Access token not found in response.</p>", status_code=400)

    try:
        # Clear any old tokens and save the new one
        # Strip whitespace from token before storing
        db.query(models.Token).delete()
        new_token = models.Token(access_token=access_token.strip())
        db.add(new_token)
        db.commit()
        print("Access token successfully saved to the database.")
    except Exception as e:
        db.rollback()
        print(f"CRITICAL: Failed to save access token to database. Error: {e}")
        return HTMLResponse(f"<h1>Error</h1><p>Could not save access token to database: {e}</p>", status_code=500)

    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(db: Session = Depends(get_db)):
    """Logs the user out by deleting the token from the database."""
    try:
        db.query(models.Token).delete()
        db.commit()
        print("Token successfully deleted from the database.")
    except Exception as e:
        db.rollback()
        print(f"Error deleting token from database: {e}")
    return RedirectResponse(url="/")


# --- UI and API Endpoints ---
class JobModel(BaseModel):
    id: str
    next_run_time: datetime.datetime

@app.get("/api/scheduled-jobs", response_model=List[JobModel])
async def get_scheduled_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(JobModel(id=job.id, next_run_time=job.next_run_time))
    return jobs

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

# Setup templates and static files
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, '..'))
static_dir = os.path.join(project_root, 'static')
templates_dir = os.path.join(project_root, 'templates')

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

def format_datetime_istanbul(dt: datetime.datetime):
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    istanbul_tz = pytz.timezone("Europe/Istanbul")
    return dt.astimezone(istanbul_tz).strftime("%Y-%m-%d %H:%M:%S")

templates.env.filters["istanbul_time"] = format_datetime_istanbul

from .models import ActionLog

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    logs = db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(10).all()
    pending_posts = db.query(models.TranslatedPost).filter(models.TranslatedPost.status == "pending").order_by(models.TranslatedPost.posted_at.desc()).all()

    # Check if logged in by looking for a token in the database
    token = db.query(models.Token).first()
    is_logged_in = token is not None
    return templates.TemplateResponse("index.html", {
        "request": request,
        "logs": logs,
        "is_logged_in": is_logged_in,
        "pending_posts": pending_posts
    })

from fastapi import BackgroundTasks
from .worker import trigger_post_creation, trigger_commenting, trigger_invitation

@app.post("/api/trigger/post")
async def trigger_post(background_tasks: BackgroundTasks):
    result = await trigger_post_creation()
    if result and result.get("success"):
        return {
            "success": True,
            "message": result.get("message", "Post creation triggered successfully."),
            "url": result.get("url"),
            "actions": result.get("actions", [])
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "Post creation failed.") if result else "Post creation failed."
        }

@app.post("/api/trigger/comment")
async def trigger_comment(background_tasks: BackgroundTasks):
    result = await trigger_commenting()
    if result and result.get("success"):
        return {
            "success": True,
            "message": result.get("message", "Comment triggered successfully."),
            "url": result.get("url"),
            "actions": result.get("actions", [])
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "Commenting failed.") if result else "Commenting failed."
        }

@app.post("/api/trigger/invite")
async def trigger_invite(background_tasks: BackgroundTasks):
    result = await trigger_invitation()
    if result and result.get("success"):
        return {
            "success": True,
            "message": result.get("message", "Invitation triggered successfully."),
            "url": result.get("url"),
            "actions": result.get("actions", [])
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "Invitation failed.") if result else "Invitation failed."
        }

@app.post("/api/manual_comment")
async def manual_comment(request: Request):
    """Manually comment on a specific LinkedIn post by URL."""
    from .ai_core import generate_text
    from .linkedin_api_client import LinkedInApiClient
    from .worker import log_action
    import re
    
    try:
        data = await request.json()
        post_url = data.get("post_url", "").strip()
        custom_comment = data.get("comment", "").strip()
        
        if not post_url:
            return {"success": False, "message": "Post URL is required"}
        
        # Extract post URN from LinkedIn URL
        # LinkedIn post URLs are like: https://www.linkedin.com/feed/update/urn:li:activity:1234567890/
        # or https://www.linkedin.com/posts/username_activity-1234567890-abcd
        urn_match = re.search(r'urn:li:(activity|share|ugcPost):(\d+)', post_url)
        if not urn_match:
            # Try alternative format
            activity_match = re.search(r'activity-(\d+)', post_url)
            if activity_match:
                post_urn = f"urn:li:activity:{activity_match.group(1)}"
            else:
                return {"success": False, "message": "Could not extract post URN from URL. Please use a valid LinkedIn post URL."}
        else:
            post_urn = f"urn:li:{urn_match.group(1)}:{urn_match.group(2)}"
        
        # Get API client
        api_client = LinkedInApiClient()
        profile = await api_client.get_profile()
        user_urn = profile.get("id")
        
        if not user_urn:
            return {"success": False, "message": "Could not get user profile"}
        
        # Generate or use custom comment
        if custom_comment:
            comment_text = custom_comment
        else:
            # Generate AI comment
            comment_prompt = f"""Write a LinkedIn comment. Write as Kürşat: 21-year-old solo entrepreneur who builds massive projects alone, 
skilled in software, music, boxing, and design. A Turkish nationalist following Atatürk's path. 
Match the post's language. Be authentic and add value. Maximum 280 characters."""
            comment_text = generate_text(comment_prompt)
            
            if not comment_text:
                return {"success": False, "message": "Could not generate comment text. Please provide a custom comment or check GEMINI_API_KEY."}
        
        # Submit comment
        await api_client.submit_comment(user_urn, post_urn, comment_text)
        
        # Log the action
        log_action("Manual Comment Added", f"Commented on post: {post_url[:50]}...", url=post_url)
        
        return {
            "success": True,
            "message": "Comment posted successfully!",
            "url": post_url,
            "actions": [
                f"✅ Yorum gönderildi",
                f"📝 Yorum: {comment_text[:100]}...",
                f"🔗 Post: {post_url[:50]}..."
            ]
        }
        
    except Exception as e:
        log_action("Manual Comment Failed", f"Error: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/posts/{post_id}/approve")
async def approve_and_post(post_id: int, db: Session = Depends(get_db)):
    """Approves a translated post, shares it on LinkedIn, and likes it."""
    from .linkedin_api_client import LinkedInApiClient
    from .worker import log_action

    post_to_share = db.query(models.TranslatedPost).filter(models.TranslatedPost.id == post_id).first()
    if not post_to_share or post_to_share.status != "pending":
        return {"success": False, "message": "Post not found or already processed."}

    try:
        api_client = LinkedInApiClient()
        profile = await api_client.get_profile()
        author_urn = profile.get("id")

        if not author_urn:
            return {"success": False, "message": "Could not get user profile URN."}

        # Share the post, including the image if it exists
        post_result = await api_client.share_post(
            author_urn,
            post_to_share.translated_content,
            post_to_share.image_url
        )
        our_post_urn = post_result.get("id") # This is the URN of our new post

        if not our_post_urn:
            return {"success": False, "message": "Gönderi paylaşılamadı, LinkedIn'den geçerli bir URN alınamadı."}

        # Like our own post
        await api_client.add_reaction(author_urn, our_post_urn)

        # Add source comment
        if post_to_share.original_author and post_to_share.original_author != "Unknown":
            source_comment = f"Kaynak: {post_to_share.original_author}"
            await api_client.submit_comment(author_urn, our_post_urn, source_comment)

        # Update database
        post_to_share.status = "posted"
        post_to_share.our_post_url = f"https://www.linkedin.com/feed/update/{our_post_urn}"
        db.commit()

        log_action("Translated Post Shared", f"Shared post: {post_to_share.translated_content[:50]}...", url=post_to_share.our_post_url)

        return {"success": True, "message": "Gönderi başarıyla paylaşıldı ve beğenildi."}
    except Exception as e:
        log_action("Translated Post Failed", f"Error sharing post ID {post_id}: {str(e)}")
        post_to_share.status = "failed"
        db.commit()
        return {"success": False, "message": f"Bir hata oluştu: {str(e)}"}

@app.post("/api/posts/{post_id}/reject")
async def reject_post(post_id: int, db: Session = Depends(get_db)):
    """Rejects and deletes a translated post."""
    post_to_reject = db.query(models.TranslatedPost).filter(models.TranslatedPost.id == post_id).first()
    if not post_to_reject or post_to_reject.status != "pending":
        return {"success": False, "message": "Post not found or already processed."}

    db.delete(post_to_reject)
    db.commit()

    return {"success": True, "message": "Çeviri reddedildi ve silindi."}


@app.post("/api/translate-post")
async def handle_translate_post(request: Request, db: Session = Depends(get_db)):
    """
    Handles the submission of a LinkedIn post URL for translation.
    It fetches the post, translates it, and saves it for approval.
    """
    from .linkedin_api_client import LinkedInApiClient
    from .ai_core import generate_text
    import re

    try:
        data = await request.json()
        post_url = data.get("post_url", "").strip()

        if not post_url:
            return {"success": False, "message": "Post URL is required"}

        # Extract post URN from URL
        urn_match = re.search(r'urn:li:(activity|share|ugcPost):(\d+)', post_url)
        if not urn_match:
            return {"success": False, "message": "Could not extract a valid Post URN from the URL."}

        post_urn = f"urn:li:{urn_match.group(1)}:{urn_match.group(2)}"

        # Check if already translated
        if db.query(models.TranslatedPost).filter(models.TranslatedPost.original_post_url == post_url).first():
             return {"success": False, "message": "Bu gönderi daha önce çevrilmiş veya çevrilmek üzere işleniyor."}

        # Fetch post details
        api_client = LinkedInApiClient()
        post_details = await api_client.get_post_details(post_urn)

        original_content = post_details.get("original_content")
        original_author = post_details.get("original_author")
        image_url = post_details.get("image_url")

        if not original_content:
            return {"success": False, "message": "Gönderi metni alınamadı."}

        # Translate the content
        translation_prompt = f"Translate the following LinkedIn post into high-quality Turkish, maintaining a professional and engaging tone. Post:\n\n{original_content}"
        translated_content = generate_text(translation_prompt)

        if not translated_content:
            return {"success": False, "message": "Metin çevrilemedi. Gemini API'yi kontrol edin."}

        # Save to database for approval
        new_post = models.TranslatedPost(
            original_post_url=post_url,
            original_content=original_content,
            translated_content=translated_content.strip(),
            original_author=original_author,
            image_url=image_url,
            status="pending"
        )
        db.add(new_post)
        db.commit()

        return {"success": True, "message": "Gönderi çeviri için başarıyla gönderildi."}

    except Exception as e:
        import logging
        logging.error(f"Error in translate-post endpoint: {e}")
        return {"success": False, "message": f"Bir hata oluştu: {str(e)}"}
