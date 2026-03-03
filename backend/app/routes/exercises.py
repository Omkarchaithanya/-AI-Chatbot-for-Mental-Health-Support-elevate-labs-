"""MindEase PRO — Mindfulness Exercises Routes"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.db.models import ExerciseLog

logger = logging.getLogger("mindease.routes.exercises")
exercises_bp = Blueprint("exercises", __name__)

# Full exercise data
_EXERCISES: list[dict] = [
    {
        "id": "breathing_4_7_8",
        "name": "4-7-8 Breathing",
        "category": "breathing",
        "description": (
            "The 4-7-8 breathing technique is a simple but powerful relaxation method developed by "
            "Dr. Andrew Weil. It involves breathing in for 4 counts, holding for 7, and exhaling slowly "
            "for 8. This technique activates the parasympathetic nervous system, reducing anxiety and "
            "promoting restful sleep."
        ),
        "duration_seconds": 240,
        "phases": [
            {"name": "Inhale", "duration": 4, "instruction": "Breathe in slowly through your nose"},
            {"name": "Hold", "duration": 7, "instruction": "Hold your breath gently"},
            {"name": "Exhale", "duration": 8, "instruction": "Exhale completely through your mouth"},
        ],
        "cycles": 4,
        "benefits": [
            "Reduces anxiety and stress",
            "Improves sleep quality",
            "Lowers heart rate and blood pressure",
            "Activates the relaxation response",
        ],
        "suitable_for": ["anxiety", "stress", "insomnia", "panic attacks"],
        "difficulty": "beginner",
    },
    {
        "id": "box_breathing",
        "name": "Box Breathing",
        "category": "breathing",
        "description": (
            "Box breathing, also called square breathing or Navy SEAL breathing, is used by elite "
            "military personnel to stay calm under extreme pressure. Each phase lasts exactly 4 seconds, "
            "creating a steady, balanced rhythm that rapidly calms the nervous system."
        ),
        "duration_seconds": 240,
        "phases": [
            {"name": "Inhale", "duration": 4, "instruction": "Breathe in slowly through your nose"},
            {"name": "Hold", "duration": 4, "instruction": "Hold your breath at the top"},
            {"name": "Exhale", "duration": 4, "instruction": "Exhale slowly through your mouth"},
            {"name": "Hold", "duration": 4, "instruction": "Hold empty at the bottom"},
        ],
        "cycles": 6,
        "benefits": [
            "Rapidly reduces stress",
            "Improves focus and concentration",
            "Regulates the autonomic nervous system",
            "Used by Navy SEALs for performance",
        ],
        "suitable_for": ["stress", "anxiety", "focus", "performance anxiety"],
        "difficulty": "beginner",
    },
    {
        "id": "grounding_54321",
        "name": "5-4-3-2-1 Grounding Technique",
        "category": "grounding",
        "description": (
            "The 5-4-3-2-1 grounding technique uses your five senses to anchor you to the present "
            "moment. It is particularly effective during panic attacks, flashbacks, or episodes of "
            "dissociation. By focusing attention on sensory details, it interrupts the anxiety cycle."
        ),
        "duration_seconds": 300,
        "phases": [
            {"name": "See", "duration": 60, "instruction": "Name 5 things you can see right now"},
            {"name": "Touch", "duration": 60, "instruction": "Notice 4 things you can physically feel"},
            {"name": "Hear", "duration": 60, "instruction": "Listen for 3 sounds around you"},
            {"name": "Smell", "duration": 60, "instruction": "Identify 2 things you can smell"},
            {"name": "Taste", "duration": 60, "instruction": "Notice 1 thing you can taste"},
        ],
        "cycles": 1,
        "benefits": [
            "Interrupts panic attacks",
            "Reduces dissociation",
            "Grounds you in the present moment",
            "Can be used anywhere, anytime",
        ],
        "suitable_for": ["panic attacks", "dissociation", "PTSD flashbacks", "severe anxiety"],
        "difficulty": "beginner",
    },
    {
        "id": "body_scan",
        "name": "Progressive Body Scan",
        "category": "relaxation",
        "description": (
            "A guided progressive body relaxation technique that systematically releases tension "
            "from head to toe. You'll move your attention slowly through each part of your body, "
            "noticing sensations without judgment and consciously releasing held tension."
        ),
        "duration_seconds": 600,
        "phases": [
            {"name": "Head & Scalp", "duration": 60, "instruction": "Gently release tension in your scalp and forehead"},
            {"name": "Face & Jaw", "duration": 60, "instruction": "Soften your jaw, let your tongue rest, unclench"},
            {"name": "Neck & Shoulders", "duration": 60, "instruction": "Roll your shoulders back and let them drop"},
            {"name": "Chest & Belly", "duration": 60, "instruction": "Take a deep breath and feel your chest expand"},
            {"name": "Arms & Hands", "duration": 60, "instruction": "Feel the weight of your arms, open your palms"},
            {"name": "Lower Back & Hips", "duration": 60, "instruction": "Release any tightness in your lower back"},
            {"name": "Legs & Feet", "duration": 60, "instruction": "Feel the ground beneath your feet, soften your legs"},
            {"name": "Whole Body", "duration": 120, "instruction": "Take a moment to feel your whole body at rest"},
        ],
        "cycles": 1,
        "benefits": [
            "Releases chronic muscle tension",
            "Improves body awareness",
            "Reduces physical symptoms of anxiety",
            "Improves sleep when done at bedtime",
        ],
        "suitable_for": ["tension", "anxiety", "insomnia", "chronic pain", "relaxation"],
        "difficulty": "beginner",
    },
    {
        "id": "gratitude_three",
        "name": "Three Good Things",
        "category": "positive_psychology",
        "description": (
            "The Three Good Things exercise, based on positive psychology research by Martin Seligman, "
            "involves writing down three good things that happened today and why they happened. "
            "Studies show that doing this for just one week can increase happiness and decrease "
            "depressive symptoms for up to six months."
        ),
        "duration_seconds": 300,
        "phases": [
            {"name": "First Good Thing", "duration": 90, "instruction": "Think of one good thing that happened today, no matter how small. Why did it happen?"},
            {"name": "Second Good Thing", "duration": 90, "instruction": "What was another positive moment? It could be a kind word, a small achievement, or simply a good cup of coffee."},
            {"name": "Third Good Thing", "duration": 90, "instruction": "Find one more good thing. Feel free to write it down. What caused this positive moment?"},
            {"name": "Reflection", "duration": 30, "instruction": "Take a moment to appreciate these three things. Notice how they make you feel."},
        ],
        "cycles": 1,
        "benefits": [
            "Increases happiness and life satisfaction",
            "Reduces symptoms of depression",
            "Trains the brain to notice positive events",
            "Improves sleep quality",
        ],
        "suitable_for": ["depression", "low mood", "negativity bias", "improving wellbeing"],
        "difficulty": "beginner",
    },
    {
        "id": "cognitive_reframe",
        "name": "Thought Challenging Worksheet",
        "category": "cbt",
        "description": (
            "A guided Cognitive Behavioral Therapy (CBT) exercise to identify and challenge negative "
            "automatic thoughts. You'll examine the evidence for and against a difficult thought, "
            "identify any cognitive distortions, and develop a more balanced perspective."
        ),
        "duration_seconds": 480,
        "phases": [
            {"name": "Identify the Thought", "duration": 60, "instruction": "What is the negative thought or belief bothering you right now? Write it down as specifically as possible."},
            {"name": "Rate Your Distress", "duration": 30, "instruction": "On a scale of 0-10, how distressing is this thought right now?"},
            {"name": "Evidence For", "duration": 90, "instruction": "What evidence or facts support this thought being true? Think objectively."},
            {"name": "Evidence Against", "duration": 90, "instruction": "What evidence contradicts this thought? Are there facts that disprove it?"},
            {"name": "Cognitive Distortions", "duration": 60, "instruction": "Does this thought involve all-or-nothing thinking, catastrophizing, mind-reading, or other distortions?"},
            {"name": "Balanced Thought", "duration": 90, "instruction": "What is a more balanced, realistic version of this thought? How does it change your feelings?"},
            {"name": "Re-Rate Distress", "duration": 30, "instruction": "Now rate your distress level again (0-10). Has it shifted?"},
        ],
        "cycles": 1,
        "benefits": [
            "Breaks negative thought patterns",
            "Evidence-based CBT technique",
            "Improves emotional regulation",
            "Increases cognitive flexibility",
        ],
        "suitable_for": ["negative thoughts", "anxiety", "depression", "rumination", "CBT practice"],
        "difficulty": "intermediate",
    },
]

_EXERCISE_MAP = {ex["id"]: ex for ex in _EXERCISES}


@exercises_bp.route("/exercises", methods=["GET"])
def list_exercises():
    summaries = [
        {
            "id": ex["id"],
            "name": ex["name"],
            "category": ex["category"],
            "duration_seconds": ex["duration_seconds"],
            "suitable_for": ex["suitable_for"],
            "difficulty": ex["difficulty"],
            "benefits": ex["benefits"][:2],
        }
        for ex in _EXERCISES
    ]
    return jsonify({"exercises": summaries, "count": len(summaries)}), 200


@exercises_bp.route("/exercises/<exercise_id>", methods=["GET"])
def get_exercise(exercise_id: str):
    exercise = _EXERCISE_MAP.get(exercise_id)
    if not exercise:
        return jsonify({"error": f"Exercise '{exercise_id}' not found."}), 404
    return jsonify(exercise), 200


@exercises_bp.route("/exercises/log", methods=["POST"])
def log_exercise():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    session_id = data.get("session_id", "").strip()
    exercise_id = data.get("exercise_id", "").strip()
    duration = int(data.get("duration_seconds", 0))
    completed = bool(data.get("completed", False))

    if not session_id or not exercise_id:
        return jsonify({"error": "session_id and exercise_id are required."}), 400

    try:
        # Ensure user session exists (may complete exercise before first chat)
        from app.db.database import get_or_create_user
        get_or_create_user(session_id)

        log = ExerciseLog(
            session_id=session_id,
            exercise_type=exercise_id,
            duration_seconds=duration,
            completed=completed,
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({"message": "Exercise logged.", "id": log.id}), 200
    except Exception as exc:
        db.session.rollback()
        logger.error(f"Exercise log error: {exc}")
        return jsonify({"error": "Failed to log exercise."}), 500
