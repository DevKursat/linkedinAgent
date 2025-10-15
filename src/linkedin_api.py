"""LinkedIn API integration."""
import time
import re
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode, quote
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
        self._rest_backoff_until: float = 0.0
        self._rest_disabled_reason: Optional[str] = None
        self._rest_enabled_config: bool = config.LINKEDIN_ENABLE_REST
        if not self._rest_enabled_config:
            self._rest_disabled_reason = "Disabled via configuration"

    @staticmethod
    def _normalize_version(version: str) -> Optional[str]:
        if not version:
            return None
        candidate = version.strip()
        if not candidate:
            return None
        match = re.match(r"^(20\d{4})(?:\.\d{2})?", candidate)
        if match:
            return match.group(1)
        return None

    def _rest_versions(self) -> List[str]:
        versions: List[str] = []
        primary = self._normalize_version(config.LINKEDIN_REST_VERSION or "")
        if primary:
            versions.append(primary)
        fallbacks = [self._normalize_version(v) for v in (config.LINKEDIN_REST_VERSION_FALLBACKS or "").split(",")]
        for v in fallbacks:
            if v and v not in versions:
                versions.append(v)
        # Add a small sweep of recent versions as additional fallbacks to increase
        # chances of matching the app's accepted LinkedIn-Version header.
        extra_candidates = [
            "202501", "202410", "202409", "202408", "202407", "202405", "202401",
        ]
        for c in extra_candidates:
            if c not in versions:
                versions.append(c)
        # Ensure we always try at least one default if nothing configured
        if not versions:
            versions.append("202405")
        return versions

    def _rest_allowed(self) -> bool:
        return (
            self._rest_enabled_config
            and self._rest_disabled_reason is None
            and time.time() >= self._rest_backoff_until
        )

    def _disable_rest(self, reason: str) -> None:
        if self._rest_disabled_reason == "Disabled via configuration":
            return
        if self._rest_disabled_reason:
            return
        self._rest_disabled_reason = reason
        self._rest_backoff_until = float("inf")
        print(f"LinkedIn REST disabled: {reason}")

    def _mark_rest_success(self) -> None:
        if not self._rest_enabled_config:
            return
        self._rest_disabled_reason = None
        self._rest_backoff_until = 0.0

    def _extract_versions_from_error(self, error_text: str) -> List[str]:
        """Extract possible version strings from LinkedIn 426 error messages."""
        if not error_text:
            return []
        ordered: List[str] = []
        seen = set()
        for match in re.findall(r"20\d{4,6}", error_text):
            normalized = self._normalize_version(match)
            if normalized and normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)
        return ordered

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

    @staticmethod
    def _encode_urn_for_path(urn: str) -> str:
        """Percent-encode a URN to safely use it inside REST path segments."""
        return quote(urn, safe="")

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
    def post_ugc(self, text: str, visibility: str = "PUBLIC", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Post to LinkedIn using the new Posts API (v3)."""
        me = self.me()
        person_id = me['id']
        author_urn = f"urn:li:person:{person_id}"
        
        # LinkedIn API v3 Posts endpoint
        # If tags provided, append them as hashtags to the commentary text
        if tags:
            cleaned = []
            for t in tags:
                t = t.strip()
                if not t:
                    continue
                if not t.startswith('#'):
                    # sanitize basic characters for hashtag
                    tag = re.sub(r'[^0-9A-Za-z_ğüşöçıİĞÜŞÖÇ-]', '', t.replace(' ', ''))
                    cleaned.append('#' + tag)
                else:
                    cleaned.append(t)
            if cleaned:
                text = text.rstrip() + "\n\n" + " ".join(cleaned)

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
        versions_to_try: List[str] = self._rest_versions() if self._rest_allowed() else []
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
                        
                        self._mark_rest_success()
                        return {"id": post_id, "urn": urn}
            except httpx.HTTPStatusError as e:
                print(f"API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    if self._rest_enabled_config:
                        self._disable_rest(f"LinkedIn returned 426 for version {version}")
                        versions_to_try = []
                    if self._rest_disabled_reason is None:
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
            # Try classic ugcPosts
            try:
                r = c.post(f"{API_BASE}/ugcPosts", json=payload_v2)
                r.raise_for_status()
                urn = r.json().get("id") or r.headers.get("x-restli-id")
            except Exception as e:
                print(f"ugcPosts fallback failed: {e}")
                urn = None

        if urn:
            if urn and not str(urn).startswith("urn:"):
                urn = f"urn:li:ugcPost:{urn}"
            return {"id": urn.split(":")[-1] if urn else "", "urn": urn}

        # As a last resort, try creating a simple share via shares endpoint
        try:
            share_payload = {
                "owner": author_urn,
                "text": {"text": text},
                "distribution": {"feedDistribution": "MAIN_FEED"},
            }
            with httpx.Client(timeout=30, headers=self._headers()) as c:
                r = c.post(f"{API_BASE}/shares", json=share_payload)
                r.raise_for_status()
                share_id = r.json().get("id") or r.headers.get("x-restli-id")
                urn = f"urn:li:share:{share_id}" if share_id else None
                if urn:
                    return {"id": urn.split(":")[-1], "urn": urn}
        except Exception as e:
            print(f"shares fallback failed: {e}")

        # If all creation attempts fail, raise
        raise RuntimeError("Failed to create post using any known LinkedIn endpoint")

    def comment_on_post(self, ugc_urn: str, text: str, parent_comment_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to a post. If parent_comment_id is provided, attempt to post a threaded reply to that comment.
        Works with both old ugcPost and new share URNs."""
        # Normalize URN
        if not ugc_urn.startswith("urn:"):
            ugc_urn = f"urn:li:share:{ugc_urn}"
        
        me = self.me()
        actor = f"urn:li:person:{me['id']}"
        
        # Try new Posts comments REST endpoint first (safer and newer)
        def _extract_post_id(urn: str) -> Optional[str]:
            if urn.startswith("urn:li:share:") or urn.startswith("urn:li:ugcPost:"):
                return urn.split(":")[-1]
            return None

        post_id = _extract_post_id(ugc_urn)
        payload = {"actor": actor, "message": {"text": text}}
        # If a parent comment id was provided, construct a parent URN and include it in the payload
        if parent_comment_id:
            parent_urn = parent_comment_id if parent_comment_id.startswith("urn:") else f"urn:li:comment:{parent_comment_id}"
            # Some LinkedIn endpoints accept parent or inReplyTo fields for threaded replies; include both to increase compatibility
            payload["parent"] = parent_urn
            payload["inReplyTo"] = parent_urn

        if post_id and self._rest_allowed():
            # Prefer v3 posts endpoint
            try:
                with httpx.Client(timeout=30, headers=self._headers_v3()) as c:
                    r = c.post(f"{API_V3_BASE}/posts/{post_id}/comments", json=payload)
                    r.raise_for_status()
                    comment_id = r.json().get("id", "") or r.headers.get("x-restli-id", "")
                    self._mark_rest_success()
                    return {"id": comment_id}
            except httpx.HTTPStatusError as e:
                print(f"New posts comment API failed for post {post_id}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"New posts comment API error for post {post_id}: {e}")

        # If posts endpoint not available or failed, fall back to socialActions REST then legacy
        versions_to_try = self._rest_versions() if self._rest_allowed() else []
        tried_versions: List[str] = []
        while versions_to_try:
            version = versions_to_try.pop(0)
            if version in tried_versions:
                continue
            tried_versions.append(version)
            try:
                encoded = self._encode_urn_for_path(ugc_urn)
                with httpx.Client(timeout=30, headers=self._headers_v3(version)) as c:
                    r = c.post(f"{API_V3_BASE}/socialActions/{encoded}/comments", json=payload)
                    r.raise_for_status()
                    comment_id = r.json().get("id", "") or r.headers.get("x-restli-id", "")
                    self._mark_rest_success()
                    return {"id": comment_id}
            except httpx.HTTPStatusError as e:
                print(f"Comment API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    if self._rest_enabled_config:
                        self._disable_rest(f"LinkedIn returned 426 for version {version}")
                        versions_to_try = []
                    if self._rest_disabled_reason is None:
                        for candidate_version in self._extract_versions_from_error(e.response.text):
                            if candidate_version not in tried_versions and candidate_version not in versions_to_try:
                                versions_to_try.append(candidate_version)
                continue
            except Exception as e:
                print(f"Comment API v3 error (version {version}): {e}")
                continue
        
        # Fallback to old API
        legacy_variants = [ugc_urn]
        if ugc_urn.startswith("urn:li:share:"):
            legacy_variants.append(ugc_urn.replace("urn:li:share:", "urn:li:ugcPost:", 1))
        elif ugc_urn.startswith("urn:li:ugcPost:"):
            legacy_variants.append(ugc_urn.replace("urn:li:ugcPost:", "urn:li:share:", 1))

        last_error: Optional[Exception] = None
        for legacy_urn in legacy_variants:
            endpoint = f"{API_BASE}/socialActions/{self._encode_urn_for_path(legacy_urn)}/comments"
            try:
                with httpx.Client(timeout=30, headers=self._headers()) as c:
                    r = c.post(endpoint, json=payload)
                    r.raise_for_status()
                    comment_id = r.json().get("id", "") or r.headers.get("x-restli-id", "")
                    self._rest_backoff_until = 0.0
                    return {"id": comment_id}
            except Exception as exc:
                print(f"Legacy comment API failed for {legacy_urn}: {exc}")
                last_error = exc
                continue

        if last_error:
            raise last_error

        raise RuntimeError("LinkedIn comment API fallback exhausted without success")

    def like_post(self, target_urn: str) -> None:
        """Add a like to the given post URN using the stable v2 endpoint."""
        if not target_urn.startswith("urn:" ):
            target_urn = f"urn:li:share:{target_urn}"

        me = self.me()
        actor = f"urn:li:person:{me['id']}"
        payload = {"actor": actor}
        # Prefer REST v3 socialActions likes endpoint
        encoded = self._encode_urn_for_path(target_urn)
        try:
            with httpx.Client(timeout=30, headers=self._headers_v3()) as c:
                r = c.post(f"{API_V3_BASE}/socialActions/{encoded}/likes", json=payload)
                r.raise_for_status()
                self._mark_rest_success()
                return
        except Exception:
            # Fallback to legacy v2 endpoint
            endpoint = f"{API_BASE}/socialActions/{encoded}/likes"
            with httpx.Client(timeout=30, headers=self._headers()) as c:
                r = c.post(endpoint, json=payload)
                r.raise_for_status()

    def send_invite(self, person_urn: str, message: str = "") -> Dict[str, Any]:
        """Send a connection invite to the given person URN. Best-effort: try REST then v2."""
        if not person_urn.startswith("urn:"):
            raise ValueError("person_urn must be a full URN like 'urn:li:person:xxxxx'")

        # Prefer REST invitations endpoint if available
        if self._rest_allowed():
            versions_to_try = self._rest_versions()
            tried = []
            while versions_to_try:
                v = versions_to_try.pop(0)
                if v in tried:
                    continue
                tried.append(v)
                # Try a couple of REST endpoint/payload shapes to increase compatibility
                rest_paths = [
                    f"{API_V3_BASE}/growth/invitations",
                    f"{API_V3_BASE}/invitations",
                ]
                for path in rest_paths:
                    try:
                        payload = {
                            "invitee": {"com.linkedin.voyager.growth.invitation.InviteeProfile": {"profileUrn": person_urn}},
                            "message": message
                        }
                        with httpx.Client(timeout=30, headers=self._headers_v3(v)) as c:
                            r = c.post(path, json=payload)
                            r.raise_for_status()
                            self._mark_rest_success()
                            return r.json()
                    except httpx.HTTPStatusError as e:
                        print(f"Invite v3 failed (version {v}, path {path}): {e.response.status_code} - {e.response.text}")
                        if e.response.status_code == 426:
                            if self._rest_enabled_config:
                                self._disable_rest(f"LinkedIn returned 426 for version {v}")
                                versions_to_try = []
                        # try next path
                        continue
                    except Exception as e:
                        print(f"Invite v3 error (version {v}, path {path}): {e}")
                        continue

        # Fallback to legacy v2 endpoint if exists (best-effort)
        # Try legacy v2 with a couple payload shapes
        legacy_paths = [f"{API_BASE}/growth/invitations", f"{API_BASE}/invitations"]
        for path in legacy_paths:
            try:
                payload = {"invitee": {"profile": person_urn}, "message": message}
                with httpx.Client(timeout=30, headers=self._headers()) as c:
                    r = c.post(path, json=payload)
                    r.raise_for_status()
                    return r.json()
            except httpx.HTTPStatusError as e:
                print(f"Invite legacy failed (path {path}): {e.response.status_code} - {e.response.text}")
                continue
            except Exception as e:
                print(f"Invite legacy error (path {path}): {e}")
                continue

        # If all creation attempts fail, write an alert for operator visibility and raise
        try:
            # Try to capture last HTTP error details if available
            err_text = ""
            try:
                # `e` may be last exception from loop; guard access
                err_text = f"{getattr(e, 'response', '')}"
            except Exception:
                err_text = ""

            with open('data/alerts.log', 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Invite failed for {person_urn}: {err_text}\n")
        except Exception:
            # Best-effort logging only
            pass
        raise RuntimeError("Invite endpoints exhausted or not available for this app")

    def list_comments(self, ugc_urn: str, count: int = 50) -> List[Dict[str, Any]]:
        social_urn = ugc_urn if ugc_urn.startswith("urn:") else f"urn:li:share:{ugc_urn}"

        # Extract post ID from URN for new API
        def extract_post_id(urn: str) -> Optional[str]:
            if urn.startswith("urn:li:share:"):
                return urn.split(":")[-1]
            elif urn.startswith("urn:li:ugcPost:"):
                return urn.split(":")[-1]
            return None

        post_id = extract_post_id(social_urn)
        if post_id:
            # Try new Posts REST endpoint under /rest first
            try:
                with httpx.Client(timeout=30, headers=self._headers_v3()) as c:
                    r = c.get(f"{API_V3_BASE}/posts/{post_id}/comments", params={"count": count})
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
                    self._mark_rest_success()
                    return out
            except httpx.HTTPStatusError as e:
                print(f"New posts comments API v3 failed for post {post_id}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"New posts comments API error for post {post_id}: {e}")

        # Try modern REST API first to avoid 400 errors for share URNs.
        versions_to_try = self._rest_versions() if self._rest_allowed() else []
        tried_versions: List[str] = []
        while versions_to_try:
            version = versions_to_try.pop(0)
            if version in tried_versions:
                continue
            tried_versions.append(version)
            try:
                encoded = self._encode_urn_for_path(social_urn)
                with httpx.Client(timeout=30, headers=self._headers_v3(version)) as c:
                    r = c.get(
                        f"{API_V3_BASE}/socialActions/{encoded}/comments",
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
                    self._mark_rest_success()
                    return out
            except httpx.HTTPStatusError as e:
                print(f"List comments API v3 failed (version {version}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 426:
                    if self._rest_enabled_config:
                        self._disable_rest(f"LinkedIn returned 426 for version {version}")
                        versions_to_try = []
                    if self._rest_disabled_reason is None:
                        for candidate_version in self._extract_versions_from_error(e.response.text):
                            if candidate_version not in tried_versions and candidate_version not in versions_to_try:
                                versions_to_try.append(candidate_version)
                continue
            except Exception as e:
                print(f"List comments API v3 error (version {version}): {e}")
                continue

        # Legacy fallback for older posts/permissions
        legacy_variants = [social_urn]
        if social_urn.startswith("urn:li:share:"):
            legacy_variants.append(social_urn.replace("urn:li:share:", "urn:li:ugcPost:", 1))
        elif social_urn.startswith("urn:li:ugcPost:"):
            legacy_variants.append(social_urn.replace("urn:li:ugcPost:", "urn:li:share:", 1))

        last_error: Optional[Exception] = None
        for legacy_urn in legacy_variants:
            endpoint = f"{API_BASE}/socialActions/{self._encode_urn_for_path(legacy_urn)}/comments"
            try:
                with httpx.Client(timeout=30, headers=self._headers()) as c:
                    r = c.get(endpoint, params={"count": count})
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
                    self._rest_backoff_until = 0.0
                    return out
            except Exception as exc:
                print(f"Legacy list comments API failed for {legacy_urn}: {exc}")
                last_error = exc
                continue

        if last_error:
            raise last_error

        return []


_api_singleton: Optional[LinkedInAPI] = None


def get_linkedin_api() -> LinkedInAPI:
    global _api_singleton
    if _api_singleton is None:
        _api_singleton = LinkedInAPI()
    return _api_singleton
