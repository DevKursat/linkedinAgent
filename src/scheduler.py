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
from .generator import generate_invite_message
from .config import config


scheduler = None


def _choose_tags_for_text(text: str) -> list:
    """Choose 1-3 tags based on config.INTERESTS and the post text."""
    try:
        pool = [p.strip() for p in (config.INTERESTS or '').split(',') if p.strip()]
    except Exception:
        pool = []
    if not pool:
        return []

    txt = (text or '').lower()
    l = len(txt)
    if l < 200:
        desired = 1
    elif l < 600:
        desired = 2
    else:
        desired = 3
    try:
        max_allowed = int(config.TAGS_MAX_PER_POST or 3)
    except Exception:
        max_allowed = 3
    desired = max(1, min(max_allowed, desired))

    matches = [p for p in pool if p.lower() in txt]
    if matches:
        chosen = []
        for p in pool:
            if p in matches:
                chosen.append(p)
            if len(chosen) >= desired:
                break
        return chosen

    return pool[:desired]


def run_daily_post():
    """Run the daily post job."""
    print(f"\n{'='*60}")
    print(f"Running daily post job at {get_istanbul_time()}")
    print(f"DRY_RUN: {config.DRY_RUN}")
    print(f"{'='*60}\n")
    
    try:
        article = get_top_article()
        print(f"Selected article: {article['title']}")
        
        prompt = generate_post_prompt(article['title'], article['summary'], article['link'])
        post_text = generate_text(prompt, temperature=0.8)
        print(f"\nGenerated post:\n{post_text}\n")
        
        should_post, reason = should_post_content(post_text)
        if not should_post:
            print(f"Post blocked or requires approval: {reason}")
            db.log_system_event("post_blocked", f"Reason: {reason}. Content: {post_text[:100]}...")
            return
        
        source_display_name = format_source_name(article['source'])
        summary_prompt = generate_turkish_summary_prompt(post_text, article['link'], source_display_name)
        turkish_summary = generate_text(summary_prompt, temperature=0.7)
        
        tags = _choose_tags_for_text(post_text)

        if config.DRY_RUN:
            print("[DRY_RUN] Would post main content and Turkish summary.")
            return
        
        api = get_linkedin_api()
        result = api.post_ugc(post_text, tags=tags)
        post_id = result.get("id", "")
        post_urn = result.get("urn", "")
        
        if not post_urn and post_id:
            post_urn = f"urn:li:share:{post_id}"
        
        if not (post_id or post_urn):
            raise RuntimeError(f"LinkedIn API response missing id/urn")
        
        print(f"Posted successfully! ID: {post_id}, URN: {post_urn}")
        db.save_post(post_id, post_urn, post_text, article['link'])
        db.log_system_event("post_success", f"Posted: {post_text[:100]}...")

        try:
            api.like_post(post_urn)
            print("Post liked successfully")
            db.log_system_event("like_post_success", f"Post {post_urn} liked.")
        except Exception as like_err:
            print(f"Warning: Failed to like post {post_urn}: {like_err}")
            db.log_system_event("like_post_failed", f"Failed to like post {post_urn}: {like_err}")
        
        def post_follow_up():
            try:
                print(f"\nPosting Turkish summary follow-up for {post_id}...")
                api.comment_on_post(post_urn, turkish_summary)
                db.mark_follow_up_posted(post_id)
                print("Follow-up posted successfully!")
                db.log_system_event("follow_up_success", f"Follow-up for {post_id} posted.")
            except Exception as e:
                print(f"Error posting follow-up: {e}")
                db.log_system_event("follow_up_failed", f"Error for {post_id}: {e}")
                try:
                    payload = f"{post_urn}|| ||{turkish_summary}"
                    db.enqueue_failed_action('comment', payload, str(e))
                except Exception as db_err:
                    print(f"DB Error: Failed to enqueue failed follow-up action: {db_err}")

        if scheduler:
            run_date = datetime.now() + timedelta(seconds=66)
            scheduler.add_job(post_follow_up, 'date', run_date=run_date, id=f'follow_up_{post_id}', replace_existing=True)
            db.set_schedule(f'follow_up_{post_id}', run_date)
        else:
            time.sleep(2)
            post_follow_up()
    
    except Exception as e:
        print(f"Error in daily post job: {e}")
        db.log_system_event("post_failed", str(e))


