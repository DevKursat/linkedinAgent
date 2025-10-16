"""Flask web application for LinkedIn Agent."""
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash
import secrets
from . import db
from .config import config
from .linkedin_api import LinkedInAPI, get_linkedin_api
from .proactive import enqueue_target as enqueue_target_fn
from .scheduler import get_next_runs, run_now
from .utils import get_istanbul_time
from .proactive import discover_and_enqueue
from .gemini import generate_text
from .generator import generate_refine_post_prompt, generate_invite_message
from .connections import get_suggested_accounts_for_connections
from .diagnostics import doctor as diag_doctor
from .comment_handler import handle_incoming_comment


app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY


# Initialize database on startup
db.init_db()


# HTML Templates (inline for simplicity)
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <title>LinkedIn Ajan - Durum</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #0077b5; }
        .status { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .info { margin: 10px 0; }
        .button { display: inline-block; padding: 10px 20px; background: #0077b5; color: white; 
                  text-decoration: none; border-radius: 5px; margin: 5px; border: none; cursor: pointer; }
        .button:hover { background: #005885; }
        textarea, input[type="text"] { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; font-family: Arial, sans-serif; }
        .checklist { list-style: none; padding-left: 0; }
        .checklist li { margin: 6px 0; padding-left: 4px; }
        .checklist .done { color: #1f7a1f; font-weight: bold; }
    </style>
</head>
<body>
        <h1>LinkedIn Ajan</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="status" style="background: {{ '#ffe0e0' if category=='error' else '#e7ffe7' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    
    <div class="status">
        <h2>Durum</h2>
        <div class="info"><strong>Zaman:</strong> {{ time }}</div>
        <div class="info"><strong>Saat Dilimi:</strong> {{ timezone }}</div>
        <div class="info"><strong>Test Modu:</strong> {{ 'Açık' if dry_run else 'Kapalı (Canlı)' }}</div>
        <div class="info"><strong>LinkedIn Girişi:</strong> {{ 'Yapıldı ✓' if authenticated else 'Yapılmadı' }}</div>
        {% if persona %}
        <div class="info"><strong>Kişilik:</strong> {{ persona.name }}, {{ persona.age }}, {{ persona.role }}</div>
        {% endif %}
        <div class="info"><strong>Zamanlanmış İşler:</strong>
            <ul>
                <li>Günlük paylaşım: {{ next_runs.get('daily_post','-') }}</li>
                <li>Yorum kontrolü: {{ next_runs.get('poll_comments','-') }}</li>
                <li>Proaktif kuyruk: {{ next_runs.get('proactive_queue','-') }}</li>
            </ul>
        </div>
    </div>

    <div class="status">
        <h2>İşlemler</h2>
        {% if not authenticated %}
        <a href="{{ url_for('login') }}" class="button">LinkedIn ile Giriş Yap</a>
        {% else %}
        <a href="{{ url_for('logout') }}" class="button" style="background: #dc3545;">Çıkış Yap</a>
        {% endif %}
        <a href="{{ url_for('health') }}" class="button">Sağlık Kontrolü</a>
        <a href="{{ url_for('diagnostics') }}" class="button">Tanılama</a>
        <a href="{{ url_for('queue') }}" class="button">Proaktif Kuyruk</a>
        <form method="POST" action="{{ url_for('discover') }}" style="display:inline;">
            <button class="button" type="submit">İlgili Gönderileri Bul</button>
        </form>
        <form method="POST" action="{{ url_for('trigger_job') }}" style="display:inline;">
            <input type="hidden" name="job" value="daily_post">
            <button class="button" type="submit">Günlük Paylaşımı Şimdi Yap</button>
        </form>
        <form method="POST" action="{{ url_for('trigger_job') }}" style="display:inline;">
            <input type="hidden" name="job" value="poll_comments">
            <button class="button" type="submit">Yorumları Şimdi Kontrol Et</button>
        </form>
        <form method="POST" action="{{ url_for('trigger_job') }}" style="display:inline;">
            <input type="hidden" name="job" value="proactive_queue">
            <button class="button" type="submit">Proaktif Kuyruğu İşle</button>
        </form>
        <a href="{{ url_for('invites') }}" class="button">Davetler</a>
    </div>
    
    <div class="status">
        <h2>Son Paylaşımlar</h2>
        {% if posts %}
            {% for post in posts %}
            <div class="info">
                <strong>{{ post.posted_at }}</strong><br>
                {{ post.content[:100] }}...
                {% if post.follow_up_posted %}✓ Takip yorumu eklendi{% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div class="info">Henüz paylaşım yok</div>
        {% endif %}
    </div>
        
        <div class="status">
            <h2>Davet İstatistikleri</h2>
            <div id="invite-stats">
                <p>Toplam gönderilen: {{ invite_stats.total_sent }}</p>
                    <form method="POST" action="{{ url_for('send_suggested_invite') }}" style="display:inline; margin-top:8px;">
                        <button class="button" type="submit">Önerilen Kişiye Davet Gönder (Test)</button>
                    </form>
                <p>Onay oranı: {{ invite_stats.acceptance_rate }}%</p>
            </div>
            <h3>Test: Bağlantı Daveti Gönder</h3>
            <form method="POST" action="{{ url_for('send_invite_ui') }}" style="display:inline;">
                <input type="text" name="profile" placeholder="https://www.linkedin.com/in/slug veya urn:li:person:..." style="width:400px;padding:6px;margin-right:6px" required />
                <label style="margin-right:8px"><input type="checkbox" name="force"> Zorla gönder (DRY_RUN yok say)</label>
                <button class="button" type="submit">Bağlantı Daveti Gönder (Test)</button>
            </form>
        </div>

    <div class="status">
        <h2>Manuel Paylaşım</h2>
        <form method="POST" action="{{ url_for('manual_post') }}">
            <textarea name="content" rows="6" placeholder="Gönderi yazın..." required>{{ refined_text or '' }}</textarea>
            <button type="submit" class="button">Paylaş</button>
        </form>
        <form method="POST" action="{{ url_for('refine_post') }}" style="margin-top:10px;">
            <textarea name="draft" rows="3" placeholder="AI ile düzeltmek için taslağınızı buraya yapıştırın..."></textarea>
            <button type="submit" class="button">AI ile Düzenle</button>
        </form>
        <h3>Bir Gönderiye Yorum Yap</h3>
        <form method="POST" action="{{ url_for('manual_comment') }}">
            <input type="text" name="target_urn" placeholder="urn:li:share:..." required>
            <textarea name="comment" rows="3" placeholder="Yorum yazın..." required></textarea>
            <button type="submit" class="button">Yorumu Gönder</button>
        </form>
        <h3>Simüle Gelen Yorum (Webhook testi)</h3>
        <form method="POST" action="{{ url_for('simulate_incoming_comment') }}">
            <input type="text" name="sim_post_urn" placeholder="urn:li:share:..." required>
            <input type="text" name="sim_comment_id" placeholder="comment_id (ör: sim-123)" required>
            <input type="text" name="sim_actor" placeholder="actor urn (ör: urn:li:person:abcdef)" required>
            <textarea name="sim_text" rows="3" placeholder="Gelen yorum metni" required></textarea>
            <label style="display:block; margin-top:6px;"><input type="checkbox" name="sim_reply_as_user"> Kullanıcı gibi yanıtla (ilk tekil şahıs)</label>
            <button type="submit" class="button">Simüle Et ve Yanıtla</button>
        </form>
    </div>
</body>
</html>
"""

QUEUE_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <title>LinkedIn Ajan - Proaktif Kuyruk</title>
    <meta charset="UTF-8">
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
    <h1>Proaktif Kuyruk</h1>
    <a href="{{ url_for('index') }}" class="button">← Geri</a>
    
    <h2>Yeni Hedef Ekle</h2>
    <form method="POST" action="{{ url_for('enqueue_target_route') }}">
        <label>Hedef URL veya URN:</label>
        <input type="text" name="target_url" required placeholder="https://linkedin.com/feed/update/...">
        
        <label>Hedef URN (isteğe bağlı, URL'den çıkarılacak):</label>
        <input type="text" name="target_urn" placeholder="urn:li:share:...">
        
        <label>Bağlam (isteğe bağlı):</label>
        <textarea name="context" rows="3" placeholder="Bu gönderiye neden yorum yapmak istiyorsunuz?"></textarea>
        
        <button type="submit" class="button">Kuyruğa Ekle</button>
    </form>
    
    <h2>Onay Bekleyenler ({{ pending|length }})</h2>
    {% for item in pending %}
    <div class="item">
        <div><strong>URL:</strong> {{ item.target_url }}</div>
        <div><strong>URN:</strong> {{ item.target_urn or 'Yok' }}</div>
        <div><strong>Bağlam:</strong> {{ item.context or 'Yok' }}</div>
        <div><strong>Önerilen Yorum:</strong> {{ item.suggested_comment }}</div>
        <div><strong>Oluşturulma:</strong> {{ item.created_at }}</div>
        <form method="POST" action="{{ url_for('approve_item', item_id=item.id) }}" style="display: inline; padding: 0; margin: 0; background: none;">
            <button type="submit" class="button approve">Onayla</button>
        </form>
        <form method="POST" action="{{ url_for('reject_item', item_id=item.id) }}" style="display: inline; padding: 0; margin: 0; background: none;">
            <button type="submit" class="button reject">Reddet</button>
        </form>
    </div>
    {% else %}
    <div class="item">Bekleyen öğe yok</div>
    {% endfor %}
    
    <h2>Onaylananlar ({{ approved|length }})</h2>
    {% for item in approved %}
    <div class="item">
        <div><strong>URL:</strong> {{ item.target_url }}</div>
        <div><strong>Yorum:</strong> {{ item.suggested_comment }}</div>
        <div><strong>Onaylandı:</strong> {{ item.approved_at }}</div>
        <div>{% if item.posted_at %}<strong>Gönderildi:</strong> {{ item.posted_at }}{% else %}<em>Gönderme bekleniyor...</em>{% endif %}</div>
    </div>
    {% else %}
    <div class="item">Onaylanmış öğe yok</div>
    {% endfor %}
</body>
</html>
"""


INVITES_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
        <meta charset="utf-8">
        <title>Dav etler</title>
        <style>body{font-family:Arial,sans-serif;padding:20px} .invite{border:1px solid #ddd;padding:12px;margin:8px 0} .button{padding:8px 12px;background:#0077b5;color:#fff;border:none;border-radius:4px;cursor:pointer}</style>
        </head>
<body>
<h1>Bekleyen Davetler</h1>
<a href="{{ url_for('index') }}">← Geri</a>
<div style="margin-top:12px; padding:8px; background:#f6f8fa; border-radius:4px">
    <strong>Davet İstatistikleri (30 gün):</strong>
    <div>Toplam gönderilen: {{ invite_stats.total_sent }}</div>
    <div>Onay oranı: {{ invite_stats.acceptance_rate }}%</div>
</div>

<h3>Son Gönderilen Davetler</h3>
{% set recent = db.get_recent_sent_invites(5) %}
{% if recent %}
    <ul>
    {% for r in recent %}
        <li>{{ r.person_name or r.person_urn }} — gönderildi: {{ r.sent_at }}</li>
    {% endfor %}
    </ul>
{% else %}
    <div>Henüz gönderilen davet yok</div>
{% endif %}
{% if invites %}
    {% for i in invites %}
        <div class="invite" data-id="{{ i.id }}">
            <strong>{{ i.person_name or i.person_urn }}</strong><br/>
            <em>{{ i.reason }}</em><br/>
            <form method="POST" action="{{ url_for('send_invite_route', invite_id=i.id) }}" style="display:inline;">
                <button class="button">Sunucudan Gönder</button>
            </form>
            <button class="button" onclick="markSent({{ i.id }}, this)">Mark sent</button>
            <pre>{{ generate_invite_message(i.person_name or '') }}</pre>
        </div>
    {% endfor %}
{% else %}
    <div>Bekleyen davet yok</div>
{% endif %}

<h2>Önerilen Hesaplar</h2>
{% if suggested_accounts %}
    <ul>
    {% for s in suggested_accounts %}
        <li>
            <strong>{{ s.name or (s.urn or 'Profil') }}</strong>
            {% if s.profile_url %}
                — <a href="{{ s.profile_url }}" target="_blank">Profil</a>
            {% endif %}
            {% if s.urn %}
                <form method="POST" action="{{ url_for('send_invite_ui') }}" style="display:inline; margin-left:8px">
                    <input type="hidden" name="profile" value="{{ s.profile_url or s.urn }}" />
                    <button class="button" type="submit">Davet Gönder (Test)</button>
                </form>
            {% endif %}
        </li>
    {% endfor %}
    </ul>
{% else %}
    <div>Önerilen hesap yok</div>
{% endif %}

<script>
async function markSent(id, btn) {
    btn.disabled = true;
    try {
        const res = await fetch('/mark-invite-sent', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id:id}) });
        const j = await res.json();
        if (j.ok) { btn.innerText='Marked'; btn.style.background='#28a745' } else { alert('Failed: '+(j.error||'unknown')); btn.disabled=false }
    } catch (e) { alert('Network error:'+e); btn.disabled=false }
}
</script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main status page."""
    token = db.get_token()
    authenticated = token is not None
    
    posts = db.get_recent_posts(limit=5)
    invite_stats = db.get_invite_stats(days=7)

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
        invite_stats=invite_stats,
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
    flash("Başarıyla çıkış yapıldı", 'success')
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

    return render_template_string(
        INVITES_TEMPLATE,
        invites=items,
        generate_invite_message=generate_invite_message,
        suggested_accounts=suggested,
        invite_stats=invite_stats,
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
