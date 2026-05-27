# tests/test_jarvis_core.py
"""
Integration tests for the main Jarvis pipeline (jarvis_core.py).

Tests the full listen → think → speak flow with mocked external APIs.
No real Gemini, ElevenLabs, or STT/TTS hardware is used.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, ANY

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AppConfig
from jarvis_core import JarvisApp


@pytest.fixture
def mock_config():
    """Create a test config with mocked API keys."""
    return AppConfig(
        gemini_api_key="test-gemini-key",
        elevenlabs_api_key="test-eleven-key",
        ptt_enabled=False,
        wake_word_enabled=False,
        idle_checkin_minutes=0,  # Disable idle check-in for tests
    )


@pytest.fixture
def mock_speech_modules(mocker):
    """Mock STT, TTS, and other speech-related modules."""
    mock_stt_class = mocker.patch("jarvis_core.SpeechToText")
    mock_stt = MagicMock()
    mock_stt.listen_text.return_value = "user input"
    mock_stt_class.return_value = mock_stt

    mock_tts_class = mocker.patch("jarvis_core.TextToSpeech")
    mock_tts = MagicMock()
    mock_tts_class.return_value = mock_tts

    mock_ptt_class = mocker.patch("jarvis_core.PushToTalk")
    mock_ptt = MagicMock()
    mock_ptt_class.return_value = mock_ptt

    return {
        "stt": mock_stt,
        "tts": mock_tts,
        "ptt": mock_ptt,
    }


@pytest.fixture
def mock_memory(mocker):
    """Mock the MemoryManager."""
    mock_memory_class = mocker.patch("jarvis_core.MemoryManager")
    mock_mgr = MagicMock()
    mock_mgr.context_block.return_value = ""
    mock_mgr.fact_count.return_value = 0
    mock_memory_class.return_value = mock_mgr
    return mock_mgr


# ── Initialization ────────────────────────────────────────────────────────────

class TestJarvisAppInitialization:
    """Test JarvisApp can initialize without errors."""

    def test_app_initializes_with_defaults(self, mock_config, mocker, mock_memory):
        """Test basic initialization."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert app is not None
        assert app.cfg == mock_config
        assert app.memory is not None

    def test_app_creates_gemini_chat(self, mock_config, mocker, mock_memory):
        """Test Gemini chat is created correctly."""
        mock_genai = mocker.patch("jarvis_core.genai.Client")
        mock_client = MagicMock()
        mock_genai.return_value = mock_client
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert app.gemini_client == mock_client
        mock_client.chats.create.assert_called_once()

    def test_app_initializes_stt(self, mock_config, mocker, mock_memory):
        """Test STT is initialized."""
        mocker.patch("jarvis_core.genai.Client")
        mock_stt_class = mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        mock_stt_class.assert_called_once_with(
            model=mock_config.stt_model,
            language=mock_config.stt_language,
        )

    def test_app_initializes_tts(self, mock_config, mocker, mock_memory):
        """Test TTS is initialized with correct parameters."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mock_tts_class = mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        mock_tts_class.assert_called_once()
        call_kwargs = mock_tts_class.call_args[1]
        assert call_kwargs["api_key"] == mock_config.elevenlabs_api_key
        assert call_kwargs["voice_id"] == mock_config.eleven_voice_id

    def test_app_initializes_ptt_when_enabled(self, mock_config, mocker, mock_memory):
        """Test PTT is initialized when enabled."""
        mock_config.ptt_enabled = True
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mock_ptt_class = mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert app.ptt is not None
        mock_ptt_class.assert_called_once()

    def test_app_skips_ptt_when_disabled(self, mock_config, mocker, mock_memory):
        """Test PTT is not initialized when disabled."""
        mock_config.ptt_enabled = False
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mock_ptt_class = mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert app.ptt is None
        mock_ptt_class.assert_not_called()

    def test_app_starts_active_without_wake_word(self, mock_config, mocker, mock_memory):
        """Test app is active immediately if wake word is disabled."""
        mock_config.wake_word_enabled = False
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert app._active is True

    def test_app_starts_sleeping_with_wake_word(self, mock_config, mocker, mock_memory):
        """Test app starts in sleep mode if wake word is enabled."""
        mock_config.wake_word_enabled = True
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])
        # WakeWordDetector is imported dynamically from wake_word module
        mocker.patch("wake_word.WakeWordDetector")

        app = JarvisApp(mock_config)
        assert app._active is False


# ── Pipeline Shutdown ─────────────────────────────────────────────────────────

class TestJarvisAppShutdown:
    """Test shutdown behavior."""

    def test_shutdown_closes_stt(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test STT is properly shut down."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        app.shutdown()

        mock_speech_modules["stt"].shutdown.assert_called_once()

    def test_shutdown_closes_memory(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test memory is closed on shutdown."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        app.shutdown()

        mock_memory.close.assert_called_once()

    def test_shutdown_sets_event(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test shutdown event is set."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert not app._shutdown_event.is_set()
        app.shutdown()
        assert app._shutdown_event.is_set()


# ── Tool Declarations ─────────────────────────────────────────────────────────

class TestToolIntegration:
    """Test that tools are properly registered with Gemini."""

    def test_app_passes_tools_to_gemini(self, mock_config, mocker, mock_memory):
        """Test tools are passed to Gemini chat."""
        mock_genai = mocker.patch("jarvis_core.genai.Client")
        mock_client = MagicMock()
        mock_genai.return_value = mock_client
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")

        # Return empty list to avoid Pydantic validation errors with MagicMock
        mock_get_tools = mocker.patch(
            "jarvis_core.get_tool_declarations",
            return_value=[]
        )

        app = JarvisApp(mock_config)

        # Verify tools were retrieved
        mock_get_tools.assert_called()

        # Verify chats.create was called
        mock_client.chats.create.assert_called_once()


# ── Memory Context Injection ──────────────────────────────────────────────────

class TestMemoryContextInjection:
    """Test that memory context is injected into system prompt."""

    def test_memory_context_block_retrieved(self, mock_config, mocker, mock_memory):
        """Test memory context block is fetched at startup."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        mock_memory.context_block.return_value = "Previous facts: User likes Python."

        app = JarvisApp(mock_config)
        mock_memory.context_block.assert_called()

    def test_memory_context_injected_into_prompt(self, mock_config, mocker, mock_memory):
        """Test memory context is included in system prompt."""
        mock_genai = mocker.patch("jarvis_core.genai.Client")
        mock_client = MagicMock()
        mock_genai.return_value = mock_client
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        memory_context = "\n\n## MEMORY\nUser name: Alex"
        mock_memory.context_block.return_value = memory_context

        app = JarvisApp(mock_config)

        # Get the system_instruction passed to Gemini
        call_args = mock_client.chats.create.call_args
        system_prompt = call_args[1]["config"].system_instruction

        # Verify memory context was appended
        assert memory_context in system_prompt
        assert "Jarvis" in system_prompt  # Original prompt still there