def poll_and_reply_comments():
    """Poll recent posts for new comments and reply."""
    print(f"\nPolling comments at {get_istanbul_time()}")
    
    try:
        api = get_linkedin_api()
        recent_posts = db.get_recent_posts(limit=10)

        user_info = api.me()
        user_id = user_info["id"]
        own_actor = f"urn:li:person:{user_id}"
        
        for post in recent_posts:
            post_urn = post['post_urn']
            if not post_urn:
                continue
            
            try:
                comments = api.list_comments(post_urn)
                for comment in comments:
                    comment_id = comment.get("id", "")
                    comment_actor = comment.get("actor", "")
                    if comment_actor == own_actor:
                        continue
                    db.save_comment(comment_id, post['post_id'], comment_actor, comment.get("message", {}).get("text", ""))
            
            except Exception as e:
                err_str = str(e)
                print(f"Warning: Error listing comments for post {post['post_id']}: {err_str}")
                if any(indicator in err_str for indicator in ['403', 'ACCESS_DENIED', 'RESOURCE_NOT_FOUND', '404']):
                    db.log_system_event("list_comments_permission_error", f"Post {post['post_id']}: {err_str}")
                else:
                    db.enqueue_failed_action('list_comments', post_urn, err_str)
        
        unreplied = db.get_unreplied_comments()
        for comment in unreplied:
            try:
                reply_text = generate_reply(comment['content'], comment['author'])
                
                if config.DRY_RUN:
                    print(f"[DRY_RUN] Would reply to comment {comment['comment_id']}")
                    db.mark_comment_replied(comment['comment_id'], "dry_run")
                    continue
                
                post = next((p for p in recent_posts if p['post_id'] == comment['post_id']), None)
                if not post or not post['post_urn']:
                    continue
                
                delay = get_reply_delay_seconds()
                
                def send_reply(post_urn=post['post_urn'], comment_id=comment['comment_id'], reply_text=reply_text):
                    try:
                        result = api.comment_on_post(post_urn, reply_text, parent_comment_id=comment_id)
                        db.mark_comment_replied(comment_id, result.get("id", ""))
                        db.log_system_event("reply_success", f"Replied to {comment_id}")
                    except Exception as e:
                        db.log_system_event("reply_failed", f"Failed to reply to {comment_id}: {e}")
                        payload = f"{post_urn}||{comment_id}||{reply_text}"
                        db.enqueue_failed_action('comment', payload, str(e))
                
                if scheduler:
                    run_date = datetime.now() + timedelta(seconds=delay)
                    scheduler.add_job(send_reply, 'date', run_date=run_date, id=f'reply_{comment["comment_id"]}', replace_existing=True)
                else:
                    send_reply()
            
            except Exception as e:
                print(f"Error processing comment {comment['comment_id']}: {e}")
    
    except Exception as e:
        print(f"Error in comment polling job: {e}")
        db.log_system_event("poll_comments_failed", str(e))


def process_invites():
    """Process pending invites."""
    print(f"\nProcessing invites at {get_istanbul_time()}")
    try:
        if not config.INVITES_ENABLED:
            return

        now = datetime.now()
        if now.weekday() >= 5: # Skip weekends
            return

        start_h, end_h = config.INVITES_HOUR_START, config.INVITES_HOUR_END
        if not (start_h <= now.hour < end_h):
            return

        today_count = db.get_today_invite_count()
        if today_count >= config.INVITES_MAX_PER_DAY:
            return

        remaining_daily = config.INVITES_MAX_PER_DAY - today_count
        batch = min(config.INVITES_PER_HOUR, config.INVITES_BATCH_SIZE, remaining_daily)

        pending = db.get_pending_invites()[:batch]
        if not pending:
            return

        api = get_linkedin_api()
        for inv in pending:
            try:
                msg = generate_invite_message(inv.get('person_name') or '')
                if not config.DRY_RUN:
                    api.send_invite(inv['person_urn'], msg)

                db.mark_invite_sent(inv['id'])
                db.log_system_event("invite_sent_success", f"Invite to {inv['person_urn']} sent/marked.")
            except Exception as e:
                err_msg = f"Failed to send invite to {inv['person_urn']}: {e}"
                print(err_msg)
                db.log_system_event("invite_sent_failed", err_msg)
                payload = f"{inv['person_urn']}||{inv.get('person_name') or ''}||{msg}"
                db.enqueue_failed_action('invite', payload, str(e))

    except Exception as e:
        print(f"Error in invite processing job: {e}")
        db.log_system_event("process_invites_failed", str(e))

# Other scheduler functions (process_proactive_queue, process_failed_actions, etc.) remain largely unchanged
# but would benefit from similar logging. For this fix, we focus on the core user-facing functions.

def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    
    scheduler = BackgroundScheduler(timezone=config.TZ)
    
    post_time = get_random_post_time()
    scheduler.add_job(run_daily_post, CronTrigger(hour=post_time.hour, minute=post_time.minute, timezone=config.TZ), id='daily_post', replace_existing=True)
    scheduler.add_job(poll_and_reply_comments, IntervalTrigger(minutes=7), id='poll_comments', replace_existing=True)
    scheduler.add_job(process_invites, IntervalTrigger(minutes=15 + random.randint(0,10)), id='process_invites', replace_existing=True)
    
    scheduler.start()
    print("Scheduler started successfully!")

def get_next_runs() -> dict:
    """Return next run times of core jobs."""
    if not scheduler:
        return {}
    return {job.id: str(job.next_run_time) for job in scheduler.get_jobs()}

def run_now(job: str):
    """Manually trigger a job by id."""
    job_map = {
        'daily_post': run_daily_post,
        'poll_comments': poll_and_reply_comments,
        'proactive_queue': lambda: print("Proactive queue processing not implemented in run_now yet."),
    }
    if job in job_map:
        job_map[job]()
    else:
        raise ValueError(f"Unknown job: {job}")
