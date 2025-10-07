import time
import random
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from news_fetcher import fetch_all_news, select_best_article
from content_generator import (
    generate_linkedin_post, generate_turkish_summary,
    generate_comment_reply, generate_proactive_comment,
    detect_language, is_negative_comment
)
from linkedin_api import (
    create_post, create_comment, get_user_posts,
    get_post_comments, get_access_token
)
from database import (
    save_post, update_post_status, save_comment, update_comment_status,
    get_pending_engagement_targets, mark_engagement_posted,
    increment_daily_stat, get_daily_stats
)
from config import DAILY_POST_TIME, COMMENT_CHECK_INTERVAL, COMMENT_DELAY_MIN, PROACTIVE_COMMENTS_PER_DAY

logger = logging.getLogger(__name__)


def daily_content_pipeline():
    """Daily content generation and posting pipeline"""
    try:
        logger.info("Starting daily content pipeline")
        
        # Check if we have authentication
        if not get_access_token():
            logger.warning("No access token available, skipping daily post")
            return
        
        # Fetch news
        articles = fetch_all_news()
        if not articles:
            logger.warning("No articles found, skipping daily post")
            return
        
        # Select best article
        selected_article = select_best_article(articles)
        if not selected_article:
            logger.warning("Could not select article, skipping daily post")
            return
        
        logger.info(f"Selected article: {selected_article['title']}")
        
        # Generate LinkedIn post
        post_content = generate_linkedin_post(selected_article)
        
        # Save to database
        post_id = save_post(
            content=post_content,
            source_url=selected_article['link'],
            status='generating'
        )
        
        # Post to LinkedIn
        result = create_post(post_content)
        linkedin_post_id = result.get('id')
        
        # Update status
        update_post_status(post_id, 'posted', linkedin_post_id)
        increment_daily_stat('posts_created')
        
        logger.info(f"Successfully posted to LinkedIn: {linkedin_post_id}")
        
        # Wait before adding Turkish summary comment
        logger.info(f"Waiting {COMMENT_DELAY_MIN} seconds before adding Turkish summary")
        time.sleep(COMMENT_DELAY_MIN)
        
        # Generate and post Turkish summary
        turkish_summary = generate_turkish_summary(post_content, selected_article['link'])
        comment_result = create_comment(linkedin_post_id, turkish_summary)
        
        # Save comment to database
        save_comment(
            post_id=linkedin_post_id,
            content=turkish_summary,
            language='tr',
            linkedin_comment_id=comment_result.get('id')
        )
        
        logger.info("Daily content pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Error in daily content pipeline: {e}", exc_info=True)


def check_and_reply_to_comments():
    """Check for new comments and reply to them"""
    try:
        logger.info("Checking for new comments")
        
        # Check if we have authentication
        if not get_access_token():
            logger.warning("No access token available, skipping comment check")
            return
        
        # Get recent posts
        posts_response = get_user_posts(count=5)
        posts = posts_response.get('elements', [])
        
        for post in posts:
            post_urn = post.get('id')
            if not post_urn:
                continue
            
            try:
                # Get comments on this post
                comments_response = get_post_comments(post_urn)
                comments = comments_response.get('elements', [])
                
                for comment in comments:
                    comment_id = comment.get('id')
                    comment_text = comment.get('message', {}).get('text', '')
                    
                    if not comment_text:
                        continue
                    
                    # Check if we already replied (simple check - in production, track in DB)
                    # For now, we'll skip this check and implement basic logic
                    
                    # Detect language
                    language = detect_language(comment_text)
                    
                    # Check if negative
                    is_neg = is_negative_comment(comment_text)
                    
                    # Calculate delay (5-30 minutes, shorter during peak hours)
                    current_hour = datetime.now().hour
                    is_peak = 9 <= current_hour <= 17  # 9 AM - 5 PM
                    
                    if is_peak:
                        delay = random.randint(5, 15) * 60  # 5-15 minutes
                    else:
                        delay = random.randint(15, 30) * 60  # 15-30 minutes
                    
                    logger.info(f"Comment detected, will reply in {delay/60} minutes")
                    time.sleep(delay)
                    
                    # Generate reply
                    reply_text = generate_comment_reply(comment_text, language, is_neg)
                    
                    # Post reply
                    reply_result = create_comment(post_urn, reply_text)
                    
                    # Save to database
                    save_comment(
                        post_id=post_urn,
                        content=reply_text,
                        language=language,
                        linkedin_comment_id=reply_result.get('id')
                    )
                    
                    increment_daily_stat('comments_replied')
                    logger.info(f"Replied to comment on post {post_urn}")
                    
            except Exception as e:
                logger.error(f"Error processing comments for post {post_urn}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error checking comments: {e}", exc_info=True)


def process_proactive_engagement():
    """Process approved proactive engagement targets"""
    try:
        logger.info("Processing proactive engagement queue")
        
        # Check if we have authentication
        if not get_access_token():
            logger.warning("No access token available, skipping proactive engagement")
            return
        
        # Check daily limit
        stats = get_daily_stats()
        if stats['proactive_comments'] >= PROACTIVE_COMMENTS_PER_DAY:
            logger.info(f"Daily proactive comment limit reached ({PROACTIVE_COMMENTS_PER_DAY})")
            return
        
        # Get pending approved targets
        targets = get_pending_engagement_targets()
        
        if not targets:
            logger.info("No pending engagement targets")
            return
        
        # Process one target at a time
        target = targets[0]
        target_url = target['target_url']
        target_urn = target.get('target_urn')
        
        try:
            # For now, use a simple context (in production, fetch the actual post)
            post_context = f"LinkedIn post at {target_url}"
            
            # Generate comment
            comment_text = generate_proactive_comment(post_context)
            
            # Post comment (need the URN)
            if target_urn:
                comment_result = create_comment(target_urn, comment_text)
                
                # Mark as posted
                mark_engagement_posted(target['id'], comment_result.get('id'))
                increment_daily_stat('proactive_comments')
                
                logger.info(f"Posted proactive comment to {target_url}")
            else:
                logger.warning(f"No URN available for target {target_url}")
                mark_engagement_posted(target['id'])
            
        except Exception as e:
            logger.error(f"Error posting proactive comment to {target_url}: {e}")
            
    except Exception as e:
        logger.error(f"Error in proactive engagement: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Daily content pipeline at specified time
    hour, minute = DAILY_POST_TIME.split(':')
    scheduler.add_job(
        daily_content_pipeline,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id='daily_content_pipeline',
        name='Daily content generation and posting'
    )
    logger.info(f"Scheduled daily content pipeline at {DAILY_POST_TIME}")
    
    # Check comments every 7 minutes
    scheduler.add_job(
        check_and_reply_to_comments,
        IntervalTrigger(minutes=COMMENT_CHECK_INTERVAL),
        id='comment_check',
        name='Check and reply to comments'
    )
    logger.info(f"Scheduled comment checking every {COMMENT_CHECK_INTERVAL} minutes")
    
    # Process proactive engagement every 30 minutes
    scheduler.add_job(
        process_proactive_engagement,
        IntervalTrigger(minutes=30),
        id='proactive_engagement',
        name='Process proactive engagement queue'
    )
    logger.info("Scheduled proactive engagement every 30 minutes")
    
    scheduler.start()
    logger.info("Scheduler started successfully")
    
    return scheduler


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from database import init_db
    init_db()
    
    scheduler = start_scheduler()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down")
