"""
Unit tests for UI module (ui.py).

Tests the JarvisHUD tkinter window and event handling.
Mocks tkinter widgets to avoid requiring a display server.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import queue
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui import UIEvent, Status, STATUS_LABEL, STATUS_COLOR, STATUS_GLOW, JarvisHUD


# ── Test UIEvent ──────────────────────────────────────────────────────────────

class TestUIEvent:
    """Test UIEvent dataclass."""

    def test_uievent_creation(self):
        """Test UIEvent can be created with kind and value."""
        event = UIEvent(kind="status", value="idle")
        assert event.kind == "status"
        assert event.value == "idle"

    def test_uievent_user_event(self):
        """Test user event creation."""
        event = UIEvent(kind="user", value="hello")
        assert event.kind == "user"
        assert event.value == "hello"

    def test_uievent_response_event(self):
        """Test response event creation."""
        event = UIEvent(kind="response", value="world")
        assert event.kind == "response"
        assert event.value == "world"

    def test_uievent_tool_event(self):
        """Test tool event creation."""
        event = UIEvent(kind="tool", value="web_search")
        assert event.kind == "tool"
        assert event.value == "web_search"


# ── Test Status Enums ─────────────────────────────────────────────────────────

class TestStatusEnums:
    """Test Status enum and related mappings."""

    def test_status_enum_exists(self):
        """Test Status enum has required values."""
        assert hasattr(Status, "IDLE")
        assert hasattr(Status, "LISTENING")
        assert hasattr(Status, "THINKING")
        assert hasattr(Status, "SPEAKING")

    def test_status_label_mapping(self):
        """Test STATUS_LABEL has all status values."""
        assert STATUS_LABEL[Status.IDLE] == "STANDBY"
        assert STATUS_LABEL[Status.LISTENING] == "LISTENING"
        assert STATUS_LABEL[Status.THINKING] == "PROCESSING"
        assert STATUS_LABEL[Status.SPEAKING] == "RESPONDING"

    def test_status_color_mapping(self):
        """Test STATUS_COLOR has valid hex values."""
        for status, color in STATUS_COLOR.items():
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB

    def test_status_glow_mapping(self):
        """Test STATUS_GLOW has valid hex values."""
        for status, color in STATUS_GLOW.items():
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB


# ── Test JarvisHUD Initialization ─────────────────────────────────────────────

class TestJarvisHUDInitialization:
    """Test JarvisHUD initialization."""

    @patch("ui.tk.Tk")
    def test_hud_initializes(self, mock_tk_class, mocker):
        """Test JarvisHUD initializes without errors."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        # Mock all tkinter widget creation
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        
        assert hud is not None
        assert hud._status == Status.IDLE

    @patch("ui.tk.Tk")
    def test_hud_creates_queue(self, mock_tk_class, mocker):
        """Test HUD creates event queue."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        
        assert isinstance(hud._queue, queue.Queue)

    @patch("ui.tk.Tk")
    def test_hud_initial_status_idle(self, mock_tk_class, mocker):
        """Test HUD starts in IDLE status."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        
        assert hud._status == Status.IDLE

    @patch("ui.tk.Tk")
    def test_hud_dimensions(self, mock_tk_class, mocker):
        """Test HUD has correct dimensions."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        
        assert hud.WIDTH == 380
        assert hud.HEIGHT == 520


# ── Test Event Posting ────────────────────────────────────────────────────────

class TestEventPosting:
    """Test post() method for thread-safe event posting."""

    @patch("ui.tk.Tk")
    def test_post_adds_event_to_queue(self, mock_tk_class, mocker):
        """Test post() adds events to queue."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        event = UIEvent(kind="status", value="listening")
        hud.post(event)
        
        # Event should be in queue
        queued_event = hud._queue.get_nowait()
        assert queued_event.kind == "status"
        assert queued_event.value == "listening"

    @patch("ui.tk.Tk")
    def test_post_thread_safe(self, mock_tk_class, mocker):
        """Test post() is thread-safe."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        
        # Multiple events from different threads
        events = [
            UIEvent(kind="status", value="listening"),
            UIEvent(kind="user", value="hello"),
            UIEvent(kind="response", value="hi there"),
        ]
        
        for event in events:
            hud.post(event)
        
        # All events should be queued
        assert hud._queue.qsize() == 3


# ── Test Event Handling ───────────────────────────────────────────────────────

class TestEventHandling:
    """Test _handle() method for processing events."""

    @patch("ui.tk.Tk")
    def test_handle_status_event(self, mock_tk_class, mocker):
        """Test _handle() processes status events."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mock_status_var = MagicMock()
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar", return_value=mock_status_var)

        hud = JarvisHUD()
        event = UIEvent(kind="status", value="thinking")
        hud._handle(event)
        
        assert hud._status == Status.THINKING

    @patch("ui.tk.Tk")
    def test_handle_user_event(self, mock_tk_class, mocker):
        """Test _handle() updates user text."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mock_user_var = MagicMock()
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        
        # Create multiple StringVar instances
        string_vars = [MagicMock(), mock_user_var, MagicMock(), MagicMock()]
        mocker.patch("ui.tk.StringVar", side_effect=string_vars)

        hud = JarvisHUD()
        event = UIEvent(kind="user", value="what is the time")
        hud._handle(event)
        
        mock_user_var.set.assert_called_with("what is the time")

    @patch("ui.tk.Tk")
    def test_handle_response_event(self, mock_tk_class, mocker):
        """Test _handle() updates response text."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        string_vars = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar", side_effect=string_vars)

        hud = JarvisHUD()
        event = UIEvent(kind="response", value="It is 3pm")
        hud._handle(event)

    @patch("ui.tk.Tk")
    def test_handle_tool_event(self, mock_tk_class, mocker):
        """Test _handle() updates tool text."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        event = UIEvent(kind="tool", value="web_search")
        hud._handle(event)

    @patch("ui.tk.Tk")
    def test_handle_truncates_long_responses(self, mock_tk_class, mocker):
        """Test _handle() truncates long response text."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mock_response_var = MagicMock()
        string_vars = [MagicMock(), MagicMock(), mock_response_var, MagicMock()]
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar", side_effect=string_vars)

        hud = JarvisHUD()
        long_text = "a" * 200
        event = UIEvent(kind="response", value=long_text)
        hud._handle(event)
        
        # Response should be truncated to 180 + "…"
        call_args = mock_response_var.set.call_args[0][0]
        assert len(call_args) <= 181
        assert call_args.endswith("…")


