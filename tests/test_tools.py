# tests/test_tools.py
"""
Tests for the tool registry and individual tool logic.

Covers:
  - Auto-discovery and registration
  - run_tool routing and error handling
  - Individual tool behaviour (no hardware, no APIs)
"""

import pytest
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools  # triggers auto-discovery
from tools import _HANDLERS, _DECLARATIONS, run_tool


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:

    def test_tools_are_registered(self):
        assert len(_HANDLERS) > 0, "No tools were registered — check auto-discovery"

    def test_declarations_match_handlers(self):
        """Every handler should have a corresponding Gemini declaration."""
        handler_names     = set(_HANDLERS.keys())
        declaration_names = {d.name for d in _DECLARATIONS}
        assert handler_names == declaration_names

    def test_expected_tools_present(self):
        expected = {
            "open_app", "create_file", "open_file", "draft_email",
            "web_search", "play_music",
            "get_time", "get_date", "get_weather",
            "get_volume", "set_volume", "get_battery", "get_system_status",
            "capture_screen",
        }
        missing = expected - set(_HANDLERS.keys())
        assert not missing, f"Missing tools: {missing}"

    def test_run_tool_unknown_name(self):
        result = run_tool("does_not_exist", {})
        assert "not found" in result.lower()

    def test_run_tool_returns_string(self):
        """run_tool should always return a string, never raise."""
        result = run_tool("open_app", {})
        assert isinstance(result, str)

    def test_run_tool_empty_args(self):
        """Tools receiving no args should return an error string, not crash."""
        for name in ("open_app", "create_file", "web_search", "play_music"):
            result = run_tool(name, {})
            assert isinstance(result, str), f"{name} did not return a string"


# ── web_search ────────────────────────────────────────────────────────────────

class TestWebSearch:

    def test_google_url(self, mocker):
        mocker.patch("webbrowser.open")
        import webbrowser
        result = run_tool("web_search", {"query": "test query", "engine": "google"})
        assert "google" in result.lower()
        webbrowser.open.assert_called_once()
        url = webbrowser.open.call_args[0][0]
        assert "google.com/search" in url
        assert "test+query" in url or "test%20query" in url

    def test_duckduckgo_url(self, mocker):
        mocker.patch("webbrowser.open")
        import webbrowser
        run_tool("web_search", {"query": "privacy search", "engine": "duckduckgo"})
        url = webbrowser.open.call_args[0][0]
        assert "duckduckgo.com" in url

    def test_bing_url(self, mocker):
        mocker.patch("webbrowser.open")
        import webbrowser
        run_tool("web_search", {"query": "bing test", "engine": "bing"})
        url = webbrowser.open.call_args[0][0]
        assert "bing.com" in url

    def test_defaults_to_google(self, mocker):
        mocker.patch("webbrowser.open")
        import webbrowser
        run_tool("web_search", {"query": "default engine"})
        url = webbrowser.open.call_args[0][0]
        assert "google.com" in url

    def test_missing_query(self):
        result = run_tool("web_search", {})
        assert "missing" in result.lower()


# ── get_time / get_date ───────────────────────────────────────────────────────

