"""LinkedIn API integration."""
import time
import re
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

    def _rest_versions(self) -> List[str]:
        versions: List[str] = []
        primary = (config.LINKEDIN_REST_VERSION or "").strip()
        if primary:
            versions.append(primary)
        fallbacks = [v.strip() for v in (config.LINKEDIN_REST_VERSION_FALLBACKS or "").split(",") if v.strip()]
        for v in fallbacks:
            if v not in versions:
                versions.append(v)
        # Ensure we always try at least one default if nothing configured
        if not versions:
            versions.append("202405")
        return versions

    def _extract_versions_from_error(self, error_text: str) -> List[str]:
        """Extract possible version strings from LinkedIn 426 error messages."""
        if not error_text:
            return []
        found = set()
        for match in re.findall(r"20\d{4,6}", error_text):
            found.add(match)
            if len(match) == 8:
                found.add(match[:6])
        return [v for v in found if v]

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

    def _headers_v3(self, version: Optional[str] = None) -> Dict[str, str]:
        """Headers for LinkedIn API v3 (REST API)."""
        token = self._get_token()
        if not token:
            raise RuntimeError("LinkedIn not authenticated")
        version = (version or config.LINKEDIN_REST_VERSION).strip()
        return {
            "Authorization": f"Bearer {token}",
            # Keep LinkedIn-Version fresh; LinkedIn rejects stale versions with HTTP 426.
            "LinkedIn-Version": version,
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
        
        # Try new v3 REST API first with version fallbacks
        versions_to_try = self._rest_versions()
        tried_versions: List[str] = []
        while versions_to_try:
            version = versions_to_try.pop(0)
            if version in tried_versions:
                continue
            tried_versions.append(version)
            try:
                with httpx.Client(timeout=30, headers=self._headers_v3(version)) as c:
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
                print(f"API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    for candidate_version in self._extract_versions_from_error(e.response.text):
                        if candidate_version not in tried_versions and candidate_version not in versions_to_try:
                            versions_to_try.append(candidate_version)
                continue
            except Exception as e:
                print(f"API v3 error (version {version}): {e}")
                continue
        
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
        payload = {"actor": actor, "message": {"text": text}}
        versions_to_try = self._rest_versions()
        tried_versions: List[str] = []
        while versions_to_try:
            version = versions_to_try.pop(0)
            if version in tried_versions:
                continue
            tried_versions.append(version)
            try:
                with httpx.Client(timeout=30, headers=self._headers_v3(version)) as c:
                    r = c.post(f"{API_V3_BASE}/socialActions/{ugc_urn}/comments", json=payload)
                    r.raise_for_status()
                    comment_id = r.json().get("id", "") or r.headers.get("x-restli-id", "")
                    return {"id": comment_id}
            except httpx.HTTPStatusError as e:
                print(f"Comment API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    for candidate_version in self._extract_versions_from_error(e.response.text):
                        if candidate_version not in tried_versions and candidate_version not in versions_to_try:
                            versions_to_try.append(candidate_version)
                continue
            except Exception as e:
                print(f"Comment API v3 error (version {version}): {e}")
                continue
        
        # Fallback to old API
        legacy_urn = ugc_urn
        if legacy_urn.startswith("urn:li:share:"):
            legacy_urn = legacy_urn.replace("urn:li:share:", "urn:li:ugcPost:", 1)
        endpoint = f"{API_BASE}/socialActions/{legacy_urn}/comments"
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.post(endpoint, json=payload)
            r.raise_for_status()
            comment_id = r.headers.get("x-restli-id", "")
            return {"id": comment_id}

    def list_comments(self, ugc_urn: str, count: int = 50) -> List[Dict[str, Any]]:
        social_urn = ugc_urn if ugc_urn.startswith("urn:") else f"urn:li:share:{ugc_urn}"

        # Try modern REST API first to avoid 400 errors for share URNs.
        versions_to_try = self._rest_versions()
        tried_versions: List[str] = []
        while versions_to_try:
            version = versions_to_try.pop(0)
            if version in tried_versions:
                continue
            tried_versions.append(version)
            try:
                with httpx.Client(timeout=30, headers=self._headers_v3(version)) as c:
                    r = c.get(
                        f"{API_V3_BASE}/socialActions/{social_urn}/comments",
                        params={"count": count},
                    )
                    r.raise_for_status()
                    data = r.json()
                    elements = data.get("elements", [])
                    out: List[Dict[str, Any]] = []
                    for e in elements:
                        out.append({
                            "id": e.get("id", "") or e.get("entityUrn", "").split(":")[-1],
                            "actor": e.get("actor"),
                            "message": {"text": e.get("message", {}).get("text", "")},
                            "created": e.get("createdAt", e.get("created", {}).get("time", 0)),
                        })
                    return out
            except httpx.HTTPStatusError as e:
                print(f"List comments API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    for candidate_version in self._extract_versions_from_error(e.response.text):
                        if candidate_version not in tried_versions and candidate_version not in versions_to_try:
                            versions_to_try.append(candidate_version)
                continue
            except Exception as e:
                print(f"List comments API v3 error (version {version}): {e}")
                continue

        # Legacy fallback for older posts/permissions
        legacy_urn = social_urn
        if legacy_urn.startswith("urn:li:share:"):
            legacy_urn = legacy_urn.replace("urn:li:share:", "urn:li:ugcPost:", 1)

        endpoint = f"{API_BASE}/socialActions/{legacy_urn}/comments"
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
