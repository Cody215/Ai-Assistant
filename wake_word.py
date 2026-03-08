# wake_word.py
from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import numpy as np
import sounddevice as sd

import openwakeword
from openwakeword.model import Model


@dataclass
class WakeWordDetector:
    models: Optional[List[str]] = None
    threshold: float = 0.55
    cooldown_s: float = 1.5
    device: Optional[int] = None

    sample_rate: int = 16000
    frame_samples: int = 1280  # 80ms frames

    def __post_init__(self):
        try:
            openwakeword.utils.download_models()
        except Exception:
            pass

        # None => load default included models
        self.model = Model(wakeword_models=self.models) if self.models else Model()

        self._triggered = threading.Event()
        self._stop_flag = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self._last_fire = 0.0
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return

            self._triggered.clear()
            self._stop_flag.clear()

            def callback(indata, frames, time_info, status):
                if self._stop_flag.is_set():
                    return

                audio = (indata[:, 0] * 32767).astype(np.int16)
                pred: Dict[str, Any] = self.model.predict(audio)

                now = time.time()
                if now - self._last_fire < self.cooldown_s:
                    return

                for _, score in pred.items():
                    try:
                        if float(score) >= self.threshold:
                            self._last_fire = now
                            self._triggered.set()
                            return
                    except Exception:
                        continue

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.frame_samples,
                callback=callback,
                device=self.device,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_flag.set()
            if self._stream is not None:
                try:
                    self._stream.stop()
                except Exception:
                    pass
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def wait_for_wake(self) -> None:
        if self._stream is None:
            self.start()
        self._triggered.wait()
        self._triggered.clear()
