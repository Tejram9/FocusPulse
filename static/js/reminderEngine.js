/**
 * FocusPulse — Intelligent Daily Reminder Engine v2.0
 *
 * Storage keys:
 *   focuspulse_reminder_time     — "HH:MM" (24-hour)
 *   focuspulse_reminder_enabled  — "true" | "false"
 *   focuspulse_reminder_lastfired — "YYYY-MM-DDTHH:MM" (prevents duplicate fires)
 *   fp_focus_minutes_today       — integer, seeded from server
 *   fp_distractions_today        — integer, seeded from server
 *
 * Global function exposed for onclick:
 *   saveReminder()   — reads the form, persists to localStorage, updates UI
 */

'use strict';

/* ─── Storage Keys ──────────────────────────────────────────────── */
const LS = {
    TIME:       'focuspulse_reminder_time',
    ENABLED:    'focuspulse_reminder_enabled',
    LAST_FIRED: 'focuspulse_reminder_lastfired',
    FOCUS_MIN:  'fp_focus_minutes_today',
    DISTRACTS:  'fp_distractions_today',
};

/* ─── Motivational Quotes ───────────────────────────────────────── */
const QUOTES = [
    'Stay consistent — small steps compound into big results.',
    'Small focus sessions build lasting success.',
    "You're closer to today's goals than you think. Keep going.",
    'Discipline is choosing the future over the present moment.',
    'One focused session can change your entire day.',
    'Every minute you focus today is an investment in tomorrow.',
    'Progress, not perfection. Start now.',
    'Your future self will thank you for this session.',
    'Turn off distractions and turn on your potential.',
    'Focus is the art of saying no to a hundred other ideas.',
    'The secret of getting ahead is getting started.',
    "Don't watch the clock — do what it does. Keep going.",
    'Hard work beats talent when talent does not work hard.',
    'Consistency is what transforms average into excellence.',
];

/* ─── Safe Helpers ───────────────────────────────────────────────── */
function _safeInt(key, fallback) {
    try {
        const v = parseInt(localStorage.getItem(key), 10);
        return (isNaN(v) || v < 0) ? fallback : v;
    } catch { return fallback; }
}
function _safeStr(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}
function _safeBool(key, fallback) {
    try {
        const v = localStorage.getItem(key);
        return v === null ? fallback : v === 'true';
    } catch { return fallback; }
}
function _randomQuote() { return QUOTES[Math.floor(Math.random() * QUOTES.length)]; }

/* ─── Formatters ─────────────────────────────────────────────────── */
function _formatMinutes(min) {
    min = Math.max(0, Math.round(min));
    if (min === 0) return '0 min';
    const h = Math.floor(min / 60), m = min % 60;
    if (h > 0 && m > 0) return `${h} hr ${m} min`;
    return h > 0 ? `${h} hr` : `${m} min`;
}

