# tests/test_memory_db.py
"""
Tests for the SQLite conversation database layer.

Uses pytest's tmp_path fixture so real data is never touched.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.db import ConversationDB


@pytest.fixture
def db(tmp_path):
    """Fresh database for each test, wiped afterwards."""
    return ConversationDB(tmp_path / "test.db")


# ── Turns ─────────────────────────────────────────────────────────────────────

class TestTurns:

    def test_save_and_retrieve_single_turn(self, db):
        db.save_turn("user", "Hello Jarvis")
        turns = db.recent_turns(n=10)
        assert len(turns) == 1
        assert turns[0] == ("user", "Hello Jarvis")

    def test_save_multiple_turns_preserves_order(self, db):
        db.save_turn("user",   "Open Chrome")
        db.save_turn("jarvis", "Chrome's open.")
        db.save_turn("user",   "What time is it?")
        db.save_turn("jarvis", "The time is 3:00 PM")
        turns = db.recent_turns(n=10)
        assert turns[0][1] == "Open Chrome"
        assert turns[1][1] == "Chrome's open."
        assert turns[2][1] == "What time is it?"
        assert turns[3][1] == "The time is 3:00 PM"

    def test_recent_turns_respects_n_limit(self, db):
        for i in range(20):
            db.save_turn("user", f"Message {i}")
        turns = db.recent_turns(n=5)
        assert len(turns) == 5

    def test_recent_turns_returns_most_recent(self, db):
        for i in range(10):
            db.save_turn("user", f"Message {i}")
        turns = db.recent_turns(n=3)
        # Should be the last 3, oldest first
        assert turns[0][1] == "Message 7"
        assert turns[1][1] == "Message 8"
        assert turns[2][1] == "Message 9"

    def test_recent_turns_empty_db(self, db):
        turns = db.recent_turns(n=10)
        assert turns == []

    def test_roles_stored_correctly(self, db):
        db.save_turn("user",   "Hello")
        db.save_turn("jarvis", "Ready.")
        turns = db.recent_turns(n=10)
        assert turns[0][0] == "user"
        assert turns[1][0] == "jarvis"


# ── Sessions ──────────────────────────────────────────────────────────────────

class TestSessions:

    def test_session_created_on_init(self, tmp_path):
        db = ConversationDB(tmp_path / "test.db")
        rows = db.conn.execute("SELECT * FROM sessions").fetchall()
        assert len(rows) == 1

    def test_end_session_writes_summary(self, db):
        db.end_session(summary="Discussed action movies.")
        summaries = db.get_recent_summaries(n=5)
        assert len(summaries) == 1
        assert "action movies" in summaries[0]

    def test_end_session_no_summary(self, db):
        db.end_session(summary=None)
        summaries = db.get_recent_summaries(n=5)
        assert len(summaries) == 0  # None summaries excluded

    def test_recent_summaries_respects_n(self, tmp_path):
        """Each DB init creates a new session — create several."""
        summaries_written = []
        for i in range(5):
            d = ConversationDB(tmp_path / f"test_{i}.db")
            d.end_session(summary=f"Session {i} summary")
            summaries_written.append(f"Session {i} summary")
            d.close()

        # Re-open last db and check only n returned
        d = ConversationDB(tmp_path / "test_4.db")
        results = d.get_recent_summaries(n=2)
        assert len(results) <= 2
        d.close()

    def test_unique_session_ids(self, tmp_path):
        db1 = ConversationDB(tmp_path / "a.db")
        db2 = ConversationDB(tmp_path / "b.db")
        assert db1.session_id != db2.session_id
        db1.close()
        db2.close()


# ── Profile ───────────────────────────────────────────────────────────────────

class TestProfile:

    def test_set_and_get_single_fact(self, db):
        db.set_profile("name", "Alex")
        profile = db.get_profile()
        assert profile["name"] == "Alex"

    def test_set_multiple_facts(self, db):
        db.set_profile("name",       "Alex")
        db.set_profile("preference", "action movies")
        db.set_profile("project",    "Jarvis AI assistant")
        profile = db.get_profile()
        assert profile["name"]       == "Alex"
        assert profile["preference"] == "action movies"
        assert profile["project"]    == "Jarvis AI assistant"

    def test_update_existing_key(self, db):
        db.set_profile("name", "Alex")
        db.set_profile("name", "James")
        profile = db.get_profile()
        assert profile["name"] == "James"
        # Should not create a duplicate row
        rows = db.conn.execute("SELECT * FROM profile WHERE key='name'").fetchall()
        assert len(rows) == 1

    def test_empty_profile(self, db):
        profile = db.get_profile()
        assert profile == {}
