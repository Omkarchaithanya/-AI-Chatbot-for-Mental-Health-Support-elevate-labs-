"""MindEase PRO — Chatbot with Streaming Support"""
from __future__ import annotations

import logging
import random
from collections import deque
from typing import Generator, Optional

logger = logging.getLogger("mindease.chatbot")

# ── Varied, context-aware response bank ─────────────────────────────────────
# Each entry is a list so we can pick randomly to avoid repetition.

_RESPONSES: dict[str, list[str]] = {
    "sadness": [
        "It sounds like you're carrying something really heavy right now. Whatever you're feeling is completely valid — you don't have to hold this alone. Can you tell me a little more about what's been happening?",
        "I hear you, and I'm so glad you reached out. Feeling sad or low can be really draining. Would it help to talk through what's been weighing on you?",
        "That sounds really tough, and it makes sense that you're feeling this way. You're not alone in this. What's been on your mind most today?",
        "Thank you for sharing that with me. When sadness feels overwhelming, sometimes it helps just to put it into words. I'm here — take your time.",
        "I'm sorry you're going through this. Your feelings are real and they matter. What happened, if you feel comfortable sharing?",
    ],
    "fear": [
        "It sounds like anxiety is really showing up for you right now. That's a tough feeling to sit with. Let's take things one step at a time — you're safe here. What's worrying you most?",
        "Feeling anxious or scared can be exhausting. I want you to know you're not facing this alone. Can you describe what the worry feels like for you right now?",
        "I can hear the anxiety in what you're sharing. Grounding can help — try taking one slow deep breath with me. Then, when you're ready, tell me what's on your mind.",
        "Fear and anxiety are signals your mind is under pressure. Let's slow down together. What specifically is making you feel this way?",
        "That sounds really overwhelming. Anxiety has a way of amplifying everything. You're safe right now, in this moment. What would feel most helpful to talk about?",
    ],
    "anger": [
        "It sounds like something has really frustrated or upset you, and that's completely understandable. Before we figure out next steps, would you like to just vent a bit? I'm listening.",
        "I can hear how frustrated you are, and honestly, your feelings make sense. What happened? Sometimes just naming it helps.",
        "Anger is often a sign that something important was threatened or crossed. I want to understand — what's been going on for you?",
        "That sounds really maddening. I'm not going to dismiss how you feel — your frustration is valid. Tell me more about the situation.",
        "It takes courage to sit with anger and talk about it rather than let it consume you. I'm here. What's going on?",
    ],
    "joy": [
        "That's wonderful to hear! It sounds like things are going well for you today. What's been making you feel good?",
        "I love hearing that — positive moments like these are so important. What's been bringing you joy lately?",
        "That's really great! It's important to acknowledge and celebrate the good feelings too. What's been going well?",
        "It sounds like you're in a really good place right now! I'd love to hear more about what's been uplifting you.",
        "That's lovely! Sometimes just noticing the positive moments makes a big difference. What's been making you smile?",
    ],
    "neutral": [
        "Thanks for sharing that with me. I'm curious — how are you feeling about it overall? Sometimes things that seem neutral on the surface can carry more weight underneath.",
        "I appreciate you talking to me. What's been going on for you lately? I'm here to listen to whatever is on your mind.",
        "That's interesting. How does that sit with you? I want to make sure I understand what you're experiencing.",
        "I'm here and I'm listening. What would be most useful to explore together today?",
        "Sometimes it's hard to know exactly how we feel. That's okay. Take your time — what's been on your mind?",
    ],
    "surprise": [
        "That does sound unexpected! Life can catch us off guard like that. How are you processing it so far?",
        "Wow — that sounds like a lot to take in. Unexpected things can be hard to wrap our heads around. How are you feeling about it?",
        "That's quite something to deal with. Surprises — good or bad — can leave us feeling unsettled. What's going through your mind right now?",
        "It sounds like something shifted unexpectedly. That can be disorienting. Would you like to talk through how that's affecting you?",
    ],
    "love": [
        "That's really beautiful. Feeling connected and grateful is so nourishing. What's been fostering those feelings for you?",
        "It's wonderful when we can feel that warmth and connection. Tell me more — what's been happening that's brought this on?",
        "That sounds really meaningful. Those feelings of love and appreciation are so powerful. What would you like to do with them?",
    ],
    "disgust": [
        "It sounds like something has really bothered or disturbed you. Your reaction makes complete sense. What happened?",
        "That sounds really uncomfortable. When something strikes us as wrong or off-putting it can be hard to shake. Would it help to talk through it?",
        "I can hear that something's genuinely upsetting you, and that's a valid response. What's going on?",
    ],
}

