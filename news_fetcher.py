import feedparser
import logging
from config import NEWS_SOURCES

logger = logging.getLogger(__name__)

# Filter keywords
EXCLUDED_KEYWORDS = [
    'trump', 'biden', 'election', 'politics', 'political',
    'cryptocurrency', 'crypto', 'bitcoin', 'ethereum',
    'speculative', 'meme coin', 'nft'
]


def fetch_news_from_source(source_name, source_url):
    """Fetch news from a single RSS feed"""
    try:
        logger.info(f"Fetching news from {source_name}")
        feed = feedparser.parse(source_url)
        
        articles = []
        for entry in feed.entries[:10]:  # Get top 10 articles
            article = {
                'title': entry.get('title', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'link': entry.get('link', ''),
                'source': source_name,
                'published': entry.get('published', '')
            }
            articles.append(article)
        
        logger.info(f"Fetched {len(articles)} articles from {source_name}")
        return articles
    except Exception as e:
        logger.error(f"Error fetching from {source_name}: {e}")
        return []


def should_filter_article(article):
    """Check if article should be filtered out"""
    title_lower = article['title'].lower()
    summary_lower = article.get('summary', '').lower()
    
    for keyword in EXCLUDED_KEYWORDS:
        if keyword in title_lower or keyword in summary_lower:
            logger.info(f"Filtering article: {article['title']} (matched: {keyword})")
            return True
    
    return False


def fetch_all_news():
    """Fetch and filter news from all sources"""
    all_articles = []
    
    for source_name, source_url in NEWS_SOURCES.items():
        articles = fetch_news_from_source(source_name, source_url)
        all_articles.extend(articles)
    
    # Filter out unwanted content
    filtered_articles = [a for a in all_articles if not should_filter_article(a)]
    
    logger.info(f"Total articles: {len(all_articles)}, After filtering: {len(filtered_articles)}")
    return filtered_articles


def select_best_article(articles):
    """Select the best article for posting"""
    if not articles:
        return None
    
    # Priority order: Product Hunt > Indie Hackers > YC > TechCrunch
    source_priority = {
        'producthunt': 4,
        'indiehackers': 3,
        'ycombinator': 2,
        'techcrunch': 1
    }
    
    # Sort by source priority
    sorted_articles = sorted(
        articles,
        key=lambda x: source_priority.get(x['source'], 0),
        reverse=True
    )
    
    return sorted_articles[0] if sorted_articles else None
