"""LinkedIn API integration."""
import httpx
from typing import Optional, Dict, Any, List
from .config import config
from . import db


class LinkedInAPI:
    """LinkedIn API client."""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize LinkedIn API client."""
        self.access_token = access_token or self._get_stored_token()
    
    def _get_stored_token(self) -> Optional[str]:
        """Get stored access token from database."""
        token_data = db.get_token()
        if token_data:
            return token_data["access_token"]
        return None
    
    def get_authorization_url(self, state: str) -> str:
        """Get LinkedIn OAuth authorization URL."""
        scopes = config.LINKEDIN_SCOPES.replace(" ", "%20")
        return (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"response_type=code&"
            f"client_id={config.LINKEDIN_CLIENT_ID}&"
            f"redirect_uri={config.LINKEDIN_REDIRECT_URI}&"
            f"state={state}&"
            f"scope={scopes}"
        )
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.LINKEDIN_REDIRECT_URI,
            "client_id": config.LINKEDIN_CLIENT_ID,
            "client_secret": config.LINKEDIN_CLIENT_SECRET,
        }
        
        response = httpx.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        token_data = response.json()
        
        # Save token to database
        db.save_token(
            token_data["access_token"],
            token_data["expires_in"],
            token_data.get("refresh_token")
        )
        
        self.access_token = token_data["access_token"]
        return token_data
    
    def me(self) -> Dict[str, Any]:
        """Get current user profile."""
        if not self.access_token:
            raise ValueError("No access token available")
        
        response = httpx.get(
            f"{self.BASE_URL}/me",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        response.raise_for_status()
        return response.json()
    
    def post_ugc(self, text: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        """Post a UGC (User Generated Content) post to LinkedIn."""
        if not self.access_token:
            raise ValueError("No access token available")
        
        # Get user ID
        user_info = self.me()
        user_id = user_info["id"]
        
        author = f"urn:li:person:{user_id}"
        
        post_data = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        response = httpx.post(
            f"{self.BASE_URL}/ugcPosts",
            json=post_data,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
        )
        response.raise_for_status()
        return response.json()
    
    def comment_on_post(self, post_urn: str, text: str) -> Dict[str, Any]:
        """Comment on a LinkedIn post."""
        if not self.access_token:
            raise ValueError("No access token available")
        
        # Get user ID
        user_info = self.me()
        user_id = user_info["id"]
        
        actor = f"urn:li:person:{user_id}"
        
        comment_data = {
            "actor": actor,
            "object": post_urn,
            "message": {
                "text": text
            }
        }
        
        response = httpx.post(
            f"{self.BASE_URL}/socialActions/{post_urn}/comments",
            json=comment_data,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
        )
        response.raise_for_status()
        return response.json()
    
    def list_comments(self, post_urn: str, count: int = 100) -> List[Dict[str, Any]]:
        """List comments on a LinkedIn post."""
        if not self.access_token:
            raise ValueError("No access token available")
        
        params = {
            "count": count,
            "start": 0
        }
        
        response = httpx.get(
            f"{self.BASE_URL}/socialActions/{post_urn}/comments",
            params=params,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "X-Restli-Protocol-Version": "2.0.0"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return data.get("elements", [])


def get_linkedin_api() -> LinkedInAPI:
    """Get configured LinkedIn API client."""
    return LinkedInAPI()
