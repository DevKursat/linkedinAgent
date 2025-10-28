"""Content moderation and approval logic."""
from .config import config
from . import db
from .gemini import generate_text
from .generator import generate_moderation_prompt


def should_post_content(content: str) -> (bool, str):
    """
    Check if the content should be posted based on moderation rules.
    Returns a tuple of (should_post, reason).
    """
    moderation_level = (config.MODERATION_LEVEL or 'none').lower()

    if moderation_level == 'none':
        return True, "No moderation required."

    if moderation_level == 'self_moderate':
        try:
            prompt = generate_moderation_prompt(content)
            decision = generate_text(prompt, temperature=0.1).strip().lower()

            if decision.startswith('yes'):
                return True, "Content self-approved by AI."
            else:
                # Log this for review
                db.log_system_event("self_moderation_rejected", f"Content: {content[:100]}...")
                return False, "Content rejected by AI self-moderation."
        except Exception as e:
            print(f"Error during self-moderation: {e}")
            # Fail safe: if moderation fails, block the post.
            db.log_system_event("self_moderation_failed", f"Error: {e}")
            return False, "Self-moderation process failed."

    if moderation_level == 'human_in_the_loop':
        # In this mode, all generated content is saved for manual approval.
        # The scheduler does not post directly. Another process would read approved content.
        # For this application, we can simulate this by logging and blocking.
        db.add_pending_post(content, "Awaiting human approval.")
        return False, "Content pending human approval."

    return True, "Moderation level not recognized, defaulting to approve."
