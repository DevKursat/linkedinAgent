# src/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, time
import pytz
from .config import settings
from .worker import (
    trigger_post_creation,
    trigger_commenting,
    trigger_invitation
)

# Create a scheduler instance
scheduler = AsyncIOScheduler(timezone="Europe/Istanbul") # Set to user's timezone

def is_within_operating_hours() -> bool:
    """
    Check if current time is within operating hours (7 AM - 10 PM Istanbul time).
    Returns True if within operating hours, False otherwise.
    """
    tz = pytz.timezone("Europe/Istanbul")
    now = datetime.now(tz)
    current_hour = now.hour
    
    return settings.OPERATING_HOURS_START <= current_hour < settings.OPERATING_HOURS_END

async def safe_trigger_post_creation():
    """Wrapper that only triggers post creation during operating hours."""
    if is_within_operating_hours():
        await trigger_post_creation()
    else:
        print("⏰ Outside operating hours (7 AM - 10 PM). Skipping post creation.")

async def safe_trigger_commenting():
    """Wrapper that only triggers commenting during operating hours."""
    if is_within_operating_hours():
        await trigger_commenting()
    else:
        print("⏰ Outside operating hours (7 AM - 10 PM). Skipping commenting.")

async def safe_trigger_invitation():
    """Wrapper that only triggers invitation during operating hours."""
    if is_within_operating_hours():
        await trigger_invitation()
    else:
        print("⏰ Outside operating hours (7 AM - 10 PM). Skipping invitation.")

def setup_scheduler():
    """
    Initializes, adds all jobs, and starts the scheduler.
    """
    if not scheduler.running:
        # --- Add Core Automation Jobs ---

        # 1. Post Creation Job: Runs 2-3 times per day at strategic times.
        scheduler.add_job(
            safe_trigger_post_creation,
            trigger=CronTrigger(
                hour='9,14,19',  # Run at 9 AM, 2 PM, and 7 PM (3 times per day)
                minute='0',
                jitter=1800 # Add randomness of up to 30 minutes
            ),
            id='daily_post_creation',
            name='Create and publish a new LinkedIn post 3 times daily at optimal times.',
            replace_existing=True
        )

        # 2. Proactive Commenting Job: Runs every 2-3 hours during operating hours.
        scheduler.add_job(
            safe_trigger_commenting,
            trigger=CronTrigger(
                hour='7-21',  # 7 AM to 9 PM
                minute='30', # Run at half past the hour
                jitter=900 # Add randomness of up to 15 minutes
            ),
            id='proactive_commenting',
            name='Find and comment on a relevant post during operating hours.',
            replace_existing=True,
            misfire_grace_time=900
        )

        # 3. Invitation Sending Job: Runs every 25 minutes during operating hours (9 AM - 10 PM)
        # This allows approximately 31 invitations per day during active hours
        # Using interval trigger with time window check in the worker function
        scheduler.add_job(
            safe_trigger_invitation,
            trigger=IntervalTrigger(minutes=25),
            id='send_invitations',
            name='Send connection invitations every 25 minutes (9 AM - 10 PM).',
            replace_existing=True
        )

        # 4. System Health Check (for debugging)
        # scheduler.add_job(log_system_health, 'interval', seconds=30, id='health_check')

        scheduler.start()
        print("✅ Scheduler started and all automation jobs are configured (7 AM - 10 PM).")

def shutdown_scheduler():
    """
    Shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler shut down.")
