# memory/db.py
"""
SQLite layer — stores conversation history and session summaries.

Schema:
  turns    — every user/Jarvis exchange with timestamp and session ID
  sessions — one row per session with a written summary
  profile  — key/value facts about the user (name, preferences, etc.)

The database file lives at cfg.memory_dir / "jarvis.db".
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


class ConversationDB:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self.session_id = str(uuid.uuid4())
        self._start_session()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL,  -- 'user' or 'jarvis'
                content     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT    PRIMARY KEY,
                started_at  TEXT    NOT NULL,
                ended_at    TEXT,
                summary     TEXT
            );

            CREATE TABLE IF NOT EXISTS profile (
                key         TEXT    PRIMARY KEY,
                value       TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );
        """)
        self.conn.commit()

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def _start_session(self):
        self.conn.execute(
            "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
            (self.session_id, _now()),
        )
        self.conn.commit()

    def end_session(self, summary: Optional[str] = None):
        self.conn.execute(
            "UPDATE sessions SET ended_at = ?, summary = ? WHERE id = ?",
            (_now(), summary, self.session_id),
        )
        self.conn.commit()

    # ── Turns ─────────────────────────────────────────────────────────────────

    def save_turn(self, role: str, content: str):
        self.conn.execute(
            "INSERT INTO turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (self.session_id, role, content, _now()),
        )
        self.conn.commit()

    def recent_turns(self, n: int = 10) -> List[Tuple[str, str]]:
        """Returns the last n turns as (role, content) pairs, oldest first."""
        rows = self.conn.execute(
            "SELECT role, content FROM turns ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [(r["role"], r["content"]) for r in reversed(rows)]

    # ── Profile ───────────────────────────────────────────────────────────────

    def set_profile(self, key: str, value: str):
        self.conn.execute(
            "INSERT INTO profile (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, _now()),
        )
        self.conn.commit()

    def get_profile(self) -> dict:
        rows = self.conn.execute("SELECT key, value FROM profile").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def get_recent_summaries(self, n: int = 3) -> List[str]:
        """Returns summaries from the last n completed sessions."""
        rows = self.conn.execute(
            "SELECT summary FROM sessions WHERE summary IS NOT NULL "
            "ORDER BY started_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [r["summary"] for r in rows]

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self):
        self.conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
