/**
 * MindEase PRO — Chat UI Controller
 * Handles message rendering, streaming token display, emotion badge, and input bar.
 */

class ChatUI {
  constructor(socket, voiceManager) {
    this.socket = socket;
    this.voice  = voiceManager;

    /* DOM refs */
    this.chatWindow      = document.getElementById('chat-window');
    this.inputEl         = document.getElementById('chat-input');
    this.sendBtn         = document.getElementById('send-btn');
    this.voiceBtn        = document.getElementById('voice-btn');
    this.emotionBadge    = document.getElementById('emotion-indicator');
    this.emotionEmoji    = document.getElementById('emotion-emoji');
    this.emotionLabel    = document.getElementById('emotion-label');
    this.typingIndicator = document.getElementById('typing-indicator');
    this.suggestCard     = document.getElementById('exercise-suggestion-card');
    this.suggestText     = document.getElementById('suggestion-desc');
    this.suggestBtn      = document.getElementById('suggestion-open-btn');
    this.crisisBanner    = document.getElementById('crisis-banner');
    this.crisisText      = document.getElementById('crisis-text');

    // Dismiss buttons
    document.getElementById('crisis-dismiss')?.addEventListener('click', () => {
      this.crisisBanner?.setAttribute('hidden', '');
      this.crisisBanner?.classList.remove('visible');
    });
    document.getElementById('suggestion-dismiss')?.addEventListener('click', () => {
      this._hideSuggestCard();
    });

    /* DOM refs — TTS toggle button in input bar */
    this.ttsBtn          = document.getElementById('tts-btn');

    /* State */
    this._session_id   = null;
    this._ttsEnabled   = false;
    this._isWaiting    = false;
    this._streamBubble = null;    // the <p> being streamed into
    this._accumulated  = '';      // full streamed text so far (typo fix)

    this._bindEvents();
    this._wireSocket();
  }

