"""Proactive posting queue management."""
from typing import Dict, Any, Optional
from . import db
from .gemini import generate_text
from .generator import generate_proactive_comment_prompt
from .sources import discover_relevant_posts
from .config import config

import re
import httpx


def enqueue_target(target_url: str, target_urn: str, context: str = "", suggest_invite: bool = False, person_urn: str = "", person_name: str = "") -> int:
    """Enqueue a target post for proactive commenting."""
    suggested_comment = suggest_comment(target_url, context)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO proactive_queue (target_url, target_urn, context, suggested_comment, created_at) VALUES (?, ?, ?, ?, ?)",
        (target_url, target_urn, context, suggested_comment, __import__('datetime').datetime.now())
    )
    conn.commit()
    conn.close()

    print(f"Enqueued target: {target_url}")
    return 1


def suggest_comment(post_content: str, context: str) -> str:
    """Suggest a comment for a target post."""
    try:
        prompt = generate_proactive_comment_prompt(post_content, context)
        return generate_text(prompt, temperature=0.7).strip()
    except Exception as e:
        print(f"Error suggesting comment: {e}")
        return ""


def get_approved_targets(limit: int = 9) -> list:
    """Get approved targets ready to post."""
    return db.get_approved_queue_items()[:limit]


def mark_posted(item_id: int):
    """Mark a queue item as posted."""
    db.mark_queue_item_posted(item_id)
    print(f"Marked queue item {item_id} as posted")


def discover_and_enqueue(limit: int = 3) -> int:
    """Discover relevant posts and enqueue with suggested comments."""
    count = 0
    articles = discover_relevant_posts(limit=limit)
    for a in articles:
        context = f"Relevant to interests: {config.INTERESTS}. Source: {a['source']}"
        content = f"{a['title']}\n{a['summary']}\n{a['link']}"
        try:
            enqueue_target(a['link'], "", context)
            count += 1
        except Exception as e:
            print(f"Error enqueueing discovered item: {e}")
    print(f"Discovered and enqueued {count} items")
    return count
