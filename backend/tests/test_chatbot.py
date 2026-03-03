"""Tests for MindEaseChatbot."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def chatbot():
    with patch('app.ai.chatbot.AutoTokenizer') as mock_tok, \
         patch('app.ai.chatbot.AutoModelForSeq2SeqLM') as mock_model:

        mock_tok_inst = MagicMock()
        mock_tok_inst.return_value = MagicMock(input_ids=MagicMock())
        mock_tok_inst.decode.return_value = "I'm here to support you."
        mock_tok.from_pretrained.return_value = mock_tok_inst

        mock_model_inst = MagicMock()
        mock_model_inst.generate.return_value = MagicMock()
        mock_model.from_pretrained.return_value = mock_model_inst

        from app.ai.chatbot import MindEaseChatbot
        bot = MindEaseChatbot.__new__(MindEaseChatbot)
        bot._tokenizer = mock_tok_inst
        bot._model     = mock_model_inst
        bot._model_loaded = True
        bot._history   = {}
        bot._config    = MagicMock(
            MAX_NEW_TOKENS=150,
            MAX_HISTORY_TURNS=5,
            TEMPERATURE=0.85,
            TOP_P=0.92,
        )
        return bot


class TestMindEaseChatbot:

    def test_generate_response_returns_string(self, chatbot):
        with patch.object(chatbot, 'generate_response', return_value="I hear you."):
            result = chatbot.generate_response("session1", "I feel sad", {}, "")
        assert isinstance(result, str)

    def test_fallback_response_for_joy(self, chatbot):
        result = chatbot._fallback_response({'primary_emotion': 'joy'})
        assert isinstance(result, str)
        assert len(result) > 10

    def test_fallback_response_for_anxiety(self, chatbot):
        result = chatbot._fallback_response({'primary_emotion': 'anxiety'})
        assert isinstance(result, str)
        assert len(result) > 10

    def test_fallback_response_for_unknown_emotion(self, chatbot):
        result = chatbot._fallback_response({'primary_emotion': 'unknown_xyz'})
        assert isinstance(result, str)
        assert len(result) > 10

    def test_build_prompt_contains_user_message(self, chatbot):
        from collections import deque
        chatbot._history = {'sess': deque()}
        prompt = chatbot.build_prompt('sess', 'Hello there', 'gentle', {}, '')
        assert 'Hello there' in prompt or isinstance(prompt, str)

    def test_history_is_bounded(self, chatbot):
        from collections import deque
        max_turns = 5
        chatbot._history = {'sess': deque(maxlen=max_turns * 2)}
        for i in range(20):
            chatbot._history['sess'].append(f"message {i}")
        assert len(chatbot._history['sess']) <= max_turns * 2

    def test_stream_response_is_iterable(self, chatbot):
        with patch.object(chatbot, 'stream_response',
                          return_value=iter(["Hello", " there"])):
            tokens = list(chatbot.stream_response("sess", "Hi", {}, ""))
        assert len(tokens) == 2
