"""Utility functions for LinkedIn Agent."""
import pytz
import random
from datetime import datetime, time
from typing import Tuple, Optional
from langdetect import detect, LangDetectException
from .config import config


def get_istanbul_time() -> datetime:
    """Get current time in Istanbul timezone."""
    tz = pytz.timezone(config.TZ)
    return datetime.now(tz)


def parse_time_window(window_str: str) -> Tuple[time, time]:
    """Parse time window string like '09:30-11:00' to time objects."""
    start_str, end_str = window_str.split("-")
    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))

    return time(start_hour, start_min), time(end_hour, end_min)


def is_in_peak_window() -> bool:
    """Check if current time is in peak posting window."""
    now = get_istanbul_time()
    current_time = now.time()

    # Parse windows from config
    windows = config.POST_WINDOWS.split(",")

    for window in windows:
        window = window.strip()
        if ":" not in window:
            continue

        # Check if weekday restriction
        if window.startswith("weekday:"):
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                continue
            window = window.replace("weekday:", "")

        try:
            start_time, end_time = parse_time_window(window)
            if start_time <= current_time <= end_time:
                return True
        except Exception:
            continue

    return False


def get_random_post_time() -> datetime:
    """Get a random time within posting windows today."""
    now = get_istanbul_time()
    windows = config.POST_WINDOWS.split(",")

    valid_windows = []
    for window in windows:
        window = window.strip()
        if ":" not in window:
            continue

        # Check weekday restriction
        if window.startswith("weekday:"):
            if now.weekday() >= 5:
                continue
            window = window.replace("weekday:", "")

        try:
            start_time, end_time = parse_time_window(window)
            valid_windows.append((start_time, end_time))
        except Exception:
            continue

    if not valid_windows:
        # Default to 10 AM if no valid windows
        return now.replace(hour=10, minute=0, second=0, microsecond=0)

    # Pick random window
    start_time, end_time = random.choice(valid_windows)

    # Random time within window
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    random_minutes = random.randint(start_minutes, end_minutes)

    hour = random_minutes // 60
    minute = random_minutes % 60

    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def get_reply_delay_seconds() -> int:
    """Get random delay for replying to comments (5-30 minutes, faster in peak)."""
    if is_in_peak_window():
        # Faster replies during peak: 5-15 minutes
        return random.randint(5 * 60, 15 * 60)
    else:
        # Slower replies off-peak: 15-30 minutes
        return random.randint(15 * 60, 30 * 60)


def detect_language(text: str) -> str:
    """Detect language of text."""
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return "en"  # Default to English


def is_negative_sentiment(text: str) -> bool:
    """Simple heuristic to detect negative sentiment."""
    negative_indicators = [
        "wrong", "bad", "terrible", "awful", "disagree", "hate",
        "stupid", "nonsense", "ridiculous", "false", "misleading",
        "yanlış", "kötü", "berbat", "katılmıyorum", "saçma",
    ]

    text_lower = text.lower()
    for indicator in negative_indicators:
        if indicator in text_lower:
            return True

    return False


def format_source_name(source_key: str) -> str:
    """Format source key to display name."""
    mapping = {
        "techcrunch": "TechCrunch",
        "ycombinator": "Y Combinator",
        "indiehackers": "Indie Hackers",
        "producthunt": "Product Hunt",
    }
    return mapping.get(source_key, source_key.title())
