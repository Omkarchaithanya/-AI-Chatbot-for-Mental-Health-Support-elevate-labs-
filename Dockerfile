# ── MindEase PRO — Dockerfile ──────────────────────────────────────
FROM python:3.10-slim

# System deps: ffmpeg (audio), build tools for faiss/torch wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    git \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Pre-download NLTK data (used by better-profanity / tokenisers)
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)" || true

# Create writable dirs
RUN mkdir -p backend/logs backend/data

# Non-root user for security
RUN adduser --disabled-password --gecos '' mindease
RUN chown -R mindease:mindease /app
USER mindease

WORKDIR /app/backend

# Expose default port
EXPOSE 5000

# Use Gunicorn with eventlet worker for SocketIO
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "run:app"]
