# LinkedIn Agent

A production-ready LinkedIn bot that posts tech news with a strategic persona, manages comments, and handles proactive engagement.

## Features

- **Daily Tech Posts**: Fetches from TechCrunch, Y Combinator, Indie Hackers, Product Hunt
- **Persona**: Kürşat (21), Product Builder - direct, sharp, strategic, friendly
- **Smart Commenting**: Auto-replies in commenter's language with appropriate tone
- **Turkish Follow-ups**: Adds Turkish summary 66 seconds after each post
- **Proactive Queue**: Web UI to manage comments on others' posts
- **Personalized Voice**: Injects your about/style docs so it writes exactly like you
- **Interest-aware Discovery**: Finds posts matching your INTERESTS for proactive engagement
- **Content Moderation**: Blocks politics and speculative crypto, flags sensitive topics
- **Time-aware**: Respects Istanbul timezone and peak posting windows

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- LinkedIn Developer App ([create one here](https://www.linkedin.com/developers/apps))
- Google Gemini API key ([get one here](https://makersuite.google.com/app/apikey))

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
```

2. **Configure environment**
```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:
- `LINKEDIN_CLIENT_ID` - From LinkedIn Developer App
- `LINKEDIN_CLIENT_SECRET` - From LinkedIn Developer App
- `GOOGLE_API_KEY` - From Google AI Studio
- `LINKEDIN_REDIRECT_URI` - Keep as `http://localhost:5000/callback` for local development
- `INTERESTS` - Comma-separated keywords to bias discovery and writing (e.g., `ai,llm,product`)
- `ABOUT_ME_PATH`, `POST_STYLE_FILE`, `COMMENT_STYLE_FILE` - Paths to your style docs

**Important**: Ensure `DRY_RUN=true` for initial testing!

3. **Build and run**
```bash
docker compose up -d --build
```

4. **Authenticate with LinkedIn**

Open http://localhost:5000 in your browser and click "Login with LinkedIn"

5. **Test in DRY_RUN mode**
```bash
docker compose exec worker python -c "from src.scheduler import run_daily_post; run_daily_post()"
```

You should see:
- `[DRY_RUN] Would post:` with generated content
- Turkish summary preview

6. **Go live** (when ready)

Edit `.env`:
```env
DRY_RUN=false
```

Restart:
```bash
docker compose restart worker
```

## Architecture

### Services

- **web**: Flask UI for authentication and queue management (port 5000)
- **worker**: Background scheduler for posting and comment monitoring

### Web Routes

- `/` - Status dashboard
- `/health` - Health check endpoint
- `/login` - LinkedIn OAuth flow
- `/callback` - OAuth callback
- `/queue` - Proactive queue management
- `/enqueue_target` - Add target (POST)
- `/approve/<id>` - Approve queue item (POST)
- `/reject/<id>` - Reject queue item (POST)
- `/trigger` - Run a job now (POST)
- `/discover` - Discover relevant posts into proactive queue (POST)
- `/manual_post` - Manually share a post (POST)
- `/manual_comment` - Manually comment on a post (POST)

### Scheduler Jobs

- **Daily Post**: Random time in peak windows (09:30-11:00, 17:30-19:30 weekdays)
- **Comment Polling**: Every 7 minutes
- **Proactive Queue**: Every hour (max 9 posts/day)
- **Follow-ups**: 66 seconds after main post

## Configuration

All settings in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_CLIENT_ID` | - | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | - | LinkedIn app client secret |
| `GEMINI_API_KEY` | - | Google Gemini API key |
| `DRY_RUN` | `true` | Test mode (no actual posting) |
| `DAILY_POSTS` | `1` | Posts per day |
| `MAX_DAILY_PROACTIVE` | `9` | Max proactive comments/day |
| `PERSONA_NAME` | `Kürşat` | Bot persona name |
| `PERSONA_AGE` | `21` | Bot persona age |
| `PERSONA_ROLE` | `Product Builder` | Bot persona role |
| `INTERESTS` | `ai,llm,product,saas,startup,founder,ux,devtools,infra` | Discovery and bias |
| `ABOUT_ME_PATH` | `./data/about_me.md` | Personal bio file |
| `POST_STYLE_FILE` | `./data/style.md` | Post style file |
| `COMMENT_STYLE_FILE` | `./data/style_comment.md` | Comment style file |
| `MAX_POST_LENGTH` | `1200` | Character cap for posts |
| `BLOCK_POLITICS` | `true` | Block political content |
| `BLOCK_SPECULATIVE_CRYPTO` | `true` | Block crypto speculation |

## Development

### Local Python Setup

1. **Set up virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
```
Now, edit the newly created `.env` file and fill in your credentials, particularly:
- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`
- `GEMINI_API_KEY`

**Important**: For local development without Docker, the application runs on port 8000. Ensure your `LINKEDIN_REDIRECT_URI` in the `.env` file is set to `http://127.0.0.1:8000/callback`.

3. **Run the web server**
```bash
uvicorn src.main:app --reload
```
The application will be available at http://127.0.0.1:8000.

4. **Run the worker (in a separate terminal)**
```bash
# Make sure to activate the virtual environment in the new terminal as well
source .venv/bin/activate
python -m src.worker
```
```bash
# Web UI
python -m src.main

# Worker
python -m src.worker
```

### Database

SQLite database stored in `./data/bot.db`

Tables:
- `tokens` - LinkedIn OAuth tokens
- `posts` - Posted content history
- `comments` - Seen comments and replies
- `proactive_queue` - Proactive engagement queue

### Logs

View logs:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f worker
docker compose logs -f web
```

## Monitoring

- **Health Check**: `curl http://localhost:5000/health`
- **Status Page**: http://localhost:5000
- **Queue Management**: http://localhost:5000/queue

## Safety & Compliance

- Default `DRY_RUN=true` prevents accidental posting
- Content moderation blocks politics and speculative crypto
- Sensitive content flagged for manual approval
- Never reveals AI identity
- Respects rate limits with randomized delays

## Simulating incoming comments (how auto-reply is triggered)

- UI: On the main dashboard (`/`) there is a "Simüle Gelen Yorum" form. Use it to test the automatic reply flow without needing LinkedIn to trigger a webhook.
- Browser (optional): Use the Tampermonkey script in `scripts/tampermonkey/linkedin-forward-comment.user.js` to detect comments you post in the LinkedIn web UI and forward them to the agent's `/incoming_comment` endpoint.

See `docs/simulate-incoming-comment.md` for installation and security notes.

## Bulk invite enqueuing (CSV)

You can bulk enqueue connection invites using a CSV file. CSV columns:

- person_urn (required)
- person_name (optional)
- country (optional)
- tags (optional; semicolon-separated)

Example CSV line:

```
urn:li:person:ABC123,Jane Doe,TR,product;ai
```

Command to load CSV into invites queue:

```bash
python3 manage.py enqueue-invites-csv invites.csv
```

This only enqueues invites into the local DB; actual sending is controlled by the scheduler and `INVITES_ENABLED` config.

## Running continuously (background)

If you want the agent to keep posting daily and processing the proactive queue, run the worker/service continuously. Example using Docker Compose:

```bash
docker compose up -d --build
```

Notes about PC sleep and availability:

- The agent only runs while the process/container is active and the host machine is awake and connected to the network. If you run it locally on your laptop and put the laptop to sleep (suspend), the agent will stop executing until the machine wakes up.
- For a reliable always-on operation, run the agent on a server or VM that stays online (cloud VM, Raspberry Pi that stays awake, or a small VPS). Alternatively, run via Docker on a home machine with power settings adjusted to avoid sleep.

## Getting full permissions for comment-listing & invites

To enable full automation (reading comments on external posts, sending invites), follow the steps below. Use the exact text and curl snippets in your App Review submission to speed up approval.

1) Required scopes

- `w_member_social` — post on behalf of member
- `r_liteprofile` / `r_member_social` — (as required for your flows)
- invitations scope (LinkedIn may require a specific growth/invitations scope or manual approval). Include this phrase in your request: "Requesting permission to create connection invitations on behalf of authenticated users as part of an explicit consented flow."

2) App Review submission text (copy-paste)

Title: Requesting invitations.CREATE permission for linkedinAgent

Description (copy/paste):
```
linkedinAgent is a personal assistant that helps users grow their professional network by suggesting and sending connection invitations as part of a consented workflow. The feature is disabled by default and only runs when the authenticated user or operator explicitly enables it via the app UI. 

We will only send invitations on behalf of authenticated users who have explicitly granted permission. The app enforces rate limits, message templates, and manual confirmation fallbacks to avoid spam or policy violations. If server-side invitation API calls fail or are not available, the app falls back to a browser-assisted, user-confirmed flow (manual export + Tampermonkey) so no invitations are sent without human oversight.

Requested permission: invitations.CREATE (or the equivalent scope LinkedIn requires for server-side invitation creation).

Use-case: Allow linkedinAgent to create connection invitations on behalf of authenticated users as part of an explicit, consented workflow where the user triggers or approves the invites via the app UI.
```

3) Example request (curl) to include in the submission

```bash
curl -X POST 'https://api.linkedin.com/v2/invitations' \
	-H 'Authorization: Bearer <ACCESS_TOKEN>' \
	-H 'Content-Type: application/json' \
	-d '{
		"invitee": {"com.linkedin.voyager.growth.invitation.InviteeProfile": {"profileUrn": "urn:li:person:TARGET_ID"}},
		"message": "Merhaba, sizi profesyonel ağımda görmek isterim. Selamlar, Kürşat."
	}'
```

4) Screenshots to attach