/** "14:30" → "2:30 PM" */
function _fmt12(hhmm) {
    if (!hhmm) return '';
    const [hS, mS] = hhmm.split(':');
    let h = parseInt(hS, 10);
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h}:${mS || '00'} ${ampm}`;
}

function _todayPrefix() { return new Date().toISOString().slice(0, 10); }

/* ─── Productivity Score ─────────────────────────────────────────── */
function _score(focusMin, distractions, remaining) {
    const raw = focusMin - distractions * 2 - remaining * 3;
    return Math.min(100, Math.max(0, Math.round(raw)));
}

/* ─── Task Fetcher ───────────────────────────────────────────────── */
async function _fetchTasks() {
    try {
        const res = await fetch('/api/tasks', { credentials: 'same-origin' });
        if (!res.ok) throw new Error('http');
        const all = await res.json();
        if (!Array.isArray(all)) return { remaining: [], completed: [] };
        return {
            remaining: all.filter(t => t && t.status !== 'Completed'),
            completed: all.filter(t => t && t.status === 'Completed'),
        };
    } catch { return { remaining: [], completed: [] }; }
}

/* ─── Notification Message ───────────────────────────────────────── */
function _buildBody(remaining, focusMin, distractions) {
    const score    = _score(focusMin, distractions, remaining.length);
    const focusFmt = _formatMinutes(focusMin);

    let taskBlock;
    if (remaining.length === 0) {
        taskBlock = '🎉 All tasks done for today — amazing work!';
    } else {
        const list = remaining.slice(0, 5)
            .map(t => `• ${String(t.title || 'Untitled').slice(0, 55)}`)
            .join('\n');
        taskBlock = `You have ${remaining.length} task${remaining.length !== 1 ? 's' : ''} remaining:\n${list}`;
        if (remaining.length > 5) taskBlock += `\n  …and ${remaining.length - 5} more`;
    }

    const urgency =
        remaining.length === 0 ? '🏆 Take a well-deserved break!' :
        remaining.length <= 2  ? '💪 Almost there — finish strong!' :
        remaining.length <= 5  ? '📌 Good progress — keep momentum.' :
                                 '⚠️ Busy day — start a focus session now!';

    return {
        title: 'FocusPulse Daily Reminder 🎯',
        body: [
            taskBlock, '',
            `🕐 Focus today: ${focusFmt}`,
            `⚡ Productivity score: ${score}/100`,
            '', urgency, '',
            `💡 ${_randomQuote()}`,
            '', '▶ Suggested: Start a 25-min Focus Session now.'
        ].join('\n'),
        score,
    };
}

/* ─── Browser Notification ───────────────────────────────────────── */
async function _requestPerm() {
    if (!('Notification' in window)) return 'unsupported';
    if (Notification.permission === 'granted') return 'granted';
    if (Notification.permission === 'denied')  return 'denied';
    try { return await Notification.requestPermission(); } catch { return 'denied'; }
}

function _fireBrowserNotif(title, body) {
    try {
        const n = new Notification(title, {
            body, tag: 'focuspulse-reminder', renotify: true,
            icon: '/static/images/focuspulse-icon.png',
        });
        n.onclick = () => { window.focus(); n.close(); };
        return true;
    } catch { return false; }
}

/* ─── In-App Toast Fallback ──────────────────────────────────────── */
function _escHtml(s) {
    return String(s)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function _showToast(title, body, score) {
    const old = document.getElementById('fp-reminder-toast');
    if (old) old.remove();

    const t = document.createElement('div');
    t.id = 'fp-reminder-toast';
    t.className = 'fp-toast';
    t.innerHTML = `
        <div class="fp-toast-header">
            <span class="fp-toast-icon">🎯</span>
            <strong class="fp-toast-title">${_escHtml(title)}</strong>
            <button class="fp-toast-close" onclick="document.getElementById('fp-reminder-toast').remove()">✕</button>
        </div>
        <div class="fp-toast-body">${_escHtml(body).replace(/\n/g,'<br>')}</div>
        <div class="fp-toast-footer">
            <span class="fp-toast-score">Score: ${score}/100</span>
            <a href="/focus" class="fp-toast-cta">▶ Start Focus</a>
        </div>`;
    document.body.appendChild(t);

    requestAnimationFrame(() => t.classList.add('fp-toast-visible'));
    setTimeout(() => {
        t.classList.add('fp-toast-hiding');
        setTimeout(() => t.remove(), 600);
    }, 20000);
}

/* ─── UI Sync ────────────────────────────────────────────────────── */
function _syncUI() {
    const enabled  = _safeBool(LS.ENABLED, false);
    const time     = _safeStr(LS.TIME, '');
    const focusMin = _safeInt(LS.FOCUS_MIN, 0);

    /* Pulse dot */
    const dot = document.getElementById('fp-reminder-dot');
    if (dot) {
        dot.className = 'fp-pulse-dot ' +
            (enabled && time ? 'fp-pulse-dot-active' : 'fp-pulse-dot-inactive');
    }

    /* Status text */
    const txt = document.getElementById('fp-reminder-status-text');
    if (txt) {
        if (enabled && time) {
            txt.textContent = `Active — next at ${_fmt12(time)}`;
            txt.style.color = 'var(--success-green)';
        } else if (time && !enabled) {
            txt.textContent = 'Configured but disabled';
            txt.style.color = 'var(--core-muted)';
        } else {
            txt.textContent = 'Not set';
            txt.style.color = 'var(--core-muted)';
        }
    }

    /* Next reminder label */
    const next = document.getElementById('fp-next-reminder-label');
    if (next) {
        next.textContent = (enabled && time)
            ? `Today at ${_fmt12(time)}`
            : 'Not set';
    }

    /* Focus pill */
    const fp = document.getElementById('fp-reminder-focus-today');
    if (fp) fp.textContent = `Focus: ${_formatMinutes(focusMin)}`;

    /* Sync form controls to stored values (on page load) */
    const timeInput = document.getElementById('reminderTime');
    const toggle    = document.getElementById('reminderEnabled');
    if (timeInput && !timeInput._userEditing) timeInput.value = time;
    if (toggle)    toggle.checked = enabled;
}

/* ─── Fire the reminder ──────────────────────────────────────────── */
async function _fire() {
    const focusMin    = _safeInt(LS.FOCUS_MIN, 0);
    const distractions = _safeInt(LS.DISTRACTS, 0);
    const { remaining } = await _fetchTasks();

    /* Update tasks-left pill live */
    const tp = document.getElementById('fp-reminder-tasks-left');
    if (tp) tp.textContent = `Tasks left: ${remaining.length}`;

    const { title, body, score } = _buildBody(remaining, focusMin, distractions);

    /* Record fired timestamp to prevent duplicate fires in same minute */
    const now   = new Date();
    const stamp = `${_todayPrefix()}T${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    localStorage.setItem(LS.LAST_FIRED, stamp);

    const perm = await _requestPerm();
    if (perm === 'granted') {
        if (!_fireBrowserNotif(title, body)) _showToast(title, body, score);
    } else {
        _showToast(title, body, score);
    }
}

