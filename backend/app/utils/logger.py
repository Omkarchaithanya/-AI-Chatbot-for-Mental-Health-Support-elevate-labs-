"""MindEase PRO — Structured JSONL Session Logger"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("mindease.session_logger")


class SessionLogger:
    """Logs conversations to a persistent JSONL file."""

    def __init__(self, log_file: Optional[str] = None) -> None:
        if log_file is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_file = os.path.join(base, "logs", "sessions.jsonl")
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log(
        self,
        session_id: str,
        user_message: str,
        bot_response: str,
        emotion_data: Optional[dict],
        crisis_level: int = 0,
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "user": user_message[:500],
            "bot": bot_response[:500],
            "emotion": emotion_data.get("primary_emotion") if emotion_data else None,
            "valence": emotion_data.get("valence") if emotion_data else None,
            "crisis_level": crisis_level,
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning(f"Failed to write session log: {exc}")
