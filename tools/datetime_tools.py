# tools/datetime_tools.py
"""
Tools for time, date, and weather lookups.
"""

import urllib.parse
from datetime import datetime
from typing import Any, Dict

import requests

from tools import register_tool, schema

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore


# ── Time ──────────────────────────────────────────────────────────────────────

@register_tool(
    name="get_time",
    description="Get the current time, optionally for a specific timezone.",
    parameters=schema(
        zone="optional: IANA timezone e.g. Australia/Sydney, America/New_York (default: local)",
    ),
)
def get_time(args: Dict[str, Any]) -> str:
    zone = (args.get("zone") or "").strip()

    if not zone:
        return datetime.now().strftime("The time is %I:%M %p")

    if ZoneInfo is None:
        return "Timezone support unavailable on this system."

    try:
        now = datetime.now(ZoneInfo(zone))
        return now.strftime(f"The time in {zone} is %I:%M %p")
    except Exception:
        return f"Unknown timezone '{zone}'. Try Australia/Sydney or America/New_York."


# ── Date ──────────────────────────────────────────────────────────────────────

@register_tool(
    name="get_date",
    description="Get the current date, optionally for a specific timezone.",
    parameters=schema(
        zone="optional: IANA timezone e.g. Australia/Sydney (default: local)",
    ),
)
def get_date(args: Dict[str, Any]) -> str:
    zone = (args.get("zone") or "").strip()

    if not zone:
        return datetime.now().strftime("Today is %A, %B %d %Y")

    if ZoneInfo is None:
        return "Timezone support unavailable on this system."

    try:
        now = datetime.now(ZoneInfo(zone))
        return now.strftime(f"In {zone}, today is %A, %B %d %Y")
    except Exception:
        return f"Unknown timezone '{zone}'."


# ── Weather ───────────────────────────────────────────────────────────────────

@register_tool(
    name="get_weather",
    description="Get current weather and conditions for a location.",
    parameters=schema(
        location="City or location name, e.g. Sydney, AU",
        unit="optional: celsius | fahrenheit (default: celsius)",
    ),
)
def get_weather(args: Dict[str, Any]) -> str:
    location = str(args.get("location", "")).strip()
    unit     = str(args.get("unit", "celsius")).lower()

    if not location:
        return "Missing argument: location"

    try:
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(location)}&count=1&language=en"
        )
        geo = requests.get(geo_url, timeout=5).json()

        if not geo.get("results"):
            return f"Couldn't find location: {location}"

        result  = geo["results"][0]
        lat     = result["latitude"]
        lon     = result["longitude"]
        name    = result["name"]
        country = result.get("country_code", "")

        temp_unit = "fahrenheit" if "f" in unit else "celsius"
        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,weathercode,wind_speed_10m"
            f"&timezone=auto&temperature_unit={temp_unit}"
        )
        wx = requests.get(wx_url, timeout=8).json()
        current = wx["current"]

        temp  = current["temperature_2m"]
        wind  = current["wind_speed_10m"]
        code  = current["weathercode"]
        sym   = "°F" if "f" in unit else "°C"

        desc = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 51: "light drizzle", 61: "light rain", 71: "light snow",
            80: "rain showers", 95: "thunderstorm",
        }.get(code, "mixed conditions")

        return f"{name}, {country}: {temp}{sym}, {desc}, wind {wind} km/h."

    except Exception as e:
        return f"Weather lookup failed: {e}"
