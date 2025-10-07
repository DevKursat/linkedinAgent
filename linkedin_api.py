import requests
from datetime import datetime, timedelta
from config import LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI
from database import save_oauth_token, get_latest_oauth_token
import logging

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = 'https://api.linkedin.com/v2'
LINKEDIN_AUTH_URL = 'https://www.linkedin.com/oauth/v2/authorization'
LINKEDIN_TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'


def get_authorization_url(state=None):
    """Generate LinkedIn OAuth authorization URL"""
    params = {
        'response_type': 'code',
        'client_id': LINKEDIN_CLIENT_ID,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'scope': 'r_liteprofile r_emailaddress w_member_social rw_organization_admin'
    }
    if state:
        params['state'] = state
    
    query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    return f'{LINKEDIN_AUTH_URL}?{query_string}'


def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET,
        'redirect_uri': LINKEDIN_REDIRECT_URI
    }
    
    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        # Calculate expiration time
        expires_in = token_data.get('expires_in', 5184000)  # Default 60 days
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Save to database
        save_oauth_token(
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            expires_at=expires_at.isoformat()
        )
        
        logger.info("Successfully exchanged code for access token")
        return token_data
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        raise


def get_access_token():
    """Get current valid access token"""
    token_data = get_latest_oauth_token()
    if not token_data:
        return None
    
    # Check if token is expired
    if token_data.get('expires_at'):
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() >= expires_at:
            logger.warning("Access token expired")
            return None
    
    return token_data['access_token']


def get_user_profile():
    """Get authenticated user's LinkedIn profile"""
    access_token = get_access_token()
    if not access_token:
        raise Exception("No valid access token available")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f'{LINKEDIN_API_BASE}/me', headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise


def create_post(text, visibility='PUBLIC'):
    """Create a LinkedIn post"""
    access_token = get_access_token()
    if not access_token:
        raise Exception("No valid access token available")
    
    # Get user profile to get the person URN
    profile = get_user_profile()
    person_urn = f"urn:li:person:{profile['id']}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    post_data = {
        'author': person_urn,
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {
                    'text': text
                },
                'shareMediaCategory': 'NONE'
            }
        },
        'visibility': {
            'com.linkedin.ugc.MemberNetworkVisibility': visibility
        }
    }
    
    try:
        response = requests.post(
            f'{LINKEDIN_API_BASE}/ugcPosts',
            headers=headers,
            json=post_data
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Successfully created post: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        raise


def create_comment(post_urn, text):
    """Create a comment on a LinkedIn post"""
    access_token = get_access_token()
    if not access_token:
        raise Exception("No valid access token available")
    
    # Get user profile
    profile = get_user_profile()
    person_urn = f"urn:li:person:{profile['id']}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    comment_data = {
        'actor': person_urn,
        'object': post_urn,
        'message': {
            'text': text
        }
    }
    
    try:
        response = requests.post(
            f'{LINKEDIN_API_BASE}/socialActions/{post_urn}/comments',
            headers=headers,
            json=comment_data
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Successfully created comment on post: {post_urn}")
        return result
    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        raise


def get_post_comments(post_urn, count=100):
    """Get comments on a LinkedIn post"""
    access_token = get_access_token()
    if not access_token:
        raise Exception("No valid access token available")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f'{LINKEDIN_API_BASE}/socialActions/{post_urn}/comments?count={count}',
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting post comments: {e}")
        raise


def get_user_posts(count=10):
    """Get authenticated user's recent posts"""
    access_token = get_access_token()
    if not access_token:
        raise Exception("No valid access token available")
    
    profile = get_user_profile()
    person_urn = f"urn:li:person:{profile['id']}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f'{LINKEDIN_API_BASE}/ugcPosts?q=authors&authors=List({person_urn})&count={count}',
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        raise
