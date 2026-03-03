"""MindEase PRO — Session Management Routes"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.db.database import get_or_create_user
from app.db.models import ChatMessage, ExerciseLog, MoodEntry, User

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions/new", methods=["POST"])
def new_session():
    session_id = str(uuid.uuid4())
    user = get_or_create_user(session_id)
    return jsonify({"session_id": session_id, "created_at": user.created_at.isoformat()}), 201


def _enrich_session(user: User) -> dict:
    """Return user dict enriched with computed stats."""
    base = user.to_dict()

    # Live message count from ChatMessage table (user messages only)
    try:
        user_msg_count = ChatMessage.query.filter_by(
            session_id=user.session_id, role="user"
        ).count()
        base["message_count"] = user_msg_count
    except Exception:
        pass  # keep column value from to_dict()

    # Most common emotion from mood entries
    entries = MoodEntry.query.filter_by(session_id=user.session_id).all()
    if entries:
        counts = Counter(e.emotion for e in entries)
        base["most_common_emotion"] = counts.most_common(1)[0][0].capitalize()
        # Days active = distinct calendar dates with mood entries
        dates = {e.timestamp.date() for e in entries}
        base["days_active"] = len(dates)
    else:
        base["most_common_emotion"] = "Neutral"
        base["days_active"] = 0

    # Exercises completed
    try:
        ex_count = ExerciseLog.query.filter_by(session_id=user.session_id).count()
    except Exception:
        ex_count = 0
    base["exercises_completed"] = ex_count

    return base


@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        return jsonify({"error": "Session not found."}), 404
    return jsonify(_enrich_session(user)), 200


@sessions_bp.route("/sessions/<session_id>", methods=["PATCH"])
def update_session(session_id: str):
    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        return jsonify({"error": "Session not found."}), 404

    data = request.get_json(silent=True) or {}
    if "preferred_tone" in data:
        allowed = {"empathetic", "professional", "friendly", "gentle", "validating", "balanced"}
        if data["preferred_tone"] in allowed:
            user.preferred_tone = data["preferred_tone"]
    if "tts_enabled" in data:
        user.tts_enabled = bool(data["tts_enabled"])

    db.session.commit()
    return jsonify(user.to_dict()), 200


@sessions_bp.route("/sessions/<session_id>/history", methods=["GET"])
def session_history(session_id: str):
    limit = int(request.args.get("limit", 50))
    messages = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(limit)
        .all()
    )
    return jsonify({"session_id": session_id, "messages": [m.to_dict() for m in messages]}), 200


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    try:
        MoodEntry.query.filter_by(session_id=session_id).delete()
        ChatMessage.query.filter_by(session_id=session_id).delete()
        ExerciseLog.query.filter_by(session_id=session_id).delete()
        User.query.filter_by(session_id=session_id).delete()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
    return jsonify({"message": "Session data deleted."}), 200
