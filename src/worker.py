# src/worker.py

from .database import SessionLocal
from .models import ActionLog

def log_action(action_type: str, details: str):
    """Logs a specific action to the database."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(
            action_type=action_type,
            details=details
        )
        db.add(log_entry)
        db.commit()
        print(f"Logged action: {action_type}")
    except Exception as e:
        print(f"Error logging action: {e}")
        db.rollback()
    finally:
        db.close()

def log_system_health():
    """A simple worker function to log a health check message to the database."""
    log_action("System Health Check", "Scheduler is running and logging correctly.")

# --- Manual Trigger Functions ---

def trigger_post_creation():
    """Manually triggers the process of creating and publishing a new post."""
    # In the future, this will contain the full logic for finding an article,
    # generating content with AI, posting it, and adding a summary.
    log_action("Manual Trigger", "Global post creation and summary process initiated.")
    # Placeholder for the real logic
    print("Simulating post creation...")

def trigger_commenting():
    """Manually triggers the process of finding a relevant post and commenting on it."""
    # In the future, this will scan LinkedIn for a high-engagement post
    # and use the AI to generate a relevant comment.
    log_action("Manual Trigger", "Proactive commenting process initiated.")
    # Placeholder for the real logic
    print("Simulating proactive commenting...")

def trigger_invitation():
    """Manually triggers sending a connection invitation."""
    # In the future, this will find a suitable profile and send a connection request.
    log_action("Manual Trigger", "Connection invitation process initiated.")
    # Placeholder for the real logic
    print("Simulating sending an invitation...")
