# tools/screen.py
"""
Screen analysis tool — uses a local Ollama vision model.

Nothing is sent to Google. The screenshot stays on your machine.

Requirements:
    pip install pillow ollama
    ollama pull llava          # or llava-phi3 for a lighter model

Configuration:
    OLLAMA_VISION_MODEL in config.py (default: "llava")
    OLLAMA_HOST         in config.py (default: "http://localhost:11434")

How it works:
    1. capture_screen() takes a screenshot and stores it in a buffer
    2. jarvis_core._think() detects the pending screenshot after the tool call
    3. _ask_with_image() sends the image + question to Ollama locally
    4. Response is spoken by Jarvis — Gemini never sees the image
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, Optional

from tools import register_tool, schema

# ── Screenshot buffer ─────────────────────────────────────────────────────────

_pending_screenshot: Optional[str] = None  # base64 PNG


def get_pending_screenshot() -> Optional[str]:
    return _pending_screenshot


def clear_pending_screenshot():
    global _pending_screenshot
    _pending_screenshot = None


# ── Tool ──────────────────────────────────────────────────────────────────────

@register_tool(
    name="capture_screen",
    description=(
        "Capture a screenshot of the user's full screen and analyse it locally. "
        "Use when the user asks you to look at, describe, read, or analyse "
        "anything currently visible on their screen. "
        "This is processed locally — nothing is sent to external servers."
    ),
    parameters=schema(
        reason="optional: what to focus on, e.g. 'error message', 'code review', 'summarise screen'",
    ),
)
def capture_screen(args: Dict[str, Any]) -> str:
    global _pending_screenshot

    try:
        from PIL import ImageGrab
    except ImportError:
        return "Pillow not installed. Run: pip install pillow"

    try:
        screenshot = ImageGrab.grab()

        # Resize if very large — keeps Ollama processing time reasonable
        max_width = 1280
        if screenshot.width > max_width:
            ratio  = max_width / screenshot.width
            height = int(screenshot.height * ratio)
            screenshot = screenshot.resize((max_width, height))

        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG", optimize=True)
        _pending_screenshot = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return "Screenshot captured. Analysing locally now."

    except Exception as e:
        return f"Screenshot failed: {e}"
