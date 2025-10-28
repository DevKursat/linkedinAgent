"""Database management for LinkedIn Agent."""
import sqlite3
import os
from datetime import datetime, timedelta
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
    
    # Create tables if they don't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY, access_token TEXT NOT NULL, expires_at INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY, post_id TEXT UNIQUE, post_urn TEXT, content TEXT,
            source_url TEXT, posted_at TIMESTAMP, follow_up_posted INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY, comment_id TEXT UNIQUE, post_id TEXT, author TEXT,
            content TEXT, replied INTEGER DEFAULT 0, reply_id TEXT, seen_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proactive_queue (
            id INTEGER PRIMARY KEY, target_url TEXT, target_urn TEXT, context TEXT,
            suggested_comment TEXT, status TEXT DEFAULT 'pending', posted_at TIMESTAMP,
            created_at TIMESTAMP, approved_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY, job_id TEXT UNIQUE, next_run TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY, person_urn TEXT, person_name TEXT, reason TEXT,
            status TEXT DEFAULT 'pending', created_at TIMESTAMP, sent_at TIMESTAMP,
            tags TEXT, country TEXT, accepted_at TIMESTAMP, rejected_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_actions (
            id INTEGER PRIMARY KEY, action_type TEXT, payload TEXT, error TEXT,
            attempts INTEGER DEFAULT 0, last_attempt TIMESTAMP, next_attempt TIMESTAMP,
            created_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def save_token(access_token: str, expires_in: int):
    conn = get_connection()
    expires_at = int(datetime.now().timestamp()) + expires_in
    conn.execute("DELETE FROM tokens")
    conn.execute("INSERT INTO tokens (access_token, expires_at) VALUES (?, ?)", (access_token, expires_at))
    conn.commit()
    conn.close()

def get_token() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM tokens LIMIT 1").fetchone()
    conn.close()
    if row and row['expires_at'] > datetime.now().timestamp():
        return dict(row)
    return None

def delete_token():
    conn = get_connection()
    conn.execute("DELETE FROM tokens")
    conn.commit()
    conn.close()

def save_post(post_id: str, post_urn: str, content: str, source_url: Optional[str] = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO posts (post_id, post_urn, content, source_url, posted_at) VALUES (?, ?, ?, ?, ?)",
        (post_id, post_urn, content, source_url, datetime.now())
    )
    conn.commit()
    conn.close()

def mark_follow_up_posted(post_id: str):
    conn = get_connection()
    conn.execute("UPDATE posts SET follow_up_posted = 1 WHERE post_id = ?", (post_id,))
    conn.commit()
    conn.close()

def get_recent_posts(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM posts ORDER BY posted_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_comment(comment_id: str, post_id: str, author: str, content: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO comments (comment_id, post_id, author, content, seen_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, post_id, author, content, datetime.now())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Comment already exists
    finally:
        conn.close()

def get_unreplied_comments() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM comments WHERE replied = 0 ORDER BY seen_at ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_comment_replied(comment_id: str, reply_id: str):
    conn = get_connection()
    conn.execute("UPDATE comments SET replied = 1, reply_id = ? WHERE comment_id = ?", (reply_id, comment_id))
    conn.commit()
    conn.close()

def enqueue_invite(person_urn: str, person_name: str, reason: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO invites (person_urn, person_name, reason, created_at) VALUES (?, ?, ?, ?)",
        (person_urn, person_name, reason, datetime.now())
    )
    conn.commit()
    conn.close()

def get_pending_invites() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM invites WHERE status = 'pending' ORDER BY created_at ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_invite_sent(invite_id: int):
    conn = get_connection()
    conn.execute("UPDATE invites SET status='sent', sent_at = ? WHERE id = ?", (datetime.now(), invite_id))
    conn.commit()
    conn.close()

def get_today_invite_count() -> int:
    conn = get_connection()
    today = datetime.now().date()
    row = conn.execute(
        "SELECT COUNT(*) as count FROM invites WHERE DATE(sent_at) = ? AND status = 'sent'", (today,)
    ).fetchone()
    conn.close()
    return row['count'] if row else 0

def get_invite_stats(days: int = 7) -> Dict[str, Any]:
    conn = get_connection()
    since = datetime.now() - timedelta(days=days)
    total_sent = conn.execute(
        "SELECT COUNT(*) FROM invites WHERE status = 'sent' AND sent_at >= ?", (since,)
    ).fetchone()[0] or 0
    accepted = conn.execute(
        "SELECT COUNT(*) FROM invites WHERE accepted_at IS NOT NULL AND accepted_at >= ?", (since,)
    ).fetchone()[0] or 0

    acceptance_rate = (accepted / total_sent * 100.0) if total_sent > 0 else 0.0
    return {
        'total_sent': total_sent,
        'accepted': accepted,
        'acceptance_rate': round(acceptance_rate, 2),
    }

def get_recent_sent_invites(limit: int = 5) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM invites WHERE status='sent' ORDER BY sent_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def enqueue_failed_action(action_type: str, payload: str, error: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO failed_actions (action_type, payload, error, created_at) VALUES (?, ?, ?, ?)",
        (action_type, payload, error, datetime.now())
    )
    conn.commit()
    conn.close()

def log_system_event(event_type: str, details: str = ""):
    """Log a system event for diagnostics and UI visibility."""
    try:
        conn = get_connection()
        conn.execute("INSERT INTO system_events (event_type, details) VALUES (?, ?)", (event_type, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging system event: {e}")

def get_recent_system_events(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent system events."""
    try:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM system_events ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []

# Proactive Queue Functions
def get_pending_queue_items() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM proactive_queue WHERE status = 'pending' ORDER BY created_at ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_approved_queue_items() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM proactive_queue WHERE status = 'approved' AND posted_at IS NULL ORDER BY approved_at ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def approve_queue_item(item_id: int):
    conn = get_connection()
    conn.execute("UPDATE proactive_queue SET status = 'approved', approved_at = ? WHERE id = ?", (datetime.now(), item_id))
    conn.commit()
    conn.close()

def mark_queue_item_posted(item_id: int):
    conn = get_connection()
    conn.execute("UPDATE proactive_queue SET posted_at = ? WHERE id = ?", (datetime.now(), item_id))
    conn.commit()
    conn.close()

def reject_queue_item(item_id: int):
    conn = get_connection()
    conn.execute("UPDATE proactive_queue SET status = 'rejected' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def set_schedule(job_id: str, next_run_dt):
    conn = get_connection()
    conn.execute(
        "INSERT INTO schedules (job_id, next_run) VALUES (?, ?) ON CONFLICT(job_id) DO UPDATE SET next_run=excluded.next_run",
        (job_id, next_run_dt)
    )
    conn.commit()
    conn.close()

def get_schedules() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT job_id, next_run FROM schedules ORDER BY job_id ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
