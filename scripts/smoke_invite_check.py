#!/usr/bin/env python3
"""Safe smoke-test for LinkedIn invite endpoints.

This script inspects the configured REST v3 and legacy v2 invite endpoints
to report whether they appear reachable from the current environment.

Usage:
  python3 scripts/smoke_invite_check.py [--execute] [--person-urn urn:li:person:...] 

By default the script runs in probe-only mode (safe): it will not send actual
invitations. If you pass --execute and the app is configured with INVITES_ENABLED
and DRY_RUN=false, the script will call LinkedInAPI.send_invite once with the
provided --person-urn (required in execute mode).
"""
import sys
import argparse
import time
import os
from urllib.parse import urlencode

# Ensure project root is on sys.path when running as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.config import config
from src.linkedin_api import LinkedInAPI, API_BASE, API_V3_BASE


def probe_urls() -> dict:
    """Return a mapping of endpoint -> (status, detail) by doing HEAD requests where possible.
    We avoid sending payloads in probe mode to be non-destructive."""
    results = {}
    api = LinkedInAPI()
    # Candidate REST v3 paths
    v3_paths = ["/growth/invitations", "/invitations"]
    # Candidate legacy v2 paths
    v2_paths = ["/growth/invitations", "/invitations"]

    # Probe REST versions if REST allowed
    if api._rest_allowed():
        versions = api._rest_versions()
        for v in versions[:3]:
            for p in v3_paths:
                url = f"{API_V3_BASE}{p}"
                results[f"v3:{v}:{p}"] = probe_url(url, headers=api._headers_v3(v))
                time.sleep(0.1)

    # Probe legacy
    for p in v2_paths:
        url = f"{API_BASE}{p}"
        try:
            results[f"v2:{p}"] = probe_url(url, headers=api._headers())
        except Exception as e:
            results[f"v2:{p}"] = (False, str(e))

    return results


def probe_url(url: str, headers: dict = None) -> tuple:
    """Do a safe HEAD request to the URL using the configured token if present.
    Returns (ok: bool, detail: str).
    """
    import httpx

    headers = headers or {}
    try:
        with httpx.Client(timeout=10, headers=headers) as c:
            # Use HEAD first; some endpoints may not respond to HEAD -> fallback to OPTIONS
            r = c.head(url)
            if r.status_code >= 200 and r.status_code < 400:
                return True, f"HEAD {r.status_code}"
            # Try OPTIONS as a fallback
            r = c.options(url)
            return (200 <= r.status_code < 400, f"OPTIONS {r.status_code} - {r.text[:200]}")
    except Exception as e:
        return False, str(e)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually call send_invite (destructive)")
    parser.add_argument("--person-urn", type=str, help="Person URN to use when --execute is provided")
    args = parser.parse_args(argv)

    print("LinkedIn invite smoke-test")
    print(f"DRY_RUN={config.DRY_RUN} INVITES_ENABLED={config.INVITES_ENABLED}")

    results = probe_urls()

    ok_count = 0
    for k, v in results.items():
        ok, detail = v
        status = "OK" if ok else "FAIL"
        print(f"{k}: {status} - {detail}")
        if ok:
            ok_count += 1

    summary = f"Probe summary: {ok_count}/{len(results)} endpoints appear reachable"
    print(summary)

    # Append to alerts.log for operator visibility
    try:
        with open('data/alerts.log', 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - smoke_probe - {summary}\n")
    except Exception:
        pass

    # If execute requested, enforce safety checks
    if args.execute:
        if not args.person_urn:
            print("--person-urn is required when --execute is used")
            sys.exit(2)
        if config.DRY_RUN:
            print("Refusing to execute: DRY_RUN=true")
            sys.exit(2)
        if not config.INVITES_ENABLED:
            print("Refusing to execute: INVITES_ENABLED=false")
            sys.exit(2)
        # Call send_invite once
        api = LinkedInAPI()
        try:
            resp = api.send_invite(args.person_urn, message="Smoke test invite - please ignore")
            print("send_invite response:", resp)
        except Exception as e:
            print("send_invite failed:", e)
            try:
                with open('data/alerts.log', 'a', encoding='utf-8') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - smoke_execute_failed - {e}\n")
            except Exception:
                pass
            sys.exit(1)

    print("Done")


if __name__ == '__main__':
    main()
