# tools/apps.py
"""
Tools for launching desktop applications.
Add new apps to APP_PATHS — no other changes needed.
"""

import subprocess
from typing import Any, Dict

from tools import register_tool, schema

# ── Configuration ─────────────────────────────────────────────────────────────
# Edit these paths to match your machine.

APP_PATHS: Dict[str, str] = {
    "chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode":      r"C:\Users\codye\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code\Visual Studio Code.exe",
    "notepad":     "notepad.exe",
    "calculator":  "calc.exe",
    "word":        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":       r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "outlook":     r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    "explorer":    "explorer.exe",
}

# ── Tool ──────────────────────────────────────────────────────────────────────

@register_tool(
    name="open_app",
    description="Open a desktop application by name (e.g. chrome, vscode, notepad, word).",
    parameters=schema(app="Name of the app to open"),
)
def open_app(args: Dict[str, Any]) -> str:
    app = str(args.get("app", "")).strip().lower()
    if not app:
        return "Missing argument: app"

    path = APP_PATHS.get(app)
    if not path:
        known = ", ".join(sorted(APP_PATHS.keys()))
        return f"I don't know '{app}'. Known apps: {known}"

    try:
        subprocess.Popen(path, shell=False)
        return f"Opened {app}."
    except FileNotFoundError:
        return f"Could not find {app} at the configured path. You may need to update APP_PATHS in tools/apps.py."
