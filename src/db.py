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

    # Connection invites table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_urn TEXT,
            person_name TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """)

    # Ensure new columns exist (tags, country) for invites without full migrations
    try:
        cursor.execute("PRAGMA table_info(invites)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'tags' not in cols:
            cursor.execute("ALTER TABLE invites ADD COLUMN tags TEXT")
        if 'country' not in cols:
            cursor.execute("ALTER TABLE invites ADD COLUMN country TEXT")
    except Exception:
        pass

    # Failed actions queue (for retrying transient failures)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            payload TEXT,
            error TEXT,
            attempts INTEGER DEFAULT 0,
            last_attempt TIMESTAMP,
            next_attempt TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def delete_token():
    """Delete current LinkedIn access token (logout)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tokens")
    conn.commit()
    conn.close()


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


def enqueue_invite(person_urn: str, person_name: str, reason: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO invites (person_urn, person_name, reason) VALUES (?, ?, ?)""",
        (person_urn, person_name, reason)
    )
    conn.commit()
    conn.close()


def get_pending_invites() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invites WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_invite_sent(invite_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE invites SET status='sent', sent_at = ? WHERE id = ?", (datetime.now(), invite_id))
    conn.commit()
    conn.close()


def mark_invite_failed(invite_id: int, reason: str = '') -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE invites SET status='failed' WHERE id = ?", (invite_id,))
    # Also write an alert line for operator visibility
    try:
        with open(os.path.join(os.path.dirname(config.DB_PATH), 'alerts.log'), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Invite failed for id={invite_id}: {reason}\n")
    except Exception:
        pass
    conn.commit()
    conn.close()


def get_today_invite_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute(
        "SELECT COUNT(*) as count FROM invites WHERE DATE(sent_at) = ? AND status = 'sent'",
        (today,)
    )
    row = cursor.fetchone()
    conn.close()
    return row['count'] if row else 0


def enqueue_failed_action(action_type: str, payload: str, error: str = "", next_attempt=None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO failed_actions (action_type, payload, error, attempts, last_attempt, next_attempt) VALUES (?, ?, ?, ?, ?, ?)",
        (action_type, payload, error, 0, None, next_attempt)
    )
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def get_due_failed_actions(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM failed_actions WHERE next_attempt IS NULL OR next_attempt <= ? ORDER BY next_attempt ASC, created_at ASC LIMIT ?",
        (datetime.now(), limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_failed_action_attempt(action_id: int, error: str, next_attempt) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE failed_actions SET attempts = attempts + 1, error = ?, last_attempt = ?, next_attempt = ? WHERE id = ?",
        (error, datetime.now(), next_attempt, action_id)
    )
    conn.commit()
    conn.close()


def delete_failed_action(action_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM failed_actions WHERE id = ?", (action_id,))
    conn.commit()
    conn.close()


def bump_failed_action_next_attempt_now(action_id: int) -> None:
    """Set the failed action's next_attempt to now so it becomes due immediately."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE failed_actions SET next_attempt = ?, last_attempt = ? WHERE id = ?",
        (datetime.now(), datetime.now(), action_id)
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
