"""Tests for /api/mood routes."""

import pytest


class TestMoodRoutes:

    def test_history_returns_200(self, client, session_id):
        resp = client.get(f'/api/mood/history/{session_id}')
        assert resp.status_code == 200

    def test_history_structure(self, client, session_id):
        resp = client.get(f'/api/mood/history/{session_id}')
        body = resp.get_json()
        assert 'entries' in body
        assert isinstance(body['entries'], list)

    def test_history_with_days_param(self, client, session_id):
        resp = client.get(f'/api/mood/history/{session_id}?days=7')
        assert resp.status_code == 200

    def test_history_summary_keys(self, client, session_id, sample_mood_entries):
        resp = client.get(f'/api/mood/history/{session_id}')
        body = resp.get_json()
        assert 'summary' in body
        summary = body['summary']
        assert 'avg_valence' in summary

    def test_history_chart_data(self, client, session_id, sample_mood_entries):
        resp = client.get(f'/api/mood/history/{session_id}')
        body = resp.get_json()
        assert 'chart_data' in body
        cd = body['chart_data']
        assert 'labels' in cd
        assert 'valence' in cd

    def test_entries_ordered_chronologically(self, client, session_id, sample_mood_entries):
        resp = client.get(f'/api/mood/history/{session_id}?limit=100')
        body = resp.get_json()
        entries = body.get('entries', [])
        if len(entries) > 1:
            # timestamps should be ascending or all present
            timestamps = [e.get('timestamp') for e in entries if e.get('timestamp')]
            assert timestamps == sorted(timestamps)

    def test_insights_returns_200(self, client, session_id):
        resp = client.get(f'/api/mood/insights/{session_id}')
        assert resp.status_code == 200

    def test_insights_structure(self, client, session_id, sample_mood_entries):
        resp = client.get(f'/api/mood/insights/{session_id}')
        body = resp.get_json()
        assert 'insights' in body
        assert isinstance(body['insights'], list)

    def test_insight_items_have_type_and_text(self, client, session_id, sample_mood_entries):
        resp = client.get(f'/api/mood/insights/{session_id}')
        body = resp.get_json()
        for item in body.get('insights', []):
            assert 'type' in item
            assert 'text' in item

    def test_history_unknown_session_empty_entries(self, client):
        resp = client.get('/api/mood/history/nonexistent-session-xyz')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body.get('entries') == []
