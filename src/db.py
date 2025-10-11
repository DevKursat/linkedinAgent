"""Database management for LinkedIn Agent."""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from .config import config


def get_connection():
    """Get database connection."""
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            refresh_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            post_urn TEXT,
            content TEXT,
            source_url TEXT,
            posted_at TIMESTAMP,
            follow_up_posted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Comments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT UNIQUE,
            post_id TEXT,
            author TEXT,
            content TEXT,
            replied INTEGER DEFAULT 0,
            reply_id TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP
        )
    """)
    
    # Proactive queue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proactive_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_url TEXT,
            target_urn TEXT,
            context TEXT,
            suggested_comment TEXT,
            status TEXT DEFAULT 'pending',
            posted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP
        )
    """)

    # Schedules table (for displaying next run times in web UI)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            next_run TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")


def save_token(access_token: str, expires_in: int, refresh_token: Optional[str] = None):
    """Save LinkedIn access token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    expires_at = int(datetime.now().timestamp()) + expires_in
    
    # Delete old tokens
    cursor.execute("DELETE FROM tokens")
    
    cursor.execute(
        "INSERT INTO tokens (access_token, expires_at, refresh_token) VALUES (?, ?, ?)",
        (access_token, expires_at, refresh_token)
    )
    
    conn.commit()
    conn.close()


def get_token() -> Optional[Dict[str, Any]]:
    """Get current LinkedIn access token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tokens ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def save_post(post_id: str, post_urn: str, content: str, source_url: Optional[str] = None):
    """Save posted content."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO posts (post_id, post_urn, content, source_url, posted_at) 
           VALUES (?, ?, ?, ?, ?)""",
        (post_id, post_urn, content, source_url, datetime.now())
    )
    
    conn.commit()
    conn.close()


def mark_follow_up_posted(post_id: str):
    """Mark that follow-up comment was posted."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE posts SET follow_up_posted = 1 WHERE post_id = ?", (post_id,))
    
    conn.commit()
    conn.close()


def get_recent_posts(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent posts."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM posts ORDER BY posted_at DESC LIMIT ?",
        (limit,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def save_comment(comment_id: str, post_id: str, author: str, content: str):
    """Save a comment seen on a post."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO comments (comment_id, post_id, author, content) 
               VALUES (?, ?, ?, ?)""",
            (comment_id, post_id, author, content)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Comment already exists
        pass
    finally:
        conn.close()


def get_unreplied_comments() -> List[Dict[str, Any]]:
    """Get comments that haven't been replied to."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM comments WHERE replied = 0 ORDER BY seen_at ASC"
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def mark_comment_replied(comment_id: str, reply_id: str):
    """Mark a comment as replied."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE comments SET replied = 1, reply_id = ?, replied_at = ? WHERE comment_id = ?",
        (reply_id, datetime.now(), comment_id)
    )
    
    conn.commit()
    conn.close()


def enqueue_proactive_target(target_url: str, target_urn: str, context: str, suggested_comment: str):
    """Add a target to the proactive queue."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO proactive_queue (target_url, target_urn, context, suggested_comment) 
           VALUES (?, ?, ?, ?)""",
        (target_url, target_urn, context, suggested_comment)
    )
    
    conn.commit()
    conn.close()


def get_pending_queue_items() -> List[Dict[str, Any]]:
    """Get pending proactive queue items."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM proactive_queue WHERE status = 'pending' ORDER BY created_at ASC"
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_approved_queue_items() -> List[Dict[str, Any]]:
    """Get approved proactive queue items that haven't been posted."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM proactive_queue WHERE status = 'approved' AND posted_at IS NULL ORDER BY approved_at ASC"
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def approve_queue_item(item_id: int):
    """Approve a queue item."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE proactive_queue SET status = 'approved', approved_at = ? WHERE id = ?",
        (datetime.now(), item_id)
    )
    
    conn.commit()
    conn.close()


def reject_queue_item(item_id: int):
    """Reject a queue item."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE proactive_queue SET status = 'rejected' WHERE id = ?",
        (item_id,)
    )
    
    conn.commit()
    conn.close()


def mark_queue_item_posted(item_id: int):
    """Mark a queue item as posted."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE proactive_queue SET posted_at = ? WHERE id = ?",
        (datetime.now(), item_id)
    )
    
    conn.commit()
    conn.close()


def get_daily_proactive_count() -> int:
    """Get count of proactive posts today."""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    cursor.execute(
        """SELECT COUNT(*) as count FROM proactive_queue 
           WHERE DATE(posted_at) = ? AND status = 'approved'""",
        (today,)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    return row["count"] if row else 0


# ---------------- Schedules helpers ---------------- #

def set_schedule(job_id: str, next_run_dt) -> None:
    """Upsert a schedule's next run time."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO schedules (job_id, next_run, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            next_run=excluded.next_run,
            updated_at=excluded.updated_at
        """,
        (job_id, next_run_dt, datetime.now())
    )
    conn.commit()
    conn.close()


def get_schedules() -> list:
    """Return all schedules with job id and next run time."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, next_run FROM schedules ORDER BY job_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
