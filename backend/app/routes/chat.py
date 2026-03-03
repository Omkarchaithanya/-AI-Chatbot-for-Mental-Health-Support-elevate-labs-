"""MindEase PRO — Chat Routes (REST + WebSocket)"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_socketio import emit

from app.extensions import db, socketio
from app.ai.personalizer import Personalizer
from app.db.database import get_or_create_user
from app.db.models import ChatMessage, MoodEntry
from app.safety.rate_limiter import check_session_rate_limit
from app.utils.helpers import sanitize_text
from app.utils.logger import SessionLogger

logger = logging.getLogger("mindease.routes.chat")
chat_bp = Blueprint("chat", __name__)
session_logger = SessionLogger()


def _get_or_generate_session(data: dict) -> str:
    sid = data.get("session_id", "").strip()
    if not sid:
        sid = str(uuid.uuid4())
    return sid


def _run_chat_pipeline(
    message: str,
    session_id: str,
    tts: bool = False,
    stream: bool = False,
    tts_lang: str = "en",
):
    """
    Full AI pipeline. Returns response dict (non-streaming) OR
    yields tokens (streaming mode).
    """
    start_ms = time.time()

    safety_filter = current_app.safety_filter
    emotion_detector = current_app.emotion_detector
    rag_engine = current_app.rag_engine
    chatbot = current_app.chatbot
    tts_engine = current_app.tts_engine

    with current_app.app_context():
        # 1 ── Safety analysis
        safety = safety_filter.analyze(message)
        clean_message = safety["clean_text"]
        crisis_level = safety["crisis_level"]

        # 2 ── Ensure user session exists
        user = get_or_create_user(session_id)

        # 3 ── Crisis level 3: skip AI entirely
        if crisis_level == 3:
            crisis_resp = safety_filter.get_crisis_response(3)
            _save_messages(session_id, message, crisis_resp, None, False, 0)
            return {
                "response": crisis_resp,
                "session_id": session_id,
                "emotion": {"primary_emotion": "fear", "confidence": 1.0, "valence": -0.9,
                            "arousal": 1.0, "is_negative": True, "needs_support": True,
                            "all_emotions": {}, "emoji": "🆘"},
                "crisis_level": 3,
                "safety_resources": safety["safety_resources"] or [
                    "988 Suicide & Crisis Lifeline — call or text 988",
                    "Crisis Text Line — text HOME to 741741",
                    "Emergency Services — call 911",
                ],
                "rag_used": False,
                "audio_base64": None,
                "exercise_suggestion": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": int((time.time() - start_ms) * 1000),
            }

        # 4 ── Emotion detection
        emotion_data = emotion_detector.detect(clean_message)

        # 5 ── Personalizer params
        personalizer = Personalizer(db.session)
        params = personalizer.get_personalized_params(session_id)
        tone = params.get("tone", "empathetic")

        # 6 ── RAG retrieval
        rag_results = rag_engine.retrieve(clean_message, emotion_data.get("primary_emotion"))
        rag_context = rag_engine.format_context(rag_results) if rag_results else None
        rag_used = bool(rag_context)

        # 7 ── Crisis level 1/2: prepend crisis response to AI response
        crisis_prefix = ""
        if crisis_level >= 1:
            crisis_prefix = safety_filter.get_crisis_response(crisis_level) + "\n\n"

        if stream:
            # Return generator — caller handles streaming
            def _stream_gen():
                if crisis_prefix:
                    for word in crisis_prefix.split(" "):
                        yield word + " "
                yield from chatbot.stream_response(
                    session_id, clean_message, rag_context, emotion_data, tone
                )
            return _stream_gen(), emotion_data, safety, rag_used, params

        # 8 ── Generate response (blocking)
        ai_response = chatbot.generate_response(
            session_id, clean_message, rag_context, emotion_data, tone
        )
        full_response = crisis_prefix + ai_response

        # 9 ── TTS
        audio_b64 = None
        if tts:
            try:
                audio_b64 = tts_engine.synthesize_to_base64(ai_response, lang=tts_lang)
            except Exception as exc:
                logger.warning(f"TTS failed: {exc}")

        # 10 ── Save to DB
        response_ms = int((time.time() - start_ms) * 1000)
        _save_messages(session_id, message, full_response, emotion_data, rag_used, response_ms)

        # 11 ── Update personalizer
        personalizer.update_preferences(session_id, emotion_data)

        # 12 ── Log session
        try:
            session_logger.log(session_id, message, full_response, emotion_data, crisis_level)
        except Exception:
            pass

        # Increment message count
        try:
            user.message_count = (user.message_count or 0) + 2
            db.session.commit()
        except Exception:
            pass

        return {
            "response": full_response,
            "session_id": session_id,
            "emotion": emotion_data,
            "crisis_level": crisis_level,
            "safety_resources": safety["safety_resources"],
            "rag_used": rag_used,
            "audio_base64": audio_b64,
            "exercise_suggestion": params.get("exercise_suggestion") or safety.get("recommended_exercise"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": response_ms,
        }


def _save_messages(
    session_id: str,
    user_content: str,
    bot_content: str,
    emotion_data,
    rag_used: bool,
    response_ms: int,
) -> None:
    try:
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_content[:4096],
            emotion_detected=emotion_data.get("primary_emotion") if emotion_data else None,
            rag_used=False,
            response_time_ms=0,
        )
        bot_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=bot_content[:4096],
            emotion_detected=emotion_data.get("primary_emotion") if emotion_data else None,
            rag_used=rag_used,
            response_time_ms=response_ms,
        )
        # Save mood entry
        if emotion_data:
            mood = MoodEntry(
                session_id=session_id,
                emotion=emotion_data.get("primary_emotion", "neutral"),
                confidence=emotion_data.get("confidence", 0.0),
                valence=emotion_data.get("valence", 0.0),
                arousal=emotion_data.get("arousal", 0.0),
                user_message=user_content[:512],
            )
            db.session.add(mood)

        db.session.add(user_msg)
        db.session.add(bot_msg)
        db.session.commit()
    except Exception as exc:
        logger.error(f"DB save error: {exc}")
        db.session.rollback()


# ── REST endpoint ─────────────────────────────────────────────────────────────

@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    message = sanitize_text(data.get("message", ""))
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    session_id = _get_or_generate_session(data)
    tts = bool(data.get("tts", False))
    tts_lang = data.get("tts_lang", "en")
    if tts_lang not in ("en", "hi", "kn", "ta", "te"):
        tts_lang = "en"

    # Rate limiting
    is_limited, retry_after = check_session_rate_limit(session_id)
    if is_limited:
        return jsonify({
            "error": f"Please take a moment to breathe. You can continue in {retry_after} seconds.",
            "retry_after": retry_after,
        }), 429

    # Safety check (empty / too long)
    safety_filter = current_app.safety_filter
    pre_check = safety_filter.analyze(message)
    if pre_check["is_empty"]:
        return jsonify({"error": "Message cannot be empty."}), 400
    if pre_check["is_offensive"]:
        return jsonify({"error": "Message contains content that cannot be processed."}), 400

    try:
        result = _run_chat_pipeline(message, session_id, tts=tts, tts_lang=tts_lang)
        return jsonify(result), 200
    except Exception as exc:
        logger.error(f"Chat pipeline error: {exc}", exc_info=True)
        return jsonify({"error": "An internal error occurred. Please try again."}), 500


# ── WebSocket events ──────────────────────────────────────────────────────────

@socketio.on("chat_message")
def handle_chat_message(data):
    if not isinstance(data, dict):
        emit("error", {"message": "Invalid data format."})
        return

    message = sanitize_text(data.get("message", ""))
    if not message:
        emit("error", {"message": "Message cannot be empty."})
        return

    session_id = data.get("session_id") or str(uuid.uuid4())
    tts: bool = bool(data.get("tts", False))
    tts_lang: str = data.get("tts_lang", "en")
    if tts_lang not in ("en", "hi", "kn", "ta", "te"):
        tts_lang = "en"

    # Rate limiting
    is_limited, retry_after = check_session_rate_limit(session_id)
    if is_limited:
        emit("error", {"message": f"Rate limit reached. Retry in {retry_after}s.", "retry_after": retry_after})
        return

    with current_app.app_context():
        try:
            safety_filter = current_app.safety_filter
            pre_check = safety_filter.analyze(message)

            if pre_check["is_empty"] or pre_check["is_offensive"]:
                emit("error", {"message": "Message cannot be processed."})
                return

            # Crisis level 3: immediate resources, no streaming
            if pre_check["crisis_level"] == 3:
                result = _run_chat_pipeline(message, session_id, tts=False, tts_lang=tts_lang)
                emit("response_complete", result)
                return

            # Emotion detected immediately (before generation)
            emotion_data = current_app.emotion_detector.detect(pre_check["clean_text"])
            emit("emotion_detected", emotion_data)

            # Stream tokens
            clean_message = pre_check["clean_text"]
            personalizer = Personalizer(db.session)
            params = personalizer.get_personalized_params(session_id)
            rag_results = current_app.rag_engine.retrieve(
                clean_message, emotion_data.get("primary_emotion")
            )
            rag_context = current_app.rag_engine.format_context(rag_results) if rag_results else None
            rag_used = bool(rag_context)

            crisis_prefix = ""
            if pre_check["crisis_level"] >= 1:
                crisis_prefix = safety_filter.get_crisis_response(pre_check["crisis_level"]) + "\n\n"
                for word in crisis_prefix.split(" "):
                    emit("response_token", {"token": word + " "})

            full_response_parts: list[str] = [crisis_prefix]
            start_ms = time.time()

            for token in current_app.chatbot.stream_response(
                session_id, clean_message, rag_context, emotion_data, params.get("tone", "empathetic")
            ):
                emit("response_token", {"token": token})
                full_response_parts.append(token)

            full_response = "".join(full_response_parts).strip()
            response_ms = int((time.time() - start_ms) * 1000)

            # Save to DB
            _save_messages(session_id, message, full_response, emotion_data, rag_used, response_ms)
            personalizer.update_preferences(session_id, emotion_data)

            # TTS (optional)
            audio_b64 = None
            if tts:
                try:
                    audio_b64 = current_app.tts_engine.synthesize_to_base64(full_response)
                except Exception:
                    pass

            emit("response_complete", {
                "response": full_response,
                "session_id": session_id,
                "emotion": emotion_data,
                "crisis_level": pre_check["crisis_level"],
                "safety_resources": pre_check["safety_resources"],
                "rag_used": rag_used,
                "audio_base64": audio_b64,
                "exercise_suggestion": params.get("exercise_suggestion"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": response_ms,
            })

        except Exception as exc:
            logger.error(f"WebSocket chat error: {exc}", exc_info=True)
            emit("error", {"message": "An internal error occurred."})
