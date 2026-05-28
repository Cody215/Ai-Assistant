"""
Tests for llm/formatters.py — direct response formatting.

Validates that deterministic tool results (time, battery, etc.) are formatted
quickly and naturally without requiring Ollama inference.
"""

from __future__ import annotations

import pytest
from llm.formatters import (
    should_format_directly,
    format_response,
    _format_time,
    _format_date,
    _format_battery,
    _format_volume,
    _format_system_status,
)


class TestShouldFormatDirectly:
    """Test detection of tools that can be formatted directly."""

    def test_get_time_should_format_directly(self):
        """get_time should be detected as directly formattable."""
        assert should_format_directly("get_time") is True

    def test_get_date_should_format_directly(self):
        """get_date should be detected as directly formattable."""
        assert should_format_directly("get_date") is True

    def test_get_battery_should_format_directly(self):
        """get_battery should be detected as directly formattable."""
        assert should_format_directly("get_battery") is True

    def test_get_volume_should_format_directly(self):
        """get_volume should be detected as directly formattable."""
        assert should_format_directly("get_volume") is True

    def test_get_system_status_should_format_directly(self):
        """get_system_status should be detected as directly formattable."""
        assert should_format_directly("get_system_status") is True

    def test_capture_screen_should_not_format_directly(self):
        """capture_screen should not be directly formattable."""
        assert should_format_directly("capture_screen") is False

    def test_web_search_should_not_format_directly(self):
        """web_search should not be directly formattable."""
        assert should_format_directly("web_search") is False

    def test_draft_email_should_not_format_directly(self):
        """draft_email should not be directly formattable (complex)."""
        assert should_format_directly("draft_email") is False

    def test_open_app_should_not_format_directly(self):
        """open_app should not be directly formattable (may fail)."""
        assert should_format_directly("open_app") is False


class TestFormatTime:
    """Test time formatting."""

    def test_format_simple_time(self):
        """Format a simple time string."""
        result = _format_time("3:45 PM")
        assert "3:45 PM" in result
        assert result.startswith("It's")

    def test_format_time_with_prefix(self):
        """Remove 'The time is' prefix."""
        result = _format_time("The time is 3:45 PM")
        assert "The time is" not in result
        assert "3:45 PM" in result

    def test_format_time_case_insensitive_prefix(self):
        """Handle 'THE TIME IS' in uppercase."""
        result = _format_time("THE TIME IS 3:45 PM")
        assert "The time is" not in result.lower()
        assert "3:45 PM" in result

    def test_format_time_with_seconds(self):
        """Format time with seconds."""
        result = _format_time("3:45:30 PM")
        assert "3:45:30 PM" in result

    def test_format_time_24h(self):
        """Format 24-hour format time."""
        result = _format_time("15:45")
        assert "15:45" in result


class TestFormatDate:
    """Test date formatting."""

    def test_format_simple_date(self):
        """Format a simple date string."""
        result = _format_date("Tuesday, May 28, 2026")
        assert "Tuesday, May 28, 2026" in result
        assert result.startswith("Today's")

    def test_format_date_with_prefix(self):
        """Remove 'Today is' prefix."""
        result = _format_date("Today is Tuesday, May 28, 2026")
        assert "Today is" not in result
        assert "Tuesday, May 28, 2026" in result

    def test_format_short_date(self):
        """Format short date format."""
        result = _format_date("5/28/2026")
        assert "5/28/2026" in result


class TestFormatBattery:
    """Test battery formatting."""

    def test_format_high_battery(self):
        """Format battery above 80%."""
        result = _format_battery("Battery at 85%")
        assert "85%" in result
        assert "Battery" in result or "battery" in result

    def test_format_medium_battery(self):
        """Format battery between 50-80%."""
        result = _format_battery("Battery at 65%")
        assert "65%" in result
        assert "holding" in result.lower()

    def test_format_low_battery(self):
        """Format battery between 20-50%."""
        result = _format_battery("Battery at 30%")
        assert "30%" in result
        assert "low" in result.lower()

    def test_format_critical_battery(self):
        """Format battery below 20%."""
        result = _format_battery("Battery at 10%")
        assert "10%" in result
        assert "critical" in result.lower() or "low" in result.lower()

    def test_format_battery_no_percentage(self):
        """Handle battery string without percentage."""
        result = _format_battery("Battery: low")
        assert "Battery" in result

    def test_format_battery_zero_percent(self):
        """Format zero battery."""
        result = _format_battery("0%")
        assert "0%" in result


