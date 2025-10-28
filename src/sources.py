"""Module for fetching articles from configured sources."""
import feedparser
from .config import config
from . import db
from .utils import get_clean_url
from .gemini import generate_text
from .generator import generate_summary_prompt


def get_all_articles():
    """Fetch articles from all configured RSS feeds."""
    all_entries = []

    # Pre-defined high-quality sources
    default_sources = {
        'Stratechery': 'https://stratechery.com/feed/',
        'A16Z': 'https://a16z.com/feed/',
    }

    # User-defined custom sources
    custom_sources = {}
    try:
        raw_custom = (config.CUSTOM_RSS_FEEDS or '').strip()
        if raw_custom:
            for item in raw_custom.split(','):
                parts = item.split('|')
                if len(parts) == 2 and parts[0].strip() and parts[1].strip().startswith(('http', 'https')):
                    custom_sources[parts[0].strip()] = parts[1].strip()
    except Exception as e:
        print(f"Warning: Could not parse CUSTOM_RSS_FEEDS. Error: {e}")

    # Combine sources, with custom sources taking precedence
    sources = {**default_sources, **custom_sources}

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                all_entries.append({
                    'title': entry.title,
                    'link': get_clean_url(entry.link),
                    'summary': entry.summary,
                    'source': name
                })
        except Exception as e:
            print(f"Error fetching feed for {name}: {e}")
            db.log_system_event("rss_fetch_failed", f"Failed to fetch from {name}: {e}")

    return all_entries


def get_top_article():
    """Select the top article and generate a summary."""
    articles = get_all_articles()
    if not articles:
        raise ValueError("No articles found from any source.")

    # Simple selection logic: for now, just pick the first one.
    # Future enhancement: implement a scoring system.
    top_article = articles[0]

    try:
        summary_prompt = generate_summary_prompt(top_article['title'], top_article['summary'])
        generated_summary = generate_text(summary_prompt)
        top_article['summary'] = generated_summary
    except Exception as e:
        print(f"Warning: Failed to generate summary for '{top_article['title']}': {e}")
        # Proceed with the original summary if generation fails

    return top_article
