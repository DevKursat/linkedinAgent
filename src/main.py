from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

from .scheduler import setup_scheduler, shutdown_scheduler

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

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

@app.get("/health")
def health_check():
    return {"status": "ok"}
