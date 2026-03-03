# memory/view.py
"""
View what Jarvis has stored in memory.

Usage:
    python memory/view.py              — show everything
    python memory/view.py --facts      — show stored facts only
    python memory/view.py --summaries  — show session summaries only
    python memory/view.py --history    — show recent conversation turns
    python memory/view.py --history 20 — show last N turns
"""

import argparse
import sqlite3
import sys
from pathlib import Path

MEMORY_DIR = Path(__file__).parent.parent / "memory_data"
DB_PATH    = MEMORY_DIR / "jarvis.db"
CHROMA_DIR = MEMORY_DIR / "chroma"

# ── Colours (works on Windows 10+ terminals) ──────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def header(title: str):
    width = 52
    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")

def no_data(msg: str):
    print(f"  {DIM}{msg}{RESET}")

# ── Facts (ChromaDB) ──────────────────────────────────────────────────────────

def show_facts():
    header("STORED FACTS  (ChromaDB)")
    if not CHROMA_DIR.exists():
        no_data("No ChromaDB store found. Run Jarvis first.")
        return

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            col = client.get_collection("jarvis_facts")
        except Exception:
            no_data("No facts stored yet.")
            return

        count = col.count()
        if count == 0:
            no_data("No facts stored yet.")
            return

        results = col.get()
        docs = results.get("documents", [])
        print(f"  {DIM}{count} fact(s) on record:{RESET}\n")
        for i, fact in enumerate(docs, 1):
            print(f"  {GREEN}{i:>2}.{RESET}  {fact}")

    except ImportError:
        print("  chromadb not installed. Run: pip install chromadb")

# ── Summaries (SQLite) ────────────────────────────────────────────────────────

def show_summaries():
    header("SESSION SUMMARIES  (SQLite)")
    if not DB_PATH.exists():
        no_data("No database found. Run Jarvis first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, started_at, ended_at, summary FROM sessions ORDER BY started_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        no_data("No sessions recorded yet.")
        return

    for row in rows:
        started = row["started_at"][:16].replace("T", "  ")
        ended   = (row["ended_at"] or "")[:16].replace("T", "  ")
        summary = row["summary"] or "(no summary written)"
        sid     = row["id"][:8]

        print(f"\n  {YELLOW}{BOLD}Session {sid}...{RESET}")
        print(f"  {DIM}Started : {started}  UTC{RESET}")
        if ended:
            print(f"  {DIM}Ended   : {ended}  UTC{RESET}")
        print(f"  {GREEN}Summary : {summary}{RESET}")

# ── History (SQLite) ──────────────────────────────────────────────────────────

def show_history(n: int = 10):
    header(f"RECENT CONVERSATION  (last {n} turns)")
    if not DB_PATH.exists():
        no_data("No database found. Run Jarvis first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT role, content, timestamp FROM turns ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()

    if not rows:
        no_data("No conversation history yet.")
        return

    for row in reversed(rows):
        role      = row["role"].upper()
        content   = row["content"]
        timestamp = row["timestamp"][:16].replace("T", "  ")
        colour    = CYAN if role == "USER" else GREEN
        print(f"\n  {colour}{BOLD}{role}{RESET}  {DIM}({timestamp} UTC){RESET}")
        print(f"  {content}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="View Jarvis memory.")
    parser.add_argument("--facts",     action="store_true", help="Show stored facts only")
    parser.add_argument("--summaries", action="store_true", help="Show session summaries only")
    parser.add_argument("--history",   nargs="?", const=10, type=int, metavar="N",
                        help="Show last N conversation turns (default: 10)")
    args = parser.parse_args()

    any_flag = args.facts or args.summaries or (args.history is not None)

    if args.facts or not any_flag:
        show_facts()
    if args.summaries or not any_flag:
        show_summaries()
    if args.history is not None:
        show_history(args.history)
    elif not any_flag:
        show_history(10)

    print(f"\n{DIM}Memory location: {MEMORY_DIR.resolve()}{RESET}\n")


if __name__ == "__main__":
    main()
