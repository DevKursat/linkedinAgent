"""Helpers for connections UI: fetch suggested accounts in a defensive way."""
from typing import List, Dict, Any
from . import db
from .linkedin_api import get_linkedin_api


def get_suggested_accounts_for_connections(limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of suggested accounts for the connections page.

    This function is defensive: it prefers a DB cache if available, then
    attempts best-effort API calls. It never raises; on error it returns an
    empty list.
    Each item returned: {"urn": str|None, "name": str, "profile_url": str}
    """
    # Try DB cache first if available
    try:
        if hasattr(db, 'get_cached_suggested_accounts'):
            cached = db.get_cached_suggested_accounts(limit)
            if cached:
                return cached
    except Exception:
        # swallow cache errors
        pass

    raw_suggestions = []
    try:
        api = get_linkedin_api()
        # Try a few possible helper method names that an API wrapper might expose
        candidate_methods = (
            'get_suggested_profiles', 'get_suggested_connections',
            'suggested_connections', 'recommended_people', 'suggested',
        )
        for m in candidate_methods:
            if hasattr(api, m):
                try:
                    raw_suggestions = getattr(api, m)(limit=limit)
                except TypeError:
                    try:
                        raw_suggestions = getattr(api, m)()
                    except Exception:
                        raw_suggestions = []
                break
        else:
            # No convenience method found; try a best-effort generic search if available
            if hasattr(api, 'people_search'):
                try:
                    raw_suggestions = api.people_search(limit=limit)
                except Exception:
                    raw_suggestions = []
    except Exception:
        raw_suggestions = []

    normalized = []
    for item in (raw_suggestions or [])[:limit]:
        try:
            if isinstance(item, dict):
                urn = item.get('urn') or item.get('entityUrn') or item.get('id')
                name = item.get('name') or item.get('formattedName') or (
                    " ".join(filter(None, [item.get('firstName'), item.get('lastName')]))
                )
                profile_url = item.get('publicProfileUrl') or item.get('profileUrl') or ''
            else:
                urn = getattr(item, 'urn', None) or getattr(item, 'id', None)
                name = getattr(item, 'name', None) or getattr(item, 'formattedName', None) or ''
                profile_url = getattr(item, 'profileUrl', None) or ''

            if not profile_url and urn and isinstance(urn, str) and ':' in urn:
                slug = urn.split(':')[-1]
                profile_url = f"https://www.linkedin.com/in/{slug}"

            normalized.append({'urn': urn, 'name': name or '', 'profile_url': profile_url or ''})
        except Exception:
            continue

    # Non-blocking cache of results if helper exists
    try:
        if normalized and hasattr(db, 'cache_suggested_accounts'):
            try:
                db.cache_suggested_accounts(normalized)
            except Exception:
                pass
    except Exception:
        pass

    return normalized
