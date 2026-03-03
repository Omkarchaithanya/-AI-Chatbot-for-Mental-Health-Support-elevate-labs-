"""Tests for /api/chat route."""

import pytest
import json
from unittest.mock import MagicMock


class TestChatRoute:

    def test_chat_requires_session_id(self, client):
        resp = client.post('/api/chat',
                           data=json.dumps({'message': 'hello'}),
                           content_type='application/json')
        assert resp.status_code in (400, 422)

    def test_chat_requires_message(self, client, session_id):
        resp = client.post('/api/chat',
                           data=json.dumps({'session_id': session_id}),
                           content_type='application/json')
        assert resp.status_code in (400, 422)

    def test_chat_ok_response_structure(self, client, session_id, app):
        # Override AI components on the test app
        app.emotion_detector = MagicMock()
        app.emotion_detector.detect.return_value = {
            'primary_emotion': 'neutral',
            'confidence': 0.7,
            'valence': 0.0,
            'arousal': 0.3,
            'is_negative': False,
            'needs_support': False,
            'emoji': '😐',
        }
        app.chatbot = MagicMock()
        app.chatbot.generate_response.return_value = "I'm here for you."
        app.rag_engine = MagicMock()
        app.rag_engine.retrieve.return_value = []
        app.rag_engine.is_relevant.return_value = False
        app.rag_engine.format_context.return_value = ''
        app.tts_engine = MagicMock()
        app.tts_engine.synthesize_to_base64.return_value = None
        app.safety_filter = MagicMock()
        app.safety_filter.analyze.return_value = {
            'crisis_level': 0,
            'is_offensive': False,
            'detected_emotions': [],
            'safety_resources': [],
            'recommended_exercise': None,
        }

        resp = client.post('/api/chat',
                           data=json.dumps({'session_id': session_id, 'message': 'Hello'}),
                           content_type='application/json')
        assert resp.status_code == 200
        body = resp.get_json()
        for key in ('response', 'emotion', 'session_id'):
            assert key in body, f"Missing key {key} in response"

    def test_chat_crisis_l3_returns_resources(self, client, session_id, app):
        app.safety_filter = MagicMock()
        app.safety_filter.analyze.return_value = {
            'crisis_level': 3,
            'is_offensive': False,
            'detected_emotions': [],
            'safety_resources': ['988 Suicide & Crisis Lifeline: Call or text 988'],
            'recommended_exercise': None,
        }
        app.safety_filter.get_crisis_response.return_value = \
            "Please call 988 immediately. Your life matters."

        resp = client.post('/api/chat',
                           data=json.dumps({'session_id': session_id, 'message': 'test crisis'}),
                           content_type='application/json')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body.get('crisis_level') == 3

    def test_chat_rejects_empty_message(self, client, session_id):
        resp = client.post('/api/chat',
                           data=json.dumps({'session_id': session_id, 'message': '   '}),
                           content_type='application/json')
        assert resp.status_code in (400, 422)
