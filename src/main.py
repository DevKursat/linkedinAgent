"""Flask web application for LinkedIn Agent."""
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import secrets
from . import db
from .config import config
from .linkedin_api import LinkedInAPI
from .proactive import enqueue_target
from .utils import get_istanbul_time


app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY


# Initialize database on startup
db.init_db()


# HTML Templates (inline for simplicity)
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Agent - Status</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #0077b5; }
        .status { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .info { margin: 10px 0; }
        .button { display: inline-block; padding: 10px 20px; background: #0077b5; color: white; 
                  text-decoration: none; border-radius: 5px; margin: 5px; }
        .button:hover { background: #005885; }
    </style>
</head>
<body>
    <h1>LinkedIn Agent</h1>
    
    <div class="status">
        <h2>Status</h2>
        <div class="info"><strong>Time:</strong> {{ time }}</div>
        <div class="info"><strong>Timezone:</strong> {{ timezone }}</div>
        <div class="info"><strong>DRY_RUN:</strong> {{ dry_run }}</div>
        <div class="info"><strong>Authenticated:</strong> {{ authenticated }}</div>
        {% if persona %}
        <div class="info"><strong>Persona:</strong> {{ persona.name }}, {{ persona.age }}, {{ persona.role }}</div>
        {% endif %}
    </div>
    
    <div class="status">
        <h2>Actions</h2>
        {% if not authenticated %}
        <a href="{{ url_for('login') }}" class="button">Login with LinkedIn</a>
        {% endif %}
        <a href="{{ url_for('health') }}" class="button">Health Check</a>
        <a href="{{ url_for('queue') }}" class="button">Proactive Queue</a>
    </div>
    
    <div class="status">
        <h2>Recent Posts</h2>
        {% if posts %}
            {% for post in posts %}
            <div class="info">
                <strong>{{ post.posted_at }}</strong><br>
                {{ post.content[:100] }}...
                {% if post.follow_up_posted %}✓ Follow-up posted{% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div class="info">No posts yet</div>
        {% endif %}
    </div>
</body>
</html>
"""

QUEUE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Agent - Proactive Queue</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 50px auto; padding: 20px; }
        h1 { color: #0077b5; }
        .item { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .button { display: inline-block; padding: 8px 15px; background: #0077b5; color: white; 
                  text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
        .button:hover { background: #005885; }
        .approve { background: #28a745; }
        .approve:hover { background: #218838; }
        .reject { background: #dc3545; }
        .reject:hover { background: #c82333; }
        form { margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        label { font-weight: bold; display: block; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Proactive Queue</h1>
    <a href="{{ url_for('index') }}" class="button">← Back</a>
    
    <h2>Add New Target</h2>
    <form method="POST" action="{{ url_for('enqueue_target') }}">
        <label>Target URL or URN:</label>
        <input type="text" name="target_url" required placeholder="https://linkedin.com/feed/update/...">
        
        <label>Target URN (optional, will be extracted from URL if possible):</label>
        <input type="text" name="target_urn" placeholder="urn:li:ugcPost:...">
        
        <label>Context (optional):</label>
        <textarea name="context" rows="3" placeholder="Why do you want to comment on this post?"></textarea>
        
        <button type="submit" class="button">Enqueue</button>
    </form>
    
    <h2>Pending Approval ({{ pending|length }})</h2>
    {% for item in pending %}
    <div class="item">
        <div><strong>URL:</strong> {{ item.target_url }}</div>
        <div><strong>URN:</strong> {{ item.target_urn or 'N/A' }}</div>
        <div><strong>Context:</strong> {{ item.context or 'N/A' }}</div>
        <div><strong>Suggested Comment:</strong> {{ item.suggested_comment }}</div>
        <div><strong>Created:</strong> {{ item.created_at }}</div>
        <form method="POST" action="{{ url_for('approve_item', item_id=item.id) }}" style="display: inline; padding: 0; margin: 0; background: none;">
            <button type="submit" class="button approve">Approve</button>
        </form>
        <form method="POST" action="{{ url_for('reject_item', item_id=item.id) }}" style="display: inline; padding: 0; margin: 0; background: none;">
            <button type="submit" class="button reject">Reject</button>
        </form>
    </div>
    {% else %}
    <div class="item">No pending items</div>
    {% endfor %}
    
    <h2>Approved ({{ approved|length }})</h2>
    {% for item in approved %}
    <div class="item">
        <div><strong>URL:</strong> {{ item.target_url }}</div>
        <div><strong>Comment:</strong> {{ item.suggested_comment }}</div>
        <div><strong>Approved:</strong> {{ item.approved_at }}</div>
        <div>{% if item.posted_at %}<strong>Posted:</strong> {{ item.posted_at }}{% else %}<em>Waiting to post...</em>{% endif %}</div>
    </div>
    {% else %}
    <div class="item">No approved items</div>
    {% endfor %}
</body>
</html>
"""


@app.route('/')
def index():
    """Main status page."""
    token = db.get_token()
    authenticated = token is not None
    
    posts = db.get_recent_posts(limit=5)
    
    return render_template_string(
        INDEX_TEMPLATE,
        time=get_istanbul_time(),
        timezone=config.TZ,
        dry_run=config.DRY_RUN,
        authenticated=authenticated,
        persona={
            'name': config.PERSONA_NAME,
            'age': config.PERSONA_AGE,
            'role': config.PERSONA_ROLE,
        },
        posts=posts
    )


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'time': str(get_istanbul_time()),
        'dry_run': config.DRY_RUN,
    }), 200


@app.route('/login')
def login():
    """Initiate LinkedIn OAuth flow."""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    api = LinkedInAPI()
    auth_url = api.get_authorization_url(state)
    
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """LinkedIn OAuth callback."""
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if state != session.get('oauth_state'):
        return "Invalid state parameter", 400
    
    if not code:
        return "No authorization code provided", 400
    
    # Exchange code for token
    api = LinkedInAPI()
    try:
        api.exchange_code_for_token(code)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error exchanging code for token: {e}", 500


@app.route('/queue')
def queue():
    """Proactive queue management page."""
    pending = db.get_pending_queue_items()
    approved = db.get_approved_queue_items()
    
    return render_template_string(
        QUEUE_TEMPLATE,
        pending=pending,
        approved=approved
    )


@app.route('/enqueue_target', methods=['POST'])
def enqueue_target_route():
    """Enqueue a target for proactive commenting."""
    target_url = request.form.get('target_url', '').strip()
    target_urn = request.form.get('target_urn', '').strip()
    context = request.form.get('context', '').strip()
    
    if not target_url:
        return "Target URL is required", 400
    
    # If URN not provided, try to extract from URL
    if not target_urn and 'ugcPost:' in target_url:
        # Extract URN from URL
        try:
            urn_part = target_url.split('ugcPost:')[1].split('/')[0].split('?')[0]
            target_urn = f"urn:li:ugcPost:{urn_part}"
        except:
            pass
    
    # Use target_url as post content for suggestion (in real scenario, would fetch)
    enqueue_target(target_url, target_urn, context or "Engaging with relevant content")
    
    return redirect(url_for('queue'))


@app.route('/approve/<int:item_id>', methods=['POST'])
def approve_item(item_id):
    """Approve a queue item."""
    db.approve_queue_item(item_id)
    return redirect(url_for('queue'))


@app.route('/reject/<int:item_id>', methods=['POST'])
def reject_item(item_id):
    """Reject a queue item."""
    db.reject_queue_item(item_id)
    return redirect(url_for('queue'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
