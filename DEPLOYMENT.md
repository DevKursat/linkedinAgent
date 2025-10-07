# Deployment Guide

This guide will help you deploy the LinkedIn Bot to production.

## Prerequisites

1. **LinkedIn Developer Account**
   - Go to https://www.linkedin.com/developers/apps
   - Create a new app
   - Note your Client ID and Client Secret
   - Add redirect URL: `https://your-render-app.onrender.com/callback`
   - Request these permissions:
     - `r_liteprofile` - Read profile
     - `r_emailaddress` - Read email
     - `w_member_social` - Post content
     - `rw_organization_admin` - Manage organization posts

2. **Google Gemini API Key**
   - Go to https://makersuite.google.com/app/apikey
   - Create a new API key
   - Note the key for configuration

## Deployment on Render (Recommended)

### Step 1: Prepare Repository

1. Fork or clone this repository to your GitHub account
2. Make sure all code is pushed to GitHub

### Step 2: Create Render Account

1. Go to https://render.com/
2. Sign up or log in
3. Connect your GitHub account

### Step 3: Deploy Using Blueprint

1. Click **"New"** → **"Blueprint"**
2. Select your repository
3. Render will detect `render.yaml` automatically
4. Click **"Apply"**

### Step 4: Configure Environment Variables

For both the **web** and **worker** services, add these environment variables:

```
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=https://your-app-name.onrender.com/callback
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=random_secret_key_min_32_chars
DAILY_POST_TIME=09:00
```

**Important:** Update `LINKEDIN_REDIRECT_URI` with your actual Render web service URL.

### Step 5: Generate Secret Key

Generate a secure random key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 6: Update LinkedIn App Settings

1. Go back to your LinkedIn Developer App
2. Update the OAuth redirect URL to match your Render URL
3. Example: `https://your-app-name.onrender.com/callback`

### Step 7: Deploy

1. Click **"Create Blueprint"**
2. Wait for both services to deploy (3-5 minutes)
3. Both web and worker will start automatically

### Step 8: Authenticate

1. Visit your web service URL: `https://your-app-name.onrender.com`
2. Click **"Login with LinkedIn"**
3. Authorize the app
4. You'll be redirected back to the status page

### Step 9: Verify

1. Check the status page shows "Authenticated ✓"
2. Go to **"Engagement Queue"** to test the UI
3. Check the Render logs to ensure the scheduler is running
4. Wait for the daily post time to see the first automated post

## Deployment on Other Platforms

### Heroku

1. Create `Procfile`:
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
worker: python scheduler.py
```

2. Deploy:
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
git push heroku main
heroku config:set LINKEDIN_CLIENT_ID=xxx
heroku config:set LINKEDIN_CLIENT_SECRET=xxx
heroku config:set GEMINI_API_KEY=xxx
heroku config:set SECRET_KEY=xxx
heroku config:set LINKEDIN_REDIRECT_URI=https://your-app-name.herokuapp.com/callback
heroku ps:scale web=1 worker=1
```

### Railway

1. Create new project from GitHub repo
2. Add environment variables in Railway dashboard
3. Railway will auto-detect and deploy both services
4. Update LinkedIn redirect URI

### DigitalOcean App Platform

1. Create new app from GitHub
2. Set up two components:
   - Web Service: `gunicorn --bind 0.0.0.0:8080 app:app`
   - Worker: `python scheduler.py`
3. Add environment variables
4. Deploy

### VPS (Ubuntu/Debian)

1. Clone repository:
```bash
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
```

2. Install dependencies:
```bash
apt-get update
apt-get install -y python3.11 python3-pip
pip3 install -r requirements.txt
```

3. Create `.env` file with your credentials

4. Set up systemd services:

**Web Service** (`/etc/systemd/system/linkedin-bot-web.service`):
```ini
[Unit]
Description=LinkedIn Bot Web
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/linkedinAgent
ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Worker Service** (`/etc/systemd/system/linkedin-bot-worker.service`):
```ini
[Unit]
Description=LinkedIn Bot Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/linkedinAgent
ExecStart=/usr/bin/python3 scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

5. Enable and start services:
```bash
systemctl enable linkedin-bot-web linkedin-bot-worker
systemctl start linkedin-bot-web linkedin-bot-worker
```

6. Set up Nginx reverse proxy (optional):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Post-Deployment

### Monitor the Bot

1. **Status Dashboard**: Check `/` for authentication and stats
2. **Health Check**: Monitor `/health` endpoint
3. **Logs**: View Render/platform logs for errors
4. **Admin CLI**: SSH into server and use `python admin.py stats`

### Customize Settings

Edit environment variables to adjust:
- `DAILY_POST_TIME` - Change posting time (default: 09:00)
- Check `config.py` for other customizations

### Test Before Going Live

1. Test OAuth flow
2. Use `python admin.py test-news` to verify news fetching
3. Use `python admin.py run-daily` to test daily pipeline manually
4. Add test targets to engagement queue

### Troubleshooting

**"No valid access token available"**
- Authenticate via `/login`
- Check token expiration in database
- Verify LinkedIn API credentials

**"Error generating LinkedIn post"**
- Verify Gemini API key
- Check API quotas
- Review logs for specific errors

**Posts not appearing**
- Verify scheduler is running (check worker logs)
- Check LinkedIn API permissions
- Review daily stats to confirm posts are being created

**News not fetching**
- Test with `python admin.py test-news`
- Check RSS feed availability
- Review firewall/network settings

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Rotate secrets regularly** - Update `SECRET_KEY` periodically
3. **Monitor API usage** - Check LinkedIn and Gemini quotas
4. **Review logs** - Watch for suspicious activity
5. **Use HTTPS** - Always use secure connections in production
6. **Limit permissions** - Only request necessary LinkedIn scopes

## Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Database Backup

```bash
# Backup SQLite database
cp linkedin_bot.db linkedin_bot_backup_$(date +%Y%m%d).db
```

### View Stats

```bash
python admin.py stats
```

### Manual Operations

```bash
# Run daily pipeline manually
python admin.py run-daily

# Test news fetching
python admin.py test-news --generate

# View engagement queue
python admin.py queue

# Add target and approve
python admin.py add-target https://linkedin.com/post/xyz --approve
```

## Scaling

For higher volume:
1. Increase Render plan (more resources)
2. Add more worker instances
3. Consider PostgreSQL instead of SQLite
4. Implement caching for news feeds
5. Add rate limiting for API calls

## Support

- GitHub Issues: https://github.com/DevKursat/linkedinAgent/issues
- Check logs for detailed error messages
- Review README for troubleshooting section
