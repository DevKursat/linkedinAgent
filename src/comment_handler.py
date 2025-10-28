"""Handle incoming comments: save, generate reply, post or enqueue retry.

Also includes helpers to analyze and publish article shares (preview + publish)
in a defensive, DRY_RUN-aware manner.
"""
from typing import Optional, List, Dict
import re
from . import db
from .commenter import generate_reply, comment_mentions_person
from .linkedin_api import get_linkedin_api
from .config import config


def handle_incoming_comment(post_urn: str, comment_id: str, actor: str, text: str, reply_as_user: bool = False) -> dict:
    """Process an incoming comment: save it and attempt to reply.

    Returns a dict with result details.
    """
    # Save comment (DB will dedupe)
    try:
        db.save_comment(comment_id, post_urn.split(':')[-1], actor, text)
    except Exception:
        pass

    # Decide whether to reply (basic heuristic: skip bot/self)
    try:
        me = get_linkedin_api().me()
        me_actor = f"urn:li:person:{me['id']}"
        if actor == me_actor:
            return {"status": "skipped_self"}
    except Exception:
        # If me() fails, continue — we may still attempt reply
        pass

    # Generate reply text
    try:
        reply_text = generate_reply(text, actor, reply_as_user=reply_as_user)
    except Exception as e:
        return {"status": "generation_failed", "error": str(e)}

    if config.DRY_RUN:
        # Mark replied in DB to avoid repeated processing in tests
        try:
            db.mark_comment_replied(comment_id, 'dry_run')
        except Exception:
            pass
        return {"status": "dry_run", "reply": reply_text}

    # Attempt to post reply via API
    api = get_linkedin_api()
    try:
        res = api.comment_on_post(post_urn, reply_text, parent_comment_id=comment_id)
        reply_id = res.get('id', '') if isinstance(res, dict) else ''
        try:
            db.mark_comment_replied(comment_id, reply_id)
        except Exception:
            pass
        return {"status": "replied", "reply_id": reply_id, "reply": reply_text}
    except Exception as e:
        # Enqueue failed action for retry
        try:
            payload = f"{post_urn}||{comment_id}||{reply_text}"
            db.enqueue_failed_action('comment', payload, str(e))
        except Exception:
            pass
        return {"status": "post_failed", "error": str(e)}


def _fetch_page_text(url: str) -> str:
    """Try to fetch a page and extract a reasonable amount of visible text (best-effort)."""
    try:
        import requests
        try:
            from bs4 import BeautifulSoup  # optional
        except Exception:
            BeautifulSoup = None
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        try:
            if BeautifulSoup:
                soup = BeautifulSoup(r.text, "html.parser")
                # Remove scripts/styles
                for s in soup(["script", "style", "noscript"]):
                    s.extract()
                texts = soup.find_all(text=True)
                visible_texts = filter(lambda t: t.strip(), texts)
                joined = " ".join(visible_texts)
                # Shorten to reasonably sized chunk
                return re.sub(r"\s+", " ", joined)[:2000]
            else:
                return r.text[:2000]
        except Exception:
            return r.text[:2000]
    except Exception:
        return ""


def _safe_generate_summary(text: str, max_chars: int = 400) -> str:
    """Generate a high-quality Turkish summary.

    Preferred: use `generate_text` (Gemini wrapper) with a Turkish prompt for
    concise summary. If unavailable or fails, try `commenter.generate_summary`.
    Fallback: safe truncation.
    """
    # Try Gemini first for better Turkish output
    try:
        from .gemini import generate_text
        # Persona: Kürşat — kıvrak, yer yer espri, net bir yorum kat. 2-4 cümle, Türkçe.
        prompt = (
            "Sen 'Kürşat' adında bir yorumcusun. Aşağıdaki metni Türkçe olarak, "
            "Kürşat'ın samimi ve hafif esprili üslubuyla, kısa ve yorumlayıcı biçimde özetle. "
            "Özet 2-4 cümle olsun, gerektiğinde bir görüş/cümlenin sonuna kısa bir yorum ilave et. "
            "Karakter sınırı %d içinde kal." % max_chars +
            "\n\nMetin:\n" + (text or "")
        )
        summary = generate_text(prompt, temperature=0.3, max_tokens=300)
        if summary and isinstance(summary, str):
            return summary.strip()[:max_chars]
    except Exception:
        pass

    # Try optional local helper
    try:
        from .commenter import generate_summary  # optional helper
        return generate_summary(text, max_chars=max_chars)
    except Exception:
        txt = re.sub(r"\s+", " ", (text or "").strip())
        return (txt[: max_chars]).rstrip() or ""


