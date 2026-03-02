# jarvis_core.py
"""
Core pipeline: STT → Gemini (native function calling) → Tool execution → TTS

Posts UI events at each stage so the HUD stays in sync:
  IDLE → LISTENING → THINKING → (tool) → SPEAKING → IDLE
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from google import genai
from google.genai import types

from config import AppConfig
from stt import SpeechToText
from tts import TextToSpeech
from ptt import PushToTalk
import tools
from tools import run_tool, get_tool_declarations

if TYPE_CHECKING:
    from ui import JarvisHUD, UIEvent


@dataclass
class Turn:
    user_text: str
    assistant_text: str


class JarvisApp:
    EXIT_PHRASES = {"exit", "exit.", "quit", "quit.", "goodbye", "goodbye."}

    def __init__(self, cfg: AppConfig, hud: Optional["JarvisHUD"] = None):
        self.cfg = cfg
        self.hud = hud

        self.gemini_client = genai.Client(api_key=cfg.gemini_api_key)
        self.chat = self.gemini_client.chats.create(
            model=cfg.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=cfg.system_instruction,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                tools=[types.Tool(function_declarations=get_tool_declarations())],
            ),
        )

        self.stt = SpeechToText(model=cfg.stt_model, language=cfg.stt_language)
        self.tts = TextToSpeech(
            api_key=cfg.elevenlabs_api_key,
            voice_id=cfg.eleven_voice_id,
            model_id=cfg.eleven_model_id,
            output_format=cfg.eleven_output_format,
            mpv_path=cfg.mpv_path,
        )

        self.ptt: Optional[PushToTalk] = None
        if cfg.ptt_enabled:
            self.ptt = PushToTalk(key_name=cfg.ptt_key)
            self.ptt.start()
            print(f"[PTT] Hold {cfg.ptt_key} to talk.")

        self._post("status", "idle")

    # ── UI bridge ─────────────────────────────────────────────────────────────

    def _post(self, kind: str, value: str):
        if self.hud is None:
            return
        from ui import UIEvent
        self.hud.post(UIEvent(kind=kind, value=value))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run_turn(self) -> bool:
        user_text = self._listen()
        if not user_text.strip():
            self._post("status", "idle")
            return True

        if user_text.lower().strip() in self.EXIT_PHRASES:
            print("Ending session. Goodbye.")
            return False

        response_text = self._think(user_text)
        if response_text:
            self._speak(response_text)

        self._post("status", "idle")
        return True

    # ── Pipeline steps ────────────────────────────────────────────────────────

    def _listen(self) -> str:
        if self.ptt is not None:
            print(f"\n[PTT] Hold {self.cfg.ptt_key} to talk...")
            self.ptt.wait_for_press()

        self._post("status", "listening")
        print("You: ", end="", flush=True)
        text = self.stt.listen_text()
        print(text)

        if text.strip():
            self._post("user", text)

        return text

    def _think(self, user_text: str) -> str:
        self._post("status", "thinking")
        print("Jarvis: ", end="", flush=True)

        try:
            response = self.chat.send_message(user_text)
        except Exception as e:
            print(f"\n[Gemini error: {e}]", file=sys.stderr)
            return "Sorry, I had trouble reaching the AI service."

        for part in response.candidates[0].content.parts:
            if part.function_call:
                fn     = part.function_call
                result = run_tool(fn.name, dict(fn.args))
                print(f"[tool:{fn.name}] {result}")
                self._post("tool", f"{fn.name} → {result}")

                tool_response = self.chat.send_message(
                    types.Part.from_function_response(
                        name=fn.name,
                        response={"result": result},
                    )
                )
                spoken = (tool_response.text or "").strip()
                print(spoken)
                self._post("response", spoken)
                return spoken

        spoken = (response.text or "").strip()
        print(spoken)
        self._post("response", spoken)
        self._post("tool", "—")
        return spoken

    def _speak(self, text: str) -> None:
        self._post("status", "speaking")
        self.tts.speak(text)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self):
        self.stt.shutdown()
        if self.ptt is not None:
            self.ptt.stop()
