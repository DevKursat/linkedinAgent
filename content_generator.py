import google.generativeai as genai
from config import GEMINI_API_KEY, PERSONA_NAME, PERSONA_AGE, PERSONA_TITLE, PERSONA_TOPICS
import logging

logger = logging.getLogger(__name__)

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)


def get_persona_context():
    """Get persona context for content generation"""
    return f"""You are {PERSONA_NAME}, a {PERSONA_AGE}-year-old {PERSONA_TITLE}. 
Your writing style is direct, sharp, strategic, and friendly. You use minimal emoji and keep things concise.
You focus on topics like: {', '.join(PERSONA_TOPICS)}.
You never reveal that you are an AI. You write from first-person perspective as {PERSONA_NAME}.
You provide practical insights and strategic thinking about building products and growing businesses."""


def generate_linkedin_post(news_item):
    """Generate a LinkedIn post from a news item using Gemini 2.5 Flash"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""{get_persona_context()}

Based on this news article, write a LinkedIn post in English:

Title: {news_item.get('title', '')}
Summary: {news_item.get('summary', '')}
Link: {news_item.get('link', '')}

Requirements:
- Write in first person as {PERSONA_NAME}
- Be direct and strategic
- Share a specific insight or take
- Keep it under 300 words
- Use minimal emoji (max 1-2)
- End with a question or call to action
- DO NOT mention that this is from an article - make it your own take
- Be authentic and conversational

Write only the post content, nothing else."""

        response = model.generate_content(prompt)
        content = response.text.strip()
        logger.info(f"Generated LinkedIn post: {content[:100]}...")
        return content
    except Exception as e:
        logger.error(f"Error generating LinkedIn post: {e}")
        raise


def generate_turkish_summary(original_post, source_url):
    """Generate Turkish summary comment for a post"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""{get_persona_context()}

You just posted this content in English:
{original_post}

Now write a brief Turkish comment that:
- Summarizes the key point in Turkish
- Keeps the same strategic, direct tone
- Is 2-3 sentences max
- Includes the source link at the end
- Uses minimal emoji

Source link to include: {source_url}

Write only the Turkish comment, nothing else."""

        response = model.generate_content(prompt)
        content = response.text.strip()
        logger.info(f"Generated Turkish summary: {content[:100]}...")
        return content
    except Exception as e:
        logger.error(f"Error generating Turkish summary: {e}")
        raise


def generate_comment_reply(comment_text, comment_language='en', is_negative=False):
    """Generate a reply to a comment"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        tone = "lightly witty but professional correction" if is_negative else "friendly and engaging"
        
        prompt = f"""{get_persona_context()}

Someone commented on your LinkedIn post:
"{comment_text}"

Write a reply in {comment_language} that:
- Matches the tone: {tone}
- Responds directly to their point
- Is 1-2 sentences max
- Uses minimal emoji
- Keeps your {PERSONA_NAME} persona

Write only the reply, nothing else."""

        response = model.generate_content(prompt)
        content = response.text.strip()
        logger.info(f"Generated comment reply: {content[:100]}...")
        return content
    except Exception as e:
        logger.error(f"Error generating comment reply: {e}")
        raise


def generate_proactive_comment(post_context):
    """Generate a proactive comment for engagement"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""{get_persona_context()}

You want to engage with this LinkedIn post:
{post_context}

Write a thoughtful comment that:
- Adds value to the discussion
- Shows your expertise in {', '.join(PERSONA_TOPICS[:2])}
- Is strategic and insightful
- Is 2-3 sentences max
- Uses minimal emoji
- Feels authentic, not salesy

Write only the comment, nothing else."""

        response = model.generate_content(prompt)
        content = response.text.strip()
        logger.info(f"Generated proactive comment: {content[:100]}...")
        return content
    except Exception as e:
        logger.error(f"Error generating proactive comment: {e}")
        raise


def detect_language(text):
    """Detect the language of a text"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""Detect the language of this text. Respond with only the two-letter language code (e.g., 'en', 'tr', 'es', 'fr'):

{text}"""

        response = model.generate_content(prompt)
        language = response.text.strip().lower()[:2]
        return language
    except Exception as e:
        logger.error(f"Error detecting language: {e}")
        return 'en'


def is_negative_comment(text):
    """Detect if a comment is negative/critical"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""Is this comment negative, critical, or disagreeing? Respond with only 'yes' or 'no':

{text}"""

        response = model.generate_content(prompt)
        result = response.text.strip().lower()
        return result == 'yes'
    except Exception as e:
        logger.error(f"Error detecting negative comment: {e}")
        return False
