# ui.py
"""
Jarvis floating HUD overlay.

A sleek, always-on-top panel that displays:
  - System status (IDLE / LISTENING / THINKING / SPEAKING)
  - What you said
  - Jarvis's response
  - Which tool was used

Run via main_ui.py instead of main.py to enable the UI.
The JarvisApp pipeline runs on a background thread; the UI
lives on the main thread (required by tkinter on Windows).
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


# ── State ─────────────────────────────────────────────────────────────────────

class Status(Enum):
    IDLE      = auto()
    LISTENING = auto()
    THINKING  = auto()
    SPEAKING  = auto()


STATUS_LABEL = {
    Status.IDLE:      "STANDBY",
    Status.LISTENING: "LISTENING",
    Status.THINKING:  "PROCESSING",
    Status.SPEAKING:  "RESPONDING",
}

STATUS_COLOR = {
    Status.IDLE:      "#1a3a4a",
    Status.LISTENING: "#00d4ff",
    Status.THINKING:  "#ffaa00",
    Status.SPEAKING:  "#00ff9d",
}

STATUS_GLOW = {
    Status.IDLE:      "#0d1f2a",
    Status.LISTENING: "#003a52",
    Status.THINKING:  "#3a2a00",
    Status.SPEAKING:  "#003a28",
}


@dataclass
class UIEvent:
    kind: str          # "status" | "user" | "response" | "tool"
    value: str


# ── HUD Window ────────────────────────────────────────────────────────────────

class JarvisHUD:
    # Palette
    BG          = "#060d12"
    BG_PANEL    = "#0a1520"
    BORDER      = "#0e2233"
    ACCENT      = "#00d4ff"
    ACCENT_DIM  = "#0a4a5e"
    TEXT_BRIGHT = "#e8f4f8"
    TEXT_MID    = "#7ab8cc"
    TEXT_DIM    = "#2a5566"
    WARN        = "#ffaa00"
    SUCCESS     = "#00ff9d"

    WIDTH  = 380
    HEIGHT = 520

    def __init__(self):
        self._queue: queue.Queue[UIEvent] = queue.Queue()
        self._status = Status.IDLE
        self._drag_x = 0
        self._drag_y = 0
        self._angle  = 0.0   # for ring animation

        self._root = tk.Tk()
        self._build_window()
        self._build_ui()
        self._start_animation()
        self._poll_events()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _build_window(self):
        root = self._root
        root.title("JARVIS")
        root.geometry(f"{self.WIDTH}x{self.HEIGHT}+80+80")
        root.configure(bg=self.BG)
        root.overrideredirect(True)          # no title bar
        root.attributes("-topmost", True)    # always on top
        root.attributes("-alpha", 0.96)

        # Drag to move
        root.bind("<Button-1>",   self._on_drag_start)
        root.bind("<B1-Motion>",  self._on_drag_move)

    def _on_drag_start(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _on_drag_move(self, e):
        x = self._root.winfo_x() + e.x - self._drag_x
        y = self._root.winfo_y() + e.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = self._root

        # ── Outer frame with angular border effect ────────────────────────────
        outer = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        inner = tk.Frame(outer, bg=self.BG)
        inner.pack(fill="both", expand=True)

        # ── Header bar ────────────────────────────────────────────────────────
        header = tk.Frame(inner, bg=self.BG_PANEL, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Corner bracket decoration (top-left)
        tk.Label(
            header, text="⌐", fg=self.ACCENT, bg=self.BG_PANEL,
            font=("Courier New", 18, "bold")
        ).place(x=8, y=4)

        # JARVIS title
        tk.Label(
            header,
            text="J.A.R.V.I.S",
            fg=self.ACCENT,
            bg=self.BG_PANEL,
            font=("Courier New", 13, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Close button
        close_btn = tk.Label(
            header, text="✕", fg=self.TEXT_DIM, bg=self.BG_PANEL,
            font=("Courier New", 11), cursor="hand2",
        )
        close_btn.place(x=self.WIDTH - 28, y=14)
        close_btn.bind("<Button-1>", lambda e: root.destroy())
        close_btn.bind("<Enter>",    lambda e: close_btn.config(fg="#ff4455"))
        close_btn.bind("<Leave>",    lambda e: close_btn.config(fg=self.TEXT_DIM))

        # Separator line
        tk.Frame(inner, bg=self.ACCENT_DIM, height=1).pack(fill="x")

        # ── Status ring canvas ────────────────────────────────────────────────
        canvas_frame = tk.Frame(inner, bg=self.BG, pady=12)
        canvas_frame.pack(fill="x")

        self._canvas = tk.Canvas(
            canvas_frame, width=110, height=110,
            bg=self.BG, highlightthickness=0,
        )
        self._canvas.pack()

        # ── Status text ───────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="STANDBY")
        tk.Label(
            inner,
            textvariable=self._status_var,
            fg=self.ACCENT,
            bg=self.BG,
            font=("Courier New", 9, "bold"),
        ).pack()

        # ── Divider ───────────────────────────────────────────────────────────
        self._div(inner)

        # ── You said ──────────────────────────────────────────────────────────
        self._section(inner, "YOU SAID")
        self._user_var = tk.StringVar(value="—")
        self._user_label = tk.Label(
            inner,
            textvariable=self._user_var,
            fg=self.TEXT_BRIGHT,
            bg=self.BG,
            font=("Courier New", 9),
            wraplength=self.WIDTH - 40,
            justify="left",
            anchor="w",
        )
        self._user_label.pack(fill="x", padx=20, pady=(0, 8))

        # ── Divider ───────────────────────────────────────────────────────────
        self._div(inner)

        # ── Jarvis response ───────────────────────────────────────────────────
        self._section(inner, "JARVIS")
        self._response_var = tk.StringVar(value="—")
        self._response_label = tk.Label(
            inner,
            textvariable=self._response_var,
            fg=self.SUCCESS,
            bg=self.BG,
            font=("Courier New", 9),
            wraplength=self.WIDTH - 40,
            justify="left",
            anchor="w",
        )
        self._response_label.pack(fill="x", padx=20, pady=(0, 8))

        # ── Divider ───────────────────────────────────────────────────────────
        self._div(inner)

        # ── Tool used ─────────────────────────────────────────────────────────
        self._section(inner, "LAST ACTION")
        self._tool_var = tk.StringVar(value="—")
        tk.Label(
            inner,
            textvariable=self._tool_var,
            fg=self.WARN,
            bg=self.BG,
            font=("Courier New", 9),
            wraplength=self.WIDTH - 40,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 10))

        # ── Bottom bar ────────────────────────────────────────────────────────
        tk.Frame(inner, bg=self.ACCENT_DIM, height=1).pack(fill="x", side="bottom")
        bottom = tk.Frame(inner, bg=self.BG_PANEL, height=24)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        tk.Label(
            bottom,
            text="SYS ACTIVE  ◆  v2.0",
            fg=self.TEXT_DIM,
            bg=self.BG_PANEL,
            font=("Courier New", 7),
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _div(self, parent):
        tk.Frame(parent, bg=self.BORDER, height=1).pack(fill="x", padx=16, pady=4)

    def _section(self, parent, label: str):
        tk.Label(
            parent,
            text=f"  {label}",
            fg=self.TEXT_DIM,
            bg=self.BG,
            font=("Courier New", 7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(6, 2))

    # ── Ring animation ────────────────────────────────────────────────────────

    def _draw_ring(self):
        c = self._canvas
        c.delete("all")

        cx, cy, r_outer, r_inner = 55, 55, 46, 36
        color = STATUS_COLOR[self._status]
        glow  = STATUS_GLOW[self._status]

        # Glow background circle
        c.create_oval(
            cx - r_outer - 4, cy - r_outer - 4,
            cx + r_outer + 4, cy + r_outer + 4,
            fill=glow, outline="",
        )

        # Static base ring
        c.create_oval(
            cx - r_outer, cy - r_outer,
            cx + r_outer, cy + r_outer,
            outline=self.BORDER, width=2, fill="",
        )

        # Animated arc (only when not idle)
        if self._status != Status.IDLE:
            start = (self._angle % 360)
            extent = 240 if self._status == Status.THINKING else 180
            c.create_arc(
                cx - r_outer, cy - r_outer,
                cx + r_outer, cy + r_outer,
                start=start, extent=extent,
                outline=color, width=3, style="arc",
            )
            # Counter arc
            c.create_arc(
                cx - r_inner, cy - r_inner,
                cx + r_inner, cy + r_inner,
                start=-start, extent=120,
                outline=self.ACCENT_DIM, width=1, style="arc",
            )
        else:
            # Idle: static ring with corner ticks
            c.create_oval(
                cx - r_outer, cy - r_outer,
                cx + r_outer, cy + r_outer,
                outline=self.ACCENT_DIM, width=2, fill="",
            )
            for deg in (0, 90, 180, 270):
                rad = math.radians(deg)
                x1 = cx + (r_outer - 4) * math.cos(rad)
                y1 = cy - (r_outer - 4) * math.sin(rad)
                x2 = cx + (r_outer + 4) * math.cos(rad)
                y2 = cy - (r_outer + 4) * math.sin(rad)
                c.create_line(x1, y1, x2, y2, fill=color, width=2)

        # Center dot
        dot_r = 6
        c.create_oval(
            cx - dot_r, cy - dot_r,
            cx + dot_r, cy + dot_r,
            fill=color, outline="",
        )

        # Hex decorative marks
        for i in range(6):
            rad = math.radians(i * 60 + self._angle * 0.3)
            dist = r_outer + 10
            x = cx + dist * math.cos(rad)
            y = cy - dist * math.sin(rad)
            c.create_rectangle(x - 1, y - 1, x + 1, y + 1, fill=self.TEXT_DIM, outline="")

    def _start_animation(self):
        def tick():
            if self._status != Status.IDLE:
                speed = 4 if self._status == Status.THINKING else 2
                self._angle = (self._angle + speed) % 360
            self._draw_ring()
            self._root.after(40, tick)   # ~25fps
        tick()

    # ── Event bridge ─────────────────────────────────────────────────────────

    def post(self, event: UIEvent):
        """Thread-safe: called from the Jarvis pipeline thread."""
        self._queue.put(event)

    def _poll_events(self):
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle(event)
        except queue.Empty:
            pass
        self._root.after(50, self._poll_events)

    def _handle(self, event: UIEvent):
        if event.kind == "status":
            s = {
                "idle":      Status.IDLE,
                "listening": Status.LISTENING,
                "thinking":  Status.THINKING,
                "speaking":  Status.SPEAKING,
            }.get(event.value, Status.IDLE)
            self._status = s
            self._status_var.set(STATUS_LABEL[s])

        elif event.kind == "user":
            self._user_var.set(event.value or "—")

        elif event.kind == "response":
            # Truncate long responses for display
            text = event.value or "—"
            self._response_var.set(text[:180] + "…" if len(text) > 180 else text)

        elif event.kind == "tool":
            self._tool_var.set(event.value or "—")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        self._root.mainloop()