# Keyword-based interjections to make responses feel more relevant
_KEYWORD_HOOKS: dict[str, str] = {
    "work": "Work stress can really pile up.",
    "job": "Job pressures can be really demanding.",
    "family": "Family dynamics can be complicated and emotionally charged.",
    "relationship": "Relationship challenges can feel deeply personal.",
    "sleep": "Sleep problems often go hand-in-hand with stress and anxiety.",
    "tired": "Feeling tired and drained is your body asking for care.",
    "lonely": "Loneliness is one of the hardest feelings to sit with.",
    "alone": "Feeling alone can be really painful.",
    "achieve": "That drive to achieve something meaningful shows real purpose in you.",
    "goal": "Having goals is powerful — it gives direction to our energy.",
    "creative": "Creativity is such a meaningful outlet and expression of who we are.",
    "happy": "I'm glad to hear there's some happiness there.",
    "sad": "I'm sorry to hear you're feeling low.",
    "anxious": "Anxiety can feel so all-consuming.",
    "stress": "Stress can really wear us down over time.",
    "overwhelm": "Feeling overwhelmed is hard — it can make everything feel impossible.",
    "future": "Thinking about the future can bring up a lot of hope and fear at the same time.",
    "past": "Sometimes our past weighs heavily on our present.",
    "friend": "Our friendships can shape how we feel so much.",
    "school": "Academic pressures can be intense and isolating.",
    "study": "Studying hard takes real dedication — and real toll sometimes.",
}


