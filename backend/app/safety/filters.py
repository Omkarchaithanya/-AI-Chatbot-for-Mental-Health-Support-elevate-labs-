"""MindEase PRO — Advanced Input Safety Filter"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("mindease.safety")

LEVEL_0 = 0  # no crisis
LEVEL_1 = 1  # distress
LEVEL_2 = 2  # risk (self-harm ideation)
LEVEL_3 = 3  # crisis (active suicidal ideation)

# Crisis keyword patterns (progressive severity)
_CRISIS_L3: list[str] = [
    r"\bkill myself\b", r"\bend my life\b", r"\bsuicide\b", r"\bsuicidal\b",
    r"\bwant to die\b", r"\bgoing to die\b", r"\btake my( own)? life\b",
    r"\blethal\b.{0,20}\b(dose|method|plan)\b",
    r"\b(hang|shoot|jump|overdose|slash).{0,30}\bmyself\b",
    r"\bi('m| am) going to (kill|end|hurt) myself\b",
    r"\bnot want(ing)? to be alive\b",
    r"\bgoodbye.{0,30}(forever|world)\b",
]

_CRISIS_L2: list[str] = [
    r"\bhurt(ing)? myself\b", r"\bself.?harm\b", r"\bself.?injur\b",
    r"\bcut(ting)? myself\b", r"\bbur(n|ning) myself\b",
    r"\bdon'?t want to (live|be here)\b",
    r"\btired of (living|life|being alive)\b",
    r"\bno reason to (live|go on)\b",
    r"\b(thinking|thought) about (dying|death|ending it)\b",
    r"\bpassive suicid\b",
]

_CRISIS_L1: list[str] = [
    r"\bhopeless\b", r"\bworthless\b", r"\bempty inside\b",
    r"\bcan'?t go on\b", r"\bcan'?t take it\b", r"\bat my limit\b",
    r"\bbreaking down\b", r"\bgive up\b", r"\bnumb\b",
    r"\bmiserable\b", r"\bdesperate\b",
    r"\bno one cares\b", r"\bno point\b", r"\bnobody would miss me\b",
]

_SAFETY_RESOURCES = [
    "988 Suicide & Crisis Lifeline — call or text 988",
    "Crisis Text Line — text HOME to 741741",
    "International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/",
]

_EMERGENCY_RESOURCES = [
    "988 Suicide & Crisis Lifeline — call or text 988 (24/7 free, confidential)",
    "Crisis Text Line — text HOME to 741741",
    "Emergency Services — call 911 (or your local emergency number)",
    "Go to your nearest emergency room or hospital.",
    "Tell a trusted person near you right now that you need help.",
]

_CRISIS_TYPES: dict[int, str] = {
    1: "distress",
    2: "self_harm",
    3: "suicidal",
}

_KEYWORD_EMOTIONS: dict[str, list[str]] = {
    "sadness": ["sad", "cry", "depressed", "unhappy", "down", "blue", "miserable", "grief"],
    "anxiety": ["anxious", "anxiety", "worried", "panic", "nervous", "stress", "overwhelmed"],
    "anger": ["angry", "furious", "rage", "mad", "irritated", "frustrated"],
    "loneliness": ["lonely", "alone", "isolated", "no one", "nobody"],
    "hopelessness": ["hopeless", "no hope", "pointless", "worthless"],
}


class AdvancedInputFilter:
    """Multi-level crisis detection and content safety filter."""

    def __init__(self) -> None:
        self._profanity = None
        self._load_profanity_filter()
        # Compile regex patterns once
        self._l3_patterns = [re.compile(p, re.IGNORECASE) for p in _CRISIS_L3]
        self._l2_patterns = [re.compile(p, re.IGNORECASE) for p in _CRISIS_L2]
        self._l1_patterns = [re.compile(p, re.IGNORECASE) for p in _CRISIS_L1]

    def _load_profanity_filter(self) -> None:
        try:
            from better_profanity import profanity
            profanity.load_censor_words()
            self._profanity = profanity
        except Exception as exc:
            logger.warning(f"Profanity filter unavailable: {exc}")

    def analyze(self, text: str) -> dict:
        """Full safety analysis of input text."""
        if not text or not text.strip():
            return {
                "clean_text": "",
                "crisis_level": 0,
                "crisis_type": None,
                "is_offensive": False,
                "is_empty": True,
                "is_too_long": False,
                "detected_emotions": [],
                "safety_resources": [],
                "recommended_exercise": None,
            }

        # Length check
        is_too_long = len(text) > 2000
        text = text[:2000]

        # Sanitize: strip HTML-like tags
        clean_text = re.sub(r"<[^>]+>", "", text).strip()

        # Crisis detection (highest level wins)
        crisis_level = 0
        if any(p.search(clean_text) for p in self._l3_patterns):
            crisis_level = 3
        elif any(p.search(clean_text) for p in self._l2_patterns):
            crisis_level = 2
        elif any(p.search(clean_text) for p in self._l1_patterns):
            crisis_level = 1

        crisis_type = _CRISIS_TYPES.get(crisis_level)

        # Profanity check (only mark offensive if NOT clinical mental health terms)
        is_offensive = False
        if self._profanity:
            is_offensive = self._profanity.contains_profanity(clean_text)
            # Override: clinical mental health terms are not offensive
            clinical_override = re.search(
                r"\b(suicid|self.harm|depress|anxiety|trauma|mental health|therapy)\b",
                clean_text, re.IGNORECASE
            )
            if clinical_override:
                is_offensive = False

        # Keyword emotion detection
        detected_emotions: list[str] = []
        lower = clean_text.lower()
        for emotion, keywords in _KEYWORD_EMOTIONS.items():
            if any(kw in lower for kw in keywords):
                detected_emotions.append(emotion)

        # Resources and exercise suggestions
        safety_resources: list[str] = []
        recommended_exercise: Optional[str] = None

        if crisis_level >= 2:
            safety_resources = list(_SAFETY_RESOURCES)
        if crisis_level == 1:
            recommended_exercise = "breathing_4_7_8"

        return {
            "clean_text": clean_text,
            "crisis_level": crisis_level,
            "crisis_type": crisis_type,
            "is_offensive": is_offensive,
            "is_empty": False,
            "is_too_long": is_too_long,
            "detected_emotions": detected_emotions,
            "safety_resources": safety_resources,
            "recommended_exercise": recommended_exercise,
        }

    def get_crisis_response(self, crisis_level: int, crisis_type: Optional[str] = None) -> str:
        """Return appropriate crisis response text based on level."""
        if crisis_level == 3:
            return (
                "🚨 **I'm very concerned about your safety right now. Please reach out for help immediately:**\n\n"
                "• **988 Suicide & Crisis Lifeline** — Call or text **988** (24/7, free, confidential)\n"
                "• **Crisis Text Line** — Text **HOME** to **741741**\n"
                "• **Emergency Services** — Call **911** (or your local emergency number)\n\n"
                "Please reach out to someone near you right now. You matter, and help is available."
            )
        if crisis_level == 2:
            return (
                "I hear you, and I'm really glad you're sharing this with me. "
                "What you're going through sounds incredibly painful. "
                "I want you to know you don't have to face this alone.\n\n"
                "**Please consider reaching out to a crisis professional:**\n"
                "• 988 Suicide & Crisis Lifeline — call or text **988**\n"
                "• Crisis Text Line — text **HOME** to **741741**\n\n"
                "I'm still here with you. Can you tell me more about what you're going through?"
            )
        if crisis_level == 1:
            return (
                "It sounds like you're carrying something really heavy right now. "
                "Those feelings of hopelessness can be overwhelming, but you reached out — and that takes courage. "
                "I'm here with you.\n\n"
                "Would you like to try a brief breathing exercise together? "
                "It might help bring a little calm right now."
            )
        return ""
