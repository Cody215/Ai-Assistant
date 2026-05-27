# jarvis_core.py
"""
Core pipeline orchestrator for Jarvis.

Pipeline per turn:
    _listen()  — STT captures speech → text (waits for PTT or wake word)
    _think()   — sends text to Gemini; handles tool calls if requested
    _speak()   — TTS plays the response via ElevenLabs → mpv

Additional responsibilities:
    - Injects persistent memory context into the system prompt at startup
    - Posts UI status events to the HUD at each pipeline stage
    - Runs an idle check-in timer on a background thread
    - Manages the wake word sleep/active cycle
    - Writes session summary and closes memory on shutdown

Wake word flow (when wake_word_enabled = True):
    [Sleeping] → "Hey Jarvis" → greeting → PTT queries → "goodbye" → [Sleeping]

Without wake word:
    PTT only — hold F9 to talk, any time.
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
from router import Router

if TYPE_CHECKING:
    from ui import JarvisHUD, UIEvent


@dataclass
class Turn:
    user_text: str
    assistant_text: str


class JarvisApp:
    # When wake word is enabled, these send Jarvis back to sleep
    SLEEP_PHRASES    = {"goodbye", "goodbye.", "go to sleep", "sleep", "that's all"}
    # These always exit the program entirely, regardless of mode
    SHUTDOWN_PHRASES = {"exit", "exit.", "quit", "quit.", "shut down", "shutdown"}

    def __init__(self, cfg: AppConfig, hud: Optional["JarvisHUD"] = None):
        self.cfg = cfg
        self.hud = hud
        self._last_interaction = time.time()
        self._shutdown_event   = threading.Event()
        self._active           = not cfg.wake_word_enabled  # start active if no wake word

        # ── Gemini ────────────────────────────────────────────────────────────
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

        # ── Gemini chat ───────────────────────────────────────────────────────
        full_system_prompt = cfg.system_instruction + memory_context
        self.chat = self.gemini_client.chats.create(
            model=cfg.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=full_system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                tools=[types.Tool(function_declarations=get_tool_declarations())],
            ),
        )

        # ── Router ───────────────────────────────────────────────────────────
        self.router = Router()

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

        # ── Wake word ─────────────────────────────────────────────────────────
        self.wwd = None
        if cfg.wake_word_enabled:
            try:
                from wake_word import WakeWordDetector
                self.wwd = WakeWordDetector(
                    threshold=cfg.wake_word_threshold,
                    cooldown_s=cfg.wake_word_cooldown,
                )
                self.wwd.start()
                print("[Wake Word] Listening for 'Hey Jarvis'...")
                self._post("status", "sleeping")
            except Exception as e:
                print(f"[Wake Word] Failed to start: {e}. Falling back to PTT only.")
                self.wwd = None
                self._active = True

        # ── Idle check-in timer ───────────────────────────────────────────────
        if cfg.idle_checkin_minutes > 0:
            t = threading.Thread(target=self._idle_watcher, daemon=True)
            t.start()

        if self._active:
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
            # Only check in when Jarvis is active, not sleeping
            if self._active and time.time() - self._last_interaction >= interval:
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

    # ── Wake word cycle ───────────────────────────────────────────────────────

    def _sleep_until_wake(self):
        """Block until the wake word fires, then greet and activate."""
        print("\n[Sleeping] Say 'Hey Jarvis' to activate...")
        self._post("status", "sleeping")
        self._active = False

        # Use a loop so KeyboardInterrupt (Ctrl+C) can interrupt the wait
        while not self._shutdown_event.is_set():
            if self.wwd._triggered.wait(timeout=0.5):
                self.wwd._triggered.clear()
                break
        if self._shutdown_event.is_set():
            return

        self._active = True
        self._last_interaction = time.time()
        print("[Wake Word] Triggered — activating Jarvis.")
        self._post("status", "idle")

        # Generate a natural wake greeting
        try:
            response = self.chat.send_message("[WAKE_GREETING]")
            greeting = (response.text or "").strip()
            if not greeting:
                greeting = "Ready."
        except Exception:
            greeting = "Ready."

        print(f"Jarvis: {greeting}")
        self._post("response", greeting)
        self._speak(greeting)
        self._post("status", "idle")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run_turn(self) -> bool:
        # If wake word is enabled and we're not active, wait for it
        if self.wwd is not None and not self._active:
            self._sleep_until_wake()
            return True

        user_text = self._listen()
        if not user_text.strip():
            self._post("status", "idle")
            return True

        phrase = user_text.lower().strip()

        # Hard shutdown — always exits regardless of wake word mode
        if phrase in self.SHUTDOWN_PHRASES:
            print("Shutting down. Goodbye.")
            return False

        # Sleep — only meaningful when wake word is enabled
        if phrase in self.SLEEP_PHRASES:
            if self.wwd is not None:
                farewell = self._generate_farewell()
                self._speak(farewell)
                self._active = False
                return True   # keep running, return to sleep
            else:
                print("Ending session. Goodbye.")
                return False

        self._last_interaction = time.time()
        response_text = self._think(user_text)
        if response_text:
            self._speak(response_text)

        self._post("status", "idle")
        return True

    def _generate_farewell(self) -> str:
        try:
            response = self.chat.send_message("[SLEEP_FAREWELL]")
            return (response.text or "Understood. Going quiet.").strip()
        except Exception:
            return "Going quiet."

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
        """
        Send user text to Gemini to decide intent and tool selection.
        Gemini always decides WHAT to do — the router decides WHERE to run it.

        Flow:
          1. Gemini receives the query and returns either a tool call or text
          2. If tool call → router checks routing flag
             - "local"  → Ollama executes the tool
             - "cloud"  → Gemini executes the tool (existing path)
          3. Result sent back to Gemini for a natural spoken reply
          4. Memory saved after every turn
        """
        self._post("status", "thinking")
        print("Jarvis: ", end="", flush=True)

        try:
            response = self.chat.send_message(user_text)
        except Exception as e:
            print(f"\n[Gemini error: {e}]", file=sys.stderr)
            return "Something went wrong on my end. Try again."

        for part in response.candidates[0].content.parts:
            if part.function_call:
                fn        = part.function_call
                tool_name = fn.name
                tool_args = dict(fn.args)

                # ── Route decision ────────────────────────────────────────────
                if self.router.is_local(tool_name):
                    print(f"[tool:{tool_name}] → Ollama (local)")
                    spoken = self._run_local_tool(
                        tool_name, tool_args, user_text
                    )
                else:
                    print(f"[tool:{tool_name}] → Gemini (cloud)")
                    spoken = self._run_cloud_tool(
                        tool_name, tool_args
                    )

                print(spoken)
                self._post("response", spoken)
                self._post("tool", f"{tool_name} → {spoken[:60]}")
                self._save_to_memory(user_text, spoken)
                return spoken

        # ── Plain text response — always Gemini ───────────────────────────────
        spoken = (response.text or "").strip()
        print(spoken)
        self._post("response", spoken)
        self._post("tool", "—")
        self._save_to_memory(user_text, spoken)
        return spoken

    def _run_local_tool(
        self, tool_name: str, tool_args: dict, user_text: str
    ) -> str:
        """
        Execute a local-routed tool via smart formatting.

        Strategy:
          - Simple tools (get_time, get_battery, etc.) → format directly (instant)
          - Complex tools (capture_screen) → use Ollama for intelligent reply
          - All tools execute locally (not sent to Gemini) → privacy preserved

        Falls back gracefully if Ollama is unavailable.
        """
        from tools.screen import get_pending_screenshot, clear_pending_screenshot
        from tools import run_tool
        from llm.ollama_client import call_with_tool
        from llm.formatters import should_format_directly, format_response

        # Run the tool handler first (this populates screenshot buffer if needed)
        result = run_tool(tool_name, tool_args)
        print(f"  result: {result}")
        self._post("tool", f"{tool_name} → {result}")

        # Screen analysis — hand off to Ollama vision
        screenshot_b64 = get_pending_screenshot()
        if screenshot_b64:
            clear_pending_screenshot()
            print("[Vision] Routing screenshot to Ollama vision...")
            return self._ask_with_image(user_text, screenshot_b64)

        # Try direct formatting for simple, deterministic tools
        if should_format_directly(tool_name):
            formatted = format_response(tool_name, result)
            if formatted:
                print(f"  [Direct format] {formatted}")
                return formatted

        # For complex tools, ask Ollama to form a spoken reply from the result
        # Falls back to Gemini if Ollama unavailable.
        tool_name_out, text, _ = call_with_tool(
            model=self.cfg.ollama_text_model,
            user_text=(
                f"The user asked: '{user_text}'. "
                f"The tool '{tool_name}' returned: '{result}'. "
                f"Give a short, natural spoken reply in Jarvis's voice — "
                f"under 20 words, dry and direct."
            ),
            system_prompt=self.cfg.system_instruction,
            declarations=[],  # no tools needed for reply generation
            host=self.cfg.ollama_host,
        )

        if text:
            return text

        # Ollama unavailable — fall back to Gemini for the reply
        print("[Router] Ollama unavailable for reply — falling back to Gemini.")
        return self._run_cloud_tool_reply(tool_name, result)

    def _run_cloud_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        Execute a cloud-routed tool via Gemini's existing function call path.
        """
        result = run_tool(tool_name, tool_args)
        print(f"  result: {result}")
        self._post("tool", f"{tool_name} → {result}")

        return self._run_cloud_tool_reply(tool_name, result)

    def _run_cloud_tool_reply(self, tool_name: str, result: str) -> str:
        """
        Send a tool result back to Gemini and get a natural spoken reply.
        Used by both the cloud tool path and as fallback for local tools.
        """
        try:
            tool_response = self.chat.send_message(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": result},
                )
            )
            return (tool_response.text or "").strip()
        except Exception as e:
            print(f"[Gemini reply error: {e}]", file=sys.stderr)
            return result  # worst case, just speak the raw result

    def _save_to_memory(self, user_text: str, spoken: str) -> None:
        """Save user and assistant turn to memory."""
        self.memory.save_turn("user",   user_text)
        self.memory.save_turn("jarvis", spoken)
        self.memory.process_turn(user_text, spoken)

    def _ask_with_image(self, user_text: str, image_b64: str) -> str:
        try:
            import ollama
            prompt = (
                f"You are Jarvis, a sharp and concise desktop voice assistant. "
                f"The user asked: \"{user_text}\"\n\n"
                f"Analyse what is visible on screen and respond naturally — "
                f"concise, direct, under 60 words. "
                f"If there is code, address it specifically. "
                f"If there is an error, explain it plainly. "
                f"Do not describe the screenshot literally unless asked."
            )
            print(f"[Vision] Sending to Ollama ({self.cfg.ollama_vision_model})...")
            response = ollama.chat(
                model=self.cfg.ollama_vision_model,
                messages=[{
                    "role":    "user",
                    "content": prompt,
                    "images":  [image_b64],
                }],
                options={"num_predict": 200},
            )
            return response["message"]["content"].strip()
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                return f"Ollama isn't running. Start it and ensure '{self.cfg.ollama_vision_model}' is pulled."
            return f"Screen analysis failed: {e}"

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
        if self.wwd is not None:
            self.wwd.stop()
