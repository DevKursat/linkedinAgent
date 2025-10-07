#!/usr/bin/env python3
"""
Admin CLI for LinkedIn Bot
Provides commands for managing the bot, viewing stats, and manual operations
"""

import sys
import argparse
from datetime import datetime, timedelta
from database import (
    init_db, get_daily_stats, get_pending_engagement_queue,
    get_latest_oauth_token, save_post, increment_daily_stat,
    add_engagement_target, approve_engagement_target
)
from content_generator import generate_linkedin_post, detect_language
from news_fetcher import fetch_all_news, select_best_article
from scheduler import daily_content_pipeline


def cmd_stats(args):
    """Show statistics"""
    print("LinkedIn Bot Statistics")
    print("=" * 60)
    
    # OAuth status
    token = get_latest_oauth_token()
    if token:
        print(f"✓ Authenticated")
        if token.get('expires_at'):
            expires = datetime.fromisoformat(token['expires_at'])
            if expires > datetime.now():
                days_left = (expires - datetime.now()).days
                print(f"  Token expires in {days_left} days")
            else:
                print(f"  ⚠ Token expired!")
    else:
        print("✗ Not authenticated")
    
    print()
    
    # Today's stats
    today_stats = get_daily_stats()
    print(f"Today's Activity ({today_stats['date']}):")
    print(f"  Posts created: {today_stats['posts_created']}")
    print(f"  Comments replied: {today_stats['comments_replied']}")
    print(f"  Proactive comments: {today_stats['proactive_comments']}")
    
    print()
    
    # Past week stats
    print("Past 7 Days:")
    total_posts = 0
    total_comments = 0
    total_proactive = 0
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        stats = get_daily_stats(date)
        total_posts += stats['posts_created']
        total_comments += stats['comments_replied']
        total_proactive += stats['proactive_comments']
        print(f"  {date}: {stats['posts_created']} posts, {stats['comments_replied']} replies, {stats['proactive_comments']} proactive")
    
    print()
    print(f"Total: {total_posts} posts, {total_comments} replies, {total_proactive} proactive")


def cmd_queue(args):
    """Show engagement queue"""
    queue = get_pending_engagement_queue()
    
    print("Pending Engagement Queue")
    print("=" * 60)
    
    if not queue:
        print("No pending items")
        return
    
    for item in queue:
        print(f"ID {item['id']}: {item['target_url']}")
        print(f"  Status: {item['status']}")
        print(f"  Created: {item['created_at']}")
        print()


def cmd_add_target(args):
    """Add engagement target"""
    target_id = add_engagement_target(args.url)
    print(f"Added target to queue (ID: {target_id})")
    
    if args.approve:
        approve_engagement_target(target_id)
        print(f"Target approved")


def cmd_test_news(args):
    """Test news fetching"""
    print("Fetching news...")
    articles = fetch_all_news()
    
    print(f"\nFound {len(articles)} articles")
    
    if articles:
        best = select_best_article(articles)
        print(f"\nBest article:")
        print(f"  Title: {best['title']}")
        print(f"  Source: {best['source']}")
        print(f"  Link: {best['link']}")
        
        if args.generate:
            print("\nGenerating LinkedIn post...")
            post = generate_linkedin_post(best)
            print("\n" + "=" * 60)
            print(post)
            print("=" * 60)


def cmd_run_daily(args):
    """Run daily content pipeline manually"""
    print("Running daily content pipeline...")
    try:
        daily_content_pipeline()
        print("✓ Daily pipeline completed successfully")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def cmd_init_db(args):
    """Initialize database"""
    print("Initializing database...")
    init_db()
    print("✓ Database initialized")


def main():
    parser = argparse.ArgumentParser(
        description='LinkedIn Bot Admin CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s stats                          Show statistics
  %(prog)s queue                          Show engagement queue
  %(prog)s add-target URL                 Add target to queue
  %(prog)s add-target URL --approve       Add and approve target
  %(prog)s test-news                      Test news fetching
  %(prog)s test-news --generate           Test news and generate post
  %(prog)s run-daily                      Run daily pipeline manually
  %(prog)s init-db                        Initialize database
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Stats command
    subparsers.add_parser('stats', help='Show statistics')
    
    # Queue command
    subparsers.add_parser('queue', help='Show engagement queue')
    
    # Add target command
    add_parser = subparsers.add_parser('add-target', help='Add engagement target')
    add_parser.add_argument('url', help='LinkedIn post URL or URN')
    add_parser.add_argument('--approve', action='store_true', help='Approve immediately')
    
    # Test news command
    news_parser = subparsers.add_parser('test-news', help='Test news fetching')
    news_parser.add_argument('--generate', action='store_true', help='Generate post from best article')
    
    # Run daily command
    subparsers.add_parser('run-daily', help='Run daily pipeline manually')
    
    # Init DB command
    subparsers.add_parser('init-db', help='Initialize database')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to command handler
    commands = {
        'stats': cmd_stats,
        'queue': cmd_queue,
        'add-target': cmd_add_target,
        'test-news': cmd_test_news,
        'run-daily': cmd_run_daily,
        'init-db': cmd_init_db,
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