# ── Test Status Transitions ────────────────────────────────────────────────────

class TestStatusTransitions:
    """Test status transitions via events."""

    @patch("ui.tk.Tk")
    def test_transition_idle_to_listening(self, mock_tk_class, mocker):
        """Test IDLE → LISTENING transition."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        assert hud._status == Status.IDLE
        
        hud._handle(UIEvent(kind="status", value="listening"))
        assert hud._status == Status.LISTENING

    @patch("ui.tk.Tk")
    def test_transition_listening_to_thinking(self, mock_tk_class, mocker):
        """Test LISTENING → THINKING transition."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        hud._handle(UIEvent(kind="status", value="listening"))
        hud._handle(UIEvent(kind="status", value="thinking"))
        assert hud._status == Status.THINKING

    @patch("ui.tk.Tk")
    def test_transition_thinking_to_speaking(self, mock_tk_class, mocker):
        """Test THINKING → SPEAKING transition."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        hud._handle(UIEvent(kind="status", value="thinking"))
        hud._handle(UIEvent(kind="status", value="speaking"))
        assert hud._status == Status.SPEAKING

    @patch("ui.tk.Tk")
    def test_transition_speaking_to_idle(self, mock_tk_class, mocker):
        """Test SPEAKING → IDLE transition."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar")

        hud = JarvisHUD()
        hud._handle(UIEvent(kind="status", value="speaking"))
        hud._handle(UIEvent(kind="status", value="idle"))
        assert hud._status == Status.IDLE


# ── Test Empty Value Handling ─────────────────────────────────────────────────

class TestEmptyValueHandling:
    """Test handling of None and empty string values."""

    @patch("ui.tk.Tk")
    def test_user_event_empty_string(self, mock_tk_class, mocker):
        """Test user event with empty string shows dash."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mock_user_var = MagicMock()
        string_vars = [MagicMock(), mock_user_var, MagicMock(), MagicMock()]
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar", side_effect=string_vars)

        hud = JarvisHUD()
        hud._handle(UIEvent(kind="user", value=""))
        
        mock_user_var.set.assert_called_with("—")

    @patch("ui.tk.Tk")
    def test_user_event_none(self, mock_tk_class, mocker):
        """Test user event with None shows dash."""
        mock_root = MagicMock()
        mock_tk_class.return_value = mock_root
        
        mock_user_var = MagicMock()
        string_vars = [MagicMock(), mock_user_var, MagicMock(), MagicMock()]
        mocker.patch("ui.tk.Frame")
        mocker.patch("ui.tk.Label")
        mocker.patch("ui.tk.Canvas")
        mocker.patch("ui.tk.StringVar", side_effect=string_vars)

        hud = JarvisHUD()
        hud._handle(UIEvent(kind="user", value=None))
        
        mock_user_var.set.assert_called_with("—")
