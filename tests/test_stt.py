"""
Unit tests for Speech-to-Text (STT) module.

Tests the SpeechToText wrapper around RealtimeSTT.
Mocks the AudioToTextRecorder to avoid requiring audio hardware.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stt import SpeechToText


class TestSpeechToTextInitialization:
    """Test STT initialization."""

    def test_stt_initializes_with_defaults(self, mocker):
        """Test SpeechToText initializes with model and language."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")

        assert stt.recorder == mock_recorder
        mock_recorder_class.assert_called_once()

    def test_stt_passes_model_to_recorder(self, mocker):
        """Test model parameter is passed to AudioToTextRecorder."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="small.en", language="en")

        call_kwargs = mock_recorder_class.call_args[1]
        assert call_kwargs["model"] == "small.en"

    def test_stt_passes_language_to_recorder(self, mocker):
        """Test language parameter is passed to AudioToTextRecorder."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="base.en", language="fr")

        call_kwargs = mock_recorder_class.call_args[1]
        assert call_kwargs["language"] == "fr"

    def test_stt_disables_silero_detection(self, mocker):
        """Test Silero detection is disabled to avoid download issues."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="base.en", language="en")

        call_kwargs = mock_recorder_class.call_args[1]
        assert call_kwargs["silero_deactivity_detection"] is False

    def test_stt_disables_spinner(self, mocker):
        """Test spinner is disabled."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="base.en", language="en")

        call_kwargs = mock_recorder_class.call_args[1]
        assert call_kwargs["spinner"] is False

    def test_stt_configures_vad_settings(self, mocker):
        """Test VAD (Voice Activity Detection) settings."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="base.en", language="en")

        call_kwargs = mock_recorder_class.call_args[1]
        # VAD tuning for responsive turn-taking
        assert call_kwargs["webrtc_sensitivity"] == 3
        assert call_kwargs["post_speech_silence_duration"] == 0.4
        assert call_kwargs["min_length_of_recording"] == 0.4
        assert call_kwargs["pre_recording_buffer_duration"] == 0.6

    def test_stt_configures_sample_rate(self, mocker):
        """Test audio sample rate is set correctly."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        SpeechToText(model="base.en", language="en")

        call_kwargs = mock_recorder_class.call_args[1]
        assert call_kwargs["sample_rate"] == 16000


class TestListenText:
    """Test listen_text() method."""

    def test_listen_text_returns_string(self, mocker):
        """Test listen_text returns a string."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder.text.return_value = "hello"
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        result = stt.listen_text()

        assert isinstance(result, str)
        assert result == "hello"

    def test_listen_text_calls_recorder_text(self, mocker):
        """Test listen_text calls recorder.text()."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder.text.return_value = "hello world"
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        stt.listen_text()

        mock_recorder.text.assert_called_once()

    def test_listen_text_handles_none_result(self, mocker):
        """Test listen_text converts None to empty string."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder.text.return_value = None
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        result = stt.listen_text()

        assert result == ""

    def test_listen_text_handles_empty_string(self, mocker):
        """Test listen_text handles empty strings."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder.text.return_value = ""
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        result = stt.listen_text()

        assert result == ""

    def test_listen_text_multiple_calls(self, mocker):
        """Test multiple listen_text calls work independently."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder
        mock_recorder.text.side_effect = ["first", "second", "third"]

        stt = SpeechToText(model="base.en", language="en")
        
        assert stt.listen_text() == "first"
        assert stt.listen_text() == "second"
        assert stt.listen_text() == "third"


class TestShutdown:
    """Test shutdown() method."""

    def test_shutdown_calls_recorder_shutdown(self, mocker):
        """Test shutdown calls recorder.shutdown()."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        stt.shutdown()

        mock_recorder.shutdown.assert_called_once()

    def test_shutdown_no_error_on_multiple_calls(self, mocker):
        """Test multiple shutdown calls don't raise errors."""
        mock_recorder_class = mocker.patch("stt.AudioToTextRecorder")
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        stt = SpeechToText(model="base.en", language="en")
        
        # Should not raise
        stt.shutdown()
        stt.shutdown()
        
        assert mock_recorder.shutdown.call_count == 2
