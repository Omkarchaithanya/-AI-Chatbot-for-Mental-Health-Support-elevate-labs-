"""MindEase PRO — Per-Session Rate Limiter"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable

from flask import current_app, jsonify, request

logger = logging.getLogger("mindease.ratelimit")

# In-memory per-session rate limit store
# {session_id: deque([timestamps])}
_minute_store: dict[str, deque] = defaultdict(lambda: deque())
_hour_store: dict[str, deque] = defaultdict(lambda: deque())

_MINUTE_LIMIT = 30
_HOUR_LIMIT = 200


def check_session_rate_limit(session_id: str) -> tuple[bool, int]:
    """
    Check rate limits for a session.
    Returns (is_limited: bool, retry_after_seconds: int).
    """
    now = time.time()

    # Per-minute window
    minute_window = _minute_store[session_id]
    cutoff_minute = now - 60
    while minute_window and minute_window[0] < cutoff_minute:
        minute_window.popleft()

    if len(minute_window) >= _MINUTE_LIMIT:
        oldest = minute_window[0]
        retry_after = int(60 - (now - oldest)) + 1
        return True, retry_after

    # Per-hour window
    hour_window = _hour_store[session_id]
    cutoff_hour = now - 3600
    while hour_window and hour_window[0] < cutoff_hour:
        hour_window.popleft()

    if len(hour_window) >= _HOUR_LIMIT:
        oldest = hour_window[0]
        retry_after = int(3600 - (now - oldest)) + 1
        return True, retry_after

    # Record this request
    minute_window.append(now)
    hour_window.append(now)
    return False, 0


def session_rate_limit(f: Callable) -> Callable:
    """Decorator to apply per-session rate limiting."""
    @wraps(f)
    def decorated(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id") or request.args.get("session_id", "anonymous")

        is_limited, retry_after = check_session_rate_limit(session_id)
        if is_limited:
            return jsonify({
                "error": f"Please take a moment to breathe. You can continue in {retry_after} seconds.",
                "retry_after": retry_after,
            }), 429

        return f(*args, **kwargs)
    return decorated
