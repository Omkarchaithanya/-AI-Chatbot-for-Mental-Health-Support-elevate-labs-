/**
 * MindEase PRO — Exercise Player
 * Breathing animations (requestAnimationFrame), step-by-step, Web Audio tones, logging.
 */

class ExercisePlayer {
  constructor() {
    /* State */
    this._current     = null;   // exercise definition object
    this._phase       = 0;      // current step index
    this._cycleCount  = 0;
    this._totalCycles = 3;
    this._running     = false;
    this._rafId       = null;
    this._startTime   = 0;
    this._sessionId   = null;

    /* Web Audio */
    this._audioCtx = null;

    /* DOM */
    this._overlay      = document.getElementById('exercise-overlay');
    this._panelTitle   = document.getElementById('exercise-title');
    this._breathCircle = document.getElementById('breathing-circle');
    this._breathLabel  = document.getElementById('breathing-phase-text');
    this._breathCounter= document.getElementById('breathing-countdown');
    this._stepsEl      = document.getElementById('step-content-area');
    this._progressFill = document.getElementById('progress-ring-fill');
    this._startBtn     = document.getElementById('exercise-start-btn');
    this._stopBtn      = document.getElementById('exercise-skip-btn');
    this._completion   = document.getElementById('exercise-complete');
    this._confetti     = document.getElementById('confetti');
    this._closeBtn     = document.getElementById('close-exercise-btn');

    /* Exercise catalogue */
    this._catalogue     = null;
    this._fullExercises = {};   // id → full exercise with phases

    this._bindControls();
  }

  init(sessionId) {
    this._sessionId = sessionId;
    this._loadCatalogue();
  }

  /* ─── Load catalogue from API ──────────────────── */
  async _loadCatalogue() {
    try {
      const resp = await fetch('/api/exercises');
      if (!resp.ok) { this._renderBuiltInGrid(); return; }
      this._catalogue = await resp.json();
      this._renderGrid();

      // Pre-fetch full exercise details (with phases) in the background
      const ids = (this._catalogue.exercises || []).map(e => e.id).filter(Boolean);
      await Promise.all(ids.map(async id => {
        try {
          const r = await fetch(`/api/exercises/${id}`);
          if (r.ok) {
            const full = await r.json();
            if (!this._fullExercises) this._fullExercises = {};
            this._fullExercises[id] = full;
          }
        } catch (_) {}
      }));
    } catch (_) {
      this._renderBuiltInGrid();
    }
  }

  /* ─── Render exercise grid ──────────────────────── */
  _renderGrid() {
    const grid = document.getElementById('exercise-grid');
    if (!grid) return;
    const exercises = this._catalogue?.exercises || [];
    if (!exercises.length) { this._renderBuiltInGrid(); return; }

    grid.innerHTML = '';
    exercises.forEach(ex => {
      grid.appendChild(this._makeCard(
        ex.id || ex.type,
        ex.name,
        ex.benefits || ex.description || '',
        ex.category || 'breathing'
      ));
    });
  }

  _renderBuiltInGrid() {
    const grid = document.getElementById('exercise-grid');
    if (!grid) return;
    const builtIn = [
      { id: 'breathing_4_7_8', name: '4-7-8 Breathing', desc: 'Calm anxiety with this ancient technique', category: 'breathing' },
      { id: 'box_breathing',   name: 'Box Breathing',   desc: 'Balance your nervous system in 4 minutes', category: 'breathing' },
      { id: 'grounding_54321', name: '5-4-3-2-1 Grounding', desc: 'Anchor yourself with your 5 senses', category: 'grounding' },
    ];
    grid.innerHTML = '';
    builtIn.forEach(ex => grid.appendChild(this._makeCard(ex.id, ex.name, ex.desc, ex.category)));
  }

  _makeCard(id, name, desc, category) {
    const ICONS = { breathing: '🫁', grounding: '🌿', meditation: '🧘', relaxation: '😌', mindfulness: '🌸', cbt: '💭', positive_psychology: '🌻' };
    const descText = Array.isArray(desc) ? desc[0] : (desc || '');
    const card = document.createElement('div');
    card.className = 'exercise-card';
    card.dataset.exercise = id;
    card.innerHTML = `
      <div class="exercise-completed-badge">✅</div>
      <div class="exercise-emoji">${ICONS[category] || '✨'}</div>
      <div class="exercise-name">${name}</div>
      <div class="exercise-meta">
        <span class="exercise-tag">${category.replace(/_/g, ' ')}</span>
      </div>
      ${descText ? `<p style="font-size:11px;color:var(--color-text-muted);margin:4px 0 0;text-align:center;line-height:1.4;padding:0 4px">${descText}</p>` : ''}`;
    card.addEventListener('click', () => this.open(id));
    return card;
  }

