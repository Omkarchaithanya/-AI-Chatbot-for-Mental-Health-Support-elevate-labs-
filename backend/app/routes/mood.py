"""MindEase PRO — Mood Tracking Routes"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.db.models import ExerciseLog, MoodEntry

logger = logging.getLogger("mindease.routes.mood")
mood_bp = Blueprint("mood", __name__)


def _trend_label(slope: float) -> str:
    if slope > 0.02:
        return "improving"
    if slope < -0.02:
        return "declining"
    return "stable"


def _compute_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(values) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
    den = sum((xi - mean_x) ** 2 for xi in x) or 1.0
    return round(num / den, 4)


@mood_bp.route("/mood/history/<session_id>", methods=["GET"])
def mood_history(session_id: str):
    days = int(request.args.get("days", 7))
    limit = int(request.args.get("limit", 50))

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    entries = (
        MoodEntry.query
        .filter(
            MoodEntry.session_id == session_id,
            MoodEntry.timestamp >= cutoff,
        )
        .order_by(MoodEntry.timestamp.asc())
        .limit(limit)
        .all()
    )

    if not entries:
        return jsonify({
            "session_id": session_id,
            "entries": [],
            "summary": {
                "avg_valence": 0.0,
                "most_common_emotion": "neutral",
                "emotion_distribution": {},
                "trend": "stable",
                "trend_value": 0.0,
                "streak_days": 0,
                "total_entries": 0,
            },
            "chart_data": {"labels": [], "valence": [], "emotions": []},
        }), 200

    valences = [e.valence for e in entries]
    emotions = [e.emotion for e in entries]
    emotion_dist = dict(Counter(emotions))
    most_common = Counter(emotions).most_common(1)[0][0]
    avg_valence = round(sum(valences) / len(valences), 3)
    slope = _compute_slope(valences)
    streak_days = len({e.timestamp.date() for e in entries})

    return jsonify({
        "session_id": session_id,
        "entries": [e.to_dict() for e in entries],
        "summary": {
            "avg_valence": avg_valence,
            "most_common_emotion": most_common,
            "emotion_distribution": emotion_dist,
            "trend": _trend_label(slope),
            "trend_value": slope,
            "streak_days": streak_days,
            "total_entries": len(entries),
        },
        "chart_data": {
            "labels": [e.timestamp.isoformat() for e in entries],
            "valence": valences,
            "emotions": emotions,
        },
    }), 200


@mood_bp.route("/mood/insights/<session_id>", methods=["GET"])
def mood_insights(session_id: str):
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    entries = (
        MoodEntry.query
        .filter(
            MoodEntry.session_id == session_id,
            MoodEntry.timestamp >= cutoff,
        )
        .order_by(MoodEntry.timestamp.asc())
        .all()
    )

    insights: list[dict] = []
    suggested_exercise = None

    if not entries:
        insights.append({
            "type": "suggestion",
            "text": "Start chatting to build your mood history and see personalized insights.",
        })
        return jsonify({"insights": insights, "suggested_exercise": None}), 200

    valences = [e.valence for e in entries]
    emotions = [e.emotion for e in entries]
    slope = _compute_slope(valences[-7:] if len(valences) >= 7 else valences)
    most_common = Counter(emotions).most_common(1)[0][0]
    avg = round(sum(valences) / len(valences), 3)

    # Trend insight
    if slope > 0.02:
        insights.append({"type": "positive", "text": f"Your mood has been improving over the last {len(entries)} sessions. Keep it up!"})
    elif slope < -0.02:
        insights.append({"type": "pattern", "text": "Your mood has been a bit lower lately. Remember, it's okay to have difficult periods."})
    else:
        insights.append({"type": "pattern", "text": f"Your mood has been fairly stable recently, mostly feeling {most_common}."})

    # Dominant emotion insight
    if most_common == "sadness":
        insights.append({"type": "suggestion", "text": "Sadness has been frequent. Behavioral activation exercises can gently lift mood over time."})
        suggested_exercise = "gratitude_three"
    elif most_common in ("fear", "surprise"):
        insights.append({"type": "suggestion", "text": "Anxiety seems to be a recurring theme. Grounding techniques can help anchor you in the present."})
        suggested_exercise = "grounding_54321"
    elif most_common == "anger":
        insights.append({"type": "suggestion", "text": "Frustration has been common. Box breathing is proven to lower physiological arousal quickly."})
        suggested_exercise = "box_breathing"
    elif most_common in ("joy", "love"):
        insights.append({"type": "positive", "text": "You've been experiencing more positive emotions lately — that's wonderful!"})

    # Average valence
    if avg < -0.3:
        insights.append({"type": "suggestion", "text": "Try the 4-7-8 breathing exercise before sleep — it activates your body's relaxation response."})
        suggested_exercise = suggested_exercise or "breathing_4_7_8"
    elif avg > 0.4:
        insights.append({"type": "positive", "text": "Your average emotional state has been positive. Keep nurturing those moments of joy!"})

    # Exercise suggestion if none done recently
    recent_exercise = (
        ExerciseLog.query
        .filter(
            ExerciseLog.session_id == session_id,
            ExerciseLog.completed.is_(True),
        )
        .order_by(ExerciseLog.timestamp.desc())
        .first()
    )
    if not recent_exercise and not suggested_exercise:
        insights.append({"type": "suggestion", "text": "You haven't tried a mindfulness exercise yet. Start with 4-7-8 breathing — just 4 minutes!"})
        suggested_exercise = "breathing_4_7_8"

    return jsonify({"insights": insights[:4], "suggested_exercise": suggested_exercise}), 200
