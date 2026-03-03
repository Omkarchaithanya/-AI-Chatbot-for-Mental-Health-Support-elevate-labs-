"""MindEase PRO — Text-to-Speech Engine (gTTS)"""
from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger("mindease.tts")

_SUPPORTED_LANGUAGES = [
    "en",   # English
    "hi",   # Hindi
    "kn",   # Kannada
    "ta",   # Tamil
    "te",   # Telugu
]

_MAX_TTS_CHARS = 200


class TTSEngine:
    """Text-to-Speech synthesis using gTTS with response caching."""

    def __init__(self) -> None:
        self._cache: dict[str, bytes] = {}
        self._audio_dir = os.path.join(tempfile.gettempdir(), "mindease_audio")
        os.makedirs(self._audio_dir, exist_ok=True)

    def _cache_key(self, text: str, lang: str) -> str:
        return hashlib.md5(f"{lang}:{text}".encode()).hexdigest()

    def synthesize(self, text: str, lang: str = "en") -> bytes:
        """Convert text to MP3 audio bytes."""
        if not text:
            return b""

        text = text[:_MAX_TTS_CHARS]
        key = self._cache_key(text, lang)

        if key in self._cache:
            return self._cache[key]

        try:
            from gtts import gTTS
            buf = io.BytesIO()
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.write_to_fp(buf)
            audio_bytes = buf.getvalue()
            self._cache[key] = audio_bytes
            # Limit in-memory cache size
            if len(self._cache) > 200:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            return audio_bytes
        except Exception as exc:
            logger.error(f"TTS synthesis error: {exc}")
            return b""

    def synthesize_to_base64(self, text: str, lang: str = "en") -> str:
        """Return base64-encoded audio for embedding in JSON."""
        audio_bytes = self.synthesize(text[:_MAX_TTS_CHARS], lang)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def get_supported_languages(self) -> list[str]:
        return list(_SUPPORTED_LANGUAGES)
