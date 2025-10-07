import os
from dotenv import load_dotenv

load_dotenv()

# LinkedIn OAuth
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI')

# Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'linkedin_bot.db')

# App settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_ENV = os.getenv('FLASK_ENV', 'production')

# Scheduling settings
DAILY_POST_TIME = os.getenv('DAILY_POST_TIME', '09:00')
COMMENT_CHECK_INTERVAL = 7  # minutes
PROACTIVE_COMMENTS_PER_DAY = 9
COMMENT_DELAY_MIN = 66  # seconds for Turkish summary comment

# Persona settings
PERSONA_NAME = "Kürşat"
PERSONA_AGE = 21
PERSONA_TITLE = "Product Builder"
PERSONA_TOPICS = ["AI/ML", "B2B SaaS", "Fintech", "product development lifecycle"]

# News sources
NEWS_SOURCES = {
    'techcrunch': 'https://techcrunch.com/feed/',
    'ycombinator': 'https://news.ycombinator.com/rss',
    'indiehackers': 'https://www.indiehackers.com/feed',
    'producthunt': 'https://www.producthunt.com/feed'
}
