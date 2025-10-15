"""Handle incoming comments: save, generate reply, post or enqueue retry."""
from typing import Optional
from . import db
from .commenter import generate_reply, comment_mentions_person
from .linkedin_api import get_linkedin_api
from .config import config


def handle_incoming_comment(post_urn: str, comment_id: str, actor: str, text: str, reply_as_user: bool = False) -> dict:
    """Process an incoming comment: save it and attempt to reply.

    Returns a dict with result details.
    """
    # Save comment (DB will dedupe)
    try:
        db.save_comment(comment_id, post_urn.split(':')[-1], actor, text)
    except Exception:
        pass

    # Decide whether to reply (basic heuristic: skip bot/self)
    try:
        me = get_linkedin_api().me()
        me_actor = f"urn:li:person:{me['id']}"
        if actor == me_actor:
            return {"status": "skipped_self"}
    except Exception:
        # If me() fails, continue — we may still attempt reply
        pass

    # Generate reply text
    try:
        reply_text = generate_reply(text, actor, reply_as_user=reply_as_user)
    except Exception as e:
        return {"status": "generation_failed", "error": str(e)}

    if config.DRY_RUN:
        # Mark replied in DB to avoid repeated processing in tests
        try:
            db.mark_comment_replied(comment_id, 'dry_run')
        except Exception:
            pass
        return {"status": "dry_run", "reply": reply_text}

    # Attempt to post reply via API
    api = get_linkedin_api()
    try:
        res = api.comment_on_post(post_urn, reply_text, parent_comment_id=comment_id)
        reply_id = res.get('id', '') if isinstance(res, dict) else ''
        try:
            db.mark_comment_replied(comment_id, reply_id)
        except Exception:
            pass
        return {"status": "replied", "reply_id": reply_id, "reply": reply_text}
    except Exception as e:
        # Enqueue failed action for retry
        try:
            payload = f"{post_urn}||{comment_id}||{reply_text}"
            db.enqueue_failed_action('comment', payload, str(e))
        except Exception:
            pass
        return {"status": "post_failed", "error": str(e)}
