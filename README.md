# LinkedIn Agent

A production-ready LinkedIn bot that posts tech news with a strategic persona, manages comments, and handles proactive engagement.

## Features

- **Daily Tech Posts**: Fetches from TechCrunch, Y Combinator, Indie Hackers, Product Hunt
- **Persona**: Kürşat (21), Product Builder - direct, sharp, strategic, friendly
- **Smart Commenting**: Auto-replies in commenter's language with appropriate tone
- **Turkish Follow-ups**: Adds Turkish summary 66 seconds after each post
- **Proactive Queue**: Web UI to manage comments on others' posts
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
| `GOOGLE_API_KEY` | - | Google Gemini API key |
| `DRY_RUN` | `true` | Test mode (no actual posting) |
| `DAILY_POSTS` | `1` | Posts per day |
| `MAX_DAILY_PROACTIVE` | `9` | Max proactive comments/day |
| `PERSONA_NAME` | `Kürşat` | Bot persona name |
| `PERSONA_AGE` | `21` | Bot persona age |
| `PERSONA_ROLE` | `Product Builder` | Bot persona role |
| `BLOCK_POLITICS` | `true` | Block political content |
| `BLOCK_SPECULATIVE_CRYPTO` | `true` | Block crypto speculation |

## Development

### Local Python Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

Run components separately:
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

## Troubleshooting

**LinkedIn login fails**
- Verify redirect URI matches exactly: `http://localhost:5000/callback`
- Check client ID and secret are correct
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

## Contributing

PRs welcome! Please test in DRY_RUN mode first.