/**
 * MindEase PRO — Profile Manager
 * Loads user stats, handles preference updates, data export, and session clear.
 */

class ProfileManager {
  constructor() {
    this._sessionId = null;

    /* DOM */
    this._totalMsgs    = document.getElementById('stat-messages');
    this._topEmotion   = document.getElementById('stat-emotion');
    this._streak       = document.getElementById('stat-days');
    this._improvement  = null;  // no stat-trend element in HTML

    this._toneSelect   = document.getElementById('tone-select');
    this._ttsToggle    = document.getElementById('tts-toggle');
    this._ttsLangSelect = document.getElementById('tts-lang-select');
    this._ttsLangRow    = document.getElementById('tts-lang-row');
    this._savePrefBtn  = document.getElementById('pref-save-btn');
    this._exportBtn    = document.getElementById('export-data-btn');
    this._clearBtn     = document.getElementById('clear-history-btn');

    this._statusMsg    = document.getElementById('pref-status');

    this._bindEvents();
  }

  init(sessionId, preferences) {
    this._sessionId = sessionId;
    // Show session ID in profile header
    const sessionDisplay = document.getElementById('session-id-display');
    if (sessionDisplay) sessionDisplay.textContent = sessionId;
    this._applyPreferences(preferences || {});
    this._loadStats();
  }

  /* ─── Apply saved preferences ──────────────────── */
  _applyPreferences({ preferred_tone, tts_enabled }) {
    if (this._toneSelect && preferred_tone)
      this._toneSelect.value = preferred_tone;
    if (this._ttsToggle)
      this._ttsToggle.checked = !!tts_enabled;    // Restore saved TTS language from localStorage
    const savedLang = localStorage.getItem('mindease_tts_lang') || 'en';
    if (this._ttsLangSelect) this._ttsLangSelect.value = savedLang;
    // Show lang row only when TTS is on
    this._syncTtsLangRow();
  }

  _syncTtsLangRow() {
    if (!this._ttsLangRow) return;
    const ttsOn = this._ttsToggle?.checked;
    if (ttsOn) this._ttsLangRow.removeAttribute('hidden');
    else       this._ttsLangRow.setAttribute('hidden', '');  }

  /* ─── Load stats from session endpoint ─────────── */
  async _loadStats() {
    if (!this._sessionId) return;
    try {
      const resp = await fetch(`/api/sessions/${this._sessionId}`);
      if (!resp.ok) return;
      const data = await resp.json();

      const s = data.session || data;

      // message_count is now the live count of user messages from ChatMessage table
      const msgs = s.message_count ?? 0;
      if (this._totalMsgs) this._totalMsgs.textContent = msgs;

      // Exercises completed
      const exEl = document.getElementById('stat-exercises');
      if (exEl) exEl.textContent = s.exercises_completed ?? 0;

      // Days active — show just the number, the HTML label says "Days Active"
      if (this._streak) this._streak.textContent = s.days_active ?? 0;

      // Top emotion
      if (this._topEmotion) {
        this._topEmotion.textContent = s.most_common_emotion || '—';
      }
    } catch (e) {
      console.warn('[Profile] stats load failed', e);
    }
  }

  /* ─── Save preferences ─────────────────────────── */
  async _savePreferences() {
    if (!this._sessionId) return;
    const tone = this._toneSelect?.value;
    const tts  = this._ttsToggle?.checked ?? false;

    try {
      const resp = await fetch(`/api/sessions/${this._sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferred_tone: tone, tts_enabled: tts }),
      });
      if (!resp.ok) throw new Error('Save failed');

      // Save TTS language to localStorage
      const lang = this._ttsLangSelect?.value || 'en';
      localStorage.setItem('mindease_tts_lang', lang);

      // Notify app to update TTS setting
      window.mindEaseApp?.updateTts(tts);

      this._showStatus('Preferences saved ✓', 'success');
    } catch (e) {
      this._showStatus('Could not save preferences.', 'error');
    }
  }

  /* ─── Export all data ──────────────────────────── */
  async _exportAllData() {
    if (!this._sessionId) return;
    try {
      const [histResp, sessResp] = await Promise.all([
        fetch(`/api/mood/history/${this._sessionId}?days=365&limit=1000`),
        fetch(`/api/sessions/${this._sessionId}`),
      ]);

      const history = histResp.ok ? await histResp.json() : {};
      const session = sessResp.ok ? await sessResp.json() : {};

      const exportData = {
        exported_at: new Date().toISOString(),
        session: session.session || session,
        mood_history: history.entries || [],
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url  = URL.createObjectURL(blob);
      const a    = Object.assign(document.createElement('a'), {
        href: url, download: `mindease_export_${Date.now()}.json`
      });
      a.click();
      URL.revokeObjectURL(url);
      this._showStatus('Data exported ✓', 'success');
    } catch (e) {
      this._showStatus('Export failed.', 'error');
    }
  }

  /* ─── Clear session data ────────────────────────── */
  async _clearData() {
    if (!this._sessionId) return;
    if (!confirm('This will permanently delete your chat and mood history. Continue?')) return;
    try {
      await fetch(`/api/sessions/${this._sessionId}`, { method: 'DELETE' });
      localStorage.removeItem('mindease_session_id');
      location.reload();
    } catch (e) {
      this._showStatus('Could not clear data.', 'error');
    }
  }

  /* ─── Status message ────────────────────────────── */
  _showStatus(msg, type = 'info') {
    if (!this._statusMsg) return;
    this._statusMsg.textContent = msg;
    this._statusMsg.style.color = type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#aaa';
    this._statusMsg.style.display = 'inline';
    setTimeout(() => { if (this._statusMsg) this._statusMsg.style.display = 'none'; }, 3000);
  }

  _bindEvents() {
    this._savePrefBtn?.addEventListener('click', () => this._savePreferences());
    this._exportBtn?.addEventListener('click',   () => this._exportAllData());
    this._clearBtn?.addEventListener('click',    () => this._clearData());
    // Show/hide language row when TTS toggle flipped
    this._ttsToggle?.addEventListener('change', () => this._syncTtsLangRow());
  }
}

window.ProfileManager = ProfileManager;
