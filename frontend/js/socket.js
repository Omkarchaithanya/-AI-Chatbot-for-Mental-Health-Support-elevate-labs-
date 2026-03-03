/**
 * MindEase PRO — Socket.IO Client Manager
 * Wraps Socket.IO with auto-reconnect, event bus, and REST fallback.
 */

class MindEaseSocket {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.listeners = new Map();   // event → [callback, ...]
    this.pendingEmits = [];       // queued while disconnected
    this._reconnectAttempts = 0;
    this._maxReconnectAttempts = 5;
    this._heartbeatInterval = null;
  }

  /* ─── Connect ─────────────────────────────────── */
  connect() {
    if (this.socket) return;

    this.socket = io({
      transports: ['websocket', 'polling'],
      reconnectionAttempts: this._maxReconnectAttempts,
      reconnectionDelay: 1500,
      timeout: 10000,
    });

    this.socket.on('connect', () => {
      this.connected = true;
      this._reconnectAttempts = 0;
      this._emit_local('connection_status', { connected: true });
      this._flushPending();
      this._startHeartbeat();
    });

    this.socket.on('disconnect', (reason) => {
      this.connected = false;
      this._stopHeartbeat();
      this._emit_local('connection_status', { connected: false, reason });
    });

    this.socket.on('connect_error', (err) => {
      this._reconnectAttempts++;
      this._emit_local('connection_error', { error: err.message, attempt: this._reconnectAttempts });
    });

    /* ── Forward server events to our bus ─────────── */
    const serverEvents = [
      'emotion_detected',
      'response_token',
      'response_complete',
      'error',
      'rate_limited',
      'crisis_detected',
    ];
    serverEvents.forEach(evt => {
      this.socket.on(evt, (data) => this._emit_local(evt, data));
    });
  }

  disconnect() {
    this._stopHeartbeat();
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.connected = false;
  }

  /* ─── Pub/Sub ─────────────────────────────────── */
  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    const list = this.listeners.get(event) || [];
    this.listeners.set(event, list.filter(fn => fn !== callback));
  }

  _emit_local(event, data) {
    (this.listeners.get(event) || []).forEach(fn => {
      try { fn(data); } catch (e) { console.error('[Socket] listener error', e); }
    });
  }

  /* ─── Send chat message via WebSocket ─────────── */
  sendMessage(sessionId, text, ttsEnabled = false) {
    const ttsLang = localStorage.getItem('mindease_tts_lang') || 'en';
    const payload = { session_id: sessionId, message: text, tts: ttsEnabled, tts_lang: ttsLang };

    if (this.connected && this.socket) {
      this.socket.emit('chat_message', payload);
    } else {
      // Queue or fall back to REST
      this.pendingEmits.push({ event: 'chat_message', payload });
      this._emit_local('using_rest_fallback', {});
      return this._restFallback(sessionId, text, ttsEnabled);
    }
    return null;
  }

  /* ─── REST fallback when WebSocket is unavailable ─ */
  async _restFallback(sessionId, text, ttsEnabled) {
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text, tts: ttsEnabled, tts_lang: localStorage.getItem('mindease_tts_lang') || 'en' }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Request failed');

      // Synthetic events to mimic streaming
      this._emit_local('emotion_detected', {
        primary_emotion: data.emotion?.primary_emotion || 'neutral',
        emoji: data.emotion?.emoji || '💭',
        confidence: data.emotion?.confidence || 0,
        valence: data.emotion?.valence || 0,
        arousal: data.emotion?.arousal || 0,
      });
      this._emit_local('response_complete', {
        response: data.response,
        audio_base64: data.audio_base64,
        rag_used: data.rag_used,
        exercise_suggestion: data.exercise_suggestion,
        crisis_level: data.crisis_level || 0,
      });
      return data;
    } catch (err) {
      this._emit_local('error', { message: err.message });
      return null;
    }
  }

  /* ─── Flush queued emits after reconnect ─────── */
  _flushPending() {
    while (this.pendingEmits.length > 0 && this.connected) {
      const { event, payload } = this.pendingEmits.shift();
      this.socket.emit(event, payload);
    }
  }

  /* ─── Heartbeat (keep connection alive) ──────── */
  _startHeartbeat() {
    this._heartbeatInterval = setInterval(() => {
      if (this.connected) this.socket.emit('ping');
    }, 25000);
  }

  _stopHeartbeat() {
    clearInterval(this._heartbeatInterval);
    this._heartbeatInterval = null;
  }
}

// Singleton
window.mindEaseSocket = new MindEaseSocket();