  init(sessionId, ttsEnabled) {
    this._session_id = sessionId;
    this._ttsEnabled = !!ttsEnabled;
    this._syncTtsBtn();
    // Set welcome timestamp (message is already in HTML)
    const welcomeTime = document.getElementById('welcome-time');
    if (welcomeTime) {
      welcomeTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }

  setTts(enabled) {
    this._ttsEnabled = !!enabled;
    this._syncTtsBtn();
  }

  _syncTtsBtn() {
    if (!this.ttsBtn) return;
    this.ttsBtn.textContent = this._ttsEnabled ? '🔊' : '🔇';
    this.ttsBtn.title = this._ttsEnabled ? 'Text-to-speech ON (click to disable)' : 'Text-to-speech OFF (click to enable)';
    this.ttsBtn.classList.toggle('tts-active', this._ttsEnabled);
  }

  /* ─── DOM Events ──────────────────────────────── */
  _bindEvents() {
    this.sendBtn.addEventListener('click', () => this._handleSend());

    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSend();
      }
    });

    // Auto-expand textarea and enable send button
    this.inputEl.addEventListener('input', () => {
      this.inputEl.style.height = 'auto';
      this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + 'px';
      this.sendBtn.disabled = !this.inputEl.value.trim();
    });

    // Voice button
    this.voiceBtn?.addEventListener('click', () => {
      const started = this.voice.toggleListening();
      this.voiceBtn.classList.toggle('recording', started);
    });

    // TTS toggle button (in chat input bar)
    this.ttsBtn?.addEventListener('click', () => {
      this._ttsEnabled = !this._ttsEnabled;
      this.ttsBtn.textContent = this._ttsEnabled ? '🔊' : '🔇';
      this.ttsBtn.title = this._ttsEnabled ? 'Text-to-speech ON (click to disable)' : 'Text-to-speech OFF (click to enable)';
      this.ttsBtn.classList.toggle('tts-active', this._ttsEnabled);
      // Sync tts-toggle in profile if present
      const profileToggle = document.getElementById('tts-toggle');
      if (profileToggle) profileToggle.checked = this._ttsEnabled;
    });

    // Also sync from profile toggle
    document.getElementById('tts-toggle')?.addEventListener('change', (e) => {
      this._ttsEnabled = e.target.checked;
      if (this.ttsBtn) {
        this.ttsBtn.textContent = this._ttsEnabled ? '🔊' : '🔇';
        this.ttsBtn.classList.toggle('tts-active', this._ttsEnabled);
      }
    });

    this.voice.onTranscript = (text, isFinal) => {
      this.inputEl.value = text;
      this.inputEl.style.height = 'auto';
      this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + 'px';
      if (isFinal) {
        this.voiceBtn?.classList.remove('recording');
        this._handleSend();
      }
    };

    this.voice.onError = (msg) => this._addSystemMessage(msg);
  }

  /* ─── Socket Events ────────────────────────────── */
  _wireSocket() {
    this.socket.on('emotion_detected', (data) => {
      // Backend sends {primary_emotion, emoji, confidence, ...}
      const emotion = data.primary_emotion || data.emotion || 'neutral';
      const emoji = data.emoji || '💭';
      const confidence = data.confidence || 0;
      this._showEmotion(emotion, emoji, confidence);
    });

    this.socket.on('response_token', ({ token }) => {
      this._appendToken(token);
    });

    this.socket.on('response_complete', (data) => {
      this._finalizeResponse(data);
    });

    this.socket.on('crisis_detected', (data) => {
      this._showCrisisBanner(data.message || 'Please reach out for support.');
    });

    this.socket.on('error', ({ message }) => {
      this._removeTyping();
      this._isWaiting = false;
      this._setInputEnabled(true);
      this._addSystemMessage('Something went wrong. Please try again.');
    });

    this.socket.on('rate_limited', ({ retry_after }) => {
      this._removeTyping();
      this._isWaiting = false;
      this._setInputEnabled(true);
      this._addSystemMessage(`You're sending messages too quickly. Please wait ${retry_after}s.`);
    });
  }

  /* ─── Send ─────────────────────────────────────── */
  _handleSend() {
    const text = this.inputEl.value.trim();
    if (!text || this._isWaiting) return;

    this._addMessage('user', text);
    this.inputEl.value = '';
    this.inputEl.style.height = 'auto';

    this._isWaiting = true;
    this._setInputEnabled(false);
    this._showTyping();
    this._hideSuggestCard();

    this.socket.sendMessage(this._session_id, text, this._ttsEnabled);
  }

  /* ─── Message Bubbles ──────────────────────────── */
  _addMessage(role, text, opts = {}) {
    const wrap = document.createElement('div');
    wrap.className = role === 'bot' ? 'message bot-message' : 'message user-message';

    if (role === 'bot') {
      const avatar = document.createElement('div');
      avatar.className = 'message-avatar';
      avatar.textContent = '🧠';
      wrap.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);

    if (opts.ragUsed) {
      const tag = document.createElement('span');
      tag.className = 'rag-tag';
      tag.textContent = '📘 CBT-informed';
      bubble.appendChild(tag);
    }

    wrap.appendChild(bubble);
    this.chatWindow.appendChild(wrap);
    this._scrollBottom();
    return p;
  }

  _addStreamingBubble() {
    const wrap = document.createElement('div');
    wrap.className = 'message bot-message';
    wrap.id = 'streaming-bubble';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🧠';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const p = document.createElement('p');
    bubble.appendChild(p);
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    this.chatWindow.appendChild(wrap);
    this._streamBubble = p;
    this._accumulated  = '';
    this._scrollBottom();
  }

  _appendToken(token) {
    if (!this._streamBubble) {
      this._removeTyping();
      this._addStreamingBubble();
    }
    this._accumulated += token;
    this._streamBubble.textContent = this._accumulated;
    this._scrollBottom();
  }

  _finalizeResponse(data) {
    this._removeTyping();
    this._isWaiting = false;
    this._setInputEnabled(true);

    // Backend sends 'response' field (both WebSocket and REST paths)
    const text = data.response || data.message || '';

    // If no streaming happened, add full message
    if (!this._streamBubble) {
      if (text) this._addMessage('bot', text, { ragUsed: data.rag_used });
    } else {
      this._streamBubble.classList.remove('streaming');
      if (data.rag_used) {
        const tag = document.createElement('span');
        tag.className = 'rag-tag';
        tag.textContent = '📘 CBT-informed';
        this._streamBubble.parentElement.appendChild(tag);
      }
      this._streamBubble = null;
    }

    // TTS playback
    if (data.audio_base64) {
      this.voice.speakFromBase64(data.audio_base64);
    } else if (this._ttsEnabled && (data.response || data.message)) {
      this.voice.speakText(data.response || data.message);
    }

    // Exercise suggestion
    if (data.exercise_suggestion || data.suggested_exercise) {
      this._showSuggestCard(data.exercise_suggestion || data.suggested_exercise);
    }

    // Show crisis banner only for serious crisis (level 2 or 3)
    if (data.crisis_level >= 2) {
      this._showCrisisBanner();
    } else if (data.crisis_level === 1) {
      // Gentle in-chat support message for mild level
      this._addSystemMessage('💙 If you ever need extra support, you can reach the 988 Lifeline anytime.');
    }
  }

  _addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'system-message';
    div.textContent = text;
    this.chatWindow.appendChild(div);
    this._scrollBottom();
  }

  /* ─── Emotion Badge ───────────────────────────── */
  _showEmotion(emotion, emoji, confidence) {
    if (!this.emotionBadge) return;
    this.emotionBadge.removeAttribute('hidden');
    const pill = this.emotionBadge.querySelector('.emotion-pill');
    if (pill) pill.dataset.emotion = emotion;
    if (this.emotionEmoji) this.emotionEmoji.textContent = emoji || '💭';
    if (this.emotionLabel) this.emotionLabel.textContent = emotion;
    const conf = this.emotionBadge.querySelector('#emotion-confidence');
    if (conf) conf.textContent = `${Math.round((confidence || 0) * 100)}%`;
  }

  /* ─── Typing Indicator ────────────────────────── */
  _showTyping() {
    if (this.typingIndicator) {
      this.typingIndicator.style.display = 'flex';
    }
    this._scrollBottom();
  }

  _removeTyping() {
    if (this.typingIndicator) this.typingIndicator.style.display = 'none';
  }

  /* ─── Exercise Suggestion card ───────────────── */
  _showSuggestCard(exercise) {
    if (!this.suggestCard) return;
    const title = document.getElementById('suggestion-title');
    if (title) title.textContent = `Try: ${exercise.replace(/_/g, ' ')}`;
    if (this.suggestText) this.suggestText.textContent = 'It only takes a few minutes';
    this.suggestCard.removeAttribute('hidden');
    this.suggestBtn?.addEventListener('click', () => {
      window.mindEaseApp?.openExercise(exercise);
      this._hideSuggestCard();
    }, { once: true });
  }

  _hideSuggestCard() {
    if (this.suggestCard) this.suggestCard.setAttribute('hidden', '');
  }

  /* ─── Crisis Banner ───────────────────────────── */
  _showCrisisBanner(message) {
    if (!this.crisisBanner) return;
    this.crisisBanner.removeAttribute('hidden');
    this.crisisBanner.classList.add('visible');
  }

  /* ─── Helpers ─────────────────────────────────── */
  _setInputEnabled(enabled) {
    this.inputEl.disabled = !enabled;
    // Keep send disabled if input is empty
    this.sendBtn.disabled = !enabled || !this.inputEl.value.trim();
    if (enabled) this.inputEl.focus();
  }

  _scrollBottom() {
    requestAnimationFrame(() => {
      this.chatWindow.scrollTop = this.chatWindow.scrollHeight;
    });
  }

  _addWelcomeMessage() {
    this._addMessage('bot',
      "Hello! I'm MindEase, your AI mental health companion. " +
      "How are you feeling today? I'm here to listen and support you. 💙"
    );
  }

  clearHistory() {
    const ti = this.typingIndicator;
    this.chatWindow.innerHTML = '';
    // Re-attach typing indicator (innerHTML wipe removes it)
    if (ti) {
      ti.style.display = 'none';
      this.chatWindow.appendChild(ti);
    }
    this._addWelcomeMessage();
  }
}

window.ChatUI = ChatUI;
