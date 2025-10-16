Enable invites runbook

This runbook guides you through enabling server-side invites once LinkedIn grants the invitations.CREATE permission.

1) Pre-requisites
- Ensure `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` and `LINKEDIN_REDIRECT_URI` are set in `.env`.
- Ensure app has been granted the invitations.CREATE permission by LinkedIn App Review.

2) Environment changes
- Edit `.env`:

```
INVITES_ENABLED=true
DRY_RUN=false
```

- Optional limits:
```
INVITES_PER_HOUR=3
INVITES_MAX_PER_DAY=20
```

3) Restart services

```bash
docker compose down
docker compose up -d --build
```

4) Smoke tests
- Run a probe (non-destructive) to see endpoint behavior and record logs:

```bash
python3 scripts/check_invite_endpoints.py
curl http://localhost:5000/debug/last-invite-error
```

- Safe smoke-test helper (preferred):

```bash
# Probe REST and legacy invite endpoints (safe, non-destructive)
python3 scripts/smoke_invite_check.py

# If you have a test account and LinkedIn has granted invitations.CREATE,
# and you really want to attempt a single invite, run with --execute and
# provide a test person URN. This will only run if DRY_RUN=false and
# INVITES_ENABLED=true in your environment.
python3 scripts/smoke_invite_check.py --execute --person-urn urn:li:person:TESTID
```

- If probes show 201/200 responses, try sending a test invite via UI (`/invites`) with a test account.

5) Monitoring
- Check `data/alerts.log` for any failures.
- Use `docker compose logs -f web` and `docker compose logs -f worker` for real-time logs.

6) Rollback
- If unexpected errors or rate-limit blocks occur, set `INVITES_ENABLED=false` and restart.

7) Notes
- Keep `DRY_RUN=true` until you confirm invites are working with a test account.
- Avoid sending large volumes until you are certain of LinkedIn's acceptance and your app's limits.

Contact: DevKursat for troubleshooting and appeal support.