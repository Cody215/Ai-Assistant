# ptt.py
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from pynput import keyboard

KEY_MAP = {
    "ALT_R":   keyboard.Key.alt_r,
    "ALT_L":   keyboard.Key.alt_l,
    "CTRL_R":  keyboard.Key.ctrl_r,
    "CTRL_L":  keyboard.Key.ctrl_l,
    "SHIFT_R": keyboard.Key.shift_r,
    "SHIFT_L": keyboard.Key.shift_l,
    "SPACE":   keyboard.Key.space,
    "ENTER":   keyboard.Key.enter,
    "TAB":     keyboard.Key.tab,
    "F8":      keyboard.Key.f8,
    "F9":      keyboard.Key.f9,
    "F10":     keyboard.Key.f10,
}


@dataclass
class PushToTalk:
    key_name: str = "F9"

    def __post_init__(self):
        if self.key_name not in KEY_MAP:
            raise ValueError(
                f"Unknown ptt_key '{self.key_name}'. "
                f"Valid options: {', '.join(KEY_MAP.keys())}"
            )
        self._key = KEY_MAP[self.key_name]
        self._pressed_event = threading.Event()
        self._is_down = False
        self._listener: Optional[keyboard.Listener] = None

    def start(self):
        if self._listener is not None:
            return

        def on_press(key):
            if key == self._key:
                self._is_down = True
                self._pressed_event.set()

        def on_release(key):
            if key == self._key:
                self._is_down = False

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def wait_for_press(self):
        self._pressed_event.clear()
        self._pressed_event.wait()

    def is_pressed(self) -> bool:
        return self._is_down
