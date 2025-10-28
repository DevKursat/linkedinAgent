# src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Create a scheduler instance
scheduler = AsyncIOScheduler(timezone="UTC")

from .worker import log_system_health

def setup_scheduler():
    """
    Initializes, adds jobs, and starts the scheduler.
    """
    if not scheduler.running:
        # Add a job that runs every 10 seconds to log a health check
        scheduler.add_job(log_system_health, 'interval', seconds=10, id='health_check')
        scheduler.start()
        print("Scheduler started and health check job added.")

def shutdown_scheduler():
    """
    Shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler shut down.")
