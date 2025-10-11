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
        <h2>Yapılacaklar ({{ checklist_done }}/{{ checklist_total }})</h2>
        <ul class="checklist">
        {% for item in checklist %}
            <li class="{{ 'done' if item.done else '' }}">{{ '✓' if item.done else '•' }} {{ item.label }}</li>
        {% endfor %}
        </ul>
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


def build_checklist_context():
    """Return checklist entries highlighting completed hardening tasks."""
    checklist = [
        {"label": "Gemini artık tam uzunlukta yazıyor", "done": True},
        {"label": "Takip yorumları 66 sn içinde kesinleşiyor", "done": True},
        {"label": "LinkedIn REST sürüm fallback zinciri aktif", "done": True},
        {"label": "Proaktif kuyrukta boş taslak kalmıyor", "done": True},
    ]
    completed = sum(1 for item in checklist if item["done"])
    return checklist, completed, len(checklist)


@app.route('/')
def index():
    """Main status page."""
    token = db.get_token()
    authenticated = token is not None
    
    posts = db.get_recent_posts(limit=5)
    checklist, checklist_done, checklist_total = build_checklist_context()
    
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
        checklist=checklist,
        checklist_done=checklist_done,
        checklist_total=checklist_total,
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
        checklist, checklist_done, checklist_total = build_checklist_context()
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
            checklist=checklist,
            checklist_done=checklist_done,
            checklist_total=checklist_total,
        )
    except Exception as e:
        flash(f"Taslak düzenleme hatası: {e}", 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
