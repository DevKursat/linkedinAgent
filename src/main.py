from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

from .scheduler import setup_scheduler, shutdown_scheduler, scheduler
from typing import List
from pydantic import BaseModel
import datetime

app = FastAPI()

class JobModel(BaseModel):
    id: str
    next_run_time: datetime.datetime

@app.get("/api/scheduled-jobs", response_model=List[JobModel])
async def get_scheduled_jobs():
    """Returns a list of all scheduled jobs."""
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

import os
from starlette.staticfiles import StaticFiles

# Determine the absolute path to the project root's "static" and "templates" directory
# This makes the app runnable from any directory
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, '..'))
static_dir = os.path.join(project_root, 'static')
templates_dir = os.path.join(project_root, 'templates')


# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=templates_dir)

from sqlalchemy.orm import Session
from fastapi import Depends
from .database import SessionLocal
from .models import ActionLog

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    logs = db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(10).all()
    return templates.TemplateResponse("index.html", {"request": request, "logs": logs})

from fastapi import BackgroundTasks
from .worker import trigger_post_creation, trigger_commenting, trigger_invitation

@app.post("/api/trigger/post")
async def trigger_post(background_tasks: BackgroundTasks):
    background_tasks.add_task(trigger_post_creation)
    return {"message": "Post creation triggered successfully."}

@app.post("/api/trigger/comment")
async def trigger_comment(background_tasks: BackgroundTasks):
    background_tasks.add_task(trigger_commenting)
    return {"message": "Proactive commenting triggered successfully."}

@app.post("/api/trigger/invite")
async def trigger_invite(background_tasks: BackgroundTasks):
    background_tasks.add_task(trigger_invitation)
    return {"message": "Invitation sending triggered successfully."}

import sys

@app.post("/api/auth/login")
async def interactive_login():
    """
    Triggers the interactive login script to refresh LinkedIn session cookies.
    This now runs the script in a way that inherits the main terminal for I/O.
    """
    import subprocess

    log_action("Authentication", "Interactive login process initiated by user.")

    print("\n" + "="*60)
    print("🚀 INTERACTIVE LOGIN STARTED: Please follow the prompts below.")
    print("="*60 + "\n")

    # Run the script ensuring it uses the main process's terminal for input and output
    try:
        subprocess.run(
            [sys.executable, 'interactive_login.py'],
            check=True, # This will raise an exception if the script fails
            input=sys.stdin, # Connect script's input to the main terminal's input
        )
        message = "Interactive login process completed successfully! Cookies saved."
        print(f"\n✅ {message}\n")
        return {"message": message}
    except subprocess.CalledProcessError as e:
        message = f"Interactive login script failed with an error: {e}"
        print(f"\n❌ {message}\n")
        # Return a 500 error to the frontend to indicate failure
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=message)
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        print(f"\n❌ {message}\n")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=message)

@app.get("/health")
def health_check():
    return {"status": "ok"}
