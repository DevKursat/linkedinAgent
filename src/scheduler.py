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
    """Choose 1-3 tags based on config.INTERESTS and the post text.

    Heuristic:
    - Build a pool from CONFIG.INTERESTS.
    - If interests appear in the text, prefer those (preserve pool order).
    - Desired number depends on text length: short=1, medium=2, long=3.
    - Fallback to the first N from pool.
    """
    try:
        pool = [p.strip() for p in (config.INTERESTS or '').split(',') if p.strip()]
    except Exception:
        pool = []
    if not pool:
        return []

    txt = (text or '').lower()
    # desired count by length
    l = len(txt)
    # base desired by length but cap by config
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

    # If Gemini available, ask it to suggest up to desired (or config max) tags
    try:
        from .gemini import generate_text
        max_allowed = int(config.TAGS_MAX_PER_POST or 9)
        ask_for = min(max_allowed, max(3, desired))
        prompt = (
            "Aşağıdaki gönderi için en alakalı 1 ile %d arasında hashtag öner. "
            "Sadece virgülle ayrılmış kelimeler (hashtag sembolü olmadan) döndür.\n\n" % ask_for
        )
        prompt += "Gönderi: \n" + (text or "")[:2000]
        if config.GOOGLE_API_KEY:
            try:
                resp = generate_text(prompt, temperature=0.2, max_tokens=120)
                # parse comma separated
                cand = [c.strip() for c in resp.replace('\n', ',').split(',') if c.strip()]
                if cand:
                    return cand[:max_allowed]
            except Exception:
                pass
    except Exception:
        pass

    # fallback
    return pool[:desired]


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
        
        post_text = generate_text(prompt, temperature=0.8)
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
        turkish_summary = generate_text(summary_prompt, temperature=0.7)
        print(f"\nGenerated Turkish summary:\n{turkish_summary}\n")
        
        # Choose tags intelligently based on post text
        tags = _choose_tags_for_text(post_text)

        if config.DRY_RUN:
            print("[DRY_RUN] Would post:")
            print(f"  Main post: {post_text[:100]}...")
            if tags:
                print(f"  Hashtags: {' '.join('#'+t if not t.startswith('#') else t for t in tags)}")
            print(f"  Turkish summary (after 66s): {turkish_summary[:100]}...")
            return
        
        # Post to LinkedIn
        api = get_linkedin_api()
        result = api.post_ugc(post_text, tags=tags)

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

        # Like the post to ensure it appears as engaged content
        try:
            api.like_post(post_urn)
            print("Post liked successfully")
        except Exception as like_err:
            print(f"Warning: Failed to like post {post_urn}: {like_err}")
        
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
        else:
            # Web panel tetiklemelerinde scheduler yoksa yorumu hemen gönder.
            print("Scheduler aktif değil; takip yorumunu hemen paylaşıyorum.")
            try:
                time.sleep(2)
            except Exception:
                pass
            post_follow_up()
    
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
                    # If the comment mentions our persona, enqueue an invite suggestion
                    try:
                        from .commenter import comment_mentions_person
                        if comment_mentions_person(comment_text):
                            # Try to extract a name from the actor URN if available
                            person_name = comment_actor.split(":")[-1] if comment_actor else ""
                            db.enqueue_invite(comment_actor, person_name, reason=f"Mentioned on post {post['post_id']}")
                            print(f"Enqueued invite suggestion for {comment_actor}")
                    except Exception:
                        pass
            
            except Exception as e:
                err_str = str(e)
                print(f"Warning: Error listing comments for post {post['post_id']}: {err_str}")
                # If the error is permission/resource related, write an alert and do NOT enqueue retries
                non_retryable = False
                try:
                    if '403' in err_str or 'ACCESS_DENIED' in err_str or 'RESOURCE_NOT_FOUND' in err_str or '404' in err_str:
                        non_retryable = True
                except Exception:
                    non_retryable = False

                if non_retryable:
                    try:
                        with open('data/alerts.log', 'a', encoding='utf-8') as f:
                            f.write(f"{datetime.now().isoformat()} - list_comments permission/resource error for post {post['post_id']}: {err_str}\n")
                    except Exception:
                        pass
                    # Do not enqueue for retries
                    continue

                # Otherwise enqueue for retry via failed_actions
                try:
                    db.enqueue_failed_action('list_comments', post_urn, err_str)
                except Exception:
                    pass
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
                        # If the original comment has an id, use it as the parent so we reply to that comment
                        if config.DRY_RUN:
                            print(f"[DRY_RUN] Would reply to {comment['comment_id']}")
                            # Do not mark replied in dry-run
                            return

                        result = api.comment_on_post(post['post_urn'], reply_text, parent_comment_id=comment.get('comment_id'))
                        reply_id = result.get("id", "")
                        db.mark_comment_replied(comment['comment_id'], reply_id)
                        print(f"Replied to comment {comment['comment_id']}")
                    except Exception as e:
                        print(f"Warning: Error sending reply: {e}")
                        # Enqueue failed action to retry posting this comment
                        try:
                            payload = f"{post['post_urn']}||{comment.get('comment_id') or ''}||{reply_text}"
                            db.enqueue_failed_action('comment', payload, str(e))
                        except Exception:
                            pass
                
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
                else:
                    # If scheduler isn't running in this process (e.g. web container),
                    # send the reply immediately so comments don't remain unreplied.
                    try:
                        print(f"Scheduler not available; sending reply immediately for {comment['comment_id']}")
                        send_reply()
                    except Exception as e:
                        print(f"Error sending immediate reply for {comment['comment_id']}: {e}")
            
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
            print(f"Item {item['id']} missing target_urn")
            # If config allows, create a new share from the suggested comment + link
            if config.AUTO_POST_DISCOVERED_AS_SHARE:
                print(f"AUTO_POST_DISCOVERED_AS_SHARE enabled: creating a new share for item {item['id']}")
                content = f"{item.get('suggested_comment','')}\n\nKaynak: {item.get('target_url','')}"
                # Choose tags for proactive share based on suggested content
                tags = _choose_tags_for_text(content)
                if config.DRY_RUN:
                    print(f"[DRY_RUN] Would create share: {content[:200]}")
                    mark_posted(item['id'])
                    return
                try:
                    api = get_linkedin_api()
                    res = api.post_ugc(content, tags=tags)
                    post_id = res.get('id','') if isinstance(res, dict) else ''
                    post_urn = res.get('urn','') if isinstance(res, dict) else ''
                    if not post_urn and post_id:
                        post_urn = f"urn:li:share:{post_id}"
                    if post_urn:
                        db.save_post(post_id or '', post_urn, content, item.get('target_url'))
                    mark_posted(item['id'])
                    print(f"Created share for proactive item {item['id']} -> {post_urn}")
                    return
                except Exception as e:
                    print(f"Failed to create share for item {item['id']}: {e}")
                    # enqueue as failed action for later retry
                    try:
                        db.enqueue_failed_action('comment', f"{item.get('target_url')}||{item.get('id')}||{content}", str(e))
                    except Exception:
                        pass
                    return
            else:
                print(f"Skipping item {item['id']}: missing target_urn and AUTO_POST_DISCOVERED_AS_SHARE disabled")
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


