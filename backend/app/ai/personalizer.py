"""MindEase PRO — User Preference Personalizer"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("mindease.personalizer")

_NEGATIVE_EMOTIONS = {"sadness", "fear", "anger", "disgust"}
_TONE_PREFERENCE_MAP = {
    "sadness": "gentle",
    "fear": "empathetic",
    "anger": "validating",
    "joy": "friendly",
    "neutral": "balanced",
}


class Personalizer:
    """Track user patterns and personalize tone / exercise suggestions."""

    def __init__(self, db_session) -> None:
        self._db = db_session

    def update_preferences(
        self,
        session_id: str,
        emotion_data: Optional[dict],
        response_feedback: Optional[dict] = None,
    ) -> None:
        """Update user tone preference based on detected emotions."""
        if not emotion_data:
            return
        try:
            from app.db.models import User, MoodEntry
            from app.extensions import db

            user = User.query.filter_by(session_id=session_id).first()
            if not user:
                return

            # Look at recent mood entries (last 10) to determine tone
            recent_entries = (
                MoodEntry.query
                .filter_by(session_id=session_id)
                .order_by(MoodEntry.timestamp.desc())
                .limit(10)
                .all()
            )

            if not recent_entries:
                return

            emotion_counts = Counter(e.emotion for e in recent_entries)
            dominant = emotion_counts.most_common(1)[0][0]

            if dominant in ("sadness", "fear"):
                new_tone = "gentle"
            elif dominant == "anger":
                new_tone = "validating"
            elif dominant == "joy":
                new_tone = "friendly"
            else:
                new_tone = "balanced"

            user.preferred_tone = new_tone
            db.session.commit()
            logger.debug(f"Updated {session_id} tone → {new_tone}")
        except Exception as exc:
            logger.error(f"Personalizer update error: {exc}")

    def get_personalized_params(self, session_id: str) -> dict:
        """Return personalized tone, exercise suggestion, and RAG boost categories."""
        try:
            from app.db.models import User, MoodEntry, ExerciseLog

            user = User.query.filter_by(session_id=session_id).first()
            if not user:
                return {"tone": "empathetic", "exercise_suggestion": None, "rag_boost_categories": []}

            tone = user.preferred_tone or "empathetic"

            # Check if exercise suggestion is warranted (3+ negative sessions, no recent exercise)
            exercise_suggestion = None
            recent_moods = (
                MoodEntry.query
                .filter_by(session_id=session_id)
                .order_by(MoodEntry.timestamp.desc())
                .limit(10)
                .all()
            )
            negative_count = sum(1 for m in recent_moods if m.valence < -0.3)
            if negative_count >= 3:
                # Check if user has done an exercise recently (last 3 days)
                cutoff = datetime.now(timezone.utc) - timedelta(days=3)
                recent_exercise = (
                    ExerciseLog.query
                    .filter(
                        ExerciseLog.session_id == session_id,
                        ExerciseLog.timestamp >= cutoff,
                        ExerciseLog.completed.is_(True),
                    )
                    .first()
                )
                if not recent_exercise:
                    exercise_suggestion = "breathing_4_7_8"

            # Determine RAG boost categories based on recent emotions
            rag_boost: list[str] = []
            if recent_moods:
                last_emotion = recent_moods[0].emotion
                from app.ai.rag_engine import _EMOTION_CATEGORY_MAP
                rag_boost = _EMOTION_CATEGORY_MAP.get(last_emotion, [])

            return {
                "tone": tone,
                "exercise_suggestion": exercise_suggestion,
                "rag_boost_categories": rag_boost,
            }
        except Exception as exc:
            logger.error(f"Personalizer params error: {exc}")
            return {"tone": "empathetic", "exercise_suggestion": None, "rag_boost_categories": []}

    def get_streak(self, session_id: str) -> dict:
        """Return streaks and improvement trend for a session."""
        try:
            from app.db.models import MoodEntry, User

            user = User.query.filter_by(session_id=session_id).first()
            total_messages = user.message_count if user else 0

            # All mood entries
            entries = (
                MoodEntry.query
                .filter_by(session_id=session_id)
                .order_by(MoodEntry.timestamp.asc())
                .all()
            )

            if not entries:
                return {
                    "days_active": 0,
                    "total_messages": total_messages,
                    "most_common_emotion": "neutral",
                    "improvement_trend": 0.0,
                }

            # Unique active days
            active_days = len({e.timestamp.date() for e in entries})

            # Most common emotion
            emotion_counts = Counter(e.emotion for e in entries)
            most_common = emotion_counts.most_common(1)[0][0]

            # Valence trend over last 7 sessions
            recent = entries[-7:]
            if len(recent) >= 2:
                valences = [e.valence for e in recent]
                x = list(range(len(valences)))
                n = len(x)
                mean_x = sum(x) / n
                mean_y = sum(valences) / n
                slope = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, valences)) / (
                    sum((xi - mean_x) ** 2 for xi in x) or 1
                )
                trend = round(slope, 4)
            else:
                trend = 0.0

            return {
                "days_active": active_days,
                "total_messages": total_messages,
                "most_common_emotion": most_common,
                "improvement_trend": trend,
            }
        except Exception as exc:
            logger.error(f"Streak error: {exc}")
            return {
                "days_active": 0,
                "total_messages": 0,
                "most_common_emotion": "neutral",
                "improvement_trend": 0.0,
            }
