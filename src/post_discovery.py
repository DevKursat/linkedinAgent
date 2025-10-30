"""
Automated LinkedIn post discovery system.
Finds relevant LinkedIn posts based on user interests without using the deprecated search API.
"""
import re
import random
import logging
from typing import List, Dict, Optional
import feedparser
from bs4 import BeautifulSoup
import httpx
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostDiscovery:
    """Discovers LinkedIn posts through indirect methods."""
    
    def __init__(self, interests: List[str]):
        """
        Initialize post discovery with user interests.
        
        Args:
            interests: List of keywords representing user interests (e.g., ['ai', 'startup', 'product'])
        """
        self.interests = interests
        self.discovered_posts = []
        
        # RSS feeds that aggregate LinkedIn content
        self.linkedin_rss_sources = [
            # Tech news sites that often link to LinkedIn posts
            "https://techcrunch.com/feed/",
            "https://www.wired.com/feed/rss",
            "https://feeds.arstechnica.com/arstechnica/index",
        ]
    
    async def discover_posts_from_rss(self, max_posts: int = 10) -> List[Dict[str, str]]:
        """
        Discover LinkedIn posts mentioned in RSS feeds.
        
        Returns:
            List of dicts with 'url' and 'title' keys
        """
        discovered = []
        
        for feed_url in self.linkedin_rss_sources:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:  # Check first 20 entries
                    # Check if article content mentions LinkedIn or contains LinkedIn links
                    content = entry.get('summary', '') + entry.get('title', '')
                    
                    # Look for LinkedIn URLs in the content
                    linkedin_urls = re.findall(
                        r'https?://(?:www\.)?linkedin\.com/(?:feed/update/urn:li:activity:\d+|posts/[\w\-]+)',
                        content
                    )
                    
                    if linkedin_urls:
                        for url in linkedin_urls:
                            discovered.append({
                                'url': url,
                                'title': entry.get('title', 'LinkedIn Post'),
                                'source': 'RSS Feed',
                                'discovered_at': datetime.now().isoformat()
                            })
                            
                            if len(discovered) >= max_posts:
                                return discovered
                
            except Exception as e:
                logger.error(f"Error parsing feed {feed_url}: {e}")
        
        return discovered
    
    async def discover_posts_from_hashtags(self, max_posts: int = 10) -> List[Dict[str, str]]:
        """
        Discover posts by constructing LinkedIn hashtag URLs based on interests.
        These URLs can be used to direct users or for scraping.
        
        Returns:
            List of suggested LinkedIn hashtag URLs
        """
        suggested_urls = []
        
        for interest in self.interests[:5]:  # Use top 5 interests
            # LinkedIn hashtag URLs
            hashtag_url = f"https://www.linkedin.com/feed/hashtag/{interest.lower()}/"
            suggested_urls.append({
                'url': hashtag_url,
                'title': f"#{interest} posts",
                'source': 'Hashtag',
                'interest': interest
            })
        
        return suggested_urls
    
    async def get_trending_topics(self) -> List[str]:
        """
        Get trending topics related to user interests.
        Uses external APIs that don't require LinkedIn authentication.
        """
        trending = []
        
        # Combine interests with trending tech keywords
        tech_trends = ['ai', 'machine learning', 'startup', 'saas', 'product', 'devtools']
        
        for interest in self.interests:
            if interest.lower() in tech_trends or len(trending) < 10:
                trending.append(interest)
        
        return trending
    
    async def discover_posts_smart(self, max_posts: int = 5) -> List[Dict[str, str]]:
        """
        Smart discovery: combines multiple methods to find relevant posts.
        
        Returns:
            List of discovered post information
        """
        all_posts = []
        
        # Method 1: Search RSS feeds for LinkedIn mentions
        rss_posts = await self.discover_posts_from_rss(max_posts)
        all_posts.extend(rss_posts)
        
        # Method 2: Generate hashtag-based suggestions
        if len(all_posts) < max_posts:
            hashtag_posts = await self.discover_posts_from_hashtags(max_posts - len(all_posts))
            all_posts.extend(hashtag_posts)
        
        # Shuffle to add randomness
        random.shuffle(all_posts)
        
        return all_posts[:max_posts]
    
    async def scrape_public_linkedin_posts(self, topic: str, max_posts: int = 5) -> List[Dict[str, str]]:
        """
        Attempts to scrape publicly available LinkedIn posts.
        Note: This may not work due to LinkedIn's anti-scraping measures.
        Use cautiously and with rate limiting.
        
        Args:
            topic: Topic to search for
            max_posts: Maximum number of posts to return
            
        Returns:
            List of discovered posts
        """
        discovered = []
        
        try:
            # Use a public LinkedIn hashtag page (these are sometimes accessible)
            url = f"https://www.linkedin.com/feed/hashtag/{topic.lower()}/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Note: This likely won't work without authentication, but we try
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    # This is a placeholder - LinkedIn's pages require JavaScript rendering
                    # In a real implementation, you'd need Playwright or similar
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Log that we attempted but likely can't scrape
                    logger.info(f"Attempted to access {url} - response code {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Could not scrape LinkedIn posts: {e}")
        
        return discovered


class ProfileDiscovery:
    """Discovers LinkedIn profiles to invite based on interests and network growth strategy."""
    
    def __init__(self, interests: List[str], max_daily_invites: int = 35):
        """
        Initialize profile discovery.
        
        Args:
            interests: User's interests for targeting
            max_daily_invites: Maximum invitations per day (default 35 for ~25 min intervals)
        """
        self.interests = interests
        self.max_daily_invites = max_daily_invites
        self.invited_today = 0
        self.last_invite_date = None
    
    def reset_daily_counter(self):
        """Reset the daily invitation counter if it's a new day."""
        today = datetime.now().date()
        if self.last_invite_date != today:
            self.invited_today = 0
            self.last_invite_date = today
    
    def can_send_invite(self) -> bool:
        """Check if we can send an invite today."""
        self.reset_daily_counter()
        
        # Check daily limit
        if self.invited_today >= self.max_daily_invites:
            logger.info(f"Daily invite limit reached ({self.max_daily_invites}). Will resume tomorrow.")
            return False
        
        return True
    
    def record_invite_sent(self):
        """Record that an invitation was sent."""
        self.reset_daily_counter()
        self.invited_today += 1
    
    async def discover_profiles_safe(self) -> Optional[Dict[str, str]]:
        """
        Safely discover a profile to invite.
        
        Returns:
            Profile info dict or None if cannot find/send
        """
        if not self.can_send_invite():
            logger.info("Daily invite limit reached. Skipping for safety.")
            return None
        
        # For now, return None to prevent invitations
        # In a real implementation, this would use:
        # 1. LinkedIn's official APIs if permissions are available
        # 2. User's existing connections' 2nd degree connections
        # 3. Industry-specific profile suggestions
        
        logger.info("Profile discovery: Waiting for user-provided targets or API permissions")
        return None
    
    async def suggest_profile_from_interests(self) -> Dict[str, str]:
        """
        Generate suggested profile criteria based on interests.
        This doesn't find actual profiles but provides guidance.
        """
        suggestion = {
            'interests': self.interests,
            'suggested_titles': [
                f"{interest} engineer" for interest in self.interests[:3]
            ],
            'suggested_companies': ['startup', 'tech company', 'saas'],
            'connection_level': '2nd degree',
            'note': 'Manually search LinkedIn for these criteria'
        }
        
        return suggestion