/* ─── 60-second Tick ─────────────────────────────────────────────── */
function _tick() {
    _syncUI();

    const enabled = _safeBool(LS.ENABLED, false);
    const time    = _safeStr(LS.TIME, '');
    if (!enabled || !time) return;

    const now   = new Date();
    const hhmm  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    const stamp = `${_todayPrefix()}T${hhmm}`;

    if (hhmm === time && _safeStr(LS.LAST_FIRED, '') !== stamp) {
        _fire();
    }
}

/* ─── Permission Button Wiring ───────────────────────────────────── */
function _wirePermBtn() {
    const btn = document.getElementById('fp-reminder-perm-btn');
    if (!btn) return;

    function _setPermState(perm) {
        if (perm === 'granted') {
            btn.textContent = '✅ Notifications Enabled';
            btn.disabled    = true;
        } else if (perm === 'denied') {
            btn.textContent = '❌ Blocked — Enable in Browser Settings';
            btn.disabled    = false;
        } else {
            btn.textContent = '🔔 Enable Notifications';
            btn.disabled    = false;
        }
    }

    if (!('Notification' in window)) {
        btn.textContent = '🚫 Not Supported';
        btn.disabled    = true;
        return;
    }

    _setPermState(Notification.permission);

    btn.addEventListener('click', async () => {
        const p = await _requestPerm();
        _setPermState(p);
    });
}

/* ─── Global saveReminder() — called by onclick ──────────────────── */
window.saveReminder = function () {
    const timeInput = document.getElementById('reminderTime');
    const toggle    = document.getElementById('reminderEnabled');

    if (!timeInput) return;

    const time    = timeInput.value;          // "HH:MM" or ""
    const enabled = toggle ? toggle.checked : false;

    if (!time) {
        /* Flash the time input red */
        timeInput.style.borderColor = '#ef4444';
        timeInput.focus();
        setTimeout(() => { timeInput.style.borderColor = ''; }, 2000);
        return;
    }

    /* Persist */
    localStorage.setItem(LS.TIME,    time);
    localStorage.setItem(LS.ENABLED, enabled ? 'true' : 'false');

    /* Show inline confirmation */
    const confirm    = document.getElementById('fp-save-confirm');
    const savedLabel = document.getElementById('fp-saved-time-display');
    if (confirm) {
        if (savedLabel) savedLabel.textContent = _fmt12(time);
        confirm.style.display = 'block';
        setTimeout(() => { confirm.style.display = 'none'; }, 5000);
    }

    /* Update header */
    _syncUI();

    /* Request notification permission automatically when saving enabled reminder */
    if (enabled) _requestPerm();
};

/* ─── Init ───────────────────────────────────────────────────────── */
const ReminderEngine = {
    init(seed) {
        /* Seed server data safely */
        if (seed) {
            const fm = parseInt(seed.focusMinutesToday, 10);
            const dd = parseInt(seed.distractionsToday,  10);
            if (!isNaN(fm) && fm >= 0) localStorage.setItem(LS.FOCUS_MIN, fm);
            if (!isNaN(dd) && dd >= 0) localStorage.setItem(LS.DISTRACTS, dd);
            if (seed.tasksRemaining !== undefined) {
                window.__fp_tasks_remaining = seed.tasksRemaining;
                const tp = document.getElementById('fp-reminder-tasks-left');
                if (tp) tp.textContent = `Tasks left: ${seed.tasksRemaining}`;
            }
        }

        _wirePermBtn();
        _tick();
        setInterval(_tick, 60_000);
    }
};
