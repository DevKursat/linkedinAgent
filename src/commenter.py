"""Comment generation and reply logic."""
from .gemini import generate_text
from .generator import generate_reply_prompt
from .utils import detect_language, is_negative_sentiment


def generate_reply(comment_text: str, commenter_name: str = "") -> str:
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
    prompt = generate_reply_prompt(comment_text, language_name, is_negative)
    
    # Generate reply
    reply = generate_text(prompt, temperature=0.8, max_tokens=200)
    
    return reply
