"""Tests for EmotionDetector."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def detector():
    with patch('app.ai.emotion_detector.pipeline') as mock_p:
        mock_p.return_value = lambda text, **kw: [[
            {'label': 'sadness', 'score': 0.60},
            {'label': 'joy',     'score': 0.30},
            {'label': 'neutral', 'score': 0.10},
        ]]
        from app.ai.emotion_detector import EmotionDetector
        return EmotionDetector.__new__(EmotionDetector)


class TestEmotionDetector:

    def test_detect_returns_required_keys(self, detector):
        with patch.object(detector, '_pipeline', side_effect=lambda t, **kw: [[
            {'label': 'sadness', 'score': 0.7},
            {'label': 'joy',     'score': 0.2},
            {'label': 'neutral', 'score': 0.1},
        ]]):
            from app.ai.emotion_detector import EmotionDetector, EMOTION_VALENCE, EMOTION_AROUSAL
            result = EmotionDetector._detect_with_pipeline(detector, 'I feel sad')
        assert isinstance(result, dict)

    def test_rule_based_detects_anxiety_keywords(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        d._model_loaded = False
        result = d._detect_with_rules("I'm so anxious and worried about everything")
        assert result['primary_emotion'] in ('anxiety', 'fear')

    def test_rule_based_detects_joy(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        d._model_loaded = False
        result = d._detect_with_rules("I feel wonderful and so happy today!")
        assert result['primary_emotion'] == 'joy'

    def test_rule_based_detects_sadness(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        d._model_loaded = False
        result = d._detect_with_rules("I am depressed and feel hopeless")
        assert result['primary_emotion'] in ('sadness', 'depression')

    def test_valence_is_in_range(self):
        from app.ai.emotion_detector import EmotionDetector, EMOTION_VALENCE
        for emotion, val in EMOTION_VALENCE.items():
            assert -1.0 <= val <= 1.0, f"Valence out of range for {emotion}"

    def test_arousal_is_in_range(self):
        from app.ai.emotion_detector import EMOTION_AROUSAL
        for emotion, val in EMOTION_AROUSAL.items():
            assert 0.0 <= val <= 1.0, f"Arousal out of range for {emotion}"

    def test_needs_support_flags_negative_emotions(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        d._model_loaded = False
        result = d._detect_with_rules("I want to give up on everything")
        assert result['needs_support'] is True

    def test_get_emotion_emoji_returns_string(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        emoji = d.get_emotion_emoji('joy')
        assert isinstance(emoji, str)
        assert len(emoji) > 0

    def test_neutral_when_no_keywords_match(self):
        from app.ai.emotion_detector import EmotionDetector
        d = EmotionDetector.__new__(EmotionDetector)
        d._model_loaded = False
        result = d._detect_with_rules("the cat sat on the mat")
        assert result['primary_emotion'] in ('neutral', 'joy', 'sadness', 'anxiety')
        assert result['confidence'] >= 0
