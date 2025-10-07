from flask import Flask, render_template_string, request, redirect, session, jsonify
from datetime import datetime
import logging
import sys
from config import SECRET_KEY, LINKEDIN_REDIRECT_URI
from database import (
    init_db, get_pending_engagement_queue, add_engagement_target,
    approve_engagement_target, get_daily_stats, get_latest_oauth_token
)
from linkedin_api import get_authorization_url, exchange_code_for_token, get_access_token
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize database
init_db()


# Templates
STATUS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Bot Status</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #0077b5; }
        .stat { 
            margin: 10px 0; 
            padding: 10px;
            background: #f8f9fa;
            border-left: 4px solid #0077b5;
        }
        .status-ok { color: green; }
        .status-error { color: red; }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            margin: 10px 5px;
            background: #0077b5;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .btn:hover { background: #005885; }
    </style>
</head>
<body>
    <div class="container">
        <h1>LinkedIn Bot Status</h1>
        
        <h2>Authentication</h2>
        <div class="stat">
            <strong>Status:</strong> 
            <span class="{{ 'status-ok' if has_token else 'status-error' }}">
                {{ 'Authenticated ✓' if has_token else 'Not Authenticated ✗' }}
            </span>
        </div>
        {% if not has_token %}
        <a href="/login" class="btn">Login with LinkedIn</a>
        {% endif %}
        
        <h2>Today's Stats</h2>
        <div class="stat">
            <strong>Posts Created:</strong> {{ stats.posts_created }}
        </div>
        <div class="stat">
            <strong>Comments Replied:</strong> {{ stats.comments_replied }}
        </div>
        <div class="stat">
            <strong>Proactive Comments:</strong> {{ stats.proactive_comments }}
        </div>
        
        <h2>Actions</h2>
        <a href="/queue" class="btn">Engagement Queue</a>
        <a href="/health" class="btn">Health Check</a>
    </div>
</body>
</html>
"""

QUEUE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Engagement Queue</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #0077b5; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #0077b5;
            color: white;
        }
        .btn {
            padding: 6px 12px;
            background: #0077b5;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #005885; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        form { margin: 20px 0; }
        input[type="text"] {
            width: 70%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .back-link {
            display: inline-block;
            margin: 20px 0;
            color: #0077b5;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Engagement Queue</h1>
        <a href="/" class="back-link">← Back to Status</a>
        
        <h2>Add New Target</h2>
        <form method="POST" action="/enqueue_target">
            <input type="text" name="target_url" placeholder="LinkedIn Post URL or URN" required>
            <button type="submit" class="btn btn-success">Add to Queue</button>
        </form>
        
        <h2>Pending Approval ({{ queue|length }})</h2>
        {% if queue %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Target URL</th>
                    <th>Created</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for item in queue %}
                <tr>
                    <td>{{ item.id }}</td>
                    <td>{{ item.target_url }}</td>
                    <td>{{ item.created_at }}</td>
                    <td>
                        <a href="/approve/{{ item.id }}" class="btn">Approve</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No pending items in queue.</p>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Status page"""
    token = get_latest_oauth_token()
    stats = get_daily_stats()
    
    return render_template_string(
        STATUS_TEMPLATE,
        has_token=token is not None,
        stats=stats
    )


@app.route('/health')
def health():
    """Health check endpoint"""
    token = get_latest_oauth_token()
    stats = get_daily_stats()
    
    return jsonify({
        'status': 'ok',
        'authenticated': token is not None,
        'stats': stats
    })


@app.route('/login')
def login():
    """Initiate LinkedIn OAuth flow"""
    state = str(uuid.uuid4())
    session['oauth_state'] = state
    auth_url = get_authorization_url(state)
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """OAuth callback handler"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if state != session.get('oauth_state'):
        return 'Invalid state parameter', 400
    
    if not code:
        return 'No authorization code received', 400
    
    try:
        # Exchange code for token
        exchange_code_for_token(code)
        logger.info("Successfully authenticated with LinkedIn")
        return redirect('/')
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return f'Authentication failed: {str(e)}', 500


@app.route('/queue')
def queue():
    """Engagement queue page"""
    pending_items = get_pending_engagement_queue()
    return render_template_string(QUEUE_TEMPLATE, queue=pending_items)


@app.route('/enqueue_target', methods=['POST'])
def enqueue_target():
    """Add a target to the engagement queue"""
    target_url = request.form.get('target_url')
    
    if not target_url:
        return 'Target URL is required', 400
    
    try:
        # Extract URN if it's a URL
        target_urn = None
        if 'urn:li:' in target_url:
            target_urn = target_url
        
        add_engagement_target(target_url, target_urn)
        logger.info(f"Added target to queue: {target_url}")
        return redirect('/queue')
    except Exception as e:
        logger.error(f"Error adding target: {e}")
        return f'Error adding target: {str(e)}', 500


@app.route('/approve/<int:target_id>')
def approve(target_id):
    """Approve an engagement target"""
    try:
        approve_engagement_target(target_id)
        logger.info(f"Approved engagement target: {target_id}")
        return redirect('/queue')
    except Exception as e:
        logger.error(f"Error approving target: {e}")
        return f'Error approving target: {str(e)}', 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
