"""Probe LinkedIn endpoints with the stored access token and write a JSON report.

Usage: called by `manage.py check-permissions` or run directly.
"""
import json
import os
from typing import List, Dict

from ..db import get_token
from ..linkedin_api import LinkedInAPI, API_V3_BASE, API_BASE
from ..config import config
import httpx


REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'permissions_report.json'))


def _ensure_data_dir():
    root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(root, 'data')
    os.makedirs(data_dir, exist_ok=True)


def probe_endpoints() -> Dict[str, Dict]:
    """Probe a set of LinkedIn endpoints and return a dict of results."""
    token = get_token()
    if not token:
        raise RuntimeError("No stored access token found. Please authenticate via the web UI first.")

    api = LinkedInAPI()

    # Define probes: name -> (method, path_or_callable)
    results = {}

    # 1) me()
    try:
        m = api.me()
        results['me'] = {'status_code': 200, 'body': m}
    except Exception as e:
        results['me'] = {'error': str(e)}

    # 2) Try GET on v3 posts list (may not be public) using LinkedIn-Version candidates
    try:
        headers = api._headers_v3()
        with httpx.Client(timeout=30, headers=headers) as c:
            r = c.get(f"{API_V3_BASE}/posts", params={'count': 1})
            try:
                r.raise_for_status()
                results['post_ugc_read_v3'] = {'status_code': r.status_code, 'body': r.json()}
            except httpx.HTTPStatusError:
                results['post_ugc_read_v3'] = {'status_code': r.status_code, 'body': r.text}
    except Exception as e:
        results['post_ugc_read_v3'] = {'error': str(e)}

    # 3) Try listing socialActions comments v3 for a fabricated URN to see permission response
    try:
        sample_urn = 'urn:li:share:0'
        encoded = sample_urn
        headers = api._headers_v3()
        with httpx.Client(timeout=30, headers=headers) as c:
            r = c.get(f"{API_V3_BASE}/socialActions/{api._encode_urn_for_path(sample_urn)}/comments", params={'count': 1})
            try:
                r.raise_for_status()
                results['comments_v3_sample'] = {'status_code': r.status_code, 'body': r.json()}
            except httpx.HTTPStatusError:
                results['comments_v3_sample'] = {'status_code': r.status_code, 'body': r.text}
    except Exception as e:
        results['comments_v3_sample'] = {'error': str(e)}

    # 4) Legacy socialActions comments v2
    try:
        headers = api._headers()
        sample_endpoint = f"{API_BASE}/socialActions/{api._encode_urn_for_path('urn:li:share:0')}/comments"
        with httpx.Client(timeout=30, headers=headers) as c:
            r = c.get(sample_endpoint, params={'count': 1})
            try:
                r.raise_for_status()
                results['socialActions_comments_v2'] = {'status_code': r.status_code, 'body': r.json()}
            except httpx.HTTPStatusError:
                results['socialActions_comments_v2'] = {'status_code': r.status_code, 'body': r.text}
    except Exception as e:
        results['socialActions_comments_v2'] = {'error': str(e)}

    # 5) Invitations v2
    try:
        headers = api._headers()
        with httpx.Client(timeout=30, headers=headers) as c:
            r = c.get(f"{API_BASE}/growth/invitations", params={'count': 1})
            try:
                r.raise_for_status()
                results['growth_invitations_v2'] = {'status_code': r.status_code, 'body': r.json()}
            except httpx.HTTPStatusError:
                results['growth_invitations_v2'] = {'status_code': r.status_code, 'body': r.text}
    except Exception as e:
        results['growth_invitations_v2'] = {'error': str(e)}

    return results


def save_report(report: Dict):
    # Ensure project-level data directory exists
    data_dir = os.path.dirname(REPORT_PATH)
    os.makedirs(data_dir, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    report = probe_endpoints()
    save_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
