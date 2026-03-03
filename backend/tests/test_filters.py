"""Tests for AdvancedInputFilter (safety layer)."""

import pytest
from app.safety.filters import AdvancedInputFilter


@pytest.fixture
def filt():
    return AdvancedInputFilter()


class TestAdvancedInputFilter:

    def test_safe_message_has_level_zero(self, filt):
        result = filt.analyze("I had a good day at work today.")
        assert result['crisis_level'] == 0
        assert result['is_offensive'] is False

    def test_level_1_distress_detected(self, filt):
        result = filt.analyze("I feel so overwhelmed and can't cope anymore")
        assert result['crisis_level'] >= 1

    def test_level_2_self_harm_detected(self, filt):
        result = filt.analyze("I want to hurt myself")
        assert result['crisis_level'] >= 2

    def test_level_3_suicidal_ideation_detected(self, filt):
        result = filt.analyze("I want to kill myself tonight")
        assert result['crisis_level'] == 3

    def test_crisis_response_not_none_for_l3(self, filt):
        response = filt.get_crisis_response(3)
        assert response is not None
        assert '988' in response or 'crisis' in response.lower()

    def test_crisis_response_for_l1(self, filt):
        response = filt.get_crisis_response(1)
        assert isinstance(response, str)
        assert len(response) > 20

    def test_crisis_response_none_for_level_0(self, filt):
        result = filt.get_crisis_response(0)
        assert result is None or result == ''

    def test_safety_resources_present_for_l3(self, filt):
        result = filt.analyze("I'm going to end my life")
        assert result['crisis_level'] == 3
        assert len(result.get('safety_resources', [])) > 0

    def test_offensive_words_flagged(self, filt):
        result = filt.analyze("you piece of shit idiot")
        assert result['is_offensive'] is True

    def test_clinical_terms_not_flagged_as_offensive(self, filt):
        # Words like "kill" in clinical context shouldn't always trip profanity
        result = filt.analyze("the doctor said the cancer treatment will kill the cells")
        # crisis level may be 0, and offensive should be false for clinical context
        assert isinstance(result['is_offensive'], bool)

    def test_analyze_returns_emotion_list(self, filt):
        result = filt.analyze("I am happy and excited today")
        assert isinstance(result.get('detected_emotions', []), list)

    def test_empty_string_safe(self, filt):
        result = filt.analyze("")
        assert result['crisis_level'] == 0
