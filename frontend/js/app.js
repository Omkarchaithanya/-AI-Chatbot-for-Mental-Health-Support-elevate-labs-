/**
 * MindEase PRO — App Bootstrap & View Router
 * Manages session, bottom nav, view transitions, settings panel.
 */

class MindEaseApp {
  constructor() {
    this._sessionId  = null;
    this._activeView = 'chat';
    this._ttsEnabled = false;
    this._settings   = {};

    /* Sub-controllers (instantiated below) */
    this.chatUI    = null;
    this.dashboard = null;
    this.exercises = null;
    this.profile   = null;

    /* DOM */
    this._views      = document.querySelectorAll('.view');
    this._navBtns    = document.querySelectorAll('.nav-btn');
    this._settingsBtn = document.getElementById('settings-btn');
    this._settingsOverlay = document.getElementById('settings-overlay');
    this._settingsClose   = document.getElementById('close-settings-btn');
    this._connDot         = document.getElementById('online-indicator');

    /* Exercise grid cards */
    document.querySelectorAll('.exercise-card').forEach(card => {
      card.addEventListener('click', () => {
        this.openExercise(card.dataset.exercise);
      });
    });
  }

  /* ─── Bootstrap ────────────────────────────────── */
  async boot() {
    this._sessionId = await this._getOrCreateSession();

    // Load preferences for session
    let prefs = {};
    try {
      const r = await fetch(`/api/sessions/${this._sessionId}`);
      if (r.ok) {
        const d = await r.json();
        prefs = d.session || d;
        this._ttsEnabled = !!prefs.tts_enabled;
      }
    } catch (_) {}

    // Instantiate sub-controllers
    this.chatUI    = new ChatUI(window.mindEaseSocket, window.voiceManager);
    this.dashboard = new MoodDashboard();
    this.exercises = new ExercisePlayer();
    this.profile   = new ProfileManager();

    this.chatUI.init(this._sessionId, this._ttsEnabled);
    this.dashboard.init(this._sessionId);
    this.exercises.init(this._sessionId);
    this.profile.init(this._sessionId, prefs);

    // Connect socket
    window.mindEaseSocket.connect();
    window.mindEaseSocket.on('connection_status', ({ connected }) => {
      this._updateConnDot(connected);
    });

    this._bindNav();
    this._bindSettings();
    this._navigateTo('chat');
  }

  /* ─── Session ID: localStorage + API ───────────── */
  async _getOrCreateSession() {
    const stored = localStorage.getItem('mindease_session_id');
    if (stored) {
      // Validate the session still exists on the server (handles server restarts)
      try {
        const check = await fetch(`/api/sessions/${stored}`);
        if (check.ok) return stored;
        // Session gone (server restarted / DB wiped) — clear and create fresh
      } catch (_) {}
      localStorage.removeItem('mindease_session_id');
    }

    try {
      const resp = await fetch('/api/sessions/new', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        const id   = data.session_id;
        localStorage.setItem('mindease_session_id', id);
        return id;
      }
    } catch (_) {}

    // Fallback local UUID
    const uid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
    localStorage.setItem('mindease_session_id', uid);
    return uid;
  }

  /* ─── View Routing ──────────────────────────────── */
  _bindNav() {
    this._navBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        this._navigateTo(btn.dataset.target);
      });
    });
  }

  _navigateTo(viewName) {
    this._activeView = viewName;

    this._views.forEach(v => {
      const isActive = v.id === `view-${viewName}`;
      v.classList.toggle('active', isActive);
      if (isActive) v.removeAttribute('hidden');
      else v.setAttribute('hidden', '');
    });

    this._navBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.target === viewName);
    });

    // Hide crisis banner when leaving chat
    if (viewName !== 'chat') {
      const banner = document.getElementById('crisis-banner');
      banner?.setAttribute('hidden', '');
      banner?.classList.remove('visible');
    }

    // Lazy refresh dashboard when activated
    if (viewName === 'mood' && this.dashboard) {
      this.dashboard.refresh();
    }

    // Reload profile stats when activated
    if (viewName === 'profile' && this.profile) {
      this.profile._loadStats();
    }
  }

  /* ─── Settings Panel ────────────────────────────── */
  _bindSettings() {
    this._settingsBtn?.addEventListener('click', () => {
      this._settingsOverlay?.removeAttribute('hidden');
    });

    this._settingsClose?.addEventListener('click', () => {
      this._settingsOverlay?.setAttribute('hidden', '');
    });

    this._settingsOverlay?.addEventListener('click', (e) => {
      if (e.target === this._settingsOverlay)
        this._settingsOverlay.setAttribute('hidden', '');
    });
  }

  /* ─── Public interface ──────────────────────────── */
  openExercise(exerciseId) {
    if (this.exercises) {
      this.exercises.open(exerciseId);
    }
  }

  updateTts(enabled) {
    this._ttsEnabled = enabled;
    if (this.chatUI) this.chatUI.setTts(enabled);
  }

  /* ─── Connection indicator ──────────────────────── */
  _updateConnDot(connected) {
    if (!this._connDot) return;
    this._connDot.classList.toggle('online',  connected);
    this._connDot.classList.toggle('offline', !connected);
    this._connDot.title = connected ? 'Connected' : 'Connecting…';
  }

  get sessionId() { return this._sessionId; }
}

/* ── Boot when DOM is ready ─────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  window.mindEaseApp = new MindEaseApp();
  try {
    await window.mindEaseApp.boot();
  } catch (e) {
    console.error('[App] boot failed:', e);
  }
});
