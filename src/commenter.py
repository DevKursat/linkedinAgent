"""Comment generation and reply logic."""
from .gemini import generate_text
from .generator import generate_reply_prompt
from .utils import detect_language, is_negative_sentiment
from .config import config


def comment_mentions_person(comment_text: str) -> bool:
    """Detect if the comment mentions the persona by @name or by name."""
    if not comment_text:
        return False
    name = config.PERSONA_NAME or ""
    lower = comment_text.lower()
    if f"@{name.lower()}" in lower:
        return True
    # Also consider plain name mention
    if name.lower() in lower:
        return True
    return False


def generate_reply(comment_text: str, commenter_name: str = "", reply_as_user: bool = False) -> str:
    """Generate a reply to a comment."""
    # Detect language
    lang = detect_language(comment_text)

    # Map language codes to full names
    lang_map = {
        "en": "English",
        "tr": "Turkish",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "ja": "Japanese",
        "zh-cn": "Chinese",
        "zh-tw": "Chinese",
        "ko": "Korean",
        "ar": "Arabic",
    }

    language_name = lang_map.get(lang, "English")

    # Check if negative
    is_negative = is_negative_sentiment(comment_text)

    # Generate prompt
    # If reply_as_user is not supplied, detect mention heuristically
    if not reply_as_user:
        reply_as_user = comment_mentions_person(comment_text)
    prompt = generate_reply_prompt(comment_text, language_name, is_negative, reply_as_user=reply_as_user)

    # Generate reply
    reply = generate_text(prompt, temperature=0.8, max_tokens=200)

    return reply
