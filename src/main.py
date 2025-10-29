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

    if not access_token:
        return HTMLResponse("<h1>Error</h1><p>Access token not found in response.</p>", status_code=400)

    try:
        # Clear any old tokens and save the new one
        db.query(models.Token).delete()
        new_token = models.Token(access_token=access_token)
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
    # Check if logged in by looking for a token in the database
    token = db.query(models.Token).first()
    is_logged_in = token is not None
    return templates.TemplateResponse("index.html", {"request": request, "logs": logs, "is_logged_in": is_logged_in})

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
            comment_prompt = f"Write a thoughtful, engaging comment for a LinkedIn post. Keep it professional, add value, and reflect a 21-year-old product builder's perspective. Make it conversational and authentic."
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
