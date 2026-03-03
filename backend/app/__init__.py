"""MindEase PRO — Flask App Factory with SocketIO"""
import os
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from app.extensions import db, socketio, limiter

# Global AI component holders
_chatbot = None
_emotion_detector = None
_rag_engine = None
_tts_engine = None
_safety_filter = None
_personalizer = None


def create_app(config_class=Config) -> Flask:
    """Application factory."""
    config = config_class()

    # Determine frontend path  (backend/app/ → ../../frontend/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.normpath(os.path.join(base_dir, "..", "..", "frontend"))

    app = Flask(
        __name__,
        static_folder=frontend_dir,
        static_url_path="",
    )

    # ── Config ────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MINDEASE_CONFIG"] = config

    # ── Extensions ────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=False,
        engineio_logger=False,
    )
    limiter.init_app(app)

    # ── Logging ───────────────────────────────────────────────────
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── Database ──────────────────────────────────────────────────
    with app.app_context():
        from app.db.database import init_db
        init_db(app)

    # ── AI Components (loaded once at startup) ────────────────────
    with app.app_context():
        _load_ai_components(app, config)

    # ── Blueprints ────────────────────────────────────────────────
    from app.routes.chat import chat_bp
    from app.routes.mood import mood_bp
    from app.routes.sessions import sessions_bp
    from app.routes.exercises import exercises_bp
    from app.routes.health import health_bp

    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(mood_bp, url_prefix="/api")
    app.register_blueprint(sessions_bp, url_prefix="/api")
    app.register_blueprint(exercises_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")

    # ── SPA Catch-all ─────────────────────────────────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        if path and os.path.exists(os.path.join(frontend_dir, path)):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")

    return app


def _load_ai_components(app: Flask, config: Config) -> None:
    """Load all AI components into app context for shared use."""
    global _chatbot, _emotion_detector, _rag_engine, _tts_engine
    global _safety_filter, _personalizer

    logger = logging.getLogger("mindease.startup")

    logger.info("Loading EmotionDetector...")
    from app.ai.emotion_detector import EmotionDetector
    _emotion_detector = EmotionDetector(config.EMOTION_MODEL)
    app.emotion_detector = _emotion_detector

    logger.info("Loading RAGEngine...")
    from app.ai.rag_engine import RAGEngine
    _rag_engine = RAGEngine(config)
    app.rag_engine = _rag_engine

    logger.info("Loading MindEaseChatbot...")
    from app.ai.chatbot import MindEaseChatbot
    _chatbot = MindEaseChatbot(config)
    app.chatbot = _chatbot

    logger.info("Loading TTSEngine...")
    from app.ai.tts_engine import TTSEngine
    _tts_engine = TTSEngine()
    app.tts_engine = _tts_engine

    logger.info("Loading AdvancedInputFilter...")
    from app.safety.filters import AdvancedInputFilter
    _safety_filter = AdvancedInputFilter()
    app.safety_filter = _safety_filter

    logger.info("All AI components loaded ✓")


def get_db():
    """Return the SQLAlchemy db instance."""
    return db