  /* ─── Open an exercise ─────────────────────────── */
  open(exerciseId) {
    const ex = this._getExercise(exerciseId);
    if (!ex) return;

    this._current      = ex;
    this._cycleCount   = 0;
    this._phase        = 0;
    this._running      = false;
    this._totalCycles  = ex.cycles || 3;  // use exercise's own cycle count

    if (this._panelTitle)  this._panelTitle.textContent = ex.name;
    if (this._breathCircle) this._breathCircle.className = 'breathing-circle';
    if (this._breathLabel)  this._breathLabel.textContent = ex.phases.length ? 'Press Start to begin' : 'Ready';
    if (this._breathCounter)this._breathCounter.textContent = `0 / ${this._totalCycles} cycles`;
    if (this._completion)   this._completion.style.display = 'none';
    if (this._confetti)     this._confetti.innerHTML = '';

    this._renderSteps(ex.phases || []);
    this._resetProgress();

    this._overlay?.removeAttribute('hidden');
    this._overlay?.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  close() {
    this._stop();
    this._overlay?.classList.remove('open');
    this._overlay?.setAttribute('hidden', '');
    document.body.style.overflow = '';
  }

  /* ─── Get exercise (full data first, then built-in) ─ */
  _getExercise(id) {
    // Full pre-fetched data has phases
    if (this._fullExercises?.[id]) {
      const ex = this._fullExercises[id];
      return { name: ex.name, type: id, phases: ex.phases || [], cycles: ex.cycles || 3 };
    }
    // Built-in fallback
    if (this._BUILT_IN[id]) return this._BUILT_IN[id];
    // Catalogue only (no phases yet) — show with empty phases but still open
    if (this._catalogue) {
      const ex = (this._catalogue.exercises || []).find(e => e.id === id);
      if (ex) return { name: ex.name, type: id, phases: [], cycles: 3 };
    }
    return null;
  }

  /* ─── Built-in fallback definitions ─────────────── */
  get _BUILT_IN() {
    return {
      breathing_4_7_8: {
        name: '4-7-8 Breathing',
        type: 'breathing_4_7_8',
        phases: [
          { name: 'Inhale', duration: 4,  instruction: 'Breathe in slowly through your nose' },
          { name: 'Hold',   duration: 7,  instruction: 'Hold your breath gently' },
          { name: 'Exhale', duration: 8,  instruction: 'Exhale completely through your mouth' },
        ]
      },
      box_breathing: {
        name: 'Box Breathing',
        type: 'box_breathing',
        phases: [
          { name: 'Inhale', duration: 4, instruction: 'Breathe in for 4 counts' },
          { name: 'Hold',   duration: 4, instruction: 'Hold for 4 counts' },
          { name: 'Exhale', duration: 4, instruction: 'Exhale for 4 counts' },
          { name: 'Hold',   duration: 4, instruction: 'Hold empty for 4 counts' },
        ]
      },
      grounding_54321: {
        name: '5-4-3-2-1 Grounding',
        type: 'grounding_54321',
        phases: [
          { name: '5 Things you SEE',   duration: 30, instruction: 'Look around and name 5 things you can see right now.' },
          { name: '4 Things you TOUCH', duration: 30, instruction: 'Notice 4 things you can feel or touch.' },
          { name: '3 Things you HEAR',  duration: 30, instruction: 'Listen and name 3 sounds around you.' },
          { name: '2 Things you SMELL', duration: 20, instruction: 'Find 2 scents you can notice.' },
          { name: '1 Thing you TASTE',  duration: 10, instruction: 'Notice 1 thing you can taste.' },
        ]
      }
    };
  }

  /* ─── Render Steps ─────────────────────────────── */
  _renderSteps(phases) {
    if (!this._stepsEl) return;
    this._stepsEl.innerHTML = '';
    phases.forEach((phase, i) => {
      const item = document.createElement('div');
      item.className = 'step-item';
      item.dataset.index = i;
      item.innerHTML = `
        <div class="step-number">${i + 1}</div>
        <div class="step-content">
          <p class="step-title">${phase.name}</p>
          <p class="step-desc">${phase.instruction || ''}</p>
          <p class="step-timer" id="step-timer-${i}"></p>
        </div>`;
      this._stepsEl.appendChild(item);
    });
  }

  /* ─── Controls ─────────────────────────────────── */
  _bindControls() {
    this._startBtn?.addEventListener('click', () => this._start());
    this._stopBtn?.addEventListener('click',  () => this._stop());
    this._closeBtn?.addEventListener('click', () => this.close());
    document.getElementById('exercise-done-btn')?.addEventListener('click', () => this.close());

    // Close on overlay backdrop click
    this._overlay?.addEventListener('click', (e) => {
      if (e.target === this._overlay) this.close();
    });
  }

  /* ─── Start / Stop ─────────────────────────────── */
  _start() {
    if (!this._current || this._running) return;
    this._running  = true;
    this._phase    = 0;
    this._cycleCount = 0;
    if (this._startBtn) this._startBtn.style.display = 'none';
    if (this._stopBtn)  this._stopBtn.style.display  = 'inline-flex';
    this._runPhase(0);
  }

  _stop() {
    this._running = false;
    cancelAnimationFrame(this._rafId);
    if (this._startBtn) this._startBtn.style.display = 'inline-flex';
    if (this._stopBtn)  this._stopBtn.style.display  = 'none';
    if (this._breathCircle) this._breathCircle.className = 'breathing-circle';
  }

  /* ─── Phase Runner (requestAnimationFrame) ──────── */
  _runPhase(phaseIdx) {
    if (!this._running) return;
    const phases   = this._current.phases || [];
    const phase    = phases[phaseIdx % phases.length];
    const duration = (phase.duration || 4) * 1000;  // ms

    // Highlight active step
    this._setActiveStep(phaseIdx % phases.length);

    // Breathing circle class
    const nameLower = (phase.name || '').toLowerCase();
    if (this._breathCircle) {
      this._breathCircle.className = 'breathing-circle';  // reset
      if (nameLower.includes('inhale') || nameLower.includes('in')) {
        void this._breathCircle.offsetWidth;  // force reflow for Safari
        this._breathCircle.classList.add('inhale');
      } else if (nameLower.includes('exhale') || nameLower.includes('out')) {
        void this._breathCircle.offsetWidth;
        this._breathCircle.classList.add('exhale');
      } else {
        void this._breathCircle.offsetWidth;
        this._breathCircle.classList.add('hold');
      }
    }
    if (this._breathLabel) this._breathLabel.textContent = phase.name;

    // Audio tone cue
    this._playTone(nameLower.includes('exhale') ? 'low' : nameLower.includes('hold') ? 'mid' : 'high');

    const start = performance.now();
    const tick  = (now) => {
      if (!this._running) return;
      const elapsed = now - start;
      const remaining = Math.max(0, Math.ceil((duration - elapsed) / 1000));

      // Update step timer
      const timerEl = document.getElementById(`step-timer-${phaseIdx % phases.length}`);
      if (timerEl) timerEl.textContent = remaining > 0 ? `${remaining}s` : '';

      // Breath counter
      if (this._breathCounter) {
        this._breathCounter.textContent = `Cycle ${this._cycleCount + 1} / ${this._totalCycles}`;
      }

      // Progress ring
      this._updateProgress((elapsed / duration) * (1 / phases.length) + ((phaseIdx % phases.length) / phases.length));

      if (elapsed < duration) {
        this._rafId = requestAnimationFrame(tick);
      } else {
        // Next phase
        const nextPhaseIdx = phaseIdx + 1;
        if (nextPhaseIdx % phases.length === 0) {
          this._cycleCount++;
        }
        if (this._cycleCount >= this._totalCycles) {
          this._complete();
        } else {
          this._runPhase(nextPhaseIdx);
        }
      }
    };
    this._rafId = requestAnimationFrame(tick);
  }

  /* ─── Step Highlight ───────────────────────────── */
  _setActiveStep(idx) {
    if (!this._stepsEl) return;
    this._stepsEl.querySelectorAll('.step-item').forEach((el, i) => {
      el.classList.toggle('active', i === idx);
      el.classList.toggle('done',   i < idx);
    });
  }

  /* ─── Progress Ring ─────────────────────────────── */
  _resetProgress() {
    if (this._progressFill) this._progressFill.style.strokeDashoffset = '264';
  }

  _updateProgress(fraction) {
    if (this._progressFill) {
      const offset = 264 * (1 - Math.min(1, fraction));
      this._progressFill.style.strokeDashoffset = offset;
    }
  }

  /* ─── Completion ────────────────────────────────── */
  _complete() {
    this._running = false;
    if (this._breathCircle) this._breathCircle.className = 'breathing-circle';
    if (this._startBtn) this._startBtn.style.display = 'none';
    if (this._stopBtn)  this._stopBtn.style.display  = 'none';
    if (this._completion) this._completion.style.display = 'flex';
    this._updateProgress(1);
    this._launchConfetti();
    this._logExercise();
  }

  /* ─── Confetti ──────────────────────────────────── */
  _launchConfetti() {
    if (!this._confetti) return;
    this._confetti.innerHTML = Array.from({ length: 20 })
      .map(() => '<div class="confetti-piece"></div>')
      .join('');
    setTimeout(() => { if (this._confetti) this._confetti.innerHTML = ''; }, 3500);
  }

  /* ─── Log to backend ────────────────────────────── */
  async _logExercise() {
    if (!this._sessionId || !this._current) return;
    const phases   = this._current.phases || [];
    const duration = phases.reduce((s, p) => s + (p.duration || 4), 0) * this._totalCycles;
    try {
      await fetch('/api/exercises/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this._sessionId,
          exercise_id: this._current.type || this._current.name,   // ← correct field name
          duration_seconds: duration,
          completed: true,
        }),
      });
    } catch (_) {}
  }

  /* ─── Web Audio Tones ───────────────────────────── */
  _playTone(type) {
    try {
      if (!this._audioCtx) this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = this._audioCtx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.type = 'sine';
      const freqMap = { high: 528, mid: 440, low: 396 };
      osc.frequency.setValueAtTime(freqMap[type] || 440, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.6);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.6);
    } catch (_) {}
  }
}

window.ExercisePlayer = ExercisePlayer;
