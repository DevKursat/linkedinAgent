# src/worker.py

from .database import SessionLocal
from .models import ActionLog

def log_system_health():
    """A simple worker function to log a health check message to the database."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(
            action_type="System Health Check",
            details="Scheduler is running and logging correctly."
        )
        db.add(log_entry)
        db.commit()
        print("Logged system health check.")
    except Exception as e:
        print(f"Error logging system health: {e}")
        db.rollback()
    finally:
        db.close()
