"""Flask web application for LinkedIn Agent."""
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash
import secrets
from . import db
from .config import config
from .linkedin_api import LinkedInAPI
from .proactive import enqueue_target as enqueue_target_fn
from .scheduler import get_next_runs, run_now
from .utils import get_istanbul_time
from .proactive import discover_and_enqueue
from .gemini import generate_text
from .generator import generate_refine_post_prompt
from .diagnostics import doctor as diag_doctor


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
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="status" style="background: {{ '#ffe0e0' if category=='error' else '#e7ffe7' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    
    <div class="status">
        <h2>Status</h2>
        <div class="info"><strong>Time:</strong> {{ time }}</div>
        <div class="info"><strong>Timezone:</strong> {{ timezone }}</div>
        <div class=\"info\"><strong>DRY_RUN:</strong> {{ dry_run }}</div>
        <div class="info"><strong>Authenticated:</strong> {{ authenticated }}</div>
        {% if persona %}
        <div class="info"><strong>Persona:</strong> {{ persona.name }}, {{ persona.age }}, {{ persona.role }}</div>
        {% endif %}
        <div class=\"info\"><strong>Next runs:</strong>
            <ul>
                <li>Daily post: {{ next_runs.get('daily_post','-') }}</li>
                <li>Comments poll: {{ next_runs.get('poll_comments','-') }}</li>
                <li>Proactive queue: {{ next_runs.get('proactive_queue','-') }}</li>
            </ul>
        </div>
    </div>
    
    <div class="status">
        <h2>Actions</h2>
        {% if not authenticated %}
        <a href="{{ url_for('login') }}" class="button">Login with LinkedIn</a>
        {% else %}
        <a href="{{ url_for('logout') }}" class="button" style="background: #dc3545;">Logout</a>
        {% endif %}
        <a href="{{ url_for('health') }}" class="button">Health Check</a>
    <a href="{{ url_for('diagnostics') }}" class="button">Diagnostics</a>
        <a href="{{ url_for('queue') }}" class="button">Proactive Queue</a>
        <form method="POST" action="{{ url_for('discover') }}" style="display:inline;">
            <button class="button" type="submit">Discover Relevant Posts</button>
        </form>
        <form method=\"POST\" action=\"{{ url_for('trigger_job') }}\" style=\"display:inline;\">
            <input type=\"hidden\" name=\"job\" value=\"daily_post\">
            <button class=\"button\" type=\"submit\">Run Daily Post Now</button>
        </form>
        <form method=\"POST\" action=\"{{ url_for('trigger_job') }}\" style=\"display:inline;\">
            <input type=\"hidden\" name=\"job\" value=\"poll_comments\">
            <button class=\"button\" type=\"submit\">Poll Comments Now</button>
        </form>
        <form method=\"POST\" action=\"{{ url_for('trigger_job') }}\" style=\"display:inline;\">
            <input type=\"hidden\" name=\"job\" value=\"proactive_queue\">
            <button class=\"button\" type=\"submit\">Process Proactive Now</button>
        </form>
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

    <div class=\"status\">
        <h2>Manual Share</h2>
        <form method=\"POST\" action=\"{{ url_for('manual_post') }}\">
            <textarea name=\"content\" rows=\"6\" placeholder=\"Write a post...\" required>{{ refined_text or '' }}</textarea>
            <button type=\"submit\" class=\"button\">Share Post</button>
        </form>
        <form method=\"POST\" action=\"{{ url_for('refine_post') }}\" style=\"margin-top:10px;\">
            <textarea name=\"draft\" rows=\"3\" placeholder=\"Paste your draft here to refine...\"></textarea>
            <button type=\"submit\" class=\"button\">Refine with AI</button>
        </form>
        <h3>Comment on a Post</h3>
        <form method=\"POST\" action=\"{{ url_for('manual_comment') }}\">
            <input type=\"text\" name=\"target_urn\" placeholder=\"urn:li:ugcPost:...\" required>
            <textarea name=\"comment\" rows=\"3\" placeholder=\"Write a comment...\" required></textarea>
            <button type=\"submit\" class=\"button\">Send Comment</button>
        </form>
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
        posts=posts,
        next_runs=get_next_runs(),
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


@app.route('/logout')
def logout():
    """Logout: delete token and clear session."""
    db.delete_token()
    session.clear()
    flash("Logged out successfully", 'success')
    return redirect(url_for('index'))


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
    enqueue_target_fn(target_url, target_urn, context or "Engaging with relevant content")
    
    return redirect(url_for('queue'))


@app.route('/discover', methods=['POST'])
def discover():
    """Discover relevant posts by interests and enqueue suggestions."""
    try:
        discover_and_enqueue(limit=3)
        return redirect(url_for('queue'))
    except Exception as e:
        return f"Error during discovery: {e}", 400

@app.route('/diagnostics')
def diagnostics():
    """Return environment and auth diagnostics as JSON."""
    return jsonify(diag_doctor()), 200

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


@app.route('/trigger', methods=['POST'])
def trigger_job():
    """Trigger a scheduled job immediately."""
    job = request.form.get('job', '')
    try:
        run_now(job)
        flash(f"Triggered job: {job}", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error triggering job: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/manual_post', methods=['POST'])
def manual_post():
    """Manually share a post immediately."""
    content = request.form.get('content', '').strip()
    if not content:
        flash("Post content required", 'error')
        return redirect(url_for('index'))
    if config.DRY_RUN:
        print("[DRY_RUN] Manual post:", content[:200])
        flash("[DRY_RUN] Manual post accepted (no real post sent)", 'success')
        return redirect(url_for('index'))
    try:
        api = LinkedInAPI()
        res = api.post_ugc(content)
        post_id = res.get('id', '')
        post_urn = res.get('urn', '')
        if not post_id and not post_urn:
            raise RuntimeError("LinkedIn API did not return a post id/urn")
        db.save_post(post_id, post_urn, content, None)
        flash("Post shared successfully", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error posting: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/manual_comment', methods=['POST'])
def manual_comment():
    """Manually add a comment to a given URN."""
    target_urn = request.form.get('target_urn', '').strip()
    comment = request.form.get('comment', '').strip()
    if not target_urn or not comment:
        flash("target_urn and comment required", 'error')
        return redirect(url_for('index'))
    if config.DRY_RUN:
        print(f"[DRY_RUN] Manual comment to {target_urn}:", comment[:200])
        flash("[DRY_RUN] Comment accepted (no real comment sent)", 'success')
        return redirect(url_for('index'))
    try:
        api = LinkedInAPI()
        api.comment_on_post(target_urn, comment)
        flash("Comment sent successfully", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error commenting: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/refine_post', methods=['POST'])
def refine_post():
    """Use Gemini to refine the user's draft and prefill the manual post textarea."""
    draft = request.form.get('draft', '').strip()
    if not draft:
        flash("Please paste a draft to refine", 'error')
        return redirect(url_for('index'))
    try:
        prompt = generate_refine_post_prompt(draft, language='English')
        refined = generate_text(prompt, temperature=0.6, max_tokens=400)
        flash("Draft refined. You can review and post.", 'success')
        # Re-render index with refined_text filled
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
            posts=posts,
            next_runs=get_next_runs(),
            refined_text=refined,
        )
    except Exception as e:
        flash(f"Error refining draft: {e}", 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
