"""
Unit tests for WakeWordDetector module (wake_word.py).

Tests the wake word detection layer that listens for "Hey Jarvis".
Mocks sounddevice and openwakeword to avoid requiring audio hardware.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import threading
import time
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wake_word import WakeWordDetector


# ── Test Initialization ────────────────────────────────────────────────────────

class TestWakeWordDetectorInitialization:
    """Test WakeWordDetector initialization."""

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_initializes_with_defaults(self, mock_model_class, mock_download):
        """Test WakeWordDetector initializes with default models."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()

        assert wwd is not None
        assert wwd.threshold == 0.55
        assert wwd.cooldown_s == 1.5
        assert wwd.sample_rate == 16000

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_uses_custom_threshold(self, mock_model_class, mock_download):
        """Test WakeWordDetector uses custom threshold."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector(threshold=0.70)

        assert wwd.threshold == 0.70

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_uses_custom_cooldown(self, mock_model_class, mock_download):
        """Test WakeWordDetector uses custom cooldown."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector(cooldown_s=2.0)

        assert wwd.cooldown_s == 2.0

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_creates_threading_event(self, mock_model_class, mock_download):
        """Test WakeWordDetector creates threading event."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()

        assert isinstance(wwd._triggered, threading.Event)
        assert isinstance(wwd._stop_flag, threading.Event)

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_creates_lock(self, mock_model_class, mock_download):
        """Test WakeWordDetector creates threading lock."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()

        # Check lock has acquire/release methods
        assert hasattr(wwd._lock, "acquire")
        assert hasattr(wwd._lock, "release")

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_initializes_stream_as_none(self, mock_model_class, mock_download):
        """Test stream is initially None."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()

        assert wwd._stream is None

    @patch("wake_word.openwakeword.utils.download_models", side_effect=Exception("Download failed"))
    @patch("wake_word.Model")
    def test_wwd_handles_download_error(self, mock_model_class, mock_download):
        """Test WakeWordDetector gracefully handles download errors."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Should not raise despite download error
        wwd = WakeWordDetector()
        assert wwd is not None

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_loads_custom_models(self, mock_model_class, mock_download):
        """Test WakeWordDetector can load custom models."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        custom_models = ["alexa", "ok_google"]
        wwd = WakeWordDetector(models=custom_models)

        mock_model_class.assert_called_once_with(wakeword_models=custom_models)

    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wwd_audio_config(self, mock_model_class, mock_download):
        """Test WakeWordDetector has correct audio configuration."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()

        assert wwd.sample_rate == 16000
        assert wwd.frame_samples == 1280


# ── Test Start ─────────────────────────────────────────────────────────────────