class TestFormatVolume:
    """Test volume formatting."""

    def test_format_zero_volume(self):
        """Format muted volume."""
        result = _format_volume("0%")
        assert "muted" in result.lower() or "0%" in result

    def test_format_low_volume(self):
        """Format volume below 33%."""
        result = _format_volume("25%")
        assert "25%" in result
        assert "low" in result.lower()

    def test_format_medium_volume(self):
        """Format volume between 33-66%."""
        result = _format_volume("50%")
        assert "50%" in result

    def test_format_high_volume(self):
        """Format volume above 66%."""
        result = _format_volume("80%")
        assert "80%" in result
        assert "loud" in result.lower()

    def test_format_volume_with_text(self):
        """Format volume with text prefix."""
        result = _format_volume("Volume is at 50%")
        assert "50%" in result


class TestFormatSystemStatus:
    """Test system status formatting."""

    def test_format_system_ok(self):
        """Format healthy system status."""
        result = _format_system_status("ok")
        assert "normal" in result.lower() or "running" in result.lower()

    def test_format_system_warning(self):
        """Format system warning."""
        result = _format_system_status("warning")
        assert "warning" in result.lower()

    def test_format_system_error(self):
        """Format system error."""
        result = _format_system_status("error")
        assert "error" in result.lower()

    def test_format_system_empty_string(self):
        """Format empty status (treat as ok)."""
        result = _format_system_status("")
        assert "normal" in result.lower() or "running" in result.lower()


class TestFormatResponse:
    """Test the main format_response() dispatcher."""

    def test_format_response_time(self):
        """format_response() should dispatch to _format_time."""
        result = format_response("get_time", "3:45 PM")
        assert result is not None
        assert "3:45 PM" in result

    def test_format_response_date(self):
        """format_response() should dispatch to _format_date."""
        result = format_response("get_date", "Tuesday, May 28")
        assert result is not None
        assert "Tuesday" in result

    def test_format_response_battery(self):
        """format_response() should dispatch to _format_battery."""
        result = format_response("get_battery", "Battery at 75%")
        assert result is not None
        assert "75%" in result

    def test_format_response_volume(self):
        """format_response() should dispatch to _format_volume."""
        result = format_response("get_volume", "50%")
        assert result is not None
        assert "50%" in result

    def test_format_response_system_status(self):
        """format_response() should dispatch to _format_system_status."""
        result = format_response("get_system_status", "ok")
        assert result is not None

    def test_format_response_unknown_tool_returns_none(self):
        """format_response() should return None for unknown tools."""
        result = format_response("capture_screen", "some_image_data")
        assert result is None

    def test_format_response_web_search_returns_none(self):
        """format_response() should return None for cloud tools."""
        result = format_response("web_search", "AI news results")
        assert result is None


class TestFormattingPerformance:
    """Test that formatting is fast enough."""

    def test_formatting_is_instant(self):
        """Formatting should complete in under 1ms."""
        import time
        
        start = time.perf_counter()
        for _ in range(100):
            format_response("get_time", "3:45 PM")
        elapsed = (time.perf_counter() - start) * 1000  # ms
        
        # 100 iterations should take <10ms for instant response
        assert elapsed < 10, f"Formatting too slow: {elapsed:.2f}ms for 100 iterations"

    def test_multiple_tool_types_instant(self):
        """Formatting all tool types should be fast."""
        import time
        
        tools = [
            ("get_time", "3:45 PM"),
            ("get_date", "Tuesday, May 28"),
            ("get_battery", "75%"),
            ("get_volume", "50%"),
            ("get_system_status", "ok"),
        ]
        
        start = time.perf_counter()
        for tool, result in tools * 20:  # 100 total
            format_response(tool, result)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        
        assert elapsed < 10, f"Multi-tool formatting too slow: {elapsed:.2f}ms"