- `/invites` UI with pending invites and the "Send (server)" button.
- Network console showing the POST request and its 403/404 response (so LinkedIn reviewers can reproduce why the app needs permission).
- `data/manual_invites.html` / Tampermonkey flow screenshot (shows fallback behavior and human confirmation UI).

5) How to enable invites safely (local test)

Edit `.env` and set:
```
INVITES_ENABLED=true
DRY_RUN=false
```
Then restart containers. Note: if LinkedIn has not granted invitations.CREATE to your app, server-side calls will still return 403/404. In that case use the manual export + Tampermonkey flow (described below).

6) Quick remediation if API returns 403/404

- Use `/debug/last-invite-error` endpoint to fetch recent alert lines: `curl http://localhost:5000/debug/last-invite-error`
- Check `data/alerts.log` for saved failure lines.

If you'd like, I can prepare the screenshots and the exact network console captures for you and add them to `docs/`.

## Troubleshooting

**LinkedIn login fails**
- **For Docker setup**: Verify redirect URI in your `.env` file matches `http://localhost:5000/callback`.
- **For Local Python setup**: Verify redirect URI in your `.env` file matches `http://127.0.0.1:8000/callback`.
- Check that your `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` in `.env` are correct.
- Ensure app has correct scopes: `w_member_social r_member_social r_liteprofile`

**Worker not posting**
- Check `DRY_RUN` setting
- Verify `GOOGLE_API_KEY` is set
- Check worker logs: `docker compose logs worker`

**Database errors**
- Ensure `./data` directory exists
- Check file permissions

## License

MIT

## Testing

Run the installation test to verify everything is working:

```bash
python3 test_installation.py
```

Expected output: All 6 tests should pass.

See [VERIFICATION.md](VERIFICATION.md) for detailed implementation verification and acceptance criteria.

---

Release: v1.0.0 — finalizing invites & app-review package. Download the App Review package from the release: https://github.com/DevKursat/linkedinAgent/releases/tag/v1.0-invites-ready

## Deploying with GitHub Actions and GHCR

On push to `main`:
- CI runs installation tests
- Docker image is built and pushed to GitHub Container Registry (GHCR)

Run in production using GHCR image:

```bash
cp .env.example .env
# fill secrets
docker compose -f docker-compose.prod.yml up -d
```

## Contributing

PRs welcome! Please test in DRY_RUN mode first.