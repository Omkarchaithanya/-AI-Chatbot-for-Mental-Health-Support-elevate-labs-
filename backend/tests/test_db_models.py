"""Tests for SQLAlchemy ORM models."""

import pytest
from datetime import datetime, timezone


class TestUserModel:

    def test_user_created_with_session_id(self, app, session_id):
        from app.db.models import User
        with app.app_context():
            user = User.query.filter_by(session_id=session_id).first()
            assert user is not None
            assert user.session_id == session_id

    def test_user_to_dict(self, app, session_id):
        from app.db.models import User
        with app.app_context():
            user = User.query.filter_by(session_id=session_id).first()
            if user:
                d = user.to_dict()
                assert isinstance(d, dict)
                assert 'session_id' in d

    def test_user_defaults(self, app):
        from app.db.models import User
        from app.db.database import db
        with app.app_context():
            u = User(session_id='test-defaults-xyz')
            db.session.add(u)
            db.session.commit()
            assert u.message_count == 0 or u.message_count is None
            assert u.preferred_tone in ('gentle', 'friendly', 'balanced', None)


class TestMoodEntryModel:

    def test_mood_entry_creation(self, app, session_id):
        from app.db.models import MoodEntry
        from app.db.database import db
        with app.app_context():
            e = MoodEntry(
                session_id=session_id,
                emotion='joy',
                confidence=0.9,
                valence=0.8,
                arousal=0.6,
            )
            db.session.add(e)
            db.session.commit()
            assert e.id is not None

    def test_mood_entry_to_dict(self, app, session_id):
        from app.db.models import MoodEntry
        from app.db.database import db
        with app.app_context():
            e = MoodEntry(session_id=session_id, emotion='neutral',
                          confidence=0.5, valence=0.0, arousal=0.3)
            db.session.add(e)
            db.session.commit()
            d = e.to_dict()
            assert 'emotion' in d
            assert 'valence' in d


class TestChatMessageModel:

    def test_chat_message_creation(self, app, session_id):
        from app.db.models import ChatMessage
        from app.db.database import db
        with app.app_context():
            m = ChatMessage(
                session_id=session_id,
                role='user',
                content='Hello world',
                emotion_detected='neutral',
                rag_used=False,
                response_time_ms=120,
            )
            db.session.add(m)
            db.session.commit()
            assert m.id is not None

    def test_chat_message_to_dict(self, app, session_id):
        from app.db.models import ChatMessage
        from app.db.database import db
        with app.app_context():
            m = ChatMessage(session_id=session_id, role='bot',
                            content='I hear you.', emotion_detected='neutral')
            db.session.add(m)
            db.session.commit()
            d = m.to_dict()
            assert 'role' in d
            assert 'content' in d


class TestExerciseLogModel:

    def test_exercise_log_creation(self, app, session_id):
        from app.db.models import ExerciseLog
        from app.db.database import db
        with app.app_context():
            ex = ExerciseLog(
                session_id=session_id,
                exercise_type='breathing_4_7_8',
                duration_seconds=90,
                completed=True,
            )
            db.session.add(ex)
            db.session.commit()
            assert ex.id is not None

    def test_exercise_log_to_dict(self, app, session_id):
        from app.db.models import ExerciseLog
        from app.db.database import db
        with app.app_context():
            ex = ExerciseLog(session_id=session_id, exercise_type='box_breathing',
                             duration_seconds=60, completed=True)
            db.session.add(ex)
            db.session.commit()
            d = ex.to_dict()
            assert 'exercise_type' in d
            assert 'completed' in d
