// ==UserScript==
// @name         LinkedIn Auto Connect (with limits)
// @namespace    https://github.com/DevKursat/linkedinAgent
// @version      0.2
// @description  Auto-click LinkedIn "Connect" on profile pages with human-like delays and hourly limits. Use at your own risk.
// @author       DevKursat
// @match        https://www.linkedin.com/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // ---------- CONFIG (edit in this file) ----------
    const CFG = {
        // Conservative defaults to minimize LinkedIn flags
    INVITES_PER_HOUR: 1,       // max invites per hour (conservative)
        INVITES_HOUR_START: 7,     // start hour (local) inclusive
        INVITES_HOUR_END: 21,      // end hour (local) inclusive
        // Ramp-up: in the first N days after first run, use DAILY_START_CAP, then increase to MAX_PER_DAY
    RAMP_UP_DAYS: 7,
    DAILY_START_CAP: 5,        // starting daily cap during ramp-up (very conservative)
    MAX_PER_DAY: 10,           // steady-state daily cap (conservative)
        AUTO_CLOSE_TAB: true,      // close tab after sending invite (if opened by manual_invites.html)
        MIN_DELAY_MS: 5000,        // minimum delay before click (ms)
        MAX_DELAY_MS: 15000,       // maximum delay before click (ms)
        JITTER_MS: 2500,           // additional jitter
        // If blocked message detected, stop automation
        BLOCK_KEYWORDS: ['limit', 'suspend', 'temporarily', "You've reached", 'reach the limit', 'cannot send', 'çok fazla'],
    };

    // ---------- utils ----------
    function nowISO(){ return new Date().toISOString(); }
    function hourNow(){ return new Date().getHours(); }
    function randomBetween(a,b){ return Math.floor(Math.random()*(b-a))+a; }

    // Counters stored in localStorage via GM_* or fallback
    const STORE_KEY = 'la_invite_events';

    function getEvents(){
        try{
            const raw = GM_getValue ? GM_getValue(STORE_KEY, '[]') : localStorage.getItem(STORE_KEY) || '[]';
            return JSON.parse(raw || '[]');
        }catch(e){ return []; }
    }
    function saveEvents(ev){
        try{
            const s = JSON.stringify(ev || []);
            if(GM_setValue) GM_setValue(STORE_KEY, s); else localStorage.setItem(STORE_KEY, s);
        }catch(e){ /* ignore */ }
    }
    function pruneEvents(){
        const ev = getEvents();
        const now = Date.now();
        // keep last 48 hours only
        const filtered = ev.filter(t=> (now - new Date(t).getTime()) < (48*3600*1000));
        saveEvents(filtered);
        return filtered;
    }
    function countLastHour(){
        const ev = pruneEvents();
        const cutoff = Date.now() - (60*60*1000);
        return ev.filter(t=> new Date(t).getTime() >= cutoff).length;
    }
    function countToday(){
        const ev = pruneEvents();
        const start = new Date(); start.setHours(0,0,0,0);
        return ev.filter(t=> new Date(t).getTime() >= start.getTime()).length;
    }

    function getFirstRunDate(){
        try{
            const v = GM_getValue ? GM_getValue('la_first_run', '') : localStorage.getItem('la_first_run') || '';
            return v ? new Date(v) : null;
        }catch(e){ return null; }
    }
        function detectBlockMessage(){
            try{
                const body = (document.body && document.body.innerText) || '';
                const text = body.toLowerCase();
                for(const k of CFG.BLOCK_KEYWORDS){
                    if(text.includes(k.toLowerCase())) return true;
                }
            }catch(e){}
            return false;
        }
    function setFirstRunDate(){
        try{
            const existing = getFirstRunDate();
            if(!existing){
                const s = new Date().toISOString();
                if(GM_setValue) GM_setValue('la_first_run', s); else localStorage.setItem('la_first_run', s);
            }
        }catch(e){}
    }
    function currentDailyCap(){
        const first = getFirstRunDate();
        if(!first) return CFG.DAILY_START_CAP;
        const days = Math.floor((Date.now() - first.getTime()) / (24*3600*1000));
        if(days < CFG.RAMP_UP_DAYS) return CFG.DAILY_START_CAP;
        return CFG.MAX_PER_DAY;
    }
    function recordEvent(){
        const ev = pruneEvents(); ev.push(new Date().toISOString()); saveEvents(ev);
    }

    // ---------- UI ----------
    GM_addStyle && GM_addStyle('\n#la-panel{position:fixed;right:12px;bottom:12px;background:#fff;border:1px solid #ddd;padding:8px;border-radius:6px;z-index:99999;box-shadow:0 2px 8px rgba(0,0,0,0.12)}#la-panel button{margin:4px}#la-panel small{display:block;color:#666}');

    let state = {running:false};

    function buildUI(){
        if(document.getElementById('la-panel')) return;
        const p = document.createElement('div'); p.id='la-panel';
        p.innerHTML = `<div><strong>Auto-Connect</strong></div>`;
        const status = document.createElement('div'); status.id='la-status'; status.innerHTML = `<small>idle</small>`;
        const start = document.createElement('button'); start.textContent='Start';
        const stop = document.createElement('button'); stop.textContent='Stop'; stop.disabled=true;
        start.onclick = ()=>{ 
            // Ensure single-instance: set running lock
            try{ 
                const other = GM_getValue ? GM_getValue('la_running_lock', '') : localStorage.getItem('la_running_lock') || '';
                if(other){ alert('Another Auto-Connect instance appears to be running. Stop it before starting a new one.'); return; }
                if(GM_setValue) GM_setValue('la_running_lock', new Date().toISOString()); else localStorage.setItem('la_running_lock', new Date().toISOString());
            }catch(e){}
            state.running=true; start.disabled=true; stop.disabled=false; status.innerHTML=`<small>running — lastHour:${countLastHour()} today:${countToday()}</small>`; runAutomation(); };
        stop.onclick = ()=>{ state.running=false; start.disabled=false; stop.disabled=true; status.innerHTML=`<small>stopped</small>`; };
        p.appendChild(status); p.appendChild(start); p.appendChild(stop);
        document.body.appendChild(p);
    }

    // ---------- action helpers ----------
    function findConnectButton(){
        // Common patterns: button span text 'Connect', or button[aria-label*='Connect']
        try{
            // aria-label match
            let btn = document.querySelector("button[aria-label*='Connect']");
            if(btn) return btn;
            // span text match
            const candidates = Array.from(document.querySelectorAll('button'));
            for(const b of candidates){
                try{
                    const txt = (b.innerText||'').trim();
                    if(txt === 'Connect' || txt === 'Bağlan' || txt.toLowerCase().includes('connect')) return b;
                }catch(e){}
            }
        }catch(e){}
        return null;
    }

    function clickConnectFlow(){
        // Check hour window
        const h = hourNow();
        if(h < CFG.INVITES_HOUR_START || h > CFG.INVITES_HOUR_END){ console.log('AutoConnect: outside allowed hour window',h); return; }
        if(countLastHour() >= CFG.INVITES_PER_HOUR){ console.log('AutoConnect: hourly limit reached'); return; }
    if(countToday() >= currentDailyCap()){ console.log('AutoConnect: daily limit reached'); return; }

        const btn = findConnectButton();
        if(!btn){ console.log('AutoConnect: no connect button found'); return; }

        // Randomized delay
        const delay = randomBetween(CFG.MIN_DELAY_MS, CFG.MAX_DELAY_MS) + Math.floor(Math.random()*CFG.JITTER_MS);
        console.log('AutoConnect: will click Connect in',delay,'ms');
        setTimeout(async ()=>{
            try{
                btn.click();
                // Wait for possible modal with "Send" button
                await waitForModalAndSend();
                // Detect block/limit messages in page and stop if found
                const blocked = detectBlockMessage();
                if(blocked){
                    // write a flag and stop
                    try{ if(GM_setValue) GM_setValue('la_blocked', new Date().toISOString()); else localStorage.setItem('la_blocked', new Date().toISOString()); }catch(e){}
                    state.running = false; console.warn('AutoConnect: detected block message, stopping automation.');
                }
                recordEvent();
                document.getElementById('la-status') && (document.getElementById('la-status').innerHTML = `<small>sent — lastHour:${countLastHour()} today:${countToday()}</small>`);
                // Optionally close tab
                if(CFG.AUTO_CLOSE_TAB && window.opener){
                    setTimeout(()=>{ window.close(); }, 2000 + randomBetween(1000,3000));
                }
            }catch(e){ console.log('AutoConnect: click/send failed',e); }
        }, delay);
    }

    function waitForModalAndSend(timeout=8000){
        return new Promise((resolve)=>{
            const start = Date.now();
            const int = setInterval(()=>{
                // Find modal send button (buttons with text 'Send' or localized variants)
                const btns = Array.from(document.querySelectorAll('button'));
                for(const b of btns){
                    try{
                        const t = (b.innerText||'').trim();
                        if(t === 'Send' || t === 'Gönder' || t.toLowerCase().includes('send')){
                            // ensure visible/enabled
                            if(!b.disabled){ b.click(); clearInterval(int); setTimeout(()=>resolve(true),500); return; }
                        }
                    }catch(e){}
                }
                if(Date.now() - start > timeout){ clearInterval(int); resolve(false); }
            },300);
        });
    }

    // ---------- main automation loop ----------
    let automationRunning = false;
    async function runAutomation(){
        if(automationRunning) return;
        automationRunning = true;
        while(state.running){
            try{
                clickConnectFlow();
            }catch(e){ console.log('AutoConnect loop error', e); }
            // Wait a bit between checks to avoid tight loop
            await new Promise(r=>setTimeout(r, 2000 + randomBetween(0,3000)));
        }
        automationRunning = false;
        // clear running lock
        try{ if(GM_setValue) GM_setValue('la_running_lock', ''); else localStorage.removeItem('la_running_lock'); }catch(e){}
    }

    // ---------- init ----------
    try{ buildUI(); }catch(e){/* ignore UI failures */}

    // Auto-run if opened from manual_invites page (common workflow)
    try{
        if(document.referrer && document.referrer.includes('manual_invites.html')){
            // Start automatically
            state.running = true; runAutomation();
            const panelStart = document.querySelector('#la-panel button'); if(panelStart) panelStart.disabled = true;
        }
    }catch(e){}

})();
