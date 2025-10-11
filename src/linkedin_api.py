"""LinkedIn API integration."""
import time
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
from .config import config
from . import db

API_BASE = "https://api.linkedin.com/v2"
API_V3_BASE = "https://api.linkedin.com/rest"


class LinkedInAPI:
    def __init__(self):
        self.client_id = config.LINKEDIN_CLIENT_ID
        self.client_secret = config.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = config.LINKEDIN_REDIRECT_URI
        self.scopes = config.LINKEDIN_SCOPES.split()
        self._me_cache: Optional[Dict[str, Any]] = None

    # URLs and OAuth
    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params)

    def exchange_code_for_token(self, code: str) -> None:
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        with httpx.Client(timeout=30) as c:
            r = c.post(token_url, data=data)
            r.raise_for_status()
            payload = r.json()
        access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 0))
        # Save using existing db helper API (single-token table)
        db.save_token(access_token, expires_in)

    # Token and headers
    def _get_token(self) -> Optional[str]:
        token = db.get_token()
        if not token:
            return None
        # Basic expiry check: if stored expires_at in past, require relogin
        expires_at = token.get("expires_at")
        if expires_at and int(expires_at) < int(time.time()):
            raise RuntimeError("LinkedIn token expired. Please re-login.")
        return token.get("access_token")

    def _headers(self) -> Dict[str, str]:
        token = self._get_token()
        if not token:
            raise RuntimeError("LinkedIn not authenticated")
        return {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    def _headers_v3(self) -> Dict[str, str]:
        """Headers for LinkedIn API v3 (REST API)."""
        token = self._get_token()
        if not token:
            raise RuntimeError("LinkedIn not authenticated")
        return {
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": "202405",  # API version
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def userinfo(self) -> Dict[str, Any]:
        # OIDC userinfo (openid/profile/email)
        token = self._get_token()
        if not token:
            raise RuntimeError("LinkedIn not authenticated")
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as c:
            r = c.get("https://api.linkedin.com/v2/userinfo")
            r.raise_for_status()
            return r.json()

    def me(self) -> Dict[str, Any]:
        if self._me_cache is not None:
            return self._me_cache
        # Try classic /v2/me (requires r_liteprofile). Fallback to OIDC userinfo.
        try:
            with httpx.Client(timeout=30, headers=self._headers()) as c:
                r = c.get(f"{API_BASE}/me")
                r.raise_for_status()
                self._me_cache = r.json()
                return self._me_cache
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                ui = self.userinfo()
                given = ui.get("given_name") or ""
                family = ui.get("family_name") or ""
                self._me_cache = {
                    "id": ui.get("sub"),
                    "localizedFirstName": given or (ui.get("name") or "").split(" ")[0] if ui.get("name") else "",
                    "localizedLastName": family,
                    "picture": ui.get("picture"),
                }
                return self._me_cache
            raise

    # Posting and comments
    def post_ugc(self, text: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        """Post to LinkedIn using the new Posts API (v3)."""
        me = self.me()
        person_id = me['id']
        author_urn = f"urn:li:person:{person_id}"
        
        # LinkedIn API v3 Posts endpoint
        payload = {
            "author": author_urn,
            "commentary": text,
            "visibility": visibility,  # PUBLIC, CONNECTIONS, or LOGGED_IN
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }
        
        # Try new v3 REST API first
        try:
            with httpx.Client(timeout=30, headers=self._headers_v3()) as c:
                r = c.post(f"{API_V3_BASE}/posts", json=payload)
                r.raise_for_status()
                response_data = r.json()
                post_id = response_data.get("id", "")
                
                # Extract URN from response
                if post_id:
                    # New API returns full URN or just ID
                    if post_id.startswith("urn:"):
                        urn = post_id
                        post_id = post_id.split(":")[-1]
                    else:
                        urn = f"urn:li:share:{post_id}"
                    
                    return {"id": post_id, "urn": urn}
        except httpx.HTTPStatusError as e:
            print(f"API v3 failed: {e.response.status_code} - {e.response.text}")
            # Fallback to old UGC API
            pass
        
        # Fallback: Try old ugcPosts API (might still work for some apps)
        payload_v2 = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.post(f"{API_BASE}/ugcPosts", json=payload_v2)
            r.raise_for_status()
            urn = r.json().get("id") or r.headers.get("x-restli-id")
            if urn and not str(urn).startswith("urn:"):
                urn = f"urn:li:ugcPost:{urn}"
            # Return a dict compatible with scheduler expectations
            return {"id": urn.split(":")[-1] if urn else "", "urn": urn}

    def comment_on_post(self, ugc_urn: str, text: str) -> Dict[str, Any]:
        """Add a comment to a post. Works with both old ugcPost and new share URNs."""
        # Normalize URN
        if not ugc_urn.startswith("urn:"):
            ugc_urn = f"urn:li:share:{ugc_urn}"
        
        me = self.me()
        actor = f"urn:li:person:{me['id']}"
        
        # Try new API first (v3 REST)
        try:
            payload = {
                "actor": actor,
                "message": {"text": text}
            }
            with httpx.Client(timeout=30, headers=self._headers_v3()) as c:
                # New endpoint format
                r = c.post(f"{API_V3_BASE}/socialActions/{ugc_urn}/comments", json=payload)
                r.raise_for_status()
                comment_id = r.json().get("id", "") or r.headers.get("x-restli-id", "")
                return {"id": comment_id}
        except httpx.HTTPStatusError as e:
            print(f"Comment API v3 failed: {e.response.status_code} - {e.response.text}")
            # Fallback to v2
            pass
        
        # Fallback to old API
        payload = {"actor": actor, "message": {"text": text}}
        endpoint = f"{API_BASE}/socialActions/{ugc_urn}/comments"
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.post(endpoint, json=payload)
            r.raise_for_status()
            comment_id = r.headers.get("x-restli-id", "")
            return {"id": comment_id}

    def list_comments(self, ugc_urn: str, count: int = 50) -> List[Dict[str, Any]]:
        social_urn = ugc_urn if ugc_urn.startswith("urn:") else f"urn:li:ugcPost:{ugc_urn}"
        endpoint = f"{API_BASE}/socialActions/{social_urn}/comments"
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.get(endpoint, params={"count": count})
            r.raise_for_status()
            data = r.json()
            elements = data.get("elements", [])
            out: List[Dict[str, Any]] = []
            for e in elements:
                out.append({
                    "id": e.get("entityUrn", "").split(":")[-1],
                    "actor": e.get("actor"),
                    "message": {"text": e.get("message", {}).get("text", "")},
                    "created": e.get("created", {}).get("time", 0),
                })
            return out


_api_singleton: Optional[LinkedInAPI] = None


def get_linkedin_api() -> LinkedInAPI:
    global _api_singleton
    if _api_singleton is None:
        _api_singleton = LinkedInAPI()
    return _api_singleton
