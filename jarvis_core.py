# jarvis_core.py
"""
Core pipeline: STT → Gemini (native function calling) → Tool execution → TTS

Memory is loaded at startup and injected into the system prompt.
Facts are extracted after each turn in a background thread.
Session summary is written on shutdown.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from google import genai
from google.genai import types

from config import AppConfig
from stt import SpeechToText
from tts import TextToSpeech
from ptt import PushToTalk
from memory.manager import MemoryManager
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
        self._last_interaction = time.time()
        self._shutdown_event   = threading.Event()

        # ── Gemini client ─────────────────────────────────────────────────────
        self.gemini_client = genai.Client(api_key=cfg.gemini_api_key)

        # ── Memory ────────────────────────────────────────────────────────────
        self.memory = MemoryManager(
            memory_dir=cfg.memory_dir,
            gemini_client=self.gemini_client,
            gemini_model=cfg.gemini_model,
        )
        memory_context = self.memory.context_block()
        fact_count     = self.memory.fact_count()
        if fact_count > 0:
            print(f"[Memory] Loaded {fact_count} facts from previous sessions.")

        # ── Gemini chat (with memory injected) ───────────────────────────────
        full_system_prompt = cfg.system_instruction + memory_context
        self.chat = self.gemini_client.chats.create(
            model=cfg.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=full_system_prompt,
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

        # ── Idle check-in timer ───────────────────────────────────────────────
        if cfg.idle_checkin_minutes > 0:
            t = threading.Thread(target=self._idle_watcher, daemon=True)
            t.start()

        self._post("status", "idle")

    # ── UI bridge ─────────────────────────────────────────────────────────────

    def _post(self, kind: str, value: str):
        if self.hud is None:
            return
        from ui import UIEvent
        self.hud.post(UIEvent(kind=kind, value=value))

    # ── Idle check-in ─────────────────────────────────────────────────────────

    def _idle_watcher(self):
        interval = self.cfg.idle_checkin_minutes * 60
        while not self._shutdown_event.is_set():
            time.sleep(15)
            if self._shutdown_event.is_set():
                break
            if time.time() - self._last_interaction >= interval:
                self._last_interaction = time.time()
                self._do_checkin()

    def _do_checkin(self):
        try:
            response = self.chat.send_message("[IDLE_CHECKIN]")
            line = (response.text or "").strip()
            if line:
                print(f"\nJarvis (check-in): {line}")
                self._post("response", line)
                self._post("status",   "speaking")
                self.tts.speak(line)
                self._post("status",   "idle")
        except Exception as e:
            print(f"[idle check-in error: {e}]", file=sys.stderr)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run_turn(self) -> bool:
        user_text = self._listen()
        if not user_text.strip():
            self._post("status", "idle")
            return True

        if user_text.lower().strip() in self.EXIT_PHRASES:
            print("Ending session. Goodbye.")
            return False

        self._last_interaction = time.time()
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
            return "Something went wrong on my end. Try again."

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

                # Save and process turn
                self.memory.save_turn("user",   user_text)
                self.memory.save_turn("jarvis", spoken)
                self.memory.process_turn(user_text, spoken)
                return spoken

        spoken = (response.text or "").strip()
        print(spoken)
        self._post("response", spoken)
        self._post("tool", "—")

        # Save and process turn
        self.memory.save_turn("user",   user_text)
        self.memory.save_turn("jarvis", spoken)
        self.memory.process_turn(user_text, spoken)
        return spoken

    def _speak(self, text: str) -> None:
        self._post("status", "speaking")
        self.tts.speak(text)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self):
        self._shutdown_event.set()
        print("[Memory] Writing session summary...")
        self.memory.close(chat=self.chat)
        self.stt.shutdown()
        if self.ptt is not None:
            self.ptt.stop()
