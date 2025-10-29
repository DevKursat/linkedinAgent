import httpx
from typing import List, Dict, Any, Optional
from .database import SessionLocal
from .models import Token

class LinkedInApiClient:
    """
    A modern, token-based client for interacting with the LinkedIn API.
    It can be initialized with a direct access token, or it can retrieve
    the token from the database as a fallback.
    """
    API_BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self, access_token: Optional[str] = None):
        # Prioritize the token passed directly to the constructor.
        # This is crucial for the worker flow.
        if access_token:
            self.access_token = access_token
        else:
            # Fallback to loading from DB for other potential use cases.
            self.access_token = self._load_token_from_db()

        if not self.access_token:
            raise ValueError("Access token is not available. Please log in or provide a token.")

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _load_token_from_db(self) -> str | None:
        """Loads the most recent access token from the database."""
        db = SessionLocal()
        try:
            token_record = db.query(Token).order_by(Token.created_at.desc()).first()
            if token_record:
                return token_record.access_token
            return None
        finally:
            db.close()

    async def get_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's profile information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.API_BASE_URL}/me", headers=self.headers)
            response.raise_for_status()
            return response.json()

    # ... (rest of the methods remain unchanged) ...

    async def send_invitation(self, inviter_urn: str, invitee_urn: str, message: str = None) -> None:
        """Sends a connection invitation to a given profile."""
        payload = {
            "invitee": f"urn:li:person:{invitee_urn}",
            "actor": f"urn:li:person:{inviter_urn}",
        }
        if message:
            payload["message"] = {
                "com.linkedin.voyager.messaging.create.EventCreate": {
                    "body": {"text": message}
                }
            }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/invitations", headers=self.headers, json=payload)
            response.raise_for_status()

    async def search_for_posts(self, keywords: str, count: int = 5) -> List[Dict[str, Any]]:
        """Searches for posts on LinkedIn based on keywords."""
        params = {"q": "keywords", "keywords": keywords, "count": count, "sort": "recency"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.API_BASE_URL}/search", headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("elements", [])

    async def share_post(self, author_urn: str, text: str) -> Dict[str, Any]:
        """Shares a text post to the authenticated user's feed."""
        payload = {
            "author": f"urn:li:person:{author_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/ugcPosts", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def add_reaction(self, actor_urn: str, post_urn: str) -> None:
        """Adds a 'LIKE' reaction to a given post."""
        payload = {"actor": f"urn:li:person:{actor_urn}", "reaction": "LIKE", "object": post_urn}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/reactions", headers=self.headers, json=payload)
            response.raise_for_status()

    async def submit_comment(self, actor_urn: str, post_urn: str, text: str) -> Dict[str, Any]:
        """Submits a comment on a given post."""
        payload = {"actor": f"urn:li:person:{actor_urn}", "object": post_urn, "message": {"text": text}}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/socialActions/{post_urn}/comments", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
