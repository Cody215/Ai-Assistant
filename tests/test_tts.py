"""
Unit tests for Text-to-Speech (TTS) module.

Tests the TextToSpeech wrapper around ElevenLabs API.
Mocks subprocess and the ElevenLabs client to avoid API calls and audio playback.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts import TextToSpeech


class TestTextToSpeechInitialization:
    """Test TTS initialization."""

    def test_tts_initializes_with_config(self, mocker):
        """Test TextToSpeech initializes with all required parameters."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
            mpv_path="mpv.exe",
        )

        assert tts.voice_id == "voice1"
        assert tts.model_id == "model1"
        assert tts.output_format == "mp3_44100_128"
        assert tts.mpv_path == "mpv.exe"
        assert tts.client == mock_client

    def test_tts_passes_api_key_to_elevenlabs(self, mocker):
        """Test API key is passed to ElevenLabs client."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        TextToSpeech(
            api_key="my-secret-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )

        mock_client_class.assert_called_once_with(api_key="my-secret-key")

    def test_tts_default_mpv_path(self, mocker):
        """Test default mpv path is 'mpv.exe'."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )

        assert tts.mpv_path == "mpv.exe"


class TestSpeak:
    """Test speak() method."""

    def test_speak_calls_text_to_speech_api(self, mocker):
        """Test speak calls ElevenLabs text_to_speech.stream()."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_stream = [b"audio_chunk"]
        mock_client.text_to_speech.stream.return_value = mock_stream
        
        mocker.patch("tts.TextToSpeech._play_with_mpv")
        mocker.patch("subprocess.Popen")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak("hello world")

        mock_client.text_to_speech.stream.assert_called_once()

    def test_speak_uses_correct_voice_id(self, mocker):
        """Test speak uses the configured voice ID."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_stream = [b"audio"]
        mock_client.text_to_speech.stream.return_value = mock_stream

        mocker.patch("tts.TextToSpeech._play_with_mpv")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="my-voice",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak("hello")

        call_kwargs = mock_client.text_to_speech.stream.call_args[1]
        assert call_kwargs["voice_id"] == "my-voice"

    def test_speak_uses_correct_model_id(self, mocker):
        """Test speak uses the configured model ID."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_stream = [b"audio"]
        mock_client.text_to_speech.stream.return_value = mock_stream

        mocker.patch("tts.TextToSpeech._play_with_mpv")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="my-model",
            output_format="mp3_44100_128",
        )
        tts.speak("hello")

        call_kwargs = mock_client.text_to_speech.stream.call_args[1]
        assert call_kwargs["model_id"] == "my-model"

    def test_speak_uses_correct_output_format(self, mocker):
        """Test speak uses the configured output format."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_stream = [b"audio"]
        mock_client.text_to_speech.stream.return_value = mock_stream

        mocker.patch("tts.TextToSpeech._play_with_mpv")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="pcm_16000",
        )
        tts.speak("hello")

        call_kwargs = mock_client.text_to_speech.stream.call_args[1]
        assert call_kwargs["output_format"] == "pcm_16000"

    def test_speak_optimizes_streaming_latency(self, mocker):
        """Test speak sets max latency optimization."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_stream = [b"audio"]
        mock_client.text_to_speech.stream.return_value = mock_stream

        mocker.patch("tts.TextToSpeech._play_with_mpv")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak("hello")

        call_kwargs = mock_client.text_to_speech.stream.call_args[1]
        assert call_kwargs["optimize_streaming_latency"] == 4

    def test_speak_ignores_empty_string(self, mocker):
        """Test speak ignores empty strings."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak("")

        mock_client.text_to_speech.stream.assert_not_called()

    def test_speak_ignores_none(self, mocker):
        """Test speak handles None gracefully."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak(None)

        mock_client.text_to_speech.stream.assert_not_called()

    def test_speak_strips_whitespace(self, mocker):
        """Test speak strips leading/trailing whitespace."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_stream = [b"audio"]
        mock_client.text_to_speech.stream.return_value = mock_stream

        mocker.patch("tts.TextToSpeech._play_with_mpv")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        tts.speak("  hello  ")

        call_kwargs = mock_client.text_to_speech.stream.call_args[1]
        assert call_kwargs["text"] == "hello"

    def test_speak_catches_api_errors(self, mocker, capsys):
        """Test speak handles API errors gracefully."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_client.text_to_speech.stream.side_effect = RuntimeError("API error")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        
        # Should not raise
        tts.speak("hello")

        # Error should be printed to stderr
        captured = capsys.readouterr()
        assert "TTS error" in captured.err


class TestPlayWithMpv:
    """Test _play_with_mpv() method."""

    def test_play_with_mpv_spawns_mpv_process(self, mocker):
        """Test _play_with_mpv spawns an mpv subprocess."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
            mpv_path="mpv.exe",
        )
        
        audio_stream = [b"chunk1", b"chunk2"]
        tts._play_with_mpv(audio_stream)

        mock_popen.assert_called_once()

    def test_play_with_mpv_uses_correct_flags(self, mocker):
        """Test _play_with_mpv passes correct mpv flags."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
            mpv_path="mpv.exe",
        )
        
        tts._play_with_mpv([b"audio"])

        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "mpv.exe"
        assert "--no-cache" in cmd
        assert "--no-terminal" in cmd
        assert "--audio-display=no" in cmd
        assert "-" in cmd

    def test_play_with_mpv_writes_audio_chunks(self, mocker):
        """Test _play_with_mpv writes audio chunks to stdin."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        
        audio_stream = [b"chunk1", b"chunk2", b"chunk3"]
        tts._play_with_mpv(audio_stream)

        # Verify write was called for each chunk
        assert mock_proc.stdin.write.call_count == 3
        mock_proc.stdin.write.assert_any_call(b"chunk1")
        mock_proc.stdin.write.assert_any_call(b"chunk2")
        mock_proc.stdin.write.assert_any_call(b"chunk3")

    def test_play_with_mpv_closes_stdin(self, mocker):
        """Test _play_with_mpv closes stdin after writing."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        
        tts._play_with_mpv([b"audio"])

        mock_proc.stdin.close.assert_called_once()

    def test_play_with_mpv_waits_for_process(self, mocker):
        """Test _play_with_mpv waits for mpv to finish."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        
        tts._play_with_mpv([b"audio"])

        mock_proc.wait.assert_called_once()

    def test_play_with_mpv_fallback_on_mpv_not_found(self, mocker, capsys):
        """Test _play_with_mpv falls back to ElevenLabs if mpv not found."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_popen.side_effect = FileNotFoundError("mpv not found")
        
        mock_fallback = mocker.patch("tts.TextToSpeech._fallback_stream")

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
            mpv_path="nonexistent.exe",
        )
        
        audio_stream = [b"audio"]
        tts._play_with_mpv(audio_stream)

        mock_fallback.assert_called_once_with(audio_stream)
        
        captured = capsys.readouterr()
        assert "mpv not found" in captured.err
        assert "Falling back" in captured.err

    def test_play_with_mpv_catches_subprocess_errors(self, mocker, capsys):
        """Test _play_with_mpv handles subprocess errors gracefully."""
        mock_client_class = mocker.patch("tts.ElevenLabs")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_popen = mocker.patch("subprocess.Popen")
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdin.write.side_effect = OSError("Write failed")
        mock_popen.return_value = mock_proc

        tts = TextToSpeech(
            api_key="test-key",
            voice_id="voice1",
            model_id="model1",
            output_format="mp3_44100_128",
        )
        
        # Should not raise
        tts._play_with_mpv([b"audio"])

        captured = capsys.readouterr()
        assert "mpv playback error" in captured.err
