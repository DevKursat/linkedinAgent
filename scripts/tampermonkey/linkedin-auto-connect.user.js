// ==UserScript==
// @name         LinkedIn Safe Auto-Connect (Kürşat mode)
// @namespace    http://devkursat.local/
// @version      0.5
// @description  From the app's invites page collect suggested profiles and help send invites from the browser. Default is safe: fills message and asks for your confirmation before sending.
// @match        *://*.linkedin.com/*
// @match        http://localhost:5000/*
// @match        http://127.0.0.1:5000/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Configuration (change in-script if you accept higher risk)
    const AUTO_SEND = false; // if true: try to click send automatically (risky)
    const CONFIRM_BEFORE_SEND = true; // if true, ask for confirmation modal before clicking Send
    const DELAY_MIN = 2000; // ms
    const DELAY_MAX = 6000; // ms
    const MAX_PER_HOUR = 5; // soft cap per hour
    const MESSAGE_TEMPLATE = (name) => `Merhaba ${name || ''},\n\nSizinle bağlantı kurmak isterim. Selamlar, Kürşat.`;

    // Utility
    function randDelay() {
        return DELAY_MIN + Math.floor(Math.random()*(DELAY_MAX-DELAY_MIN));
    }

    function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }

    // Rate limiter stored in localStorage
    function recordSend() {
        try{
            const key = 'tm_sent_times';
            let arr = JSON.parse(localStorage.getItem(key) || '[]');
            arr = arr.filter(t=>Date.now()-t < 1000*60*60);
            arr.push(Date.now());
            localStorage.setItem(key, JSON.stringify(arr));
        }catch(e){console.warn(e)}
    }
    function sentLastHour() {
        try{ const arr = JSON.parse(localStorage.getItem('tm_sent_times')||'[]'); return arr.filter(t=>Date.now()-t < 1000*60*60).length; }catch(e){return 0}
    }

    // Part A: On the app's invites page collect suggested profiles and show a control panel
    function setupAppPage() {
        // Only run on the app's invites path
        if(!location.pathname.startsWith('/invites')) return;
        // Avoid double-insert
        if(document.getElementById('tm-invite-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'tm-invite-panel';
        panel.style.position='fixed'; panel.style.right='12px'; panel.style.bottom='12px'; panel.style.zIndex=9999;
        panel.style.background='#fff'; panel.style.border='1px solid #ddd'; panel.style.padding='10px'; panel.style.borderRadius='6px'; panel.style.boxShadow='0 2px 6px rgba(0,0,0,0.12)';

        panel.innerHTML = `
            <div style="font-weight:bold;margin-bottom:6px">TamperAuto Connect</div>
            <div style="font-size:12px;margin-bottom:6px">Per-hour: <span id='tm-count'>...</span>/<span>${MAX_PER_HOUR}</span></div>
            <button id='tm-start' class='button' style='margin-right:6px'>Başlat</button>
            <button id='tm-stop' class='button'>Durdur</button>
            <div style='margin-top:6px;font-size:12px;color:#666'>Default: mesaj doldurup sizin onayınıza bırakır.</div>
        `;
        document.body.appendChild(panel);
        document.getElementById('tm-count').innerText = sentLastHour();

        let running = false;
        let profiles = [];

        function collectProfiles(){
            // find anchors to linkedin profiles in suggested list
            const anchors = Array.from(document.querySelectorAll('a[href*="linkedin.com/in/"]'));
            const unique = {};
            anchors.forEach(a=>{ try{ const href=a.href; if(href.includes('linkedin.com/in/')){ unique[href]=true } }catch(e){} });
            return Object.keys(unique);
        }

        document.getElementById('tm-start').addEventListener('click', async ()=>{
            profiles = collectProfiles();
            if(!profiles.length){ alert('Sayfada önerilen profil bulunamadı.'); return; }
            running = true;
            for(let i=0;i<profiles.length && running;i++){
                if(sentLastHour() >= MAX_PER_HOUR){ alert('Saatlik limit aşıldı — durduruluyor'); break; }
                const p = profiles[i];
                // open profile in same tab with marker
                const url = new URL(p);
                url.searchParams.set('tm_send', '1');
                url.searchParams.set('tm_idx', String(i));
                url.searchParams.set('tm_from', location.origin);
                window.location.href = url.toString();
                // navigation will break script here; subsequent control happens on LinkedIn page
                return;
            }
            if(!running) console.log('stopped');
        });

        document.getElementById('tm-stop').addEventListener('click', ()=>{ running=false; alert('Tamper flow durduruldu'); });
    }

    // Part B: On LinkedIn profile pages, detect tm_send param and act
    async function handleLinkedInProfile() {
        const params = new URLSearchParams(location.search);
        if(params.get('tm_send') !== '1') return;

        // check rate limit
        if(sentLastHour() >= MAX_PER_HOUR){ alert('Tamper: saatlik limit dolu, işlemi durdurun'); return; }

        // get name to personalize message
        let name = '';
        try{
            const el = document.querySelector('h1');
            if(el) name = el.textContent.trim().split('\n')[0];
        }catch(e){}

        // find connect button
        function findConnect(){
            const btns = Array.from(document.querySelectorAll('button'));
            for(const b of btns){
                const t = (b.innerText||'').trim();
                if(/connect|bağlan|bağlantı/i.test(t)) return b;
            }
            // sometimes the connect is in a menu
            const more = btns.find(b=>/(more|diğer)/i.test(b.innerText||''));
            if(more) { more.click(); }
            // try again
            for(const b of Array.from(document.querySelectorAll('button'))){
                const t = (b.innerText||'').trim();
                if(/connect|bağlan|bağlantı/i.test(t)) return b;
            }
            return null;
        }

        const connectBtn = findConnect();
        if(!connectBtn){ console.log('Tamper: Connect button not found, skipping'); alert('Connect bulunamadı, atlanıyor'); return; }

        // click connect
        connectBtn.scrollIntoView({behavior:'smooth', block:'center'});
        await sleep(500+Math.random()*500);
        connectBtn.click();

        // wait for modal
        let modal = null;
        for(let i=0;i<20;i++){ modal = document.querySelector('textarea, input[role="textbox"], .send-invite__custom-message'); if(modal) break; await sleep(300); }
        // if there's a checkbox "Add a note" we may need to click it first
        try{
            const addNote = Array.from(document.querySelectorAll('button,span')).find(el=>/add a note|not ekle|not ekle/i.test((el.innerText||'').toLowerCase()));
            if(addNote) { addNote.click(); await sleep(300); }
        }catch(e){}

        // find textarea in modal
        let textarea = document.querySelector('textarea') || document.querySelector('input[role="textbox"]');
        if(!textarea){ console.log('Tamper: invite message box not found'); }
        const msg = MESSAGE_TEMPLATE(name);
        if(textarea){ textarea.focus(); textarea.value = msg; textarea.dispatchEvent(new Event('input',{bubbles:true})); }

        // confirm if required
        if(CONFIRM_BEFORE_SEND && !AUTO_SEND){
            const proceed = confirm(`Davet gönderilsin mi?\n\nHedef: ${name}\nMesaj:\n${msg}`);
            if(!proceed){ alert('Kullanıcı iptal etti — bir sonraki profile gidiliyor'); redirectBack(); return; }
        }

        // find send button in modal
        let sendBtn = Array.from(document.querySelectorAll('button')).find(b=>/send|gönder/i.test(b.innerText||''));
        if(!sendBtn){ console.log('Tamper: send button not found'); }
        if(sendBtn && (AUTO_SEND || confirm('Onay verildi, göndermek üzeresiniz. Devam?'))){
            sendBtn.click();
            recordSend();
            await sleep(randDelay());
        }

        // After send or skip, navigate back to origin if provided or to the next profile
        redirectBack();
    }

    function redirectBack(){
        const params = new URLSearchParams(location.search);
        const from = params.get('tm_from');
        const idx = Number(params.get('tm_idx')||0);
        const nextIdx = idx+1;
        // try to find origin and continue to next profile stored there
        if(from && from.startsWith('http')){
            // we can't know the list from origin; simplest: return to origin and let user re-click Start
            window.location.href = from + '/invites';
        } else {
            // fallback: go to linkedin.com
            window.location.href = 'https://www.linkedin.com/feed/';
        }
    }

    // Init
    try{
        if(location.hostname.includes('linkedin.com')){
            handleLinkedInProfile();
        } else {
            setupAppPage();
        }
    }catch(e){ console.error('TamperAuto error', e); }

})();
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
        // Defaults tuned to user's request: ~20/day between 07-21
    INVITES_PER_HOUR: 2,       // max invites per hour (approx 20 / 14hrs => ~1.5 -> 2)
        INVITES_HOUR_START: 7,     // start hour (local) inclusive
        INVITES_HOUR_END: 21,      // end hour (local) inclusive
        // Ramp-up: in the first N days after first run, use DAILY_START_CAP, then increase to MAX_PER_DAY
    RAMP_UP_DAYS: 7,
    DAILY_START_CAP: 5,        // starting daily cap during ramp-up
    MAX_PER_DAY: 20,           // steady-state daily cap (user requested ~20)
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