class TestStart:
    """Test start() method for stream initialization."""

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_creates_stream(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() creates audio stream."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()

        mock_stream_class.assert_called_once()
        mock_stream.start.assert_called_once()

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_uses_correct_sample_rate(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() uses configured sample rate."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector(sample_rate=16000)
        wwd.start()

        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs["samplerate"] == 16000

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_uses_mono_audio(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() uses mono audio (1 channel)."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()

        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs["channels"] == 1

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_uses_float32_dtype(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() uses float32 data type."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()

        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs["dtype"] == "float32"

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_uses_correct_blocksize(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() uses configured frame size."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector(frame_samples=1280)
        wwd.start()

        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs["blocksize"] == 1280

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_start_idempotent(self, mock_model_class, mock_download, mock_stream_class):
        """Test start() can be called multiple times without error."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        wwd.start()

        # Stream.start() should only be called once
        assert mock_stream.start.call_count == 1


# ── Test Stop ──────────────────────────────────────────────────────────────────

class TestStop:
    """Test stop() method for stream cleanup."""

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_stop_closes_stream(self, mock_model_class, mock_download, mock_stream_class):
        """Test stop() closes the audio stream."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        wwd.stop()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_stop_sets_stop_flag(self, mock_model_class, mock_download, mock_stream_class):
        """Test stop() sets the stop flag."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        assert not wwd._stop_flag.is_set()
        
        wwd.stop()
        
        assert wwd._stop_flag.is_set()

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_stop_handles_stream_errors(self, mock_model_class, mock_download, mock_stream_class):
        """Test stop() handles stream errors gracefully."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream.stop.side_effect = Exception("Stop failed")
        mock_stream.close.side_effect = Exception("Close failed")
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        
        # Should not raise despite stream errors
        wwd.stop()
        
        assert wwd._stream is None

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_stop_without_start(self, mock_model_class, mock_download, mock_stream_class):
        """Test stop() can be called without start()."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        wwd = WakeWordDetector()
        
        # Should not raise
        wwd.stop()
        
        assert wwd._stream is None


# ── Test Wait for Wake ─────────────────────────────────────────────────────────

class TestWaitForWake:
    """Test wait_for_wake() method."""

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wait_for_wake_starts_stream_if_not_running(self, mock_model_class, mock_download, mock_stream_class):
        """Test wait_for_wake() starts stream if not already running."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        assert wwd._stream is None
        
        # Start wait in background thread and trigger after short delay
        def trigger_after_delay():
            time.sleep(0.1)
            wwd._triggered.set()

        thread = threading.Thread(target=trigger_after_delay)
        thread.start()
        
        wwd.wait_for_wake()
        thread.join()
        
        # Stream should have been started
        assert mock_stream_class.called

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wait_for_wake_clears_triggered_event(self, mock_model_class, mock_download, mock_stream_class):
        """Test wait_for_wake() clears triggered event after returning."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        
        # Manually set triggered
        wwd._triggered.set()
        assert wwd._triggered.is_set()
        
        wwd.wait_for_wake()
        
        # Should be cleared
        assert not wwd._triggered.is_set()

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_wait_for_wake_blocks_until_triggered(self, mock_model_class, mock_download, mock_stream_class):
        """Test wait_for_wake() blocks until triggered."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        wwd = WakeWordDetector()
        wwd.start()
        
        # Trigger in background after delay
        def trigger_after_delay():
            time.sleep(0.1)
            wwd._triggered.set()

        start_time = time.time()
        thread = threading.Thread(target=trigger_after_delay)
        thread.start()
        
        wwd.wait_for_wake()
        elapsed = time.time() - start_time
        
        thread.join()
        
        # Should have waited ~0.1s
        assert elapsed >= 0.08


# ── Test Audio Callback ────────────────────────────────────────────────────────

class TestAudioCallback:
    """Test the audio processing callback."""

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_callback_triggers_on_threshold(self, mock_model_class, mock_download, mock_stream_class):
        """Test callback triggers when prediction exceeds threshold."""
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.8}  # Above 0.55 threshold
        mock_model_class.return_value = mock_model
        
        mock_stream = MagicMock()
        
        def capture_callback(samplerate, channels, dtype, blocksize, callback, device):
            # Simulate callback receiving audio
            indata = np.zeros((blocksize, 1), dtype=np.float32)
            time_info = MagicMock()
            status = 0
            callback(indata, blocksize, time_info, status)
            return MagicMock()
        
        mock_stream_class.side_effect = capture_callback
        
        wwd = WakeWordDetector(threshold=0.55)
        wwd.start()
        
        # Give callback time to process
        time.sleep(0.1)
        
        # Should be triggered
        assert wwd._triggered.is_set()

    @patch("wake_word.sd.InputStream")
    @patch("wake_word.openwakeword.utils.download_models")
    @patch("wake_word.Model")
    def test_callback_respects_cooldown(self, mock_model_class, mock_download, mock_stream_class):
        """Test callback respects cooldown period."""
        mock_model = MagicMock()
        call_count = [0]
        
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] <= 2:
                return {"hey_jarvis": 0.9}
            return {"hey_jarvis": 0.0}
        
        mock_model.predict.side_effect = side_effect
        mock_model_class.return_value = mock_model
        
        captured_callback = []
        
        def capture_callback(samplerate, channels, dtype, blocksize, callback, device):
            captured_callback.append(callback)
            return MagicMock()
        
        mock_stream_class.side_effect = capture_callback
        
        wwd = WakeWordDetector(threshold=0.55, cooldown_s=1.0)
        wwd.start()
        
        # Simulate two rapid predictions
        indata = np.zeros((wwd.frame_samples, 1), dtype=np.float32)
        time_info = MagicMock()
        status = 0
        
        callback = captured_callback[0]
        callback(indata, wwd.frame_samples, time_info, status)
        
        # First trigger should work
        triggered_count = 1 if wwd._triggered.is_set() else 0
        wwd._triggered.clear()
        
        # Second trigger within cooldown should not fire
        callback(indata, wwd.frame_samples, time_info, status)
        
        # Should not trigger within cooldown period
        assert not wwd._triggered.is_set()
