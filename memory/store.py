# memory/store.py
"""
ChromaDB vector store — semantic storage and retrieval of facts about the user.

Facts are short strings like:
  "User's name is Alex."
  "User prefers action and sci-fi movies."
  "User is working on a Python AI assistant project."
  "User listens to music via Spotify."

ChromaDB stores these as embeddings so retrieval is semantic —
querying "what does the user like to watch?" surfaces the movie preference
even if those exact words weren't used when the fact was stored.

The collection lives at cfg.memory_dir / "chroma".
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import chromadb


class FactStore:
    COLLECTION = "jarvis_facts"

    def __init__(self, chroma_dir: Path):
        chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(chroma_dir))
        self._col = self._client.get_or_create_collection(
            name=self.COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Storage ───────────────────────────────────────────────────────────────

    def add_fact(self, fact: str):
        """
        Store a fact. Uses a hash of the fact text as the ID so
        identical facts are deduplicated automatically.
        """
        fact_id = _hash(fact)
        existing = self._col.get(ids=[fact_id])
        if existing["ids"]:
            return  # already stored

        self._col.add(
            ids=[fact_id],
            documents=[fact],
        )

    def add_facts(self, facts: List[str]):
        for fact in facts:
            if fact.strip():
                self.add_fact(fact.strip())

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def query(self, context: str, n: int = 5) -> List[str]:
        """
        Return the top-n facts most semantically relevant to context.
        Returns empty list if the store is empty.
        """
        if self._col.count() == 0:
            return []

        results = self._col.query(
            query_texts=[context],
            n_results=min(n, self._col.count()),
        )
        docs = results.get("documents", [[]])[0]
        return docs

    def all_facts(self) -> List[str]:
        """Returns every stored fact — useful for building a full profile summary."""
        if self._col.count() == 0:
            return []
        results = self._col.get()
        return results.get("documents", [])

    def count(self) -> int:
        return self._col.count()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def delete_fact(self, fact: str):
        self._col.delete(ids=[_hash(fact)])

    def clear(self):
        self._client.delete_collection(self.COLLECTION)
        self._col = self._client.get_or_create_collection(
            name=self.COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()
