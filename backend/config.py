"""MindEase PRO — Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

def _bool(val: str, default: bool = False) -> bool:
    return str(val).lower() in ("1", "true", "yes") if val is not None else default


class Config:
    # Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-super-secret-key-mindease")
    DEBUG: bool = _bool(os.getenv("DEBUG"), False)
    PORT: int = int(os.getenv("PORT", 5000))

    # AI Models
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "facebook/blenderbot-400M-distill")
    EMOTION_MODEL: str = os.getenv("EMOTION_MODEL", "j-hartmann/emotion-english-distilroberta-base")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # RAG
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", 3))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", 0.4))
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "data/cbt_knowledge_base.json")
    EMBEDDINGS_CACHE_PATH: str = os.getenv("EMBEDDINGS_CACHE_PATH", "data/embeddings_cache.pkl")

    # Generation
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", 150))
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", 8))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.85))
    TOP_P: float = float(os.getenv("TOP_P", 0.92))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///mindease.db")

    # Rate Limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "30 per minute")

    # Logging
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/sessions.jsonl")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # App version
    VERSION: str = "2.0.0"
