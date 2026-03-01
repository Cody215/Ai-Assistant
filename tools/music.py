# tools/music.py
"""
Tool for playing music — either via Spotify or from a local folder.
"""

import difflib
import os
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools import register_tool, schema

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_MUSIC_DIR = str(Path.home() / "Music")
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_local_track(query: str, directory: str) -> Optional[Path]:
    root = Path(directory)
    if not root.exists():
        return None

    query_l = query.lower().strip()
    if not query_l:
        return None

    candidates: List[Path] = [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS
    ]

    if not candidates:
        return None

    scored = []
    for p in candidates:
        name = p.stem.lower()
        score = difflib.SequenceMatcher(a=query_l, b=name).ratio()
        if query_l in name:
            score += 0.2
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_path = scored[0]

    return best_path if best_score >= 0.35 else None

# ── Tool ──────────────────────────────────────────────────────────────────────

@register_tool(
    name="play_music",
    description="Play music from Spotify or from the local Music folder.",
    parameters=schema(
        query="Song, artist, or album name to play",
        source="optional: spotify | local (default: spotify)",
        directory="optional: local folder path to search (default: ~/Music)",
    ),
)
def play_music(args: Dict[str, Any]) -> str:
    query     = str(args.get("query", "")).strip()
    source    = str(args.get("source", "spotify")).strip().lower()
    directory = str(args.get("directory", DEFAULT_MUSIC_DIR)).strip()

    if not query:
        return "Missing argument: query"

    if source in ("spotify", "spot"):
        q = urllib.parse.quote_plus(query)
        try:
            webbrowser.open(f"spotify:search:{query}")
        except Exception:
            pass
        webbrowser.open(f"https://open.spotify.com/search/{q}")
        return f"Opening Spotify for: {query}"

    # Local playback
    best = _best_local_track(query, directory)
    if not best:
        return f"No local track found matching '{query}' in {Path(directory).resolve()}."

    try:
        os.startfile(str(best))  # type: ignore[attr-defined]
    except Exception:
        webbrowser.open(best.as_uri())

    return f"Playing: {best.name}"