def process_invites():
    """Process pending invites: generate message, send via API, obey daily limits and batch sizes."""
    print(f"\nProcessing invites at {get_istanbul_time()}")
    try:
        if not config.INVITES_ENABLED:
            print("Invites are disabled in config")
            return

        # Respect configured invite hours window
        now_hour = datetime.now().hour
        start_h = getattr(config, 'INVITES_HOUR_START', 7)
        end_h = getattr(config, 'INVITES_HOUR_END', 21)
        if not (start_h <= now_hour < end_h):
            print(f"Current hour {now_hour} outside invite window {start_h}-{end_h}")
            return

        today_count = db.get_today_invite_count()
        remaining_daily = max(0, config.INVITES_MAX_PER_DAY - today_count)
        if remaining_daily <= 0:
            print(f"Invite daily limit reached: {today_count}/{config.INVITES_MAX_PER_DAY}")
            return

        # Determine per-hour quota and batch size
        per_hour = max(1, int(getattr(config, 'INVITES_PER_HOUR', config.INVITES_BATCH_SIZE)))
        batch = min(per_hour, int(config.INVITES_BATCH_SIZE), remaining_daily)
        pending = db.get_pending_invites()[:batch]
        if not pending:
            print("No pending invites")
            return

        api = get_linkedin_api()
        for inv in pending:
            try:
                person_urn = inv.get('person_urn')
                person_name = inv.get('person_name') or ''
                msg = generate_invite_message(person_name)
                print(f"Sending invite to {person_urn} with message: {msg[:80]}...")
                try:
                    if config.DRY_RUN:
                        print("[DRY_RUN] Would send invite")
                    else:
                        api.send_invite(person_urn, msg)
                    db.mark_invite_sent(inv['id'])
                    print(f"Invite sent/marked for {person_urn}")
                except Exception as e:
                    print(f"Failed to send invite to {person_urn}: {e}")
                    continue
            except Exception as e:
                print(f"Error processing invite id {inv.get('id')}: {e}")
                continue
    except Exception as e:
        print(f"Error in invite processing job: {e}")
        import traceback
        traceback.print_exc()


