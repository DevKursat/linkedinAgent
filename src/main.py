# src/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import models
from .database import engine
from .scheduler import setup_scheduler, shutdown_scheduler, scheduler
from typing import List
from pydantic import BaseModel
import datetime
import os
from starlette.staticfiles import StaticFiles

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

class JobModel(BaseModel):
    id: str
    next_run_time: datetime.datetime

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

# Determine the absolute path to the project root's "static" and "templates" directory
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, '..'))
static_dir = os.path.join(project_root, 'static')
templates_dir = os.path.join(project_root, 'templates')

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

from sqlalchemy.orm import Session
from fastapi import Depends
from .database import SessionLocal
from .models import ActionLog

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

@app.get("/api/scheduled-jobs", response_model=List[JobModel])
async def get_scheduled_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(JobModel(id=job.id, next_run_time=job.next_run_time))
    return jobs

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

@app.get("/health")
def health_check():
    return {"status": "ok"}