def _safe_generate_tags(text: str, title: Optional[str] = None, limit: int = 5) -> List[str]:
    """Try to use commenter.generate_tags if available, else naive keyword extraction from title/text."""
    try:
        from .commenter import generate_tags
        return generate_tags(text, title=title, limit=limit)
    except Exception:
        src = (title or "") + " " + (text or "")
        # naive keywords: pick words longer than 4 chars, uppercase first, uniq
        words = re.findall(r"\b[^\d\W]{5,}\b", src)
        seen = []
        out = []
        for w in words:
            k = w.lower()
            if k not in seen:
                seen.append(k)
                out.append(w.capitalize())
            if len(out) >= limit:
                break
        return out


def prepare_share_preview(url: str, comment_as: str = "Kürşat") -> Dict[str, object]:
    """
    Analyze a URL (news article) and return preview data:
    {title, summary_tr, tags, preview_text}
    This does NOT post anything. Safe for use in UI preview.
    """
    title = ""
    try:
        import requests
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            # try quick title extraction
            m = re.search(r"<title.*?>(.*?)</title>", r.text, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
    except Exception:
        pass

    page_text = _fetch_page_text(url)
    summary = _safe_generate_summary(page_text or title)
    tags = _safe_generate_tags(page_text, title=title)

    preview_text = f"{comment_as} olarak paylaşıyorum:\n\n{summary}\n\n#" + " #".join([t.replace(" ", "") for t in tags])
    return {"url": url, "title": title, "summary_tr": summary, "tags": tags, "preview_text": preview_text}


def publish_share(url: str, comment_as: str = "Kürşat", tags: Optional[List[str]] = None, force: bool = False) -> Dict[str, object]:
    """
    Attempt to share the article on LinkedIn as `comment_as`.
    - If config.DRY_RUN and not force: do not call API; enqueue and return preview.
    - If API call attempted and fails, enqueue failed action for retry and return error.
    Returns dict with {status, message, preview, sent_id?}
    """
    preview = prepare_share_preview(url, comment_as=comment_as)
    if tags:
        preview["tags"] = tags
        preview["preview_text"] = f"{comment_as} olarak paylaşıyorum:\n\n{preview['summary_tr']}\n\n#" + " #".join([t.replace(" ", "") for t in tags])

    if config.DRY_RUN and not force:
        # Best-effort: record planned share in DB to review later
        try:
            if hasattr(db, "enqueue_share"):
                sid = db.enqueue_share(url, preview["preview_text"], comment_as)
            else:
                sid = None
        except Exception:
            sid = None
        return {"status": "dry_run", "message": "preview created, not sent (DRY_RUN)", "preview": preview, "share_id": sid}

    api = get_linkedin_api()
    try:
        # Try common share methods in the wrapper; be defensive
        share_res = {}
        for method in ("share_article", "create_share", "post_article", "share"):
            if hasattr(api, method):
                try:
                    share_res = getattr(api, method)(url=url, text=preview["preview_text"], tags=tags)
                    break
                except TypeError:
                    share_res = getattr(api, method)(url, preview["preview_text"])
                    break

        # mark DB if helper exists
        try:
            if hasattr(db, "mark_share_sent") and share_res:
                db.mark_share_sent(share_res.get("id") if isinstance(share_res, dict) else None, url)
        except Exception:
            pass

        return {"status": "sent", "response": share_res, "preview": preview}
    except Exception as e:
        # enqueue failed action for retry
        try:
            payload = f"{url}||{preview['preview_text']}"
            if hasattr(db, "enqueue_failed_action"):
                db.enqueue_failed_action("share", payload, str(e))
        except Exception:
            pass
        return {"status": "failed", "error": str(e), "preview": preview}
