"""MindEase PRO — Health Check Route"""
from flask import Blueprint, current_app, jsonify
from config import Config

health_bp = Blueprint("health", __name__)

_config = Config()


@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "version": _config.VERSION,
        "components": {
            "chatbot": hasattr(current_app, "chatbot") and current_app.chatbot is not None,
            "emotion_detector": hasattr(current_app, "emotion_detector") and current_app.emotion_detector is not None,
            "rag_engine": hasattr(current_app, "rag_engine") and current_app.rag_engine is not None,
            "tts_engine": hasattr(current_app, "tts_engine") and current_app.tts_engine is not None,
        },
    }), 200
