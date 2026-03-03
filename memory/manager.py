# memory/manager.py
"""
MemoryManager — the single interface jarvis_core talks to.

Responsibilities:
  - Build a context block injected into the system prompt each session
  - Save turns to SQLite after each exchange
  - Extract memorable facts from conversations via Gemini and store in ChromaDB
  - Write a session summary to SQLite on shutdown
  - Expose the profile dict for display or debugging

jarvis_core only needs to call:
  manager.context_block()         → str  (inject into system prompt at startup)
  manager.save_turn(role, text)         (call after each user/jarvis turn)
  manager.process_turn(user, jarvis)    (extract facts in background)
  manager.close(chat)                   (write summary, close DB)
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from memory.db import ConversationDB
from memory.store import FactStore


class MemoryManager:
    def __init__(self, memory_dir: Path, gemini_client: genai.Client, gemini_model: str):
        self._db    = ConversationDB(memory_dir / "jarvis.db")
        self._facts = FactStore(memory_dir / "chroma")
        self._client = gemini_client
        self._model  = gemini_model
        self._lock   = threading.Lock()

    # ── Context injection ─────────────────────────────────────────────────────

    def context_block(self) -> str:
        """
        Returns a compact memory block to append to the system prompt.
        Includes: user profile facts, recent session summaries, last few turns.
        """
        sections = []

        # User profile from ChromaDB
        all_facts = self._facts.all_facts()
        if all_facts:
            facts_text = "\n".join(f"  - {f}" for f in all_facts[:15])
            sections.append(f"## WHAT YOU KNOW ABOUT THE USER\n{facts_text}")

        # Recent session summaries
        summaries = self._db.get_recent_summaries(n=2)
        if summaries:
            summ_text = "\n".join(f"  - {s}" for s in summaries)
            sections.append(f"## RECENT SESSION SUMMARIES\n{summ_text}")

        # Last few turns for conversational continuity
        recent = self._db.recent_turns(n=6)
        if recent:
            turns_text = "\n".join(
                f"  {'User' if r == 'user' else 'Jarvis'}: {c}"
                for r, c in recent
            )
            sections.append(f"## LAST CONVERSATION\n{turns_text}")

        if not sections:
            return ""

        return (
            "\n\n---\n"
            "## MEMORY CONTEXT\n"
            "The following is persistent memory from previous sessions. "
            "Use it naturally — don't announce that you remember things, "
            "just let it inform how you respond.\n\n"
            + "\n\n".join(sections)
        )

    # ── Turn saving ───────────────────────────────────────────────────────────

    def save_turn(self, role: str, content: str):
        with self._lock:
            self._db.save_turn(role, content)

    # ── Fact extraction ───────────────────────────────────────────────────────

    def process_turn(self, user_text: str, jarvis_text: str):
        """
        Runs in a background thread after each exchange.
        Asks Gemini to extract any memorable facts and stores them.
        """
        t = threading.Thread(
            target=self._extract_and_store,
            args=(user_text, jarvis_text),
            daemon=True,
        )
        t.start()

    def _extract_and_store(self, user_text: str, jarvis_text: str):
        prompt = (
            "You are a memory extraction system for a voice assistant.\n"
            "Given this exchange, extract any facts worth remembering about the user.\n"
            "Only extract concrete, durable facts — preferences, names, projects, habits, interests.\n"
            "Skip small talk, one-off questions, or anything transient.\n"
            "Return ONLY a plain list of short fact sentences, one per line. "
            "If there is nothing worth remembering, return exactly: NONE\n\n"
            f"User: {user_text}\n"
            f"Jarvis: {jarvis_text}"
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    max_output_tokens=200,
                ),
            )
            text = (response.text or "").strip()
            if text.upper() == "NONE" or not text:
                return

            facts = [line.lstrip("•-– ").strip() for line in text.splitlines() if line.strip()]
            with self._lock:
                self._facts.add_facts(facts)

        except Exception as e:
            pass  # memory extraction is best-effort, never block the pipeline

    # ── Session summary ───────────────────────────────────────────────────────

    def close(self, chat=None):
        """Write session summary then close DB. Pass the Gemini chat object if available."""
        summary = None
        if chat is not None:
            summary = self._write_summary(chat)
        self._db.end_session(summary=summary)
        self._db.close()

    def _write_summary(self, chat) -> Optional[str]:
        try:
            response = chat.send_message(
                "[SYSTEM: Write a one-sentence summary of what was discussed or accomplished "
                "in this session. Be factual and brief. Output the sentence only.]"
            )
            return (response.text or "").strip()
        except Exception:
            return None

    # ── Profile access ────────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        return self._db.get_profile()

    def fact_count(self) -> int:
        return self._facts.count()
