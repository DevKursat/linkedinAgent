// ==UserScript==
// @name         LinkedIn - Forward Posted Comment to Local Agent
// @namespace    http://devkursat.local/
// @version      0.1
// @description  When you post a comment on LinkedIn (while logged in), capture it and forward to the local LinkedInAgent /incoming_comment endpoint for automatic replies.
// @author       DevKursat
// @match        https://www.linkedin.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Configuration: change if your agent runs on a different host/port
    const AGENT_ENDPOINT = 'http://localhost:5000/incoming_comment';

    // Helper: try to extract currently logged-in user's person URN from the page
    function getMyPersonUrn() {
        try {
            // LinkedIn profile link includes /in/<slug>/ or data-urn attribute on profile image
            const possible = document.querySelector('a[data-control-name="identity_welcome_message"]') || document.querySelector('a[href*="/in/"]');
            if (possible) {
                const href = possible.getAttribute('href') || '';
                if (href.includes('/in/')) {
                    // We can't reliably get urn:li:person:<id> from DOM without API, return slug as fallback
                    return 'urn:li:person:unknown-' + href.split('/in/')[1].split('/')[0];
                }
            }
        } catch (e) { }
        return 'urn:li:person:unknown';
    }

    // MutationObserver to detect new posted comment nodes in feed or activity views
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const n of m.addedNodes) {
                if (!(n instanceof HTMLElement)) continue;
                // LinkedIn renders posted comment blocks with role="article" or data-test-comment
                if (n.querySelector && (n.querySelector('[data-testid="comment-text"]') || n.querySelector('[data-urn]'))) {
                    // small delay to allow LinkedIn to render values
                    setTimeout(() => processNode(n), 300);
                }
            }
        }
    });

    function processNode(node) {
        try {
            // Find comment text
            let textElem = node.querySelector('[data-testid="comment-text"]') || node.querySelector('.comments-comment-item__main-content');
            if (!textElem) return;
            const text = textElem.innerText.trim();
            if (!text) return;

            // Try to find post URN from ancestor or data attributes
            let cur = node;
            let postUrn = null;
            while (cur && cur !== document.body) {
                if (cur.dataset && cur.dataset.urn) {
                    postUrn = cur.dataset.urn;
                    break;
                }
                // link with /feed/update/.. may contain id
                const link = cur.querySelector('a[href*="/updates/"]') || cur.querySelector('a[href*="/feed/update/"]');
                if (link) {
                    const href = link.getAttribute('href');
                    // Try to detect share id
                    const m = href.match(/share:\/\/|share:|ugcPost:|update\/urn:li:share:(\d+)/);
                    if (m) postUrn = 'urn:li:share:' + (m[1] || 'unknown');
                }
                cur = cur.parentElement;
            }
            if (!postUrn) postUrn = window.location.href;

            // comment id
            const commentId = 'sim-' + Date.now();
            const actor = getMyPersonUrn();

            // Send to agent endpoint
            fetch(AGENT_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_urn: postUrn, comment_id: commentId, actor: actor, text: text })
            }).catch(e => console.warn('Agent forward failed', e));
        } catch (e) {
            console.warn('processNode error', e);
        }
    }

    observer.observe(document.body, { childList: true, subtree: true });

})();