def process_failed_actions():
    """Process the failed_actions queue with retries and exponential backoff."""
    print(f"\nProcessing failed actions at {get_istanbul_time()}")
    try:
        if not config.FAILED_ACTIONS_ENABLED:
            print("Failed actions processing is disabled in config")
            return

        api = get_linkedin_api()
        due = db.get_due_failed_actions(limit=50)
        print(f"Found {len(due)} failed actions due")

        for act in due:
            aid = act['id']
            action_type = act['action_type']
            payload = act['payload'] or ''
            attempts = int(act.get('attempts', 0) or 0)

            def schedule_retry(err_msg: str):
                nonlocal attempts
                attempts += 1
                max_r = config.FAILED_ACTIONS_MAX_RETRIES
                base = config.FAILED_ACTION_RETRY_BASE_SECONDS
                # If error looks like permission or resource missing, do not retry
                non_retryable_indicators = ['403', 'ACCESS_DENIED', 'RESOURCE_NOT_FOUND', '404']
                try:
                    if any(ind in err_msg for ind in non_retryable_indicators):
                        print(f"Non-retryable error for action {aid}: {err_msg}. Deleting and alerting.")
                        try:
                            with open('data/alerts.log', 'a', encoding='utf-8') as f:
                                f.write(f"{datetime.now().isoformat()} - Non-retryable failed action {aid} ({action_type}) payload={payload}: {err_msg}\n")
                        except Exception:
                            pass
                        db.delete_failed_action(aid)
                        return
                except Exception:
                    pass

                if attempts >= max_r:
                    print(f"Action {aid} reached max retries ({attempts}), removing: {err_msg}")
                    db.delete_failed_action(aid)
                else:
                    next_seconds = base * (2 ** (attempts - 1))
                    next_attempt = datetime.now() + timedelta(seconds=next_seconds)
                    db.update_failed_action_attempt(aid, str(err_msg), next_attempt)
                    print(f"Scheduled retry #{attempts} for action {aid} in {next_seconds}s: {err_msg}")

            try:
                if action_type == 'invite':
                    parts = payload.split('||')
                    person_urn = parts[0] if parts else ''
                    message = '||'.join(parts[2:]) if len(parts) >= 3 else (parts[1] if len(parts) > 1 else '')

                    if config.DRY_RUN:
                        print(f"[DRY_RUN] Would retry invite to {person_urn}")
                        db.delete_failed_action(aid)
                        continue

                    api.send_invite(person_urn, message)
                    db.delete_failed_action(aid)
                    print(f"Retried invite sent to {person_urn}")

                elif action_type == 'comment':
                    parts = payload.split('||')
                    post_urn = parts[0] if parts else ''
                    parent = parts[1] if len(parts) > 2 else None
                    message = '||'.join(parts[2:]) if len(parts) > 2 else (parts[-1] if parts else '')

                    if config.DRY_RUN:
                        print(f"[DRY_RUN] Would retry comment to {post_urn}")
                        db.delete_failed_action(aid)
                        continue

                    api.comment_on_post(post_urn, message, parent_comment_id=parent)
                    db.delete_failed_action(aid)
                    print(f"Retried comment posted to {post_urn}")

                elif action_type == 'list_comments':
                    # payload expected to be the post URN
                    post_urn = payload
                    try:
                        comments = api.list_comments(post_urn)
                        # If we can list comments now, delete the failed action. We don't auto-reply here.
                        db.delete_failed_action(aid)
                        print(f"Successfully listed comments for {post_urn}; removed failed action {aid}")
                    except Exception as e:
                        schedule_retry(str(e))

                else:
                    print(f"Unknown failed action type: {action_type}, deleting to avoid loop")
                    db.delete_failed_action(aid)

            except Exception as e:
                # Special handling: if invite exceeded retries, mark invite failed in invites table
                err = str(e)
                # If it's an invite and this attempt exhausted retries, mark pending invites as failed
                if action_type == 'invite':
                    # compute next or mark failed depending on attempts
                    if attempts + 1 >= config.FAILED_ACTIONS_MAX_RETRIES:
                        try:
                            parts = payload.split('||')
                            person_urn = parts[0] if parts else None
                            if person_urn:
                                pending_invs = db.get_pending_invites()
                                for inv in pending_invs:
                                    if inv.get('person_urn') == person_urn:
                                        db.mark_invite_failed(inv['id'], err)
                        except Exception:
                            pass
                        db.delete_failed_action(aid)
                        print(f"Invite action {aid} reached max retries and was marked failed: {err}")
                    else:
                        schedule_retry(err)
                else:
                    schedule_retry(err)

    except Exception as e:
        print(f"Error in failed actions processor: {e}")
        import traceback
        traceback.print_exc()


def monitor_failures():
    """Lightweight monitoring job: report counts of failed actions and prune very old entries."""
    try:
        from . import db
        due = db.get_due_failed_actions(limit=1000)
        cnt = len(due)
        if cnt:
            print(f"Monitor: {cnt} failed actions currently queued")
        # Prune items older than 30 days to avoid DB growth
        try:
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM failed_actions WHERE created_at <= datetime('now','-30 days')")
            conn.commit()
            conn.close()
        except Exception:
            pass
    except Exception:
        pass


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

    # Process invites every hour (if enabled)
    invite_job = scheduler.add_job(
        process_invites,
        IntervalTrigger(hours=1),
        id='process_invites',
        replace_existing=True
    )

    # Process failed actions frequently (every 10 minutes)
    failed_job = scheduler.add_job(
        process_failed_actions,
        IntervalTrigger(minutes=10),
        id='process_failed_actions',
        replace_existing=True
    )

    # Monitoring job
    monitor_job = scheduler.add_job(
        monitor_failures,
        IntervalTrigger(minutes=30),
        id='monitor_failures',
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