# ── State Management ──────────────────────────────────────────────────────────

class TestStateManagement:
    """Test app state transitions."""

    def test_initial_shutdown_event_not_set(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test shutdown event starts unset."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        assert not app._shutdown_event.is_set()

    def test_last_interaction_timestamp_set(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test last interaction timestamp is initialized."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])
        import time

        before = time.time()
        app = JarvisApp(mock_config)
        after = time.time()

        assert before <= app._last_interaction <= after


# ── UI Integration ───────────────────────────────────────────────────────────

class TestUIIntegration:
    """Test UI event posting."""

    def test_post_status_with_no_hud(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test _post() gracefully handles no HUD."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config, hud=None)
        # Should not raise
        app._post("status", "idle")

    def test_post_status_with_hud(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test _post() sends events to HUD."""
        mocker.patch("jarvis_core.genai.Client")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        mock_hud = MagicMock()
        app = JarvisApp(mock_config, hud=mock_hud)
        app._post("status", "thinking")

        # post is called during init with 'idle', then again with 'thinking'
        assert mock_hud.post.call_count >= 1
        # Verify last call was with the expected event
        from ui import UIEvent
        last_call = mock_hud.post.call_args
        assert last_call[0][0].kind == "status"
        assert last_call[0][0].value == "thinking"


# ── Configuration Injection ───────────────────────────────────────────────────

class TestConfigurationInjection:
    """Test that config values are properly used."""

    def test_gemini_model_from_config(self, mock_config, mocker, mock_memory):
        """Test custom Gemini model is used."""
        mock_config.gemini_model = "gemini-custom-model"
        mock_genai = mocker.patch("jarvis_core.genai.Client")
        mock_client = MagicMock()
        mock_genai.return_value = mock_client
        mocker.patch("jarvis_core.SpeechToText")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)

        # Verify correct model was used
        call_args = mock_client.chats.create.call_args
        assert call_args[1]["model"] == "gemini-custom-model"

    def test_ptt_key_from_config(self, mock_config, mocker, mock_speech_modules, mock_memory):
        """Test custom PTT key is used."""
        mock_config.ptt_enabled = True
        mock_config.ptt_key = "F10"
        mocker.patch("jarvis_core.genai.Client")
        mock_ptt_class = mocker.patch("jarvis_core.PushToTalk")
        mocker.patch("jarvis_core.TextToSpeech")
        mocker.patch("jarvis_core.get_tool_declarations", return_value=[])

        app = JarvisApp(mock_config)
        mock_ptt_class.assert_called_once_with(key_name="F10")
