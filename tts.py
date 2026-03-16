"""
Text-to-speech via ElevenLabs, piped directly into mpv for low-latency playback.

Why mpv instead of ElevenLabs' built-in stream():
    ElevenLabs' stream() routes audio through Python's sounddevice/soundfile
    stack. On some Windows setups this introduces 20-40 seconds of buffering
    before audio starts. mpv reads from stdin and begins playback within
    ~200ms of receiving the first audio chunk, making voice responses feel
    immediate.

Fallback:
    If mpv is not found, falls back to ElevenLabs' built-in player
    automatically — degraded latency but still functional.

mpv flags used:
    --no-cache        don't buffer — play as data arrives
    --no-terminal     suppress mpv's progress bar in the console
    --audio-display=no  don't attempt to open a video window
    -                 read audio from stdin
"""
from __future__ import annotations

import subprocess
import sys
from typing import Optional

from elevenlabs.client import ElevenLabs


class TextToSpeech:
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str,
        output_format: str,
        mpv_path: str = "mpv.exe",
    ):
        self.client        = ElevenLabs(api_key=api_key)
        self.voice_id      = voice_id
        self.model_id      = model_id
        self.output_format = output_format
        self.mpv_path      = mpv_path

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        try:
            audio_stream = self.client.text_to_speech.stream(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format=self.output_format,
                optimize_streaming_latency=4,  # max latency optimisation
            )
            self._play_with_mpv(audio_stream)

        except Exception as e:
            print(f"[TTS error] {e}", file=sys.stderr)

    def _play_with_mpv(self, audio_stream) -> None:
        """
        Spawns mpv reading from stdin and pipes audio chunks into it.
        mpv starts playing as soon as it has enough data (~200ms).
        """
        cmd = [
            self.mpv_path,
            "--no-cache", 
            "--no-terminal", 
            "--volume=100",
            "--audio-display=no",
            "-",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            for chunk in audio_stream:
                if chunk and proc.stdin:
                    proc.stdin.write(chunk)

            if proc.stdin:
                proc.stdin.close()

            proc.wait()

        except FileNotFoundError:
            print(
                f"[TTS] mpv not found at '{self.mpv_path}'. "
                "Falling back to ElevenLabs built-in playback.",
                file=sys.stderr,
            )
            self._fallback_stream(audio_stream)

        except Exception as e:
            print(f"[TTS] mpv playback error: {e}", file=sys.stderr)

    def _fallback_stream(self, audio_stream) -> None:
        """ElevenLabs built-in player — used only if mpv is unavailable."""
        from elevenlabs import stream as el_stream
        el_stream(audio_stream)
