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
            self.access_token = access_token.strip() if access_token else None
        else:
            # Fallback to loading from DB for other potential use cases.
            self.access_token = self._load_token_from_db()

        # Validate that the token is not None or empty (already stripped above or in _load_token_from_db)
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
            if token_record and token_record.access_token:
                # Strip whitespace and validate token is not empty
                token = token_record.access_token.strip() if token_record.access_token else None
                return token if token else None
            return None
        finally:
            db.close()

    async def get_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's profile information using OpenID Connect userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.API_BASE_URL}/userinfo", headers=self.headers)
            response.raise_for_status()
            profile_data = response.json()
            # Map 'sub' field to 'id' for backward compatibility
            if 'sub' in profile_data and 'id' not in profile_data:
                profile_data['id'] = profile_data['sub']
            return profile_data

    # ... (rest of the methods remain unchanged) ...

    async def send_invitation(self, inviter_urn: str, invitee_urn: str, message: str = None) -> None:
        """
        Sends a connection invitation to a given profile.
        
        NOTE: This endpoint requires special permissions from LinkedIn.
        If you receive a 403 Forbidden error, you need to request the 'invitations' 
        permission in your LinkedIn Developer app settings.
        
        Raises:
            httpx.HTTPStatusError: If the request fails with a 403, 404, or other HTTP error
        """
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
        """
        Searches for posts on LinkedIn based on keywords.
        
        NOTE: This endpoint has been deprecated by LinkedIn and will return empty results.
        The /v2/search endpoint with keywords parameter is no longer available for most apps.
        This method is kept for backward compatibility but will return an empty list.
        """
        # LinkedIn has deprecated the search endpoint for most applications
        # Returning empty list to prevent 404 errors
        import logging
        logging.warning(
            "LinkedIn search endpoint is deprecated. "
            "Search functionality is no longer available through the public API. "
            "Consider using LinkedIn's official products like Sales Navigator or Recruiter for search needs."
        )
        return []

    async def share_post(self, author_urn: str, text: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Shares a post to the authenticated user's feed, with an optional image."""
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE"
        }

        if image_url:
            share_content["shareMediaCategory"] = "IMAGE"
            share_content["media"] = [
                {
                    "status": "READY",
                    "media": image_url, # LinkedIn can fetch the image from a public URL
                    "title": {"text": "Image from translated post"}
                }
            ]

        payload = {
            "author": f"urn:li:person:{author_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/ugcPosts", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_profile_by_urn(self, person_urn: str) -> Dict[str, Any]:
        """
        Fetches a LinkedIn profile by its URN. Requires the 'r_liteprofile' permission.
        """
        import urllib.parse
        encoded_urn = urllib.parse.quote(person_urn)
        projection = "localizedFirstName,localizedLastName"
        url = f"{self.API_BASE_URL}/people/{encoded_urn}?projection=({projection})"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_post_details(self, post_urn: str) -> Dict[str, Any]:
        """
        Fetches the details of a specific UGC post, including author name and image URL.
        """
        import urllib.parse
        encoded_urn = urllib.parse.quote(post_urn)
        url = f"{self.API_BASE_URL}/ugcPosts/{encoded_urn}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            post_data = response.json()

        content = post_data.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("shareCommentary", {}).get("text")
        author_urn = post_data.get("author")

        image_url = None
        media_list = post_data.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("media", [])
        if media_list:
            media_item = media_list[0]
            if 'thumbnails' in media_item and media_item['thumbnails']:
                image_url = media_item['thumbnails'][-1].get('url')

        author_name = "Unknown"
        if author_urn:
            try:
                profile_data = await self.get_profile_by_urn(author_urn)
                first_name = profile_data.get('localizedFirstName', '')
                last_name = profile_data.get('localizedLastName', '')
                author_name = f"{first_name} {last_name}".strip()
            except Exception as e:
                import logging
                logging.warning(f"Could not fetch author profile for {author_urn}: {e}")

        return {
            "original_content": content,
            "original_author": author_name or "Unknown",
            "image_url": image_url
        }

    async def add_reaction(self, actor_urn: str, post_urn: str) -> None:
        """
        Adds a 'LIKE' reaction to a given post.
        
        NOTE: This endpoint may require additional permissions.
        If you receive a 403 Forbidden error, the app may need reaction permissions
        or the post may not be accessible.
        
        Raises:
            httpx.HTTPStatusError: If the request fails (403, 404, etc.)
        """
        payload = {"actor": f"urn:li:person:{actor_urn}", "reaction": "LIKE", "object": post_urn}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.API_BASE_URL}/reactions", headers=self.headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    # Log but don't crash - reactions may require special permissions
                    import logging
                    logging.warning(
                        f"403 Forbidden when adding reaction. This may be expected if the LinkedIn app "
                        f"doesn't have reaction permissions or the post is not accessible. "
                        f"Post URN: {post_urn}"
                    )
                    # Re-raise so caller can handle
                    raise
                else:
                    raise

    async def submit_comment(self, actor_urn: str, post_urn: str, text: str) -> Dict[str, Any]:
        """Submits a comment on a given post."""
        payload = {"actor": f"urn:li:person:{actor_urn}", "object": post_urn, "message": {"text": text}}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.API_BASE_URL}/socialActions/{post_urn}/comments", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
