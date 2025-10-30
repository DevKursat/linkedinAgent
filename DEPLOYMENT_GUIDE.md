# LinkedIn Agent - Full Autonomous System Deployment Guide

This guide provides step-by-step instructions for deploying the LinkedIn Agent as a fully autonomous system using GitHub Actions and GitHub Container Registry (GHCR).

## Overview

The system automatically:
- Posts tech news daily during peak hours (09:30-11:00, 17:30-19:30)
- Monitors and responds to comments
- Engages with relevant posts proactively
- Operates autonomously from 7 AM to 10 PM (Istanbul time)

## Deployment Methods

### Method 1: Deploy Using GitHub Container Registry (Recommended)

This method uses pre-built Docker images from GitHub Actions for production deployment.

#### Prerequisites

1. **GitHub Account** with this repository
2. **Server/VPS** (Linux recommended) with:
   - Docker and Docker Compose installed
   - Minimum 1GB RAM, 10GB storage
   - Always-on internet connection
3. **LinkedIn Developer App** credentials
4. **Google Gemini API** key

#### Step 1: Prepare Your Server

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

#### Step 2: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required Environment Variables:**

```env
# LinkedIn API Configuration
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URI=http://your-server-ip:5000/callback

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Flask Secret (generate a random string)
FLASK_SECRET_KEY=your_random_secret_key_here

# Disable dry run for production
DRY_RUN=false

# Optional: Customize interests
INTERESTS=ai,llm,product,saas,startup,founder,ux,devtools,infra
```

#### Step 3: Create Data Directory

```bash
# Create data directory for persistent storage
mkdir -p data

# Create required style files
cat > data/about_me.md << 'EOF'
# About Me
Your personal bio here...
EOF

cat > data/style.md << 'EOF'
# Post Style
Your posting style guidelines...
EOF

cat > data/style_comment.md << 'EOF'
# Comment Style
Your comment style guidelines...
EOF
```

#### Step 4: Deploy with Production Compose

```bash
# Pull the latest image from GHCR
docker compose -f docker-compose.prod.yml pull

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

#### Step 5: Authenticate with LinkedIn

1. Open your browser and navigate to: `http://your-server-ip:5000`
2. Click "Login with LinkedIn"
3. Complete the OAuth flow
4. Verify authentication is successful

#### Step 6: Verify Autonomous Operation

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Verify worker is running
docker compose -f docker-compose.prod.yml logs worker

# Check web service
curl http://localhost:5000/health
```

### Method 2: Build and Deploy Locally

Use this method if you want to build the Docker images yourself.

```bash
# Build and start services
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## GitHub Actions CI/CD

The repository includes automated CI/CD that:

1. **On Pull Request:**
   - Runs syntax checks
   - Runs all tests
   - Validates code quality

2. **On Push to Main:**
   - Runs all tests
   - Builds Docker image
   - Pushes to GitHub Container Registry (ghcr.io)
   - Tags with branch name and commit SHA

### Workflow File: `.github/workflows/ci.yml`

The workflow automatically builds and publishes Docker images on every push to `main`.

## Monitoring and Maintenance

### Health Checks

```bash
# Check system health
curl http://localhost:5000/health

# View recent posts
docker compose exec web python -c "from src.database import SessionLocal; from src.models import Post; db = SessionLocal(); posts = db.query(Post).order_by(Post.id.desc()).limit(5).all(); print([p.content[:50] for p in posts])"
```

### Log Monitoring

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View worker logs only
docker compose -f docker-compose.prod.yml logs -f worker

# View web logs only
docker compose -f docker-compose.prod.yml logs -f web

# View last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Database Backup

```bash
# Backup database
cp data/bot.db data/bot.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp data/bot.db.backup.YYYYMMDD_HHMMSS data/bot.db
docker compose -f docker-compose.prod.yml restart
```

## Updating to Latest Version

```bash
# Pull latest code
git pull origin main

# Pull latest Docker image
docker compose -f docker-compose.prod.yml pull

# Restart services
docker compose -f docker-compose.prod.yml up -d

# Verify update
docker compose -f docker-compose.prod.yml logs --tail=50
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker compose -f docker-compose.prod.yml logs

# Check container status
docker compose -f docker-compose.prod.yml ps -a

# Restart services
docker compose -f docker-compose.prod.yml restart
```

### Authentication Issues

1. Verify `LINKEDIN_REDIRECT_URI` matches your LinkedIn app settings
2. Ensure `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` are correct
3. Check that redirect URI in LinkedIn app includes your server's public IP/domain

### Worker Not Posting

1. Check `DRY_RUN` is set to `false` in `.env`
2. Verify `GEMINI_API_KEY` is valid
3. Check operating hours (7 AM - 10 PM Istanbul time)
4. Review worker logs: `docker compose logs worker`

### High Memory Usage

```bash
# Check resource usage
docker stats

# Restart services if needed
docker compose -f docker-compose.prod.yml restart

# Set memory limits in docker-compose.prod.yml
# Add under each service:
#   mem_limit: 512m
#   memswap_limit: 512m
```

## Server Setup for Always-On Operation

### Using systemd (Recommended for Linux Servers)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/linkedinagent.service
```

Add this content:

```ini
[Unit]
Description=LinkedIn Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/linkedinAgent
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable linkedinagent
sudo systemctl start linkedinagent

# Check status
sudo systemctl status linkedinagent
```

### Using Cloud Providers

#### AWS EC2

1. Launch Ubuntu 20.04 LTS instance (t2.small or larger)
2. Configure security group: Allow inbound TCP on port 5000
3. Follow deployment steps above
4. Optional: Set up Elastic IP for consistent access

#### Google Cloud Platform

1. Create Compute Engine instance (e2-small or larger)
2. Configure firewall: Allow TCP:5000
3. Follow deployment steps above
4. Optional: Reserve static IP

#### DigitalOcean Droplet

1. Create Droplet with Docker pre-installed
2. Configure firewall: Allow port 5000
3. Follow deployment steps above

## Security Best Practices

1. **Use Strong Secrets:**
   ```bash
   # Generate random secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Limit Network Access:**
   - Use firewall to restrict port 5000 to trusted IPs
   - Consider using reverse proxy (nginx) with SSL

3. **Regular Updates:**
   ```bash
   # Weekly update schedule
   git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d
   ```

4. **Monitor Logs:**
   - Set up log rotation
   - Monitor for errors and unusual activity

5. **Backup Data:**
   - Automate database backups
   - Store backups in secure location

## Performance Optimization

### Docker Resource Limits

Edit `docker-compose.prod.yml`:

```yaml
services:
  worker:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  web:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Database Optimization

```bash
# Vacuum database periodically
docker compose exec web python -c "from src.database import engine; engine.execute('VACUUM')"
```

## Support

- **Issues:** https://github.com/DevKursat/linkedinAgent/issues
- **Documentation:** Check README.md and other docs in the repository
- **Logs:** Always check logs first: `docker compose logs`

## License

MIT - See LICENSE file for details
