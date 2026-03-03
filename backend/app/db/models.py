"""MindEase PRO — SQLAlchemy Models"""
import uuid
from datetime import datetime, timezone

from app.extensions import db


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    last_active = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)
    message_count = db.Column(db.Integer, default=0, nullable=False)
    preferred_tone = db.Column(db.String(32), default="empathetic", nullable=False)
    tts_enabled = db.Column(db.Boolean, default=False, nullable=False)

    mood_entries = db.relationship("MoodEntry", backref="user", lazy="dynamic",
                                   foreign_keys="MoodEntry.session_id",
                                   primaryjoin="User.session_id == MoodEntry.session_id")
    chat_messages = db.relationship("ChatMessage", backref="user", lazy="dynamic",
                                    foreign_keys="ChatMessage.session_id",
                                    primaryjoin="User.session_id == ChatMessage.session_id")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "preferred_tone": self.preferred_tone,
            "tts_enabled": self.tts_enabled,
        }


class MoodEntry(db.Model):
    __tablename__ = "mood_entries"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(db.String(64), db.ForeignKey("users.session_id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=_now, nullable=False)
    emotion = db.Column(db.String(32), nullable=False)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    valence = db.Column(db.Float, nullable=False, default=0.0)
    arousal = db.Column(db.Float, nullable=False, default=0.0)
    user_message = db.Column(db.Text, nullable=False, default="")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion,
            "confidence": self.confidence,
            "valence": self.valence,
            "arousal": self.arousal,
            "user_message": self.user_message,
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(db.String(64), db.ForeignKey("users.session_id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=_now, nullable=False)
    role = db.Column(db.String(16), nullable=False)  # "user" | "assistant"
    content = db.Column(db.Text, nullable=False)
    emotion_detected = db.Column(db.String(32), nullable=True)
    rag_used = db.Column(db.Boolean, default=False, nullable=False)
    response_time_ms = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "content": self.content,
            "emotion_detected": self.emotion_detected,
            "rag_used": self.rag_used,
            "response_time_ms": self.response_time_ms,
        }


class ExerciseLog(db.Model):
    __tablename__ = "exercise_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=_now, nullable=False)
    exercise_type = db.Column(db.String(64), nullable=False)
    duration_seconds = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "exercise_type": self.exercise_type,
            "duration_seconds": self.duration_seconds,
            "completed": self.completed,
        }
