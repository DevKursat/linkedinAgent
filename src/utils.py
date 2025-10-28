"""Utility functions for the LinkedIn agent."""
import random
from datetime import datetime, time, timedelta
from urllib.parse import urlparse, parse_qs
import pytz

def get_istanbul_time():
    """Get the current time in Istanbul."""
    return datetime.now(pytz.timezone('Europe/Istanbul'))

def get_random_post_time():
    """Get a random time between 9 AM and 10 AM Istanbul time."""
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(istanbul_tz)
    
    # Define the target time window in the local timezone of the server
    # Then convert to Istanbul time if needed, but it's easier to work directly in the target timezone
    start_time = time(9, 0, 0)
    end_time = time(10, 0, 0)
    
    # Calculate a random minute and second within the hour
    random_minute = random.randint(start_time.minute, end_time.minute -1) # -1 to ensure it's before 10:00
    random_second = random.randint(0, 59)
    
    post_time = now.replace(hour=start_time.hour, minute=random_minute, second=random_second, microsecond=0)
    
    # If the calculated post time is in the past for today, schedule it for tomorrow
    if post_time < now:
        post_time += timedelta(days=1)
        
    return post_time.time()

def get_reply_delay_seconds():
    """Get a random delay in seconds for replies to simulate human behavior."""
    return random.randint(120, 300) # 2 to 5 minutes

def get_clean_url(url: str) -> str:
    """Remove tracking parameters from a URL."""
    if not url:
        return ""
    try:
        parsed_url = urlparse(url)
        # Reconstruct the URL without the query string or fragment
        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        # Some URLs might have the core content identifier in the query string
        # e.g., YouTube. For LinkedIn articles, cleaning is usually safe.
        # Let's check for a common LinkedIn article tracker
        if 'feedView=' in parsed_url.query:
            return clean_url

        # A more robust version could selectively keep certain query params
        # For now, we strip all for simplicity
        return clean_url
    except Exception:
        # If parsing fails, return the original URL
        return url

def format_source_name(source_name: str) -> str:
    """Format the source name for display in posts."""
    if not source_name:
        return "the original source"
    
    # Example: "A16Z" -> "a16z"
    if source_name.isupper():
        return source_name.lower()

    # Example: "Stratechery" -> "Stratechery" (no change)
    return source_name
