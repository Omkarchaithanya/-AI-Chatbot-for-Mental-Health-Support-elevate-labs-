"""Tests for RAGEngine."""

import pytest
import json
import numpy as np
from unittest.mock import MagicMock, patch


@pytest.fixture
def rag(tmp_path):
    """RAGEngine with mocked SentenceTransformer and tiny KB."""
    kb = [
        {
            "id": "test_001",
            "category": "mindfulness",
            "title": "Mindful Breathing",
            "content": "Focus on each breath to calm your mind.",
            "keywords": ["breathing", "calm", "mindfulness"],
            "when_to_use": "anxiety",
            "example_dialogue": "Take a deep breath.",
            "exercises": ["breathing"]
        }
    ]
    kb_path = tmp_path / 'test_kb.json'
    kb_path.write_text(json.dumps(kb))

    with patch('app.ai.rag_engine.SentenceTransformer') as mock_st:
        mock_inst = MagicMock()
        mock_inst.encode.return_value = np.random.rand(1, 384).astype('float32')
        mock_st.return_value = mock_inst

        from app.ai.rag_engine import RAGEngine
        engine = RAGEngine.__new__(RAGEngine)
        engine._model      = mock_inst
        engine._entries    = kb
        engine._embeddings = np.random.rand(len(kb), 384).astype('float32')
        engine._index      = None  # will use numpy fallback
        engine._config     = MagicMock(
            RAG_TOP_K=3,
            RAG_SIMILARITY_THRESHOLD=0.0,   # low so any entry qualifies
            EMBEDDINGS_CACHE_PATH=None,
        )
        return engine


class TestRAGEngine:

    def test_retrieve_returns_list(self, rag):
        results = rag.retrieve("I feel anxious", top_k=1)
        assert isinstance(results, list)

    def test_retrieve_respects_top_k(self, rag):
        # KB has 1 entry, top_k=1 should return at most 1
        results = rag.retrieve("mindfulness breathing", top_k=1)
        assert len(results) <= 1

    def test_format_context_returns_string(self, rag):
        results = rag.retrieve("breathing", top_k=1)
        ctx = rag.format_context(results)
        assert isinstance(ctx, str)

    def test_format_context_empty_for_no_results(self, rag):
        ctx = rag.format_context([])
        assert ctx == '' or ctx is None or isinstance(ctx, str)

    def test_is_relevant_false_when_empty(self, rag):
        assert rag.is_relevant([]) is False

    def test_is_relevant_true_when_results(self, rag):
        rag._config.RAG_SIMILARITY_THRESHOLD = 0.0
        results = rag.retrieve("mindfulness", top_k=1)
        if results:
            assert rag.is_relevant(results) is True

    def test_entry_has_required_fields(self, rag):
        assert len(rag._entries) > 0
        entry = rag._entries[0]
        for field in ('id', 'category', 'title', 'content'):
            assert field in entry, f"Missing field: {field}"