class TestDatetime:

    def test_get_time_returns_string(self):
        result = run_tool("get_time", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_time_contains_time_words(self):
        result = run_tool("get_time", {})
        assert "time" in result.lower() or ":" in result

    def test_get_time_valid_timezone(self):
        result = run_tool("get_time", {"zone": "Australia/Sydney"})
        assert "Sydney" in result or "time" in result.lower()

    def test_get_time_invalid_timezone(self):
        result = run_tool("get_time", {"zone": "Mars/Olympus"})
        assert "unknown" in result.lower() or "don't recognize" in result.lower()

    def test_get_date_returns_string(self):
        result = run_tool("get_date", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_date_contains_date_info(self):
        result = run_tool("get_date", {})
        # Should contain a year (2020s range)
        assert any(str(y) in result for y in range(2024, 2030))


# ── get_battery ───────────────────────────────────────────────────────────────

class TestBattery:

    def test_returns_string(self):
        result = run_tool("get_battery", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_handles_no_battery(self, mocker):
        """Desktop PCs have no battery — should return informative message."""
        mocker.patch("psutil.sensors_battery", return_value=None)
        result = run_tool("get_battery", {})
        assert "no battery" in result.lower() or "desktop" in result.lower()

    def test_charging_state(self, mocker):
        mock_battery = mocker.MagicMock()
        mock_battery.percent     = 85
        mock_battery.power_plugged = True
        mock_battery.secsleft    = -1
        mocker.patch("psutil.sensors_battery", return_value=mock_battery)
        result = run_tool("get_battery", {})
        assert "85" in result
        assert "charging" in result.lower() or "plugged" in result.lower()

    def test_low_battery_warning(self, mocker):
        mock_battery = mocker.MagicMock()
        mock_battery.percent     = 8
        mock_battery.power_plugged = False
        mock_battery.secsleft    = 1200
        mocker.patch("psutil.sensors_battery", return_value=mock_battery)
        result = run_tool("get_battery", {})
        assert "8" in result
        assert "low" in result.lower() or "critical" in result.lower() or "warning" in result.lower()


# ── get_system_status ─────────────────────────────────────────────────────────

class TestSystemStatus:

    def test_returns_string(self):
        result = run_tool("get_system_status", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_brief_contains_key_metrics(self):
        result = run_tool("get_system_status", {"detail": "brief"})
        assert "cpu" in result.lower()
        assert "ram" in result.lower()

    def test_full_contains_more_detail(self):
        result = run_tool("get_system_status", {"detail": "full"})
        assert "cpu" in result.lower()
        assert "ram" in result.lower()
        assert "disk" in result.lower()
        assert "gb" in result.lower()

    def test_high_cpu_warning(self, mocker):
        mocker.patch("psutil.cpu_percent", return_value=95.0)
        mock_ram  = mocker.MagicMock()
        mock_ram.used    = 4 * 1024**3
        mock_ram.total   = 16 * 1024**3
        mock_ram.percent = 25.0
        mock_disk = mocker.MagicMock()
        mock_disk.used   = 100 * 1024**3
        mock_disk.total  = 500 * 1024**3
        mock_disk.percent = 20.0
        mocker.patch("psutil.virtual_memory", return_value=mock_ram)
        mocker.patch("psutil.disk_usage",     return_value=mock_disk)
        result = run_tool("get_system_status", {})
        assert "warn" in result.lower() or "critical" in result.lower() or "high" in result.lower()


# ── create_file ───────────────────────────────────────────────────────────────

class TestCreateFile:

    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = run_tool("create_file", {"path": "test_note.txt", "content": "Hello Jarvis"})
        assert "created" in result.lower() or "test_note" in result.lower()
        assert (tmp_path / "test_note.txt").exists()
        assert (tmp_path / "test_note.txt").read_text() == "Hello Jarvis"

    def test_creates_nested_directories(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = run_tool("create_file", {"path": "notes/sub/deep.txt", "content": "nested"})
        assert (tmp_path / "notes" / "sub" / "deep.txt").exists()

    def test_rejects_absolute_path(self):
        result = run_tool("create_file", {"path": "C:/Windows/system32/evil.txt", "content": "bad"})
        assert "relative" in result.lower() or "safety" in result.lower()

    def test_missing_path_arg(self):
        result = run_tool("create_file", {"content": "no path given"})
        assert "missing" in result.lower()


# ── capture_screen ────────────────────────────────────────────────────────────

class TestCaptureScreen:

    def test_capture_stores_screenshot(self, mocker):
        """Mock ImageGrab so no actual screenshot is taken."""
        from PIL import Image
        import io

        fake_img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
        mocker.patch("PIL.ImageGrab.grab", return_value=fake_img)

        # Clear buffer first
        import tools.screen as sc
        sc._pending_screenshot = None

        result = run_tool("capture_screen", {})
        assert "captured" in result.lower()
        assert sc._pending_screenshot is not None
        assert isinstance(sc._pending_screenshot, str)  # base64 string

    def test_capture_resizes_large_image(self, mocker):
        """Images wider than 1280px should be resized."""
        from PIL import Image
        fake_img = Image.new("RGB", (3840, 2160))
        mocker.patch("PIL.ImageGrab.grab", return_value=fake_img)

        import tools.screen as sc
        sc._pending_screenshot = None
        run_tool("capture_screen", {})

        # Decode and check size
        import base64
        from PIL import Image as PILImage
        import io
        data = base64.b64decode(sc._pending_screenshot)
        img  = PILImage.open(io.BytesIO(data))
        assert img.width <= 1280

    def test_get_and_clear_buffer(self, mocker):
        from PIL import Image
        mocker.patch("PIL.ImageGrab.grab", return_value=Image.new("RGB", (800, 600)))

        import tools.screen as sc
        sc._pending_screenshot = None
        run_tool("capture_screen", {})

        assert sc.get_pending_screenshot() is not None
        sc.clear_pending_screenshot()
        assert sc.get_pending_screenshot() is None