class MindEaseChatbot:
    """BlenderBot-based conversational agent with streaming capability."""

    def __init__(self, config) -> None:
        self.config = config
        self._model = None
        self._tokenizer = None
        self._using_fallback = False
        self._history: dict[str, deque] = {}
        self._last_response: dict[str, str] = {}   # track last response per session
        self._load_model()

    # ── Model Loading ────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            logger.info(f"Loading chatbot model: {self.config.CHAT_MODEL}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.CHAT_MODEL)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.config.CHAT_MODEL)
            self._model.eval()
            logger.info(f"Chatbot model loaded: {self.config.CHAT_MODEL} ✓")
        except Exception as exc:
            logger.warning(f"Chatbot model unavailable ({exc}); using rule-based fallback.")
            self._using_fallback = True

    # ── History Management ───────────────────────────────────────────────────

    def _get_history(self, session_id: str) -> deque:
        if session_id not in self._history:
            self._history[session_id] = deque(maxlen=self.config.MAX_HISTORY_TURNS * 2)
        return self._history[session_id]

    def _add_to_history(self, session_id: str, role: str, text: str) -> None:
        history = self._get_history(session_id)
        history.append({"role": role, "text": text})

    def clear_history(self, session_id: str) -> None:
        self._history.pop(session_id, None)
        self._last_response.pop(session_id, None)

    # ── Prompt Building ──────────────────────────────────────────────────────

    def build_prompt(
        self,
        user_message: str,
        history: deque,
        rag_context: Optional[str],
        emotion_data: Optional[dict],
        tone: str = "empathetic",
    ) -> str:
        """Build a simplified conversational prompt BlenderBot can understand."""
        # BlenderBot works best with plain dialogue turns.
        # Keep it short — last 2 turns + current message.
        parts = []
        history_list = list(history)
        recent = history_list[-4:] if len(history_list) > 4 else history_list
        for turn in recent:
            if turn["role"] == "user":
                parts.append(f"  {turn['text']}")
            else:
                parts.append(f"  {turn['text']}")
        parts.append(user_message)
        return "\n".join(parts)

    # ── Response Generation ──────────────────────────────────────────────────

    def generate_response(
        self,
        session_id: str,
        user_message: str,
        rag_context: Optional[str] = None,
        emotion_data: Optional[dict] = None,
        user_tone: str = "empathetic",
    ) -> str:
        """Generate a complete response, choosing model or smart fallback."""
        history = self._get_history(session_id)

        # Always try model first; if bad quality, use smart fallback
        if not self._using_fallback and self._model is not None:
            prompt = self.build_prompt(user_message, history, rag_context, emotion_data, user_tone)
            raw = self._generate_with_model(prompt)
            if self._is_good_response(raw, session_id):
                response = raw
            else:
                logger.info("Model output quality low; switching to smart fallback.")
                response = self._smart_response(user_message, emotion_data, rag_context, session_id)
        else:
            response = self._smart_response(user_message, emotion_data, rag_context, session_id)

        self._last_response[session_id] = response
        self._add_to_history(session_id, "user", user_message)
        self._add_to_history(session_id, "assistant", response)
        return response

    def _is_good_response(self, response: str, session_id: str) -> bool:
        """Check if the model response is meaningful and not repetitive."""
        if not response or len(response.strip()) < 10:
            return False
        last = self._last_response.get(session_id, "")
        if last and response.strip().lower() == last.strip().lower():
            return False
        # Flag overly generic default phrases the model repeats
        bad_phrases = [
            "i'm here to listen and support you",
            "please share what's on your mind",
            "how are you doing today",
        ]
        lower = response.lower()
        if any(p in lower for p in bad_phrases):
            return False
        return True

    def _generate_with_model(self, prompt: str) -> str:
        import torch
        try:
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                max_length=128,
                truncation=True,
            )
            with torch.no_grad():
                outputs = self._model.generate(
                    inputs["input_ids"],
                    max_new_tokens=min(self.config.MAX_NEW_TOKENS, 80),
                    temperature=self.config.TEMPERATURE,
                    top_p=self.config.TOP_P,
                    do_sample=True,
                    repetition_penalty=1.4,
                    no_repeat_ngram_size=3,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response.strip()
        except Exception as exc:
            logger.error(f"Model generation error: {exc}")
            return ""

    def _smart_response(
        self,
        user_message: str,
        emotion_data: Optional[dict],
        rag_context: Optional[str],
        session_id: str,
    ) -> str:
        """Build a varied, contextual response based on emotion + keywords."""
        emotion = "neutral"
        if emotion_data:
            emotion = emotion_data.get("primary_emotion", "neutral")

        candidates = _RESPONSES.get(emotion, _RESPONSES["neutral"])

        # Avoid repeating the last response
        last = self._last_response.get(session_id, "")
        available = [r for r in candidates if r != last]
        if not available:
            available = candidates

        base = random.choice(available)

        # Inject keyword hook if a relevant word appears in the user message
        msg_lower = user_message.lower()
        hook = ""
        for keyword, line in _KEYWORD_HOOKS.items():
            if keyword in msg_lower:
                hook = line + " "
                break

        # Optionally weave in a RAG insight (max 1 sentence)
        rag_tip = ""
        if rag_context:
            lines = [l.strip() for l in rag_context.split("\n") if l.strip() and len(l.strip()) > 20]
            if lines:
                tip = lines[0][:140]
                # Don't append if it's already in the base
                if tip.lower() not in base.lower():
                    rag_tip = f" One thing that sometimes helps: {tip}"

        return f"{hook}{base}{rag_tip}".strip()

    def _fallback_response(self, emotion_data: Optional[dict]) -> str:
        """Legacy method kept for compatibility."""
        return self._smart_response("", emotion_data, None, "__fallback__")

    # ── Streaming ────────────────────────────────────────────────────────────

    def stream_response(
        self,
        session_id: str,
        user_message: str,
        rag_context: Optional[str] = None,
        emotion_data: Optional[dict] = None,
        user_tone: str = "empathetic",
    ) -> Generator[str, None, None]:
        """Yield response words for real-time streaming."""
        response = self.generate_response(session_id, user_message, rag_context, emotion_data, user_tone)
        # generate_response already adds to history/last_response — avoid double-add
        # by popping last entry (it was added inside generate_response)
        words = response.split(" ")
        for word in words:
            yield word + " "
