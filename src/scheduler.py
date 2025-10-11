"""APScheduler-based background task scheduler."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import time
import random
from . import db
from .config import config
from .linkedin_api import get_linkedin_api
from .gemini import generate_text
from .sources import get_top_article
from .generator import generate_post_prompt, generate_turkish_summary_prompt
from .moderation import should_post_content
from .commenter import generate_reply
from .proactive import get_approved_targets, mark_posted
from .utils import get_istanbul_time, get_random_post_time, get_reply_delay_seconds, format_source_name


scheduler = None


def run_daily_post():
    """Run the daily post job."""
    print(f"\n{'='*60}")
    print(f"Running daily post job at {get_istanbul_time()}")
    print(f"DRY_RUN: {config.DRY_RUN}")
    print(f"{'='*60}\n")
    
    try:
        # Get top article
        article = get_top_article()
        print(f"Selected article: {article['title']}")
        print(f"Source: {article['source']}")
        print(f"Link: {article['link']}")
        
        # Generate post
        prompt = generate_post_prompt(
            article['title'],
            article['summary'],
            article['link']
        )
        
        post_text = generate_text(prompt, temperature=0.8, max_tokens=400)
        print(f"\nGenerated post:\n{post_text}\n")
        
        # Check moderation
        should_post, reason = should_post_content(post_text)
        if not should_post:
            print(f"Post blocked or requires approval: {reason}")
            return
        
        # Generate Turkish summary for follow-up
        source_display_name = format_source_name(article['source'])
        summary_prompt = generate_turkish_summary_prompt(
            post_text, 
            article['link'],
            source_display_name
        )
        turkish_summary = generate_text(summary_prompt, temperature=0.7, max_tokens=200)
        print(f"\nGenerated Turkish summary:\n{turkish_summary}\n")
        
        if config.DRY_RUN:
            print("[DRY_RUN] Would post:")
            print(f"  Main post: {post_text[:100]}...")
            print(f"  Turkish summary (after 66s): {turkish_summary[:100]}...")
            return
        
        # Post to LinkedIn
        api = get_linkedin_api()
        result = api.post_ugc(post_text)
        
        post_id = result.get("id", "")
        post_urn = result.get("urn", "")
        
        # Fallback: if urn not set, construct it
        if not post_urn and post_id:
            post_urn = f"urn:li:share:{post_id}"
        
        if not post_id or not post_urn:
            raise RuntimeError(f"LinkedIn API yanıtı eksik: id={post_id}, urn={post_urn}")
        
        print(f"Posted successfully! ID: {post_id}, URN: {post_urn}")
        
        # Save to database
        db.save_post(post_id, post_urn, post_text, article['link'])
        
        # Schedule follow-up comment after 66 seconds
        def post_follow_up():
            try:
                print(f"\nPosting Turkish summary follow-up for {post_id}...")
                api.comment_on_post(post_urn, turkish_summary)
                db.mark_follow_up_posted(post_id)
                print("Follow-up posted successfully!")
            except Exception as e:
                print(f"Error posting follow-up: {e}")
        
        # Schedule the follow-up
        if scheduler:
            run_date = datetime.now() + timedelta(seconds=66)
            scheduler.add_job(
                post_follow_up,
                'date',
                run_date=run_date,
                id=f'follow_up_{post_id}',
                replace_existing=True
            )
            print(f"Scheduled follow-up for {run_date}")
            # Persist follow-up schedule
            try:
                db.set_schedule(f'follow_up_{post_id}', run_date)
            except Exception:
                pass
    
    except Exception as e:
        print(f"Error in daily post job: {e}")
        import traceback
        traceback.print_exc()


def poll_and_reply_comments():
    """Poll recent posts for new comments and reply."""
    print(f"\nPolling comments at {get_istanbul_time()}")
    
    try:
        api = get_linkedin_api()
        
        # Get recent posts
        recent_posts = db.get_recent_posts(limit=10)
        print(f"Checking {len(recent_posts)} recent posts for comments")
        
        for post in recent_posts:
            post_urn = post['post_urn']
            if not post_urn:
                continue
            
            try:
                # List comments
                comments = api.list_comments(post_urn)
                print(f"Post {post['post_id']}: {len(comments)} comments")
                
                # Get user info to filter own comments
                user_info = api.me()
                user_id = user_info["id"]
                own_actor = f"urn:li:person:{user_id}"
                
                for comment in comments:
                    comment_id = comment.get("id", "")
                    comment_actor = comment.get("actor", "")
                    comment_text = comment.get("message", {}).get("text", "")
                    
                    # Skip own comments
                    if comment_actor == own_actor:
                        continue
                    
                    if not comment_id or not comment_text:
                        continue
                    
                    # Save comment (will skip if already exists)
                    db.save_comment(comment_id, post['post_id'], comment_actor, comment_text)
            
            except Exception as e:
                print(f"Error listing comments for post {post['post_id']}: {e}")
                continue
        
        # Process unreplied comments
        unreplied = db.get_unreplied_comments()
        print(f"Found {len(unreplied)} unreplied comments")
        
        for comment in unreplied:
            try:
                # Generate reply
                reply_text = generate_reply(comment['content'], comment['author'])
                print(f"Generated reply to comment {comment['comment_id']}: {reply_text[:50]}...")
                
                if config.DRY_RUN:
                    print(f"[DRY_RUN] Would reply to comment {comment['comment_id']}")
                    # Mark as replied in dry run to avoid repeated generation
                    db.mark_comment_replied(comment['comment_id'], "dry_run")
                    continue
                
                # Get the post URN
                post = next((p for p in recent_posts if p['post_id'] == comment['post_id']), None)
                if not post or not post['post_urn']:
                    print(f"Could not find post URN for comment {comment['comment_id']}")
                    continue
                
                # Schedule reply with delay
                delay = get_reply_delay_seconds()
                
                def send_reply():
                    try:
                        result = api.comment_on_post(post['post_urn'], reply_text)
                        reply_id = result.get("id", "")
                        db.mark_comment_replied(comment['comment_id'], reply_id)
                        print(f"Replied to comment {comment['comment_id']}")
                    except Exception as e:
                        print(f"Error sending reply: {e}")
                
                if scheduler:
                    run_date = datetime.now() + timedelta(seconds=delay)
                    scheduler.add_job(
                        send_reply,
                        'date',
                        run_date=run_date,
                        id=f'reply_{comment["comment_id"]}',
                        replace_existing=True
                    )
                    print(f"Scheduled reply for {run_date} (in {delay}s)")
            
            except Exception as e:
                print(f"Error processing comment {comment['comment_id']}: {e}")
                continue
    
    except Exception as e:
        print(f"Error in comment polling job: {e}")
        import traceback
        traceback.print_exc()


def process_proactive_queue():
    """Process approved proactive queue items."""
    print(f"\nProcessing proactive queue at {get_istanbul_time()}")
    
    try:
        # Check daily limit
        daily_count = db.get_daily_proactive_count()
        print(f"Proactive posts today: {daily_count}/{config.MAX_DAILY_PROACTIVE}")
        
        if daily_count >= config.MAX_DAILY_PROACTIVE:
            print("Daily proactive limit reached")
            return
        
        # Get approved items
        approved = get_approved_targets(limit=config.MAX_DAILY_PROACTIVE - daily_count)
        print(f"Found {len(approved)} approved items")
        
        if not approved:
            return
        
        # Post one item
        item = approved[0]
        
        if not item['target_urn']:
            print(f"Skipping item {item['id']}: missing target_urn")
            return
        
        print(f"Posting proactive comment to {item['target_url']}")
        print(f"Comment: {item['suggested_comment']}")
        
        if config.DRY_RUN:
            print(f"[DRY_RUN] Would post proactive comment")
            mark_posted(item['id'])
            return
        
        # Post comment
        api = get_linkedin_api()
        api.comment_on_post(item['target_urn'], item['suggested_comment'])
        mark_posted(item['id'])
        
        print(f"Posted proactive comment successfully!")
    
    except Exception as e:
        print(f"Error in proactive queue job: {e}")
        import traceback
        traceback.print_exc()


def schedule_daily_post():
    """Schedule the daily post job."""
    # Random time within posting windows
    post_time = get_random_post_time()
    
    print(f"Scheduled daily post for {post_time}")
    
    # Schedule with cron (runs daily at the specified time)
    trigger = CronTrigger(
        hour=post_time.hour,
        minute=post_time.minute,
        timezone=config.TZ
    )
    
    job = scheduler.add_job(
        run_daily_post,
        trigger,
        id='daily_post',
        replace_existing=True
    )
    
    # Return job for further processing
    return job


def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    
    print(f"\n{'='*60}")
    print("Starting LinkedIn Agent Scheduler")
    print(f"DRY_RUN: {config.DRY_RUN}")
    print(f"Timezone: {config.TZ}")
    print(f"{'='*60}\n")
    
    scheduler = BackgroundScheduler(timezone=config.TZ)
    
    # Schedule daily post
    daily_job = schedule_daily_post()
    
    # Poll comments every 7 minutes
    poll_job = scheduler.add_job(
        poll_and_reply_comments,
        IntervalTrigger(minutes=7),
        id='poll_comments',
        replace_existing=True
    )
    
    # Process proactive queue every hour
    queue_job = scheduler.add_job(
        process_proactive_queue,
        IntervalTrigger(hours=1),
        id='proactive_queue',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started successfully!")
    
    # Save all next_run times to DB after scheduler starts
    try:
        if daily_job and daily_job.next_run_time:
            db.set_schedule('daily_post', daily_job.next_run_time)
    except Exception as e:
        print(f"Warning: Could not save daily_post schedule: {e}")
    
    try:
        if poll_job and poll_job.next_run_time:
            db.set_schedule('poll_comments', poll_job.next_run_time)
    except Exception as e:
        print(f"Warning: Could not save poll_comments schedule: {e}")
    
    try:
        if queue_job and queue_job.next_run_time:
            db.set_schedule('proactive_queue', queue_job.next_run_time)
    except Exception as e:
        print(f"Warning: Could not save proactive_queue schedule: {e}")
    
    # Print scheduled jobs
    jobs = scheduler.get_jobs()
    print(f"\nScheduled jobs ({len(jobs)}):")
    for job in jobs:
        print(f"  - {job.id}: {job.next_run_time}")
    print()


def get_next_runs() -> dict:
    """Return next run times of core jobs from the scheduler if running, else from DB."""
    out = {}
    try:
        if scheduler:
            for job_id in ['daily_post', 'poll_comments', 'proactive_queue']:
                job = scheduler.get_job(job_id)
                if job and job.next_run_time:
                    out[job_id] = str(job.next_run_time)
    except Exception:
        pass
    # Fallback/merge from DB
    try:
        for row in db.get_schedules():
            out.setdefault(row['job_id'], str(row['next_run']))
    except Exception:
        pass
    return out


def run_now(job: str):
    """Manually trigger a job by id."""
    if job == 'daily_post':
        return run_daily_post()
    if job == 'poll_comments':
        return poll_and_reply_comments()
    if job == 'proactive_queue':
        return process_proactive_queue()
    raise ValueError(f"Unknown job: {job}")


def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        print("Scheduler stopped")
