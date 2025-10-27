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


@app.route('/debug/last-invite-error')
def debug_last_invite_error():
    """Return last lines from alerts.log or a helpful message for invite errors."""
    log_dir = os.path.dirname(db.get_connection().__dict__.get('database', config.DB_PATH)) if hasattr(db, 'get_connection') else os.path.dirname(config.DB_PATH)
    alerts = os.path.join(log_dir, 'alerts.log')
    try:
        if os.path.exists(alerts):
            with open(alerts, 'r', encoding='utf-8') as f:
                lines = f.read().strip().splitlines()
            tail = lines[-20:]
            return jsonify({'ok': True, 'alerts_tail': tail}), 200
        else:
            return jsonify({'ok': False, 'error': 'alerts.log not found', 'path': alerts}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


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
        persona={
            'name': config.PERSONA_NAME,
            'age': config.PERSONA_AGE,
            'role': config.PERSONA_ROLE,
        },
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
        flash("Hedef URL gerekli", 'error')
        return redirect(url_for('queue'))
    
    # If URN not provided, try to extract from URL
    if not target_urn:
        # Try multiple patterns
        if 'ugcPost:' in target_url:
            try:
                urn_part = target_url.split('ugcPost:')[1].split('/')[0].split('?')[0]
                target_urn = f"urn:li:ugcPost:{urn_part}"
            except:
                pass
        elif 'share:' in target_url:
            try:
                urn_part = target_url.split('share:')[1].split('/')[0].split('?')[0]
                target_urn = f"urn:li:share:{urn_part}"
            except:
                pass
    
    try:
        # Use target_url as post content for suggestion (in real scenario, would fetch)
        enqueue_target_fn(target_url, target_urn, context or "İlgili içerikle etkileşim")
        flash("Hedef kuyruğa eklendi", 'success')
    except Exception as e:
        flash(f"Kuyruğa ekleme hatası: {e}", 'error')
    
    return redirect(url_for('queue'))


@app.route('/discover', methods=['POST'])
def discover():
    """Discover relevant posts by interests and enqueue suggestions."""
    try:
        discover_and_enqueue(limit=3)
        flash("İlgili gönderiler bulundu ve kuyruğa eklendi", 'success')
        return redirect(url_for('queue'))
    except Exception as e:
        flash(f"Keşif hatası: {e}", 'error')
        return redirect(url_for('queue'))

@app.route('/diagnostics')
def diagnostics():
    """Return environment and auth diagnostics as JSON."""
    return jsonify(diag_doctor()), 200

@app.route('/approve/<int:item_id>', methods=['POST'])
def approve_item(item_id):
    """Approve a queue item."""
    try:
        db.approve_queue_item(item_id)
        flash("Öğe onaylandı", 'success')
    except Exception as e:
        flash(f"Onaylama hatası: {e}", 'error')
    return redirect(url_for('queue'))


@app.route('/invites')
def invites():
    try:
        items = db.get_pending_invites()
    except Exception:
        items = []
    # Fetch suggested accounts defensively
    try:
        suggested = get_suggested_accounts_for_connections(limit=8)
    except Exception:
        suggested = []
    # Fetch invite statistics (defensive)
    try:
        invite_stats = db.get_invite_stats(days=30)
    except Exception:
        invite_stats = {'total_sent': 0, 'accepted': 0, 'rejected': 0, 'acceptance_rate': 0.0}
    try:
        recent = db.get_recent_sent_invites(5)
    except Exception:
        recent = []

    return render_template(
        "invites.html",
        title="Davetler",
        time=get_istanbul_time(),
        dry_run=config.DRY_RUN,
        authenticated=db.get_token() is not None,
        persona={
            'name': config.PERSONA_NAME,
            'age': config.PERSONA_AGE,
            'role': config.PERSONA_ROLE,
        },
        invites=items,
        generate_invite_message=generate_invite_message,
        suggested_accounts=suggested,
        invite_stats=invite_stats,
        recent=recent,
    )


@app.route('/send-invite/<int:invite_id>', methods=['POST'])
def send_invite_route(invite_id):
    try:
        items = db.get_pending_invites()
        target = next((i for i in items if i['id'] == invite_id), None)
        if not target:
            flash('Invite not found', 'error')
            return redirect(url_for('invites'))
        api = get_linkedin_api()
        msg = generate_invite_message(target.get('person_name') or '')
        res = api.send_invite(target['person_urn'], msg)
        db.mark_invite_sent(invite_id)
        flash('Invite sent (server): ' + str(res), 'success')
    except Exception as e:
        # On failure, create a manual export so operator can send invites via browser
        try:
            path = export_manual_invites_html(db.get_pending_invites())
            flash('Invite send error: ' + str(e) + f" — manual export created: {path}", 'error')
        except Exception:
            flash('Invite send error: ' + str(e), 'error')
    return redirect(url_for('invites'))


@app.route('/reject/<int:item_id>', methods=['POST'])
def reject_item(item_id):
    """Reject a queue item."""
    try:
        db.reject_queue_item(item_id)
        flash("Öğe reddedildi", 'success')
    except Exception as e:
        flash(f"Reddetme hatası: {e}", 'error')
    return redirect(url_for('queue'))


@app.route('/trigger', methods=['POST'])
def trigger_job():
    """Trigger a scheduled job immediately."""
    job = request.form.get('job', '')
    try:
        run_now(job)
        flash(f"İş tetiklendi: {job}", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"İş tetiklenirken hata: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/start-invite-campaign', methods=['POST'])
def start_invite_campaign():
    try:
        # Create a campaign with configured days
        campaign = db.create_invites_campaign('7-day-campaign', days=int(config.INVITES_CAMPAIGN_DAYS))
        # Enable invites and persist in .env via manage command or operator
        flash('Davet kampanyası başlatıldı: ' + str(campaign.get('id')), 'success')
    except Exception as e:
        flash('Kampanya başlatma hatası: ' + str(e), 'error')
    return redirect(url_for('index'))


@app.route('/send-invite-ui', methods=['POST'])
def send_invite_ui():
    profile = request.form.get('profile', '').strip()
    force = bool(request.form.get('force'))
    if not profile:
        flash('Profil URL/URN gerekli', 'error')
        return redirect(url_for('index'))

    # normalize into person_urn if possible
    person_urn = profile
    if profile.startswith('https://www.linkedin.com/in/') or profile.startswith('http://www.linkedin.com/in/'):
        person_urn = 'urn:li:person:' + profile.rstrip('/').split('/')[-1]

    try:
        # enqueue for tracking
        db.enqueue_invite(person_urn, person_name=person_urn, reason='ui-test')
    except Exception:
        pass

    # If force, attempt immediate send (skip DRY_RUN)
    send_result = None
    if force:
        try:
            api = get_linkedin_api()
            msg = generate_invite_message('')
            res = api.send_invite(person_urn, msg)
            send_result = res
        except Exception as e:
            # On failure, export manual invites and notify
            try:
                path = export_manual_invites_html(db.get_pending_invites())
                flash('Sunucu davet denemesi hata: ' + str(e) + f" — manual export: {path}", 'error')
            except Exception:
                flash('Sunucu davet denemesi hata: ' + str(e), 'error')
            return redirect(url_for('index'))

    # Show the invited profile URL so user can verify
    flash('Davet hedefi: ' + person_urn + ((' — sunucu cevabı: ' + str(send_result)) if send_result else ''), 'success')
    return redirect(url_for('index'))


@app.route('/send-suggested-invite', methods=['POST'])
def send_suggested_invite():
    try:
        pending = db.get_pending_invites()
        if not pending:
            flash('Gönderilecek önerilen davet yok', 'error')
            return redirect(url_for('index'))
        target = pending[0]
        person_urn = target.get('person_urn')
        # Try sending (respect DRY_RUN)
        if config.DRY_RUN:
            db.mark_invite_sent(target['id'])
            flash('DRY_RUN: Davet işaretlendi (test) -> ' + (person_urn or ''), 'success')
            return redirect(url_for('index'))
        api = get_linkedin_api()
        msg = generate_invite_message(target.get('person_name') or '')
        res = api.send_invite(person_urn, msg)
        db.mark_invite_sent(target['id'])
        flash('Davet gönderildi: ' + (person_urn or '') + ' — API cevap: ' + str(res), 'success')
    except Exception as e:
        flash('Davet gönderme hatası: ' + str(e), 'error')
    return redirect(url_for('index'))


@app.route('/test-full-flow', methods=['POST'])
def test_full_flow():
    """Trigger a full share -> like -> comment -> reply flow for a sample article.

    This uses DRY_RUN logic: if DRY_RUN is true, actions are recorded but not sent.
    """
    sample_url = request.form.get('sample_url', 'https://example.com')
    # 1) Publish share (Kürşat style)
    try:
        from .comment_handler import publish_share
        res = publish_share(sample_url, comment_as='Kürşat')
    except Exception as e:
        flash('Paylaşım testi hatası: ' + str(e), 'error')
        return redirect(url_for('index'))

    # 2) If posted, attempt to like and then comment
    try:
        if res.get('status') == 'sent' and not config.DRY_RUN:
            post_urn = None
            if isinstance(res.get('response'), dict):
                post_urn = res['response'].get('urn') or res['response'].get('id')
            # like
            if post_urn:
                api = get_linkedin_api()
                try:
                    api.like_post(post_urn)
                except Exception:
                    pass
                # comment
                try:
                    api = get_linkedin_api()
                    api.comment_on_post(post_urn, 'Güzel haber, teşekkürler! — Kürşat')
                except Exception:
                    pass

    except Exception:
        pass

    flash('Full flow test tetiklendi. Sonuç: ' + str(res.get('status')), 'success')
    return redirect(url_for('index'))


@app.route('/mark-invite-sent', methods=['POST'])
def mark_invite_sent_route():
    """Mark an invite as sent via AJAX from the manual invites page."""
    try:
        data = request.get_json() or {}
        invite_id = int(data.get('id'))
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid payload'}), 400
    try:
        from . import db as _db
        _db.mark_invite_sent(invite_id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/manual_post', methods=['POST'])
def manual_post():
    """Manually share a post immediately."""
    content = request.form.get('content', '').strip()
    if not content:
        flash("Gönderi içeriği gerekli", 'error')
        return redirect(url_for('index'))
    if config.DRY_RUN:
        print("[DRY_RUN] Manual post:", content[:200])
        flash("[TEST MODU] Gönderi kabul edildi (gerçek paylaşım yapılmadı)", 'success')
        return redirect(url_for('index'))
    try:
        api = LinkedInAPI()
        res = api.post_ugc(content)
        post_id = res.get('id', '')
        post_urn = res.get('urn', '')
        if not post_id and not post_urn:
            raise RuntimeError("LinkedIn API gönderi id/urn döndürmedi")
        db.save_post(post_id, post_urn, content, None)
        try:
            api.like_post(post_urn)
        except Exception as like_err:
            print(f"[WARN] Gönderiyi beğenemedi: {like_err}")
        flash("Gönderi başarıyla paylaşıldı", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Paylaşım hatası: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/manual_comment', methods=['POST'])
def manual_comment():
    """Manually add a comment to a given URN."""
    target_urn = request.form.get('target_urn', '').strip()
    comment = request.form.get('comment', '').strip()
    if not target_urn or not comment:
        flash("Hedef URN ve yorum gerekli", 'error')
        return redirect(url_for('index'))
    if config.DRY_RUN:
        print(f"[DRY_RUN] Manual comment to {target_urn}:", comment[:200])
        flash("[TEST MODU] Yorum kabul edildi (gerçek yorum gönderilmedi)", 'success')
        return redirect(url_for('index'))
    try:
        api = LinkedInAPI()
        api.comment_on_post(target_urn, comment)
        flash("Yorum başarıyla gönderildi", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Yorum gönderme hatası: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/refine_post', methods=['POST'])
def refine_post():
    """Use Gemini to refine the user's draft and prefill the manual post textarea."""
    draft = request.form.get('draft', '').strip()
    if not draft:
        flash("Lütfen düzenlemek için bir taslak yapıştırın", 'error')
        return redirect(url_for('index'))
    try:
        prompt = generate_refine_post_prompt(draft, language='English')
        refined = generate_text(prompt, temperature=0.6, max_tokens=400)
        flash("Taslak düzenlendi. İnceleyip paylaşabilirsiniz.", 'success')
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
        flash(f"Taslak düzenleme hatası: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/incoming_comment', methods=['POST'])
def incoming_comment():
    """Endpoint to receive an incoming comment (for webhook or manual tests).
    Expected JSON: {post_urn, comment_id, actor, text, reply_as_user (optional)}
    """
    payload = request.get_json(silent=True) or {}
    post_urn = payload.get('post_urn') or request.form.get('post_urn')
    comment_id = payload.get('comment_id') or request.form.get('comment_id')
    actor = payload.get('actor') or request.form.get('actor')
    text = payload.get('text') or request.form.get('text')
    reply_as_user = bool(payload.get('reply_as_user') or request.form.get('reply_as_user'))

    if not post_urn or not comment_id or not actor or not text:
        return jsonify({'error': 'post_urn, comment_id, actor and text required'}), 400

    try:
        res = handle_incoming_comment(post_urn, comment_id, actor, text, reply_as_user=reply_as_user)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/simulate_incoming_comment', methods=['POST'])
def simulate_incoming_comment():
    """UI route to simulate an incoming comment (calls handle_incoming_comment).
    Form fields: sim_post_urn, sim_comment_id, sim_actor, sim_text, sim_reply_as_user
    """
    post_urn = request.form.get('sim_post_urn', '').strip()
    comment_id = request.form.get('sim_comment_id', '').strip()
    actor = request.form.get('sim_actor', '').strip()
    text = request.form.get('sim_text', '').strip()
    reply_as_user = bool(request.form.get('sim_reply_as_user'))

    if not post_urn or not comment_id or not actor or not text:
        flash('Simülasyon için tüm alanlar gerekli', 'error')
        return redirect(url_for('index'))

    try:
        res = handle_incoming_comment(post_urn, comment_id, actor, text, reply_as_user=reply_as_user)
        if res.get('status') == 'dry_run':
            flash('[TEST MODU] Simüle yanıt hazır: ' + (res.get('reply') or '')[:200], 'success')
        elif res.get('status') == 'replied':
            flash('Yorum başarıyla yanıtlandı (ID: ' + (res.get('reply_id') or '') + ')', 'success')
        elif res.get('status') == 'skipped_self':
            flash('Kendi yorumunuz için atlandı', 'info')
        else:
            flash('Simülasyon sonucu: ' + str(res), 'info')
    except Exception as e:
        flash('Simülasyon sırasında hata: ' + str(e), 'error')

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
