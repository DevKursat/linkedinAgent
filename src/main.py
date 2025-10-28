"""Flask web application for LinkedIn Agent."""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import secrets
import os
from . import db
from .config import config
from .linkedin_api import LinkedInAPI, get_linkedin_api
from .proactive import enqueue_target as enqueue_target_fn
from .scheduler import get_next_runs, run_now
from .utils import get_istanbul_time
from .proactive import discover_and_enqueue
from .gemini import generate_text
from .generator import generate_refine_post_prompt, generate_invite_message
from .manual_export import export_manual_invites_html
from .connections import get_suggested_accounts_for_connections
from .diagnostics import doctor as diag_doctor
from .comment_handler import handle_incoming_comment


app = Flask(__name__, template_folder='templates')
app.secret_key = config.FLASK_SECRET_KEY


# Initialize database on startup
db.init_db()


@app.route('/')
def index():
    """Main status page."""
    token = db.get_token()
    authenticated = token is not None
    
    posts = db.get_recent_posts(limit=5)
    invite_stats = db.get_invite_stats(days=7)
    events = db.get_recent_system_events(limit=10)

    return render_template(
        "index.html",
        title="Ana Panel",
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
        invite_stats=invite_stats,
        events=events,
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
    if state != session.get('oauth_state'):
        return "Invalid state parameter", 400
    if not code:
        return "No authorization code provided", 400
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
    flash("Başarıyla çıkış yapıldı", 'success')
    return redirect(url_for('index'))


@app.route('/queue')
def queue():
    """Proactive queue management page."""
    pending = db.get_pending_queue_items()
    approved = db.get_approved_queue_items()
    return render_template(
        "queue.html",
        title="Proaktif Kuyruk",
        time=get_istanbul_time(),
        dry_run=config.DRY_RUN,
        authenticated=db.get_token() is not None,
        persona={'name': config.PERSONA_NAME, 'age': config.PERSONA_AGE, 'role': config.PERSONA_ROLE},
        pending=pending,
        approved=approved
    )


@app.route('/invites')
def invites():
    """Invites management page."""
    items = db.get_pending_invites()
    suggested = get_suggested_accounts_for_connections(limit=8)
    invite_stats = db.get_invite_stats(days=30)
    recent = db.get_recent_sent_invites(5)
    return render_template(
        "invites.html",
        title="Davetler",
        time=get_istanbul_time(),
        dry_run=config.DRY_RUN,
        authenticated=db.get_token() is not None,
        persona={'name': config.PERSONA_NAME, 'age': config.PERSONA_AGE, 'role': config.PERSONA_ROLE},
        invites=items,
        generate_invite_message=generate_invite_message,
        suggested_accounts=suggested,
        invite_stats=invite_stats,
        recent=recent,
    )

@app.route('/manual_post', methods=['POST'])
def manual_post():
    content = request.form.get('content', '').strip()
    if not content:
        flash("Gönderi içeriği gerekli", 'error')
        return redirect(url_for('index'))

    if config.DRY_RUN:
        flash("[TEST MODU] Gönderi kabul edildi (gerçek paylaşım yapılmadı)", 'success')
        return redirect(url_for('index'))

    try:
        api = get_linkedin_api()
        res = api.post_ugc(content)
        post_id = res.get('id', '')
        post_urn = res.get('urn', '')
        if not (post_id or post_urn):
            raise RuntimeError("LinkedIn API response missing id/urn")
        db.save_post(post_id, post_urn, content, None)
        api.like_post(post_urn)
        flash("Gönderi başarıyla paylaşıldı", 'success')
    except Exception as e:
        flash(f"Paylaşım hatası: {e}", 'error')

    return redirect(url_for('index'))

@app.route('/refine_post', methods=['POST'])
def refine_post():
    draft = request.form.get('draft', '').strip()
    if not draft:
        flash("Lütfen düzenlemek için bir taslak yapıştırın", 'error')
        return redirect(url_for('index'))
    try:
        prompt = generate_refine_post_prompt(draft, language='English')
        refined = generate_text(prompt, temperature=0.6, max_tokens=400)
        flash("Taslak düzenlendi. İnceleyip paylaşabilirsiniz.", 'success')

        # Re-render index with the refined text
        token = db.get_token()
        posts = db.get_recent_posts(limit=5)
        invite_stats = db.get_invite_stats(days=7)
        events = db.get_recent_system_events(limit=10)

        return render_template(
            "index.html",
            title="Ana Panel",
            time=get_istanbul_time(),
            timezone=config.TZ,
            dry_run=config.DRY_RUN,
            authenticated=token is not None,
            persona={'name': config.PERSONA_NAME, 'age': config.PERSONA_AGE, 'role': config.PERSONA_ROLE},
            posts=posts,
            next_runs=get_next_runs(),
            invite_stats=invite_stats,
            events=events,
            refined_text=refined,
        )
    except Exception as e:
        flash(f"Taslak düzenleme hatası: {e}", 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
