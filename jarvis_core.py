# jarvis_core.py
"""
Core pipeline: STT → Gemini (native function calling) → Tool execution → TTS

Key improvements over original:
  - Uses Gemini's native function calling instead of regex JSON parsing.
    The model returns a structured FunctionCall object — far more reliable.
  - Removed manual history management. The Gemini chat object tracks its own
    session history internally; sending it again was doubling the context.
  - Responsibilities are split into focused methods, each doing one thing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

from config import AppConfig
from stt import SpeechToText
from tts import TextToSpeech
from ptt import PushToTalk
import tools  # triggers auto-discovery of all tool modules
from tools import run_tool, get_tool_declarations


@dataclass
class Turn:
    user_text: str
    assistant_text: str


class JarvisApp:
    """
    Pipeline per turn:
      1. listen()       — STT captures speech → text
      2. think()        — send to Gemini; handle tool call if requested
      3. speak()        — TTS plays the response
    """

    EXIT_PHRASES = {"exit", "exit.", "quit", "quit.", "goodbye", "goodbye."}

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg

        # ── Gemini ────────────────────────────────────────────────────────────
        self.gemini_client = genai.Client(api_key=cfg.gemini_api_key)
        self.chat = self.gemini_client.chats.create(
            model=cfg.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=cfg.system_instruction,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                tools=[types.Tool(function_declarations=get_tool_declarations())],
            ),
        )

        # ── Speech ────────────────────────────────────────────────────────────
        self.stt = SpeechToText(model=cfg.stt_model, language=cfg.stt_language)
        self.tts = TextToSpeech(
            api_key=cfg.elevenlabs_api_key,
            voice_id=cfg.eleven_voice_id,
            model_id=cfg.eleven_model_id,
            output_format=cfg.eleven_output_format,
            mpv_path=cfg.mpv_path,
        )

        # ── Push-to-talk ──────────────────────────────────────────────────────
        self.ptt: Optional[PushToTalk] = None
        if cfg.ptt_enabled:
            self.ptt = PushToTalk(key_name=cfg.ptt_key)
            self.ptt.start()
            print(f"[PTT] Hold {cfg.ptt_key} to talk.")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run_turn(self) -> bool:
        """Runs one listen → think → speak cycle. Returns False to exit."""
        user_text = self._listen()
        if not user_text.strip():
            return True

        if user_text.lower().strip() in self.EXIT_PHRASES:
            print("Ending session. Goodbye.")
            return False

        response_text = self._think(user_text)
        if response_text:
            self._speak(response_text)

        return True

    # ── Pipeline steps ────────────────────────────────────────────────────────

    def _listen(self) -> str:
        if self.ptt is not None:
            print(f"\n[PTT] Hold {self.cfg.ptt_key} to talk...")
            self.ptt.wait_for_press()

        print("You: ", end="", flush=True)
        text = self.stt.listen_text()
        print(text)
        return text

    def _think(self, user_text: str) -> str:
        """
        Send user text to Gemini. If the model requests a tool call,
        execute it and send the result back for a final spoken response.
        """
        print("Jarvis: ", end="", flush=True)

        try:
            response = self.chat.send_message(user_text)
        except Exception as e:
            print(f"\n[Gemini error: {e}]", file=sys.stderr)
            return "Sorry, I had trouble reaching the AI service."

        # ── Check for a function/tool call ────────────────────────────────────
        for part in response.candidates[0].content.parts:
            if part.function_call:
                fn   = part.function_call
                result = run_tool(fn.name, dict(fn.args))
                print(f"[tool:{fn.name}] {result}")

                # Send tool result back so Gemini can form a spoken reply
                tool_response = self.chat.send_message(
                    types.Part.from_function_response(
                        name=fn.name,
                        response={"result": result},
                    )
                )
                spoken = (tool_response.text or "").strip()
                print(spoken)
                return spoken

        # ── Plain text response ───────────────────────────────────────────────
        spoken = (response.text or "").strip()
        print(spoken)
        return spoken

    def _speak(self, text: str) -> None:
        self.tts.speak(text)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self):
        self.stt.shutdown()
        if self.ptt is not None:
            self.ptt.stop()
