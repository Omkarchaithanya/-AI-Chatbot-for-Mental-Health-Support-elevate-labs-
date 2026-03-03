"""MindEase PRO — Emotion Detection Module"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("mindease.emotion")

EMOTION_VALENCE: dict[str, float] = {
    "joy": 0.9,
    "love": 0.85,
    "surprise": 0.3,
    "neutral": 0.0,
    "fear": -0.7,
    "sadness": -0.8,
    "anger": -0.75,
    "disgust": -0.65,
}

EMOTION_AROUSAL: dict[str, float] = {
    "joy": 0.7,
    "love": 0.5,
    "surprise": 0.8,
    "neutral": 0.2,
    "fear": 0.85,
    "sadness": 0.3,
    "anger": 0.9,
    "disgust": 0.6,
}

EMOTION_EMOJI: dict[str, str] = {
    "joy": "😊",
    "love": "💚",
    "surprise": "😲",
    "neutral": "😐",
    "fear": "😰",
    "sadness": "💙",
    "anger": "😤",
    "disgust": "😞",
}

# Rule-based keyword fallback
_KEYWORD_MAP: dict[str, list[str]] = {
    "sadness": ["sad", "depressed", "hopeless", "worthless", "empty", "cry", "crying", "lonely", "alone", "grief"],
    "anger": ["angry", "furious", "rage", "hate", "frustrated", "irritated", "annoyed", "mad"],
    "fear": ["scared", "afraid", "terrified", "panic", "anxious", "anxiety", "nervous", "dread", "worry", "worried"],
    "joy": ["happy", "excited", "great", "wonderful", "amazing", "love", "fantastic", "joy", "good"],
    "disgust": ["disgusting", "gross", "revolting", "sick", "nauseous"],
    "surprise": ["surprised", "shocked", "unexpected", "sudden"],
    "love": ["love", "care", "affection", "grateful", "thankful"],
    "neutral": [],
}


class EmotionDetector:
    """HuggingFace-based emotion classifier with rule-based fallback."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._pipeline = None
        self._using_fallback = False
        self._load_pipeline()

    def _load_pipeline(self) -> None:
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                return_all_scores=True,
                device=-1,  # CPU
            )
            logger.info(f"EmotionDetector loaded: {self.model_name}")
        except Exception as exc:
            logger.warning(f"Could not load emotion model ({exc}); using rule-based fallback.")
            self._using_fallback = True

    def detect(self, text: str) -> dict:
        """Detect emotion from text and return structured analysis dict."""
        text = text.strip() if text else ""
        if not text:
            return self._empty_result()

        if self._pipeline is not None:
            try:
                return self._detect_with_model(text)
            except Exception as exc:
                logger.warning(f"Model inference failed ({exc}); falling back to rules.")

        return self._detect_with_rules(text)

    def _detect_with_model(self, text: str) -> dict:
        import torch
        with torch.no_grad():
            raw = self._pipeline(text[:512])
        # raw is list[list[dict]] or list[dict]
        scores_list = raw[0] if isinstance(raw[0], list) else raw
        all_emotions: dict[str, float] = {}
        for item in scores_list:
            label = item["label"].lower().split("_")[0]  # normalise e.g. "EMOTION_joy" → "joy"
            score = float(item["score"])
            # Aggregate scores if the same base label appears multiple times
            all_emotions[label] = max(all_emotions.get(label, 0.0), score)

        primary_emotion = max(all_emotions, key=all_emotions.get)
        confidence = all_emotions[primary_emotion]
        return self._build_result(primary_emotion, confidence, all_emotions)

    def _detect_with_rules(self, text: str) -> dict:
        lower = text.lower()
        scores: dict[str, int] = {e: 0 for e in EMOTION_VALENCE}
        for emotion, keywords in _KEYWORD_MAP.items():
            for kw in keywords:
                if re.search(r"\b" + kw + r"\b", lower):
                    scores[emotion] += 1

        total = sum(scores.values())
        if total == 0:
            return self._build_result("neutral", 0.6, {e: 0.0 for e in EMOTION_VALENCE})

        all_emotions = {e: round(v / total, 3) for e, v in scores.items()}
        primary_emotion = max(all_emotions, key=all_emotions.get)
        confidence = all_emotions[primary_emotion]
        return self._build_result(primary_emotion, confidence, all_emotions)

    def _build_result(self, primary_emotion: str, confidence: float, all_emotions: dict) -> dict:
        # Normalise emotion label
        if primary_emotion not in EMOTION_VALENCE:
            primary_emotion = "neutral"

        valence = EMOTION_VALENCE.get(primary_emotion, 0.0)
        arousal = EMOTION_AROUSAL.get(primary_emotion, 0.2)

        return {
            "primary_emotion": primary_emotion,
            "confidence": round(confidence, 4),
            "all_emotions": all_emotions,
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "is_negative": valence < -0.3,
            "needs_support": valence < -0.5 or arousal > 0.7,
            "emoji": self.get_emotion_emoji(primary_emotion),
        }

    def _empty_result(self) -> dict:
        return self._build_result("neutral", 1.0, {e: 0.0 for e in EMOTION_VALENCE})

    def detect_batch(self, texts: list[str]) -> list[dict]:
        """Batch-process multiple texts efficiently."""
        if not texts:
            return []
        if self._pipeline is not None:
            try:
                import torch
                valid_texts = [t[:512] if t else " " for t in texts]
                with torch.no_grad():
                    raw_list = self._pipeline(valid_texts)
                results = []
                for raw, original_text in zip(raw_list, texts):
                    scores_list = raw if isinstance(raw[0], dict) else raw[0]
                    all_emotions: dict[str, float] = {}
                    for item in scores_list:
                        label = item["label"].lower().split("_")[0]
                        score = float(item["score"])
                        all_emotions[label] = max(all_emotions.get(label, 0.0), score)
                    primary = max(all_emotions, key=all_emotions.get)
                    results.append(self._build_result(primary, all_emotions[primary], all_emotions))
                return results
            except Exception as exc:
                logger.warning(f"Batch inference failed ({exc}); falling back.")

        return [self._detect_with_rules(t) for t in texts]

    def get_emotion_emoji(self, emotion: str) -> str:
        return EMOTION_EMOJI.get(emotion, "💬")
