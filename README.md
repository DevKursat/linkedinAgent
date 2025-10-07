# LinkedIn Persona Bot - Kürşat

A production-ready LinkedIn automation bot that generates and posts daily content, engages with comments, and manages proactive engagement through a simple web interface.

## Features

### 🤖 Automated Daily Content Pipeline
- Fetches news from TechCrunch, YC Blog, Indie Hackers, and Product Hunt
- Filters out politics and speculative crypto content
- Generates strategic LinkedIn posts using Gemini 2.5 Flash
- Posts to LinkedIn API automatically
- Adds Turkish summary comment after 66 seconds with source link

### 💬 Smart Comment Management
- Polls latest posts every 7 minutes
- Replies in the commenter's language (detected automatically)
- Response time: 5-30 minutes (shorter during peak hours 9 AM - 5 PM)
- Handles negative comments with witty but professional corrections

### 🎯 Proactive Engagement Queue
- Simple web UI to add LinkedIn post URLs/URNs
- Approval workflow before posting
- Up to 9 proactive comments per day
- Strategic, value-adding engagement

### 👤 Persona: Kürşat
- Age: 21
- Role: Product Builder
- Style: Direct, sharp, strategic, friendly
- Topics: AI/ML, B2B SaaS, Fintech, product development lifecycle
- Tone: Minimal emoji, concise, never reveals being AI

### 📊 Web Dashboard
- `/` - Status dashboard with authentication status and daily stats
- `/health` - Health check endpoint (JSON)
- `/login` - LinkedIn OAuth login
- `/callback` - OAuth callback handler
- `/queue` - Engagement queue management
- `/enqueue_target` - Add new target to queue (POST)
- `/approve/<id>` - Approve engagement target

## Architecture

The bot consists of two separate services:

1. **Web Service** (`app.py`) - Flask web UI for OAuth and queue management
2. **Worker Service** (`scheduler.py`) - Background scheduler for automated tasks

Both services share the same SQLite database for state management.

## Setup

### Prerequisites
- Python 3.11+
- LinkedIn Developer Account with OAuth app configured
- Google Gemini API key

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Configure environment variables in `.env`:
```
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:5000/callback
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_random_secret_key
FLASK_ENV=development
DATABASE_PATH=linkedin_bot.db
DAILY_POST_TIME=09:00
```

5. Run the web service:
```bash
python app.py
```

6. In a separate terminal, run the worker service:
```bash
python scheduler.py
```

7. Open your browser and navigate to `http://localhost:5000`

8. Click "Login with LinkedIn" to authenticate

## Deployment on Render

This bot is designed to be deployed on Render as two separate services.

### Option 1: Deploy using render.yaml (Blueprint)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New" → "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and create both services
6. Add environment variables in Render dashboard:
   - `LINKEDIN_CLIENT_ID`
   - `LINKEDIN_CLIENT_SECRET`
   - `LINKEDIN_REDIRECT_URI` (your Render web service URL + /callback)
   - `GEMINI_API_KEY`

### Option 2: Manual Deployment

#### Web Service
1. Create a new Web Service
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app`
5. Add environment variables
6. Deploy

#### Worker Service
1. Create a new Background Worker
2. Connect the same GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python scheduler.py`
5. Add the same environment variables
6. Deploy

### Important Notes for Render
- Both services should use the same environment variables
- Update `LINKEDIN_REDIRECT_URI` to your Render web service URL + `/callback`
- The SQLite database is stored in `/app/data/` (ephemeral on Render free tier)
- For production, consider using Render's persistent disk or external database

## Database Schema

### Tables
- **posts** - Stores generated and posted content
- **comments** - Tracks comments and replies
- **engagement_queue** - Manages proactive engagement targets
- **oauth_tokens** - Stores LinkedIn OAuth tokens
- **daily_stats** - Tracks daily activity metrics

## Configuration

Key configuration options in `config.py`:

- `DAILY_POST_TIME` - Time for daily content (default: 09:00)
- `COMMENT_CHECK_INTERVAL` - Minutes between comment checks (default: 7)
- `COMMENT_DELAY_MIN` - Seconds before Turkish summary (default: 66)
- `PROACTIVE_COMMENTS_PER_DAY` - Max proactive comments (default: 9)

## Content Filtering

The bot automatically filters out:
- Political content (elections, politicians, etc.)
- Speculative cryptocurrency content (meme coins, NFTs, etc.)

## Logging

All logs are output to stdout in a structured format:
```
2024-01-01 09:00:00 - module_name - INFO - Log message
```

Perfect for monitoring on Render's log dashboard.

## Security

- OAuth tokens stored in SQLite database
- Session management with Flask sessions
- Environment variables for sensitive credentials
- HTTPS enforced on Render
- No hardcoded secrets

## Development

### Project Structure
```
linkedinAgent/
├── app.py                 # Flask web application
├── scheduler.py           # Background worker scheduler
├── config.py              # Configuration management
├── database.py            # Database models and operations
├── linkedin_api.py        # LinkedIn API integration
├── content_generator.py   # Gemini content generation
├── news_fetcher.py        # News RSS feed fetcher
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── render.yaml           # Render blueprint
├── .env.example          # Environment variables template
└── README.md             # This file
```

### Adding New Features

1. **New Content Sources**: Add to `NEWS_SOURCES` in `config.py`
2. **Custom Prompts**: Modify functions in `content_generator.py`
3. **New UI Routes**: Add to `app.py`
4. **Database Changes**: Update `database.py` schema

## Troubleshooting

### "No valid access token available"
- Make sure you've completed LinkedIn OAuth flow
- Check token expiration in database
- Re-authenticate via `/login`

### "Error generating LinkedIn post"
- Verify Gemini API key is correct
- Check API quota limits
- Review logs for specific error

### Posts not appearing
- Verify LinkedIn API permissions
- Check scheduler is running
- Review daily stats at `/`

## License

MIT License - feel free to use and modify

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- Logs added for major operations
- Environment variables documented

## Support

For issues and questions:
- Open an issue on GitHub
- Check logs for error details
- Review LinkedIn and Gemini API documentation

---

Built with ❤️ by Kürşat - A 21-year-old Product Builder focused on AI/ML, B2B SaaS, and Fintech