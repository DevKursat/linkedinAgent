#!/usr/bin/env python3
"""Helper CLI to update, verify and run the app locally."""
import argparse
import os
import subprocess
import sys


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def cmd_update(args):
    # Git pull rebase with stash
    run(["git", "fetch", "--all"])
    run(["git", "stash", "--include-untracked"])  # ignore error if nothing to stash
    run(["git", "pull", "--rebase", "origin", "main"])  # update
    run(["git", "stash", "pop"])  # may fail if nothing to pop


def cmd_doctor(args):
    from src.diagnostics import doctor
    import json
    print(json.dumps(doctor(), indent=2, ensure_ascii=False))


def cmd_test(args):
    sys.exit(run([sys.executable, "test_installation.py"]))


def cmd_docker_up(args):
    run(["docker", "compose", "up", "-d", "--build"])  # local compose


def cmd_restart_worker(args):
    run(["docker", "compose", "restart", "worker"])


def cmd_set_dry_run(args):
    path = ".env"
    if not os.path.exists(path):
        print(".env not found; create it from .env.example")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith("DRY_RUN="):
            out.append(f"DRY_RUN={'true' if args.value else 'false'}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"DRY_RUN={'true' if args.value else 'false'}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("Updated DRY_RUN in .env ->", args.value)


def cmd_run_daily(args):
    from src.scheduler import run_daily_post
    run_daily_post()


def cmd_run_worker(args):
    from src.worker import main as worker_main
    worker_main()


def cmd_simulate_comment(args):
    """Simulate an incoming comment (useful for testing)."""
    from src.comment_handler import handle_incoming_comment
    post_urn = args.post_urn
    comment_id = args.comment_id
    actor = args.actor
    text = args.text
    reply_as_user = args.reply_as_user
    res = handle_incoming_comment(post_urn, comment_id, actor, text, reply_as_user=reply_as_user)
    print(res)


def cmd_list_invites(args):
    from src import db
    items = db.get_pending_invites()
    for i in items:
        print(f"{i['id']}: {i['person_urn']} ({i.get('person_name')}) - {i.get('reason')} - {i.get('created_at')}")


def cmd_send_invite(args):
    from src import db
    from src.linkedin_api import get_linkedin_api
    from src.generator import generate_invite_message
    inv = db.get_pending_invites()
    target = None
    if args.id:
        for i in inv:
            if i['id'] == args.id:
                target = i
                break
    else:
        target = inv[0] if inv else None
    if not target:
        print('No invite found')
        return
    api = get_linkedin_api()
    msg = generate_invite_message(target.get('person_name') or '')
    print('Message preview:', msg)
    # If --force passed or auto-invite enabled, skip confirmation
    from src.config import config
    if not args.force and not config.INVITES_ENABLED:
        ok = input('Send invite? (y/N): ').strip().lower()
        if ok != 'y':
            print('Aborted')
            return
    # Temporarily toggle DRY_RUN
    from src.config import config
    orig = config.DRY_RUN
    config.DRY_RUN = False
    try:
        res = api.send_invite(target['person_urn'], msg)
        print('Invite result:', res)
        db.mark_invite_sent(target['id'])
    except Exception as e:
        print('Invite failed:', e)
        # enqueue failed
        try:
            payload = f"{target['person_urn']}||{target.get('person_name') or ''}||{msg}"
            db.enqueue_failed_action('invite', payload, str(e))
            print('Enqueued failed action')
        except Exception as ee:
            print('Failed to enqueue failed action:', ee)
    finally:
        config.DRY_RUN = orig


def cmd_list_failed(args):
    from src import db
    items = db.get_due_failed_actions(limit=100)
    for i in items:
        print(f"{i['id']}: {i['action_type']} attempts={i['attempts']} next={i.get('next_attempt')} error={i.get('error')}")


def cmd_retry_failed(args):
    from src import db
    from src.scheduler import process_failed_actions
    if args.id:
        print('Retrying single failed action via direct process loop')
        try:
            db.bump_failed_action_next_attempt_now(args.id)
        except Exception as e:
            print('Failed to bump next_attempt:', e)
    process_failed_actions()


def cmd_tail_alerts(args):
    path = 'data/alerts.log'
    if not os.path.exists(path):
        print('No alerts.log found')
        return
    with open(path, 'r', encoding='utf-8') as f:
        for line in f.readlines()[-200:]:
            print(line.strip())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("update").set_defaults(func=cmd_update)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("test").set_defaults(func=cmd_test)
    sub.add_parser("docker-up").set_defaults(func=cmd_docker_up)
    sub.add_parser("restart-worker").set_defaults(func=cmd_restart_worker)
    p = sub.add_parser("set-dry-run")
    p.add_argument("value", type=lambda s: s.lower() in ("1","true","yes","on"))
    p.set_defaults(func=cmd_set_dry_run)
    sub.add_parser("run-daily").set_defaults(func=cmd_run_daily)
    sub.add_parser("run-worker").set_defaults(func=cmd_run_worker)
    p_sim = sub.add_parser("simulate-comment")
    p_sim.add_argument("post_urn")
    p_sim.add_argument("comment_id")
    p_sim.add_argument("actor")
    p_sim.add_argument("text")
    p_sim.add_argument("--reply-as-user", dest='reply_as_user', action='store_true')
    p_sim.set_defaults(func=cmd_simulate_comment)
    sub.add_parser("list-invites").set_defaults(func=cmd_list_invites)
    p = sub.add_parser("send-invite")
    p.add_argument("id", type=int, nargs="?", help="Invite id to send (defaults to first)")
    p.add_argument("--force", action="store_true", help="Don't ask for confirmation")
    p.set_defaults(func=cmd_send_invite)
    sub.add_parser("list-failed").set_defaults(func=cmd_list_failed)
    p2 = sub.add_parser("retry-failed")
    p2.add_argument("id", type=int, nargs="?", help="Failed action id to retry")
    p2.set_defaults(func=cmd_retry_failed)
    sub.add_parser("tail-alerts").set_defaults(func=cmd_tail_alerts)
    p_csv = sub.add_parser("enqueue-invites-csv", help="Bulk enqueue invites from CSV: person_urn,person_name,country,tags")
    p_csv.add_argument("file", help="CSV file path")
    p_csv.set_defaults(func=cmd_enqueue_invites_csv)
    sub.add_parser("check-permissions").set_defaults(func=cmd_check_permissions)
    sub.add_parser("enable-invites").set_defaults(func=cmd_enable_invites)
    p = sub.add_parser("export-invites-html", help="Export pending invites into an HTML page for manual sending")
    p.add_argument("--out", help="Output HTML path", default="data/manual_invites.html")
    p.set_defaults(func=cmd_export_invites_html)
    sub.add_parser("start-invite-campaign").set_defaults(func=cmd_start_invite_campaign)

    args = ap.parse_args()
    if not hasattr(args, "func"):
        ap.print_help()
        return 1
    return args.func(args) or 0


def cmd_check_permissions(args):
    """Run LinkedIn permission probes and print a report."""
    from src.tools.check_linkedin_permissions import main as _main
    _main()


def cmd_enqueue_invites_csv(args):
    """Bulk enqueue invites from CSV file. Columns: person_urn,person_name,country,tags (tags semicolon-separated)"""
    import csv
    from src import db
    path = args.file
    if not os.path.exists(path):
        print('File not found:', path)
        return
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        count = 0
        for row in reader:
            if not row:
                continue
            person_urn = row[0].strip()
            person_name = row[1].strip() if len(row) > 1 else ''
            country = row[2].strip() if len(row) > 2 else ''
            tags = row[3].strip() if len(row) > 3 else ''
            try:
                # Enqueue invite and store country/tags if DB supports columns
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO invites (person_urn, person_name, reason, country, tags) VALUES (?, ?, ?, ?, ?)",
                            (person_urn, person_name, f"bulk_csv", country, tags))
                conn.commit()
                conn.close()
                count += 1
            except Exception as e:
                print('Failed to enqueue row:', row, e)
    print(f'Enqueued {count} invites from {path}')


def cmd_enable_invites(args):
    """Probe LinkedIn permissions and enable invites in .env if probe passes."""
    from src.tools.check_linkedin_permissions import probe_endpoints
    print('Running permission probe...')
    report = probe_endpoints()
    # Simple heuristic: if growth_invitations_v2 or comments_v3_sample returned a 200 or not an access error
    ok = False
    inv_v2 = report.get('growth_invitations_v2')
    comments_probe = report.get('comments_v3_sample')
    def is_ok(entry):
        if not entry:
            return False
        if isinstance(entry, dict) and entry.get('status_code') == 200:
            return True
        return False
    if is_ok(inv_v2) or is_ok(comments_probe):
        ok = True

    if not ok:
        print('Permission probe did not indicate invite permissions are available. Aborting enable.')
        print('Check data/permissions_report.json for details or run `manage.py check-permissions`')
        return

    # Update .env safely
    path = '.env'
    if not os.path.exists(path):
        print('.env not found; cannot enable invites')
        return
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    out = []
    found_enabled = False
    found_dry = False
    for line in lines:
        if line.startswith('INVITES_ENABLED='):
            out.append('INVITES_ENABLED=true')
            found_enabled = True
        elif line.startswith('DRY_RUN='):
            out.append('DRY_RUN=false')
            found_dry = True
        else:
            out.append(line)
    if not found_enabled:
        out.append('INVITES_ENABLED=true')
    if not found_dry:
        out.append('DRY_RUN=false')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print('INVITES_ENABLED=true and DRY_RUN=false written to .env')


def cmd_start_invite_campaign(args):
    """Start a new invites campaign and enable invites in .env."""
    from src import db
    name = 'manual-campaign'
    try:
        days = int(os.getenv('INVITES_CAMPAIGN_DAYS', '7'))
        campaign = db.create_invites_campaign(name, days=days)
    except Exception:
        campaign = db.create_invites_campaign(name, days=7)

    # Update .env to enable invites and disable dry-run
    path = '.env'
    if not os.path.exists(path):
        print('.env not found; cannot enable invites')
        return
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    out = []
    found_enabled = False
    found_dry = False
    for line in lines:
        if line.startswith('INVITES_ENABLED='):
            out.append('INVITES_ENABLED=true')
            found_enabled = True
        elif line.startswith('DRY_RUN='):
            out.append('DRY_RUN=false')
            found_dry = True
        else:
            out.append(line)
    if not found_enabled:
        out.append('INVITES_ENABLED=true')
    if not found_dry:
        out.append('DRY_RUN=false')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print('Started invite campaign and updated .env (INVITES_ENABLED=true, DRY_RUN=false)')


def cmd_export_invites_html(args):
    """Export pending invites into a static HTML file with copy buttons and profile links."""
    from src import db
    from src.generator import generate_invite_message
    out_path = args.out
    items = db.get_pending_invites()
    rows = []
    for i in items:
        urn = i.get('person_urn') or ''
        name = i.get('person_name') or ''
        # Try to create a LinkedIn profile URL from URN if possible
        profile_url = ''
        try:
            if urn.startswith('urn:li:person:'):
                slug = urn.split(':')[-1]
                # if slug looks like an id, still provide a basic profile URL
                profile_url = f'https://www.linkedin.com/in/{slug}'
        except Exception:
            profile_url = ''
        msg = generate_invite_message(name)
        rows.append({'id': i.get('id'), 'urn': urn, 'name': name, 'profile_url': profile_url, 'message': msg})

    html = [
        '<!doctype html>',
        '<html><head><meta charset="utf-8"><title>Manual Invites</title>',
        '<style>body{font-family:Arial,sans-serif;padding:20px} .invite{border:1px solid #ddd;padding:12px;margin:8px 0} button{margin-left:8px}</style>',
        '</head><body>',
        '<h1>Pending Invites</h1>',
        '<p>Click profile to open LinkedIn. Use "Copy message" to copy the personalized invite text and paste it into the LinkedIn invite dialog.</p>',
        '<p><button id="openAll">Open all profiles</button> <button id="stopOpen">Stop</button> Delay <input id="delay" type="number" value="5000" style="width:80px"/> ms</p>',
        '<div id="list">'
    ]
    for r in rows:
        html.append(f"<div class=\"invite\"><strong>{r['name'] or r['urn']}</strong><br/>")
        if r['profile_url']:
            html.append(f"<a class=\"profile-link\" href=\"{r['profile_url']}\" target=\"_blank\">Open profile</a>")
        else:
            html.append(f"<span>No profile link available</span>")
        html.append(f"<button onclick=\"navigator.clipboard.writeText({repr(r['message'])})\">Copy message</button>")
        html.append(f"<pre style=\"white-space:pre-wrap;\">{r['message']}</pre>")
        html.append('</div>')
    html.append('</div>')
    # Add script to open profiles sequentially with configurable delay
    html.append('<script>')
    html.append('(() => {')
    html.append('  let timer = null; let idx = 0;')
    html.append('  function getLinks() { return Array.from(document.querySelectorAll(\"#list a.profile-link[target=\\\"_blank\\\"]\")); }')
    html.append('  function openNext() {')
    html.append('    const links = getLinks();')
    html.append('    if (idx >= links.length) { clearInterval(timer); timer = null; alert("All profiles opened"); return; }')
    html.append('    try { window.open(links[idx].href, "_blank"); } catch (e) { console.error(e); }')
    html.append('    idx++;')
    html.append('  }')
    html.append('  document.getElementById("openAll").addEventListener("click", () => {')
    html.append('    if (timer) return; idx = 0; const d = parseInt(document.getElementById("delay").value) || 5000; openNext(); timer = setInterval(openNext, d);')
    html.append('  });')
    html.append('  document.getElementById("stopOpen").addEventListener("click", () => { if (timer) { clearInterval(timer); timer = null; alert("Stopped"); } });')
    html.append('  // Hint: allow users to click individual links if they prefer manual control')
    html.append('})();')
    html.append('</script>')
    html.append('<p>When done, mark invites as sent via `manage.py send-invite <id> --force` or manually edit the DB.</p>')
    html.append('</body></html>')

    import os
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))
    print('Wrote manual invites page to', out_path)


if __name__ == "__main__":
    raise SystemExit(main())
