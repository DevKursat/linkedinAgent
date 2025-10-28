"""RSS feed sources for tech news."""
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .config import config


SOURCES = {
    "techcrunch": "https://techcrunch.com/feed/",
    "ycombinator": "https://news.ycombinator.com/rss",
    "indiehackers": "https://www.indiehackers.com/feed",
    "producthunt": "https://www.producthunt.com/feed",
}


def fetch_recent_articles(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch recent articles from all sources."""
    articles = []
    cutoff_time = datetime.now() - timedelta(hours=hours)

    for source_name, source_url in SOURCES.items():
        try:
            print(f"Fetching from {source_name}...")
            feed = feedparser.parse(source_url)

            for entry in feed.entries[:10]:  # Get top 10 from each source
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                # Skip old articles
                if published and published < cutoff_time:
                    continue

                article = {
                    "source": source_name,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": published,
                }
                articles.append(article)

        except Exception as e:
            print(f"Error fetching from {source_name}: {e}")
            continue

    # Interest filtering (lightweight): if INTERESTS set, boost matches
    interests = [s.strip().lower() for s in config.INTERESTS.split(',') if s.strip()]
    if interests:
        def score(a):
            text = (a.get("title","") + "\n" + a.get("summary","" )).lower()
            return sum(1 for kw in interests if kw in text)
        # Prefer items with interest hits
        articles.sort(key=lambda x: (score(x), x["published"] or datetime.min), reverse=True)
    else:
        # Sort by published date (newest first)
        articles.sort(key=lambda x: x["published"] or datetime.min, reverse=True)
    articles.sort(key=lambda x: x["published"] or datetime.min, reverse=True)

    return articles


def get_top_article() -> Dict[str, Any]:
    """Get the most recent article from sources."""
    articles = fetch_recent_articles(hours=48)

    if articles:
        return articles[0]

    return {
        "source": "fallback",
        "title": "Tech Innovation Continues",
        "link": "https://techcrunch.com",
        "summary": "The tech industry continues to innovate across various domains.",
        "published": datetime.now(),
    }


def discover_relevant_posts(limit: int = 5) -> List[Dict[str, Any]]:
    """Return top-N recent articles filtered/scored by interests."""
    return fetch_recent_articles(hours=48)[:limit]
