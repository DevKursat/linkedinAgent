import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_PATH


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                linkedin_id TEXT UNIQUE,
                content TEXT NOT NULL,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                posted_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                linkedin_comment_id TEXT UNIQUE,
                content TEXT NOT NULL,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Engagement queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engagement_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_url TEXT NOT NULL,
                target_urn TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                posted_at TIMESTAMP
            )
        ''')
        
        # OAuth tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                posts_created INTEGER DEFAULT 0,
                comments_replied INTEGER DEFAULT 0,
                proactive_comments INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()


def save_post(content, source_url=None, linkedin_id=None, status='pending'):
    """Save a post to database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO posts (content, source_url, linkedin_id, status)
            VALUES (?, ?, ?, ?)
        ''', (content, source_url, linkedin_id, status))
        return cursor.lastrowid


def update_post_status(post_id, status, linkedin_id=None):
    """Update post status"""
    with get_db() as conn:
        cursor = conn.cursor()
        if linkedin_id:
            cursor.execute('''
                UPDATE posts 
                SET status = ?, linkedin_id = ?, posted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, linkedin_id, post_id))
        else:
            cursor.execute('''
                UPDATE posts 
                SET status = ?
                WHERE id = ?
            ''', (status, post_id))


def save_comment(post_id, content, language=None, linkedin_comment_id=None):
    """Save a comment to database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO comments (post_id, content, language, linkedin_comment_id)
            VALUES (?, ?, ?, ?)
        ''', (post_id, content, language, linkedin_comment_id))
        return cursor.lastrowid


def update_comment_status(comment_id, status, linkedin_comment_id=None):
    """Update comment status"""
    with get_db() as conn:
        cursor = conn.cursor()
        if linkedin_comment_id:
            cursor.execute('''
                UPDATE comments 
                SET status = ?, linkedin_comment_id = ?, replied_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, linkedin_comment_id, comment_id))
        else:
            cursor.execute('''
                UPDATE comments 
                SET status = ?
                WHERE id = ?
            ''', (status, comment_id))


def get_pending_engagement_targets():
    """Get approved but not yet posted engagement targets"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM engagement_queue 
            WHERE status = 'approved' AND posted_at IS NULL
            ORDER BY approved_at ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def add_engagement_target(target_url, target_urn=None):
    """Add a target to engagement queue"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO engagement_queue (target_url, target_urn)
            VALUES (?, ?)
        ''', (target_url, target_urn))
        return cursor.lastrowid


def approve_engagement_target(target_id):
    """Approve an engagement target"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE engagement_queue 
            SET status = 'approved', approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (target_id,))


def mark_engagement_posted(target_id, linkedin_comment_id=None):
    """Mark engagement target as posted"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE engagement_queue 
            SET status = 'posted', posted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (target_id,))


def get_pending_engagement_queue():
    """Get all pending engagement targets for approval"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM engagement_queue 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def save_oauth_token(access_token, refresh_token=None, expires_at=None):
    """Save OAuth token"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO oauth_tokens (access_token, refresh_token, expires_at)
            VALUES (?, ?, ?)
        ''', (access_token, refresh_token, expires_at))
        return cursor.lastrowid


def get_latest_oauth_token():
    """Get the latest OAuth token"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM oauth_tokens 
            ORDER BY created_at DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        return dict(row) if row else None


def increment_daily_stat(stat_type):
    """Increment a daily stat counter"""
    today = datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO daily_stats (date, {stat_type})
            VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET {stat_type} = {stat_type} + 1
        ''', (today,))


def get_daily_stats(date=None):
    """Get daily stats for a specific date or today"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM daily_stats WHERE date = ?
        ''', (date,))
        row = cursor.fetchone()
        return dict(row) if row else {
            'date': date,
            'posts_created': 0,
            'comments_replied': 0,
            'proactive_comments': 0
        }
