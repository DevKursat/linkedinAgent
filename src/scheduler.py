# src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .worker import (
    log_system_health,
    trigger_post_creation,
    trigger_commenting,
    trigger_invitation
)

# Create a scheduler instance
scheduler = AsyncIOScheduler(timezone="Europe/Istanbul") # Set to user's timezone

def setup_scheduler():
    """
    Initializes, adds all jobs, and starts the scheduler.
    """
    if not scheduler.running:
        # --- Add Core Automation Jobs ---

        # 1. Post Creation Job: Runs once a day at a random time between 9 AM and 5 PM on weekdays.
        scheduler.add_job(
            trigger_post_creation,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-17',
                minute='*/15', # Check every 15 mins to pick a random minute
                jitter=1800 # Add randomness of up to 30 minutes
            ),
            id='daily_post_creation',
            name='Create and publish a new LinkedIn post daily.',
            replace_existing=True
        )

        # 2. Proactive Commenting Job: Runs every 2-3 hours on weekdays.
        scheduler.add_job(
            trigger_commenting,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-18',
                minute='30', # Run at half past the hour
                jitter=900 # Add randomness of up to 15 minutes
            ),
            id='proactive_commenting',
            name='Find and comment on a relevant post.',
            replace_existing=True,
            misfire_grace_time=900
        )

        # 3. Invitation Sending Job: Runs multiple times a day to spread out invitations.
        scheduler.add_job(
            trigger_invitation,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9,11,14,16', # Run 4 times a day
                minute='0',
                jitter=1200 # Add randomness of up to 20 minutes
            ),
            id='send_invitations',
            name='Send connection invitations.',
            replace_existing=True
        )

        # 4. System Health Check (for debugging)
        # scheduler.add_job(log_system_health, 'interval', seconds=30, id='health_check')

        scheduler.start()
        print("✅ Scheduler started and all automation jobs are configured.")

def shutdown_scheduler():
    """
    Shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler shut down.")
