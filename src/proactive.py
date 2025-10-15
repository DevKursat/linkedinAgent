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
    # Generate suggested comment
    suggested_comment = suggest_comment(target_url, context)
    
    # Save to database
    db.enqueue_proactive_target(target_url, target_urn, context, suggested_comment)

    # Autonomously approve good suggestions to allow fully automated posting
    try:
        if suggested_comment and len(suggested_comment) > 15:
            # Mark approved immediately for autonomous operation
            # This keeps the previous UX but enables autonomous mode
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE proactive_queue SET status='approved', approved_at = ? WHERE target_url = ? AND suggested_comment = ?",
                        ( __import__('datetime').datetime.now(), target_url, suggested_comment))
            conn.commit()
            conn.close()
            print(f"Auto-approved proactive target: {target_url}")
    except Exception:
        pass

    # Optionally queue an invite for the person associated with this target
    if suggest_invite and person_urn:
        try:
            db.enqueue_invite(person_urn, person_name or "", reason=f"From proactive target {target_url}")
        except Exception as e:
            print(f"Failed to enqueue invite for {person_urn}: {e}")
    
    print(f"Enqueued target: {target_url}")
    return 1


def suggest_comment(post_content: str, context: str) -> str:
    """Suggest a comment for a target post."""
    try:
        prompt = generate_proactive_comment_prompt(post_content, context)
        suggestion = generate_text(prompt, temperature=0.7).strip()
        if suggestion:
            return suggestion
        # Retry once with an explicit brevity hint if the first response was empty.
        retry_prompt = (
            prompt
            + "\n\nGive a concise 2-sentence LinkedIn comment that adds value to the discussion."
        )
        suggestion = generate_text(retry_prompt, temperature=0.6).strip()
        return suggestion
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
    """Discover relevant posts (by interests) and enqueue with suggested comments.

    For demo, we use article link/title as target_url and leave target_urn empty (user may fill/approve later).
    """
    count = 0
    articles = discover_relevant_posts(limit=limit)
    for a in articles:
        context = f"Relevant to interests: {config.INTERESTS}. Source: {a['source']}"
        content = f"{a['title']}\n{a['summary']}\n{a['link']}"
        try:
            # Try to suggest a comment and also attempt to enqueue an invite when possible.
            suggestion = suggest_comment(content, context)
            # Attempt to resolve a LinkedIn profile URN by downloading the target page
            # and searching for linkedin.com/in/ links which commonly point to author profiles.
            person_urn = ""
            slug = ""
            try:
                link = (a.get('link') or "")
                if link:
                    try:
                        with httpx.Client(timeout=10) as c:
                            r = c.get(link)
                            text = r.text or ""
                            # Find linkedin.com/in/<slug> patterns
                            matches = re.findall(r"linkedin\.com/in/([A-Za-z0-9\-_%]+)", text)
                            if matches:
                                slug = matches[0]
                                person_urn = f"urn:li:person:{slug}"
                    except Exception:
                        # Best-effort only; ignore network errors
                        person_urn = ""
                        slug = ""
            except Exception:
                person_urn = ""
                slug = ""

            # Enqueue proactive target and auto-approve for autonomous posting
            db.enqueue_proactive_target(a['link'], "", context, suggestion)
            # If we resolved a person urn, call enqueue_target which may enqueue an invite.
            try:
                # Use enqueue_target helper to keep auto-approval behavior and invite enqueue.
                enqueue_target(a['link'], "", context, suggest_invite=True, person_urn=person_urn, person_name=(slug if person_urn else ""))
            except Exception:
                pass

            count += 1
        except Exception as e:
            print(f"Error enqueueing discovered item: {e}")
    print(f"Discovered and enqueued {count} items")
    return count
