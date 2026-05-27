"""
Router for determining where to execute tools: locally (Ollama) or cloud (Gemini).

Rules:
  - Local tools: open_app, create_file, open_file, draft_email, play_music,
    get_time, get_date, get_volume, set_volume, get_battery, get_system_status,
    capture_screen
  - Cloud tools: web_search, get_weather
  - Always cloud: memory operations, conversational responses

Routing is deterministic — same tool always routes the same way.
If Ollama is unavailable, local tools fall back to Gemini transparently.
"""

from __future__ import annotations


class Router:
    """Determine execution location (local vs cloud) for each tool."""

    # Tools that run locally on Ollama (privacy, speed, no API calls)
    LOCAL_TOOLS = {
        "open_app",
        "create_file",
        "open_file",
        "draft_email",
        "play_music",
        "get_time",
        "get_date",
        "get_volume",
        "set_volume",
        "get_battery",
        "get_system_status",
        "capture_screen",
    }

    # Tools that must run on cloud (Gemini has capability/knowledge)
    CLOUD_TOOLS = {
        "web_search",
        "get_weather",
    }

    def is_local(self, tool_name: str) -> bool:
        """Return True if tool should execute locally (Ollama), False for cloud (Gemini)."""
        return tool_name in self.LOCAL_TOOLS

    def is_cloud(self, tool_name: str) -> bool:
        """Return True if tool should execute on cloud (Gemini)."""
        return tool_name in self.CLOUD_TOOLS

    def classify(self, tool_name: str) -> str:
        """Return 'local', 'cloud', or 'unknown'."""
        if self.is_local(tool_name):
            return "local"
        elif self.is_cloud(tool_name):
            return "cloud"
        else:
            return "unknown"
