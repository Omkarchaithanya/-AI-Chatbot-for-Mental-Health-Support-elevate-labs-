/**
 * MindEase PRO — Mood Dashboard
 * Chart.js timeline + donut, insights cards, streak tracker, export.
 */

class MoodDashboard {
  constructor() {
    this._sessionId   = null;
    this._timelineChart = null;
    this._donutChart    = null;
    this._days = 7;

    /* DOM */
    this._container   = document.getElementById('view-mood');
    this._summaryAvg  = document.getElementById('today-mood');
    this._summaryTotal= document.getElementById('total-messages');
    this._streakEl    = document.getElementById('streak-days');
    this._streakDays  = null;  // no calendar element in HTML
    this._insightsList= document.getElementById('insights-list');
    this._exportBtn   = document.getElementById('export-journal-btn');
    this._refreshBtn  = document.getElementById('refresh-insights');

    this._bindControls();
  }

  init(sessionId) {
    this._sessionId = sessionId;
    this._initCharts();
    this.refresh();
  }

  async refresh() {
    await Promise.all([this._loadHistory(), this._loadInsights()]);
  }

  /* ─── Chart Initialisation ─────────────────────── */
  _initCharts() {
    if (typeof Chart === 'undefined') {
      setTimeout(() => this._initCharts(), 200);
      return;
    }
    const tlCtx = document.getElementById('mood-timeline-chart')?.getContext('2d');
    if (tlCtx) {
      this._timelineChart = new Chart(tlCtx, {
        type: 'line',
        data: { labels: [], datasets: [{
          label: 'Mood Valence',
          data: [],
          borderColor: '#1B6CA8',
          backgroundColor: 'rgba(27,108,168,0.08)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#1B6CA8',
          pointRadius: 5,
          pointHoverRadius: 7,
        }]},
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` Valence: ${ctx.parsed.y.toFixed(2)}`,
              }
            }
          },
          scales: {
            y: {
              min: -1, max: 1,
              grid: { color: 'rgba(0,0,0,0.05)' },
              ticks: { callback: v => v > 0 ? `+${v}` : v }
            },
            x: {
              grid: { display: false },
              ticks: { maxTicksLimit: 7 }
            }
          }
        }
      });
    }

    const donutCtx = document.getElementById('emotion-donut-chart')?.getContext('2d');
    if (donutCtx) {
      this._donutChart = new Chart(donutCtx, {
        type: 'doughnut',
        data: { labels: [], datasets: [{ data: [], backgroundColor: [] }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}%` } }
          },
          cutout: '65%',
        }
      });
    }
  }

  /* ─── Data Load ────────────────────────────────── */
  async _loadHistory() {
    if (!this._sessionId) return;
    try {
      const resp = await fetch(`/api/mood/history/${this._sessionId}?days=${this._days}&limit=100`);
      if (!resp.ok) return;
      const data = await resp.json();
      this._updateCharts(data);
      this._updateSummary(data.summary);
      this._updateStreak(data.summary);
    } catch (e) {
      console.warn('[Dashboard] history load failed', e);
    }
  }

  async _loadInsights() {
    if (!this._sessionId) return;
    if (this._insightsList) this._insightsList.innerHTML =
      '<p class="insight-loading">Analyzing your patterns…</p>';
    try {
      const resp = await fetch(`/api/mood/insights/${this._sessionId}`);
      if (!resp.ok) return;
      const data = await resp.json();
      this._renderInsights(data.insights || []);
    } catch (e) {
      if (this._insightsList)
        this._insightsList.innerHTML = '<p class="insight-loading">Could not load insights.</p>';
    }
  }

  /* ─── Chart Updates ────────────────────────────── */
  _updateCharts(data) {
    const cd = data.chart_data;
    if (!cd) return;

    if (this._timelineChart) {
      this._timelineChart.data.labels   = cd.labels || [];
      this._timelineChart.data.datasets[0].data = cd.valence || [];
      this._timelineChart.update();
    }

    if (this._donutChart && cd.emotions) {
      const counts = {};
      (cd.emotions || []).forEach(e => { counts[e] = (counts[e] || 0) + 1; });
      const total = Object.values(counts).reduce((a, b) => a + b, 1);
      const COLORS = {
        joy:'#90BE6D', sadness:'#577590', anxiety:'#F9C74F', anger:'#F94144',
        fear:'#F3722C', neutral:'#ADB5BD', surprise:'#4D908E', disgust:'#277DA1'
      };
      this._donutChart.data.labels   = Object.keys(counts);
      this._donutChart.data.datasets[0].data = Object.values(counts).map(v => Math.round(v/total*100));
      this._donutChart.data.datasets[0].backgroundColor = Object.keys(counts).map(e => COLORS[e] || '#ADB5BD');
      this._donutChart.update();
    }
  }

  _updateSummary(summary) {
    if (!summary) return;
    if (this._summaryAvg) {
      const v = summary.avg_valence ?? 0;
      const label = v > 0.3 ? '😊 Positive' : v < -0.3 ? '😔 Low' : '😐 Neutral';
      this._summaryAvg.textContent = label;
    }
    if (this._summaryTotal) {
      this._summaryTotal.textContent = `${summary.total_entries ?? summary.emotion_distribution ? Object.values(summary.emotion_distribution || {}).reduce((a,b)=>a+b,0) : 0}`;
    }
  }

  _updateStreak(summary) {
    if (!summary) return;
    if (this._streakEl) this._streakEl.textContent = `${summary.streak_days ?? 0}`;
    if (this._streakDays && summary.recent_emotions) {
      this._streakDays.innerHTML = '';
      const VALENCE = {
        joy:0.9,neutral:0,sadness:-0.8,anxiety:-0.5,anger:-0.7,fear:-0.6,surprise:0.4,disgust:-0.5
      };
      (summary.recent_emotions || []).slice(-7).forEach(e => {
        const dot = document.createElement('div');
        const v = VALENCE[e] ?? 0;
        dot.className = `streak-day ${v > 0.3 ? 'active' : v < -0.3 ? 'sad' : 'neutral'}`;
        dot.title = e;
        this._streakDays.appendChild(dot);
      });
    }
  }

  /* ─── Insights ─────────────────────────────────── */
  _renderInsights(insights) {
    if (!this._insightsList) return;
    if (!insights.length) {
      this._insightsList.innerHTML =
        '<p class="insight-loading">Keep chatting to unlock personalized insights.</p>';
      return;
    }
    this._insightsList.innerHTML = '';
    const ICONS = { pattern:'🔍', positive:'🌱', suggestion:'💡' };
    insights.forEach(ins => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.innerHTML = `
        <span class="insight-icon">${ICONS[ins.type] || '💭'}</span>
        <div class="insight-body">
          <span class="insight-badge ${ins.type}">${ins.type}</span>
          <p class="insight-text">${ins.text}</p>
        </div>`;
      this._insightsList.appendChild(item);
    });
  }

  /* ─── Controls ─────────────────────────────────── */
  _bindControls() {
    // Range buttons (7d / 14d / 30d)
    document.querySelectorAll('.chart-range-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.chart-range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this._days = parseInt(btn.dataset.days) || 7;
        this._loadHistory();
      });
    });

    // Refresh insights
    this._refreshBtn?.addEventListener('click', () => this._loadInsights());

    // Export
    this._exportBtn?.addEventListener('click', () => this._exportData());
  }

  /* ─── CSV Export ────────────────────────────────── */
  async _exportData() {
    if (!this._sessionId) return;
    try {
      const resp = await fetch(`/api/mood/history/${this._sessionId}?days=90&limit=500`);
      const data = await resp.json();
      const entries = data.entries || [];
      const header  = ['timestamp','emotion','confidence','valence','arousal'];
      const rows    = entries.map(e =>
        [e.timestamp, e.emotion, e.confidence, e.valence, e.arousal].join(',')
      );
      const csv = [header.join(','), ...rows].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url  = URL.createObjectURL(blob);
      const a    = Object.assign(document.createElement('a'), {
        href: url, download: `mindease_mood_${Date.now()}.csv`
      });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.warn('[Dashboard] export failed', e);
    }
  }
}

window.MoodDashboard = MoodDashboard;
