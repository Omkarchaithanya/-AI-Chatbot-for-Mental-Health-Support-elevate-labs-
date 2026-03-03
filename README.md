# MindEase PRO 🧠

> An advanced AI-powered mental health support platform with real-time WebSocket streaming, voice I/O, CBT-informed RAG, mood tracking, and guided exercises.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser SPA                            │
│  index.html · CSS (main/chat/dashboard/exercises)           │
│  JS: app → socket → chat → voice → dashboard → exercises    │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / WebSocket (Socket.IO)
┌───────────────────────▼─────────────────────────────────────┐
│                  Flask 3.0 + Eventlet                        │
│  /api/chat  /api/mood  /api/sessions  /api/exercises         │
│                                                             │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌─────────┐  │
│  │Emotion   │  │RAG Engine │  │ Chatbot    │  │  TTS    │  │
│  │Detector  │→ │(FAISS+ST) │→ │(BlenderBot)│→ │(gTTS)   │  │
│  └──────────┘  └───────────┘  └────────────┘  └─────────┘  │
│                                                             │
│  ┌────────────────┐  ┌───────────────┐                      │
│  │ Safety Filters │  │ Rate Limiter  │                      │
│  │(3-level crisis)│  │(session-based)│                      │
│  └────────────────┘  └───────────────┘                      │
│                                                             │
│               SQLite (WAL mode) via SQLAlchemy              │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

| Category | Details |
|---|---|
| **AI Chat** | BlenderBot-400M, streaming tokens via WebSocket, 5-turn context memory |
| **Emotion AI** | DistilRoBERTa real-time classification, rule-based fallback, valence/arousal |
| **RAG** | 40-entry CBT knowledge base, SentenceTransformer + FAISS, emotion-boosted retrieval |
| **Voice I/O** | Web Speech API (STT), gTTS backend + SpeechSynthesis fallback (TTS) |
| **Safety** | 3-level crisis detection, 988/911 resources, profanity filter with clinical override |
| **Exercises** | 6 guided exercises: 4-7-8 breathing, box breathing, 5-4-3-2-1 grounding, body scan, gratitude, CBT reframe |
| **Mood Dashboard** | Chart.js timeline + emotion donut, AI insights, CSV export, streak tracker |
| **Rate Limiting** | 30 msg/min + 200 msg/hr per session (session-based, proxy-safe) |
| **Deployment** | Docker + docker-compose, Render.com Procfile, Gunicorn eventlet |

---

## Quick Start (Local)

```bash
# 1. Clone and enter
cd "AI Chatbot for Mental Health Support/mindease-pro"

# 2. Set up Python environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set a SECRET_KEY

# 5. Run
cd backend
python run.py
```

Open `http://localhost:5000` in your browser. AI models are downloaded automatically on first run (~2GB).

---

## Docker Start

```bash
# Build and run
docker-compose up --build

# Background
docker-compose up -d --build

# Logs
docker-compose logs -f mindease
```

App available at `http://localhost:5000`.

---

## Render.com Deployment

1. Fork / push to GitHub.
2. Create a new **Web Service** on Render, point to repo root.
3. Set **Build Command**: `pip install -r backend/requirements.txt`
4. Set **Start Command**: `cd backend && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 run:app`
5. Add environment variables from `.env.example` in the Render dashboard.
6. Note: First deploy takes longer (model downloads). Use a persistent disk for `/app/backend/data`.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Coverage report:
```bash
pytest tests/ --cov=app --cov-report=html
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send message, get AI response |
| `WS` | `chat_message` | Stream response tokens via Socket.IO |
| `POST` | `/api/sessions/new` | Create session |
| `GET` | `/api/sessions/<id>` | Get session info |
| `PATCH` | `/api/sessions/<id>` | Update preferences |
| `DELETE` | `/api/sessions/<id>` | Delete session + history |
| `GET` | `/api/mood/history/<id>` | Mood entries + chart data |
| `GET` | `/api/mood/insights/<id>` | AI-generated insight cards |
| `GET` | `/api/exercises/list` | Exercise catalogue |
| `POST` | `/api/exercises/log` | Log completed exercise |
| `GET` | `/api/health` | Health check |

---

## AI Models Used

| Model | Purpose | Size |
|---|---|---|
| `facebook/blenderbot-400M-distill` | Conversational AI | ~800MB |
| `j-hartmann/emotion-english-distilroberta-base` | Emotion classification | ~330MB |
| `sentence-transformers/all-MiniLM-L6-v2` | CBT knowledge retrieval | ~90MB |

All models are downloaded automatically from HuggingFace Hub on first run.

---

## Project Structure

```
mindease-pro/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory
│   │   ├── ai/                  # Emotion, RAG, Chatbot, TTS, Personalizer
│   │   ├── db/                  # Models, database helpers
│   │   ├── routes/              # chat, mood, sessions, exercises, health
│   │   ├── safety/              # Crisis filters, rate limiter
│   │   └── utils/               # Logger, helpers
│   ├── data/
│   │   └── cbt_knowledge_base.json
│   ├── tests/                   # pytest test suite (8 files)
│   ├── config.py
│   └── run.py
├── frontend/
│   ├── index.html               # SPA shell
│   ├── css/                     # main, chat, dashboard, exercises
│   └── js/                      # app, socket, chat, voice, dashboard, exercises, profile
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── .env.example
└── .gitignore
```

---

## Crisis Disclaimer

> MindEase PRO is **not a substitute** for professional mental health care. In any life-threatening emergency, call **911** or the **988 Suicide & Crisis Lifeline** (call or text **988**).

---

## License

MIT
