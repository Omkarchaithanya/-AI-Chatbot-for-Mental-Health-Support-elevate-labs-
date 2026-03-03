"""
MindEase PRO — Pytest Fixtures (conftest.py)
Provides: in-memory SQLite app, mocked AI components, sample data helpers.
"""

import pytest
import json
from unittest.mock import MagicMock, patch

# ── Create app with test config ─────────────────────────────────────
@pytest.fixture(scope='session')
def app():
    """Flask test app with in-memory SQLite and all AI components mocked."""
    # Patch heavy AI loaders before import so models are never downloaded
    with patch('app.ai.emotion_detector.pipeline') as mock_pipeline, \
         patch('app.ai.chatbot.AutoTokenizer') as mock_tok, \
         patch('app.ai.chatbot.AutoModelForSeq2SeqLM') as mock_model, \
         patch('app.ai.rag_engine.SentenceTransformer') as mock_st, \
         patch('app.ai.tts_engine.gTTS') as mock_gtts:

        # Emotion pipeline mock
        mock_pipeline.return_value = lambda text, **kw: [[
            {'label': 'joy',     'score': 0.72},
            {'label': 'neutral', 'score': 0.18},
        ]]

        # SentenceTransformer mock
        import numpy as np
        mock_st_inst = MagicMock()
        mock_st_inst.encode.return_value = np.random.rand(1, 384).astype('float32')
        mock_st.return_value = mock_st_inst

        # gTTS mock
        mock_gtts_inst = MagicMock()
        mock_gtts_inst.write_to_fp = lambda fp: fp.write(b'FAKE_AUDIO')
        mock_gtts.return_value = mock_gtts_inst

        # Chatbot tokenizer / model mocks
        mock_tok_inst = MagicMock()
        mock_tok_inst.return_value = {'input_ids': MagicMock(), 'attention_mask': MagicMock()}
        mock_tok.from_pretrained.return_value = mock_tok_inst

        mock_model_inst = MagicMock()
        mock_model_inst.generate.return_value = MagicMock()
        mock_model.from_pretrained.return_value = mock_model_inst

        from app import create_app
        test_app = create_app({
            'TESTING': True,
            'DATABASE_URL': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret',
            'KNOWLEDGE_BASE_PATH': 'data/cbt_knowledge_base.json',
            'EMBEDDINGS_CACHE_PATH': None,
        })

        yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session_id(client):
    """Creates a fresh session and returns its ID."""
    resp = client.post('/api/sessions/new')
    data = resp.get_json()
    return data['session_id']


@pytest.fixture
def sample_mood_entries(app, session_id):
    """Seeds 5 mood entries for testing."""
    from app.db.models import MoodEntry
    from app.db.database import db
    entries = []
    emotions = ['joy', 'sadness', 'anxiety', 'joy', 'neutral']
    with app.app_context():
        for i, emo in enumerate(emotions):
            e = MoodEntry(
                session_id=session_id,
                emotion=emo,
                confidence=0.8,
                valence=0.5 if emo == 'joy' else -0.5,
                arousal=0.4,
            )
            db.session.add(e)
            entries.append(e)
        db.session.commit()
    return entries


@pytest.fixture
def mock_emotion_detector():
    detector = MagicMock()
    detector.detect.return_value = {
        'primary_emotion': 'joy',
        'confidence': 0.85,
        'all_emotions': {'joy': 0.85, 'neutral': 0.15},
        'valence': 0.9,
        'arousal': 0.6,
        'is_negative': False,
        'needs_support': False,
        'emoji': '😊',
    }
    return detector


@pytest.fixture
def mock_rag_engine():
    engine = MagicMock()
    engine.retrieve.return_value = []
    engine.format_context.return_value = ''
    engine.is_relevant.return_value = False
    return engine


@pytest.fixture
def mock_chatbot():
    bot = MagicMock()
    bot.generate_response.return_value = "I hear you. Let's work through this together."
    bot.stream_response.return_value = iter(["I hear", " you.", " Let's work through this", " together."])
    return bot
