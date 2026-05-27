"""
Response formatters for instant tool result formatting.

Deterministic tool results (time, battery, volume) are formatted directly here
without waiting for Ollama. Preserves privacy while eliminating latency.

Complex results (screenshots, web searches) still go to Ollama for intelligent replies.
"""

from __future__ import annotations
from typing import Optional


def should_format_directly(tool_name: str) -> bool:
    """Return True if this tool result can be formatted without Ollama."""
    deterministic_tools = {
        "get_time",
        "get_date",
        "get_battery",
        "get_volume",
        "get_system_status",
    }
    return tool_name in deterministic_tools


def format_response(tool_name: str, result: str) -> Optional[str]:
    """
    Format a tool result directly to natural language.
    Returns a spoken reply, or None if tool needs Ollama processing.
    """
    if tool_name == "get_time":
        return _format_time(result)
    elif tool_name == "get_date":
        return _format_date(result)
    elif tool_name == "get_battery":
        return _format_battery(result)
    elif tool_name == "get_volume":
        return _format_volume(result)
    elif tool_name == "get_system_status":
        return _format_system_status(result)
    
    return None


def _format_time(time_str: str) -> str:
    """Format time result naturally."""
    time_str = time_str.strip()
    # Remove common prefixes like "The time is"
    if time_str.lower().startswith("the time is"):
        time_str = time_str[11:].strip()
    
    return f"It's {time_str}."


def _format_date(date_str: str) -> str:
    """Format date result naturally."""
    date_str = date_str.strip()
    if date_str.lower().startswith("today is"):
        date_str = date_str[8:].strip()
    
    return f"Today's {date_str}."


def _format_battery(battery_str: str) -> str:
    """Format battery status naturally."""
    battery_str = battery_str.strip()
    
    # Try to extract percentage if present
    if "%" in battery_str:
        try:
            pct = int(battery_str.split("%")[0].split()[-1])
            if pct > 80:
                return f"Battery's at {pct}%."
            elif pct > 50:
                return f"Battery's holding at {pct}%."
            elif pct > 20:
                return f"Battery's at {pct}%. Getting low soon."
            else:
                return f"Battery's critically low — {pct}%."
        except (ValueError, IndexError):
            pass
    
    return f"Battery status: {battery_str}."


def _format_volume(volume_str: str) -> str:
    """Format volume level naturally."""
    volume_str = volume_str.strip()
    
    # Try to extract percentage
    try:
        pct = int(''.join(filter(str.isdigit, volume_str.split()[0])))
        if pct == 0:
            return "Volume's muted."
        elif pct < 33:
            return f"Volume's at {pct}% — quite low."
        elif pct < 66:
            return f"Volume's at {pct}%."
        else:
            return f"Volume's at {pct}% — pretty loud."
    except (ValueError, IndexError):
        pass
    
    return f"Volume: {volume_str}."


def _format_system_status(status_str: str) -> str:
    """Format system status naturally."""
    status_str = status_str.strip()
    
    if not status_str or status_str.lower() == "ok":
        return "System's running normally."
    elif status_str.lower() == "warning":
        return "There's a system warning — check details."
    elif status_str.lower() == "error":
        return "System's reporting an error."
    
    return f"System status: {status_str}."
