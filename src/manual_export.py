"""Generate a manual invites HTML export for browser-assisted sending.

This module creates `data/manual_invites.html` containing the pending invites
and simple JS to mark items as sent by calling the app's `/mark-invite-sent` endpoint.
"""
from typing import List, Dict
import os
from pathlib import Path


HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Manual Invites</title>
  <style>body{font-family:Arial,sans-serif;padding:20px} .invite{border:1px solid #ddd;padding:12px;margin:8px 0} .button{padding:8px 12px;background:#0077b5;color:#fff;border:none;border-radius:4px;cursor:pointer}</style>
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body>
<h1>Manual Invites</h1>
<p>This page was exported by linkedinAgent. Use your browser to open each profile and send invites manually. After sending, click "Mark sent" to update the app's database.</p>
<div style="margin-bottom:12px"><button class='button' id='open-all'>Open all profiles (Tampermonkey)</button></div>
{items}
<script>
async function markSent(id, btn){ btn.disabled=true; try{ const res = await fetch('/mark-invite-sent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})}); const j = await res.json(); if(j.ok){ btn.innerText='Marked'; btn.style.background='#28a745'} else { alert('Failed: '+(j.error||'unknown')); btn.disabled=false } } catch(e){ alert('Network error:'+e); btn.disabled=false }}

document.getElementById('open-all') && document.getElementById('open-all').addEventListener('click', function(){
    const links = Array.from(document.querySelectorAll('a.open-tm'));
    if(!links.length){ alert('No profile links found'); return; }
    for(let i=0;i<links.length;i++){
        const href = links[i].href;
        const sep = href.indexOf('?')===-1 ? '?' : '&';
        const url = href + sep + 'tm_send=1&tm_idx='+i+'&tm_from=' + encodeURIComponent(location.href);
        window.open(url, '_blank');
    }
});
</script>
</body>
</html>
"""


def export_manual_invites_html(invites: List[Dict], out_path: str = 'data/manual_invites.html') -> str:
    """Write the manual invites HTML file and return its path.

    invites: list of dicts with keys: id, person_urn, person_name, reason
    """
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    parts = []
    for i in invites:
        name = i.get('person_name') or i.get('person_urn') or 'Unknown'
        urn = i.get('person_urn') or ''
        profile_url = urn if urn.startswith('http') else (f'https://www.linkedin.com/in/{urn.split(":")[-1]}' if urn else '')
        item_html = f"<div class='invite' data-id='{i.get('id')}'><strong>{name}</strong><br/><em>{i.get('reason') or ''}</em><br/>"
        if profile_url:
            # Add class open-tm so 'Open all' can pick this link and add tm params
            item_html += f"<a class='open-tm' href='{profile_url}' target='_blank'>Open profile</a> "
            # Also add a direct 'Open with Tampermonkey' button to open a single profile with params
            sep = '?' if '?' not in profile_url else '&'
            tm_url = f"{profile_url}{sep}tm_send=1&tm_from={os.path.basename(os.getcwd())}"
            item_html += f"<a class='button' style='text-decoration:none;margin-left:6px' href='{tm_url}' target='_blank'>Open (TM)</a> "
        item_html += f"<button class='button' onclick='markSent({i.get('id')}, this)'>Mark sent</button></div>"
        parts.append(item_html)

    full = HTML_TEMPLATE.format(items='\n'.join(parts))
    p = Path(out_path)
    p.write_text(full, encoding='utf-8')
    return str(p.resolve())
