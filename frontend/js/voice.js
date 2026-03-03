/**
 * MindEase PRO — Voice Manager
 * Handles Speech-to-Text (Web Speech API) and Text-to-Speech (backend audio / SpeechSynthesis).
 */

class VoiceManager {
  constructor() {
    /* STT */
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this._sttSupported = !!SpeechRecognition;
    this.recognition = this._sttSupported ? new SpeechRecognition() : null;

    /* TTS */
    this._ttsSupported = 'speechSynthesis' in window;
    this._currentAudio = null;   // for backend base64 audio
    this._currentUtterance = null;

    /* State */
    this.isListening = false;
    this.isSpeaking = false;

    /* Callbacks */
    this.onTranscript = null;   // (text, isFinal) => void
    this.onListenStart = null;
    this.onListenEnd = null;
    this.onError = null;

    this._setupRecognition();
  }

  /* ─── STT Setup ────────────────────────────────── */
  _setupRecognition() {
    if (!this.recognition) return;
    const r = this.recognition;
    r.continuous = false;
    r.interimResults = true;
    r.lang = 'en-US';
    r.maxAlternatives = 1;

    r.onstart = () => {
      this.isListening = true;
      this.onListenStart?.();
    };

    r.onend = () => {
      this.isListening = false;
      this.onListenEnd?.();
    };

    r.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      if (final) this.onTranscript?.(final.trim(), true);
      else if (interim) this.onTranscript?.(interim.trim(), false);
    };

    r.onerror = (event) => {
      this.isListening = false;
      const msg = event.error === 'not-allowed'
        ? 'Microphone access denied. Please allow mic permission.'
        : `Voice error: ${event.error}`;
      this.onError?.(msg);
    };
  }

  /* ─── STT Controls ─────────────────────────────── */
  startListening() {
    if (!this._sttSupported) {
      this.onError?.('Speech recognition is not supported in this browser.');
      return false;
    }
    if (this.isListening) return true;
    try {
      this.recognition.start();
      return true;
    } catch (e) {
      this.onError?.('Could not start voice input: ' + e.message);
      return false;
    }
  }

  stopListening() {
    if (!this.recognition || !this.isListening) return;
    try { this.recognition.stop(); } catch (_) {}
  }

  toggleListening() {
    return this.isListening ? (this.stopListening(), false) : this.startListening();
  }

  /* ─── TTS: Backend Base64 Audio ────────────────── */
  async speakFromBase64(base64Audio, onEnd) {
    if (!base64Audio) return;
    this.stopSpeaking();

    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);

      this._currentAudio = new Audio(url);
      this._currentAudio.onended = () => {
        this.isSpeaking = false;
        URL.revokeObjectURL(url);
        onEnd?.();
      };
      this._currentAudio.onerror = () => {
        this.isSpeaking = false;
        URL.revokeObjectURL(url);
        // Fall back to browser TTS
        onEnd?.();
      };

      this.isSpeaking = true;
      await this._currentAudio.play();
    } catch (e) {
      this.isSpeaking = false;
      console.warn('[Voice] base64 playback failed, falling back to browser TTS', e);
    }
  }

  /* ─── TTS: Browser SpeechSynthesis fallback ──── */
  speakText(text, rate = 0.95, pitch = 1.0, onEnd) {
    if (!this._ttsSupported) return;
    this.stopSpeaking();

    // Strip markdown-ish fragments
    const clean = text.replace(/[*_~`#]/g, '').substring(0, 300);
    const utt = new SpeechSynthesisUtterance(clean);
    utt.rate = rate;
    utt.pitch = pitch;
    utt.lang = 'en-US';

    // Prefer a calm English voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Samantha'))
    ) || voices.find(v => v.lang.startsWith('en'));
    if (preferred) utt.voice = preferred;

    utt.onstart = () => { this.isSpeaking = true; };
    utt.onend   = () => { this.isSpeaking = false; onEnd?.(); };
    utt.onerror = () => { this.isSpeaking = false; };

    this._currentUtterance = utt;
    window.speechSynthesis.speak(utt);
  }

  stopSpeaking() {
    if (this._currentAudio) {
      this._currentAudio.pause();
      this._currentAudio = null;
    }
    if (this._ttsSupported && window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
    }
    this.isSpeaking = false;
  }

  /* ─── Diagnostics ──────────────────────────────── */
  get sttSupported() { return this._sttSupported; }
  get ttsSupported() { return this._ttsSupported; }
}

window.voiceManager = new VoiceManager();
