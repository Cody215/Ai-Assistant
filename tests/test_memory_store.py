# tests/test_memory_store.py
"""
Tests for the ChromaDB semantic fact store.

Uses tmp_path so the real chroma/ folder is never touched.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.store import FactStore


@pytest.fixture
def store(tmp_path):
    """Fresh ChromaDB store for each test."""
    return FactStore(tmp_path / "chroma")


# ── Storage ───────────────────────────────────────────────────────────────────

class TestFactStorage:

    def test_add_single_fact(self, store):
        store.add_fact("User's name is Alex.")
        assert store.count() == 1

    def test_add_multiple_facts(self, store):
        store.add_facts([
            "User likes action movies.",
            "User is working on a Python AI project.",
            "User uses Spotify for music.",
        ])
        assert store.count() == 3

    def test_deduplication(self, store):
        """Adding the same fact twice should result in one entry."""
        store.add_fact("User prefers dark themes.")
        store.add_fact("User prefers dark themes.")
        assert store.count() == 1

    def test_add_empty_string_ignored(self, store):
        store.add_facts(["", "  ", "Valid fact here."])
        assert store.count() == 1

    def test_all_facts_returns_everything(self, store):
        facts = [
            "User's name is Alex.",
            "User likes sci-fi films.",
            "User works in software development.",
        ]
        store.add_facts(facts)
        all_facts = store.all_facts()
        assert len(all_facts) == 3

    def test_empty_store_all_facts(self, store):
        assert store.all_facts() == []

    def test_count_empty(self, store):
        assert store.count() == 0


# ── Retrieval ─────────────────────────────────────────────────────────────────

class TestFactRetrieval:

    def test_query_returns_results(self, store):
        store.add_facts([
            "User enjoys watching action movies.",
            "User's favourite genre is sci-fi.",
            "User is working on a Python project.",
        ])
        results = store.query("movie recommendations", n=2)
        assert len(results) > 0
        assert len(results) <= 2

    def test_query_empty_store(self, store):
        results = store.query("anything", n=5)
        assert results == []

    def test_query_n_respects_limit(self, store):
        store.add_facts([f"Fact number {i}." for i in range(10)])
        results = store.query("fact", n=3)
        assert len(results) <= 3

    def test_query_n_larger_than_store(self, store):
        store.add_facts(["Only one fact here."])
        results = store.query("fact", n=10)
        assert len(results) == 1


# ── Cleanup ───────────────────────────────────────────────────────────────────

class TestFactCleanup:

    def test_clear_wipes_all_facts(self, store):
        store.add_facts(["Fact one.", "Fact two.", "Fact three."])
        assert store.count() == 3
        store.clear()
        assert store.count() == 0

    def test_delete_single_fact(self, store):
        store.add_fact("Fact to keep.")
        store.add_fact("Fact to delete.")
        store.delete_fact("Fact to delete.")
        assert store.count() == 1
        remaining = store.all_facts()
        assert "Fact to keep." in remaining

    def test_clear_then_add(self, store):
        """Store should work normally after being cleared."""
        store.add_facts(["Old fact."])
        store.clear()
        store.add_fact("New fact after clear.")
        assert store.count() == 1
