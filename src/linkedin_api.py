"""LinkedIn API integration."""
import time
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
from src.config import cfg
from src.db import get_conn

API_BASE = "https://api.linkedin.com/v2"

class LinkedInAPI:
    def __init__(self):
        self.client_id = cfg.LINKEDIN_CLIENT_ID
        self.client_secret = cfg.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = cfg.LINKEDIN_REDIRECT_URI
        self.scopes = cfg.LINKEDIN_SCOPES.split()
        self._me_cache = None

    def auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params)

    def exchange_code(self, code: str) -> None:
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
            data = r.json()
        access_token = data["access_token"]
        expires_in = data.get("expires_in", 0)
        expires_at = int(time.time()) + int(expires_in) - 60
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO tokens(provider, access_token, refresh_token, expires_at) VALUES(?,?,?,?) "
                "ON CONFLICT(provider) DO UPDATE SET access_token=excluded.access_token, expires_at=excluded.expires_at",
                ("linkedin", access_token, None, expires_at),
            )

    def _get_token(self) -> Optional[str]:
        with get_conn() as conn:
            cur = conn.execute("SELECT access_token, expires_at FROM tokens WHERE provider='linkedin'")
            row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < int(time.time()):
            raise RuntimeError("LinkedIn token expired. Please re-login.")
        return row["access_token"]

    def _headers(self) -> Dict[str, str]:
        token = self._get_token()
        if not token:
            raise RuntimeError("LinkedIn not authenticated")
        return {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}

    def userinfo(self) -> Dict[str, Any]:
        # OIDC userinfo (openid/profile/email ile çalışır)
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {self._get_token()}"}) as c:
            r = c.get("https://api.linkedin.com/v2/userinfo")
            r.raise_for_status()
            return r.json()

    def me(self) -> Dict[str, Any]:
        if self._me_cache:
            return self._me_cache
        # Önce klasik /v2/me dene (r_liteprofile gerektirir). 401/403 olursa OIDC userinfo'ya düş.
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
                # OIDC 'sub' genelde person id ile aynıdır; author URN için kullanırız.
                self._me_cache = {
                    "id": ui.get("sub"),
                    "localizedFirstName": given or (ui.get("name") or "").split(" ")[0] if ui.get("name") else "",
                    "localizedLastName": family,
                    "picture": ui.get("picture"),
                }
                return self._me_cache
            raise

    def post_ugc(self, text: str, visibility: str = "PUBLIC") -> str:
        me = self.me()
        author = f"urn:li:person:{me['id']}"
        payload = {
            "author": author,
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
            r = c.post(f"{API_BASE}/ugcPosts", json=payload)
            r.raise_for_status()
            urn = r.json().get("id") or r.headers.get("x-restli-id")
            if urn and not urn.startswith("urn:"):
                urn = f"urn:li:ugcPost:{urn}"
            return urn

    def comment_on_post(self, ugc_urn: str, text: str) -> str:
        social_urn = ugc_urn if ugc_urn.startswith("urn:") else f"urn:li:ugcPost:{ugc_urn}"
        payload = {"actor": f"urn:li:person:{self.me()['id']}", "message": {"text": text}}
        endpoint = f"{API_BASE}/socialActions/{social_urn}/comments"
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.post(endpoint, json=payload)
            r.raise_for_status()
            return r.headers.get("x-restli-id", "")

    def list_comments(self, ugc_urn: str, count: int = 50) -> List[Dict[str, Any]]:
        # Bu çağrı r_member_social isteyebilir; yoksa 403 alırsak üst katman loglayacak.
        social_urn = ugc_urn if ugc_urn.startswith("urn:") else f"urn:li:ugcPost:{ugc_urn}"
        endpoint = f"{API_BASE}/socialActions/{social_urn}/comments"
        with httpx.Client(timeout=30, headers=self._headers()) as c:
            r = c.get(endpoint, params={"count": count})
            r.raise_for_status()
            data = r.json()
            elements = data.get("elements", [])
            out = []
            for e in elements:
                out.append({
                    "urn": e.get("entityUrn"),
                    "actor": e.get("actor"),
                    "text": e.get("message", {}).get("text", ""),
                    "created": e.get("created", {}).get("time", 0),
                })
            return out
