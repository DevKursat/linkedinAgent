"""Main Flask application for the LinkedIn Agent web interface."""
from flask import Flask, render_template, jsonify, request, redirect, url_for
from . import db
from .scheduler import get_next_runs, run_now
from .config import config

app = Flask(__name__)

# Configure Flask app from config object
app.config.from_object(config)

@app.route('/')
def index():
    """Main dashboard view."""
    next_runs = get_next_runs()
    pending_actions = db.get_pending_actions_count()
    system_events = db.get_recent_system_events()

    # Format next run times for display
    for job_id, run_time in next_runs.items():
        try:
            # Attempt to parse and format the datetime string
            from datetime import datetime
            dt_obj = datetime.fromisoformat(run_time)
            next_runs[job_id] = dt_obj.strftime('%Y-%m-%d %H:%M:%S %Z')
        except (ValueError, TypeError):
            # Keep the original string if parsing fails
            next_runs[job_id] = str(run_time)

    stats = {
        'posts_today': db.get_posts_count_today(),
        'comments_today': db.get_comments_count_today(),
        'invites_today': db.get_today_invite_count(),
        'pending_invites': db.get_pending_invites_count()
    }

    return render_template(
        'index.html',
        next_runs=next_runs,
        pending_actions=pending_actions,
        events=system_events,
        stats=stats
    )

@app.route('/posts')
def posts():
    """View recent posts and their statuses."""
    recent_posts = db.get_recent_posts(limit=50)
    return render_template('posts.html', posts=recent_posts)

@app.route('/comments')
def comments():
    """View recent comments and their reply statuses."""
    unreplied = db.get_unreplied_comments()
    replied = db.get_replied_comments(limit=50)
    return render_template('comments.html', unreplied=unreplied, replied=replied)

@app.route('/invites')
def invites():
    """Manage connection invitations."""
    pending = db.get_pending_invites()
    sent = db.get_sent_invites(limit=100)
    return render_template('invites.html', pending=pending, sent=sent)

@app.route('/failed_actions')
def failed_actions():
    """View and manage failed background actions."""
    actions = db.get_failed_actions()
    return render_template('failed_actions.html', actions=actions)

@app.route('/config')
def configuration():
    """Display the current agent configuration."""
    # Expose only safe-to-display configuration values
    safe_config = {
        'DRY_RUN': config.DRY_RUN,
        'INVITES_ENABLED': config.INVITES_ENABLED,
        'PROACTIVE_ENABLED': config.PROACTIVE_ENABLED,
        'MODERATION_LEVEL': config.MODERATION_LEVEL,
        'INTERESTS': config.INTERESTS,
        'LINKEDIN_TARGET_PROFILES': config.LINKEDIN_TARGET_PROFILES,
        'CUSTOM_RSS_FEEDS': config.CUSTOM_RSS_FEEDS,
        'TZ': config.TZ
    }
    return render_template('config.html', config=safe_config)

@app.route('/api/run_job', methods=['POST'])
def run_job_now():
    """API endpoint to manually trigger a job."""
    data = request.json
    job_name = data.get('job_name')
    if not job_name:
        return jsonify({'status': 'error', 'message': 'Job name is required.'}), 400

    try:
        run_now(job_name)
        return jsonify({'status': 'success', 'message': f"Job '{job_name}' triggered."})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/retry_action', methods=['POST'])
def retry_failed_action():
    """API endpoint to retry a failed action."""
    data = request.json
    action_id = data.get('id')
    # Logic to retry the action would go here
    # For now, we'll just remove it as a placeholder
    db.delete_failed_action(action_id)
    return jsonify({'status': 'success'})

@app.route('/api/delete_action', methods=['POST'])
def delete_failed_action():
    """API endpoint to delete a failed action."""
    data = request.json
    action_id = data.get('id')
    db.delete_failed_action(action_id)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # This is for local development running `python -m src.app`
    # In production, a WSGI server like Gunicorn should be used.
    app.run(host='0.0.0.0', port=5000)
