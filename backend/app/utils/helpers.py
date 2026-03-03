"""MindEase PRO — Helper Utilities"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone


def generate_uuid() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    """Return current UTC datetime as ISO string."""
    return utc_now().isoformat()


def sanitize_text(text: str, max_length: int = 2000) -> str:
    """
    Basic text sanitization:
      - Strip leading/trailing whitespace
      - Remove HTML-like tags
      - Collapse multiple whitespace
      - Truncate to max_length
    """
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"<[^>]+>", "", text)      # strip HTML tags
    text = re.sub(r"[\r\n]{3,}", "\n\n", text)  # collapse excess newlines
    text = re.sub(r" {2,}", " ", text)          # collapse spaces
    return text[:max_length]


def truncate_text(text: str, max_chars: int = 200) -> str:
    """Truncate text to max_chars, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def ms_since(start_seconds: float) -> int:
    """Return elapsed time in milliseconds since start_seconds (time.time())."""
    import time
    return int((time.time() - start_seconds) * 1000)
