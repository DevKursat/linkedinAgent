# Quick Reference Guide

## Common Commands

### Initial Setup
```bash
# Clone and setup
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
cp .env.example .env

# Edit .env with your credentials
nano .env  # or vim, code, etc.

# Build and start
docker compose up -d --build

# View logs
docker compose logs -f
```

### Testing

```bash
# Run installation tests
python3 test_installation.py

# Test DRY_RUN mode
docker compose exec worker python -c "from src.scheduler import run_daily_post; run_daily_post()"

# Check health
curl http://localhost:5000/health
```

### Daily Operations

```bash
# View logs
docker compose logs -f worker  # Worker logs
docker compose logs -f web     # Web UI logs

# Restart services
docker compose restart worker
docker compose restart web

# Stop everything
docker compose down

# Start again
docker compose up -d
```

### Debugging

```bash
# Enter worker container
docker compose exec worker bash

# Check database
docker compose exec worker python3 -c "
from src.db import get_recent_posts
posts = get_recent_posts()
for p in posts:
    print(p)
"

# Manual post test (DRY_RUN)
docker compose exec worker python3 -c "
from src.scheduler import run_daily_post
run_daily_post()
"

# Check pending comments
docker compose exec worker python3 -c "
from src.db import get_unreplied_comments
comments = get_unreplied_comments()
print(f'Unreplied: {len(comments)}')
"
```

### Configuration Changes

```bash
# Edit .env
nano .env

# Restart to apply changes
docker compose restart worker
docker compose restart web

# Or rebuild if you changed code
docker compose up -d --build
```

### Database Operations

```bash
# Backup database
cp ./data/bot.db ./data/bot.db.backup

# View database
docker compose exec worker sqlite3 /app/data/bot.db "SELECT * FROM posts LIMIT 5;"

# Check queue items
docker compose exec worker python3 -c "
from src.db import get_pending_queue_items, get_approved_queue_items
print(f'Pending: {len(get_pending_queue_items())}')
print(f'Approved: {len(get_approved_queue_items())}')
"
```

### Going Live

```bash
# 1. Test thoroughly in DRY_RUN mode first!

# 2. Edit .env
DRY_RUN=false

# 3. Restart worker
docker compose restart worker

# 4. Monitor logs carefully
docker compose logs -f worker

# 5. Check posts
curl http://localhost:5000/
```

### Troubleshooting

#### LinkedIn Login Not Working
```bash
# Check redirect URI matches exactly
grep LINKEDIN_REDIRECT_URI .env
# Should be: LINKEDIN_REDIRECT_URI=http://localhost:5000/callback

# Check credentials
grep LINKEDIN_CLIENT .env
# Verify these match your LinkedIn app settings
```

#### Worker Not Posting
```bash
# Check DRY_RUN setting
grep DRY_RUN .env

# Check Gemini API key
grep GOOGLE_API_KEY .env

# Check worker logs
docker compose logs worker | tail -50

# Manually trigger post
docker compose exec worker python3 -c "from src.scheduler import run_daily_post; run_daily_post()"
```

#### Database Errors
```bash
# Check if data directory exists
ls -la ./data/

# Check database file
ls -la ./data/bot.db

# Recreate database (WARNING: deletes all data)
rm ./data/bot.db
docker compose restart worker
```

#### Port Already in Use
```bash
# Change port in docker-compose.yml
# Change: "5000:5000" to "5001:5000"
# Then update LINKEDIN_REDIRECT_URI in .env to http://localhost:5001/callback
docker compose up -d
```

## Web UI Routes

- **http://localhost:5000/** - Main dashboard
- **http://localhost:5000/health** - Health check (JSON)
- **http://localhost:5000/login** - LinkedIn OAuth
- **http://localhost:5000/queue** - Proactive queue management

## Environment Variables Quick Reference

### Required
- `LINKEDIN_CLIENT_ID` - From LinkedIn Developer App
- `LINKEDIN_CLIENT_SECRET` - From LinkedIn Developer App
- `GOOGLE_API_KEY` - From Google AI Studio

### Important Defaults
- `DRY_RUN=true` - Safe mode (no real posting)
- `DAILY_POSTS=1` - One post per day
- `MAX_DAILY_PROACTIVE=9` - Max proactive comments per day
- `BLOCK_POLITICS=true` - Block political content
- `BLOCK_SPECULATIVE_CRYPTO=true` - Block crypto speculation

### Customization
- `PERSONA_NAME=Kürşat` - Bot name
- `PERSONA_AGE=21` - Bot age
- `PERSONA_ROLE=Product Builder` - Bot role
- `POST_WINDOWS=weekday:09:30-11:00,17:30-19:30` - Posting time windows
- `RARE_EMOJI=true` - Use emoji sparingly

## Monitoring

### Key Metrics to Watch
- Daily posts count (should be ≤ DAILY_POSTS)
- Proactive posts count (should be ≤ MAX_DAILY_PROACTIVE)
- Unreplied comments count (should trend down)
- Worker uptime
- API errors in logs

### Health Checks
```bash
# Quick health check
curl http://localhost:5000/health

# Detailed status
curl http://localhost:5000/ | grep -o 'Authenticated: [^<]*'

# Recent activity
docker compose logs worker | grep -i "posted\|replied\|scheduled"
```

## Maintenance

### Daily
- Check logs for errors
- Monitor LinkedIn API quota usage
- Review pending queue items at /queue

### Weekly
- Backup database: `cp ./data/bot.db ./backups/bot.db.$(date +%Y%m%d)`
- Review post performance on LinkedIn
- Adjust PERSONA or POST_WINDOWS if needed

### Monthly
- Review and update content moderation keywords if needed
- Update dependencies: `pip list --outdated`
- Review Gemini API costs

## Getting Help

1. Check logs: `docker compose logs -f`
2. Run tests: `python3 test_installation.py`
3. Review VERIFICATION.md
4. Check README.md troubleshooting section
5. Open an issue on GitHub

## Safety Reminders

- ✅ Always test in DRY_RUN mode first
- ✅ Keep FLASK_SECRET_KEY secure
- ✅ Never commit .env file
- ✅ Backup database before major changes
- ✅ Monitor API usage and costs
- ✅ Review content moderation regularly
