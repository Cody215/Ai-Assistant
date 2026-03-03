# tools/system.py
"""
System awareness tools — volume, battery, and system status.

Dependencies:
    pip install psutil pycaw comtypes

All three tools work without admin rights.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

import psutil

from tools import register_tool, schema


# ── Volume ────────────────────────────────────────────────────────────────────

def _get_volume_interface():
    """
    Returns the Windows master volume interface via pycaw.
    Accesses speakers.device (the raw IMMDevice COM object) before
    calling Activate — required in current pycaw versions where
    GetSpeakers() returns an AudioDevice wrapper, not a COM object.
    """
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    speakers = AudioUtilities.GetSpeakers()
    endpoint = speakers.device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return endpoint.QueryInterface(IAudioEndpointVolume)


@register_tool(
    name="set_volume",
    description="Set the system master volume to a percentage (0–100), or mute/unmute.",
    parameters=schema(
        level="optional: volume level as a number 0–100",
        mute="optional: true | false to mute or unmute",
    ),
)
def set_volume(args: Dict[str, Any]) -> str:
    level = args.get("level")
    mute  = args.get("mute")

    try:
        vol = _get_volume_interface()

        # Handle mute toggle
        if mute is not None:
            mute_val = str(mute).lower() in ("true", "1", "yes")
            vol.SetMute(int(mute_val), None)
            return "Muted." if mute_val else "Unmuted."

        # Handle level change
        if level is not None:
            pct = max(0, min(100, int(float(str(level)))))
            # pycaw uses scalar 0.0–1.0
            vol.SetMasterVolumeLevelScalar(pct / 100.0, None)
            return f"Volume set to {pct}%."

        return "Please specify a level (0–100) or mute (true/false)."

    except Exception as e:
        return f"Volume control failed: {e}"


@register_tool(
    name="get_volume",
    description="Get the current system volume level and mute state.",
    parameters=schema(),
)
def get_volume(args: Dict[str, Any]) -> str:
    try:
        vol    = _get_volume_interface()
        level  = round(vol.GetMasterVolumeLevelScalar() * 100)
        muted  = bool(vol.GetMute())
        status = " (muted)" if muted else ""
        return f"Volume is at {level}%{status}."
    except Exception as e:
        return f"Couldn't read volume: {e}"


# ── Battery ───────────────────────────────────────────────────────────────────

@register_tool(
    name="get_battery",
    description="Get the current battery level and charging status.",
    parameters=schema(),
)
def get_battery(args: Dict[str, Any]) -> str:
    battery = psutil.sensors_battery()

    if battery is None:
        return "No battery detected — this may be a desktop PC."

    pct      = round(battery.percent)
    charging = battery.power_plugged

    if charging:
        if pct >= 100:
            return "Battery is fully charged and plugged in."
        return f"Battery is at {pct}% and charging."

    # Estimate time remaining
    secs = battery.secsleft
    if secs == psutil.POWER_TIME_UNKNOWN or secs < 0:
        return f"Battery is at {pct}%, not charging."

    hours, remainder = divmod(secs, 3600)
    mins = remainder // 60

    if hours > 0:
        time_str = f"{hours}h {mins}m remaining"
    else:
        time_str = f"{mins} minutes remaining"

    # Low battery warning
    if pct <= 10:
        return f"Warning: battery critically low at {pct}%. {time_str}."
    if pct <= 20:
        return f"Battery is low at {pct}%. {time_str}."

    return f"Battery is at {pct}%. {time_str}."


# ── System Status ─────────────────────────────────────────────────────────────

@register_tool(
    name="get_system_status",
    description="Get a summary of current system performance — CPU, RAM, and disk usage.",
    parameters=schema(
        detail="optional: full | brief (default: brief)",
    ),
)
def get_system_status(args: Dict[str, Any]) -> str:
    detail = str(args.get("detail", "brief")).lower()

    try:
        cpu_pct  = psutil.cpu_percent(interval=0.5)
        ram      = psutil.virtual_memory()
        disk     = psutil.disk_usage("/")

        ram_used  = round(ram.used  / (1024 ** 3), 1)
        ram_total = round(ram.total / (1024 ** 3), 1)
        ram_pct   = ram.percent

        disk_used  = round(disk.used  / (1024 ** 3), 1)
        disk_total = round(disk.total / (1024 ** 3), 1)
        disk_pct   = disk.percent

        if detail == "full":
            cpu_count = psutil.cpu_count(logical=True)
            cpu_freq  = psutil.cpu_freq()
            freq_str  = f" at {cpu_freq.current:.0f} MHz" if cpu_freq else ""

            lines = [
                f"CPU: {cpu_pct}% across {cpu_count} logical cores{freq_str}.",
                f"RAM: {ram_used} GB of {ram_total} GB used ({ram_pct}%).",
                f"Disk: {disk_used} GB of {disk_total} GB used ({disk_pct}%).",
            ]
            return " ".join(lines)

        # Brief summary — designed for natural speech
        parts = []

        if cpu_pct >= 80:
            parts.append(f"CPU is under heavy load at {cpu_pct}%")
        else:
            parts.append(f"CPU at {cpu_pct}%")

        parts.append(f"RAM at {ram_pct}%")
        parts.append(f"disk at {disk_pct}%")

        summary = ", ".join(parts) + "."

        # Flag anything concerning
        warnings = []
        if cpu_pct >= 90:
            warnings.append("CPU is critically high")
        if ram_pct >= 90:
            warnings.append("RAM is critically high")
        if disk_pct >= 90:
            warnings.append("disk is almost full")

        if warnings:
            summary += f" Warning: {' and '.join(warnings)}."

        return summary

    except Exception as e:
        return f"Couldn't read system status: {e}"
