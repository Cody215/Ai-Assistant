# J.A.R.V.I.S

A voice-driven AI desktop assistant powered by Gemini 2.5 Flash and ElevenLabs, with local speech recognition, persistent memory, screen analysis, and a floating HUD overlay.

> Say "Hey Jarvis" to wake it. Hold F9 to talk. It remembers you between sessions.

---

## Overview

Jarvis is a voice-first AI assistant that runs on your Windows machine. Speak naturally and jarvis listens, responds in voice, and executes real actions on your computer: opening applications, searching the web, checking system status, playing music, managing files, analysing your screen, and more.

The project is built around four engineering priorities: a **modular tool system** that makes adding new capabilities trivial, **native LLM function calling** for reliable tool dispatch, **hybrid memory** that persists across sessions, and a **tiered model architecture** that routes sensitive operations like screen analysis to a local model rather than the cloud.

---

## Demo

> *(Screenshot or GIF of the HUD overlay in action)*

The floating HUD displays live pipeline state — LISTENING, PROCESSING, RESPONDING — alongside what you said, Jarvis's reply, and the last action taken. It sits above all other windows and can be dragged anywhere on screen.

---

## Features

**Voice I/O**
- Wake word activation — say "Hey Jarvis" to wake from sleep, "goodbye" to return
- Push-to-talk input via configurable hotkey (default: F9)
- Speech-to-text via OpenAI Whisper — runs locally, no API call
- Text-to-speech via ElevenLabs, streamed directly into mpv for sub-300ms audio start

**Desktop Control**
- Open applications (Chrome, VSCode, Notepad, Calculator, Word, Outlook, and more)
- Create and open files on the filesystem
- Draft and save email templates locally
- Web search via Google, DuckDuckGo, or Bing

**Media**
- Play music via Spotify (opens app or web) or local files with fuzzy filename matching

**System Awareness**
- Read and set system volume, mute/unmute
- Battery percentage, charging state, and estimated time remaining, low battery warning voiced as a reminder
- CPU, RAM, and disk usage — brief or detailed on request

**Time & Weather**
- Current time and date with full timezone support (IANA format)
- Live weather via Open-Meteo API — no key required

**Screen Analysis**
- "What's on my screen?" — captures a full screenshot and analyses it locally
- Processed by a local Ollama vision model (llava) — nothing sent to external servers
- Works for code review, error messages, general screen description

**Persistent Memory**
- Every session logged to SQLite: conversation turns and a written summary
- Facts about you extracted automatically after each exchange via Gemini
- Facts stored in ChromaDB as vector embeddings for semantic retrieval

**Floating HUD**
- Always-on-top overlay, draggable, semi-transparent
- Animated status ring — STANDBY / LISTENING / PROCESSING / RESPONDING / SLEEPING
- Real-time display of speech input, Jarvis's response, and last tool used

**Character**
- Dry wit, calm confidence, quiet loyalty — Alfred meets JARVIS
- Idle check-in timer — speaks naturally after a configurable period of silence
- Uses memory to inform personality without announcing it

---

## Architecture

```
                    ┌─────────────┐
                    │   main_ui   │  ← entry point (HUD mode)
                    │   main      │  ← entry point (terminal mode)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ jarvis_core │  ← pipeline orchestrator
                    └──┬───┬───┬──┘
                       │   │   │
          ┌────────────┘   │   └────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │  Wake Word  │  │   Gemini    │  │     TTS     │
   │   + PTT     │  │  2.5 Flash  │  │ (ElevenLabs │
   │  (local)    │  │  function   │  │  → mpv)     │
   └─────────────┘  │  calling    │  └─────────────┘
                    └──────┬──────┘
                           │ tool call?
                    ┌──────▼──────┐
                    │    tools/   │  ← auto-discovered plugin registry
                    └──┬──────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │               │
   ┌────▼────┐   ┌─────▼────┐  ┌─────▼────┐  ┌──────▼────┐
   │  apps   │   │  system  │  │  screen  │  │  files    │  ...
   └─────────┘   └──────────┘  └────┬─────┘  └───────────┘
                                    │ image only
                             ┌──────▼──────┐
                             │   Ollama    │  ← local vision model
                             │   (llava)   │  ← screen stays on machine
                             └─────────────┘

                    ┌──────▼──────┐
                    │   memory/   │
                    │  manager    │
                    └──┬──────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
   ┌──────▼──────┐           ┌──────▼──────┐
   │   SQLite    │           │  ChromaDB   │
   │  (history + │           │  (semantic  │
   │  summaries) │           │   facts)    │
   └─────────────┘           └─────────────┘
```

### Key Design Decisions

**Native function calling over regex parsing**
Earlier iterations detected tool requests by scanning Gemini's text output for JSON patterns with regex — brittle and prone to false positives. The current implementation passes tool definitions as structured `FunctionDeclaration` objects via the Gemini SDK. The model returns a typed `FunctionCall` object, eliminating an entire class of parsing bugs and making tool dispatch fully reliable.

**Plugin-based tool registry with auto-discovery**
Each tool lives in its own file in `tools/`. A `@register_tool` decorator registers the handler and builds the Gemini `FunctionDeclaration` simultaneously. On startup, `tools/__init__.py` scans the directory and imports every module automatically. Adding a new tool means creating one file — no wiring, no changes elsewhere.

**mpv for TTS audio**
ElevenLabs' built-in `stream()` function on some Windows setups introduces 20-40 seconds of audio buffering. The current implementation pipes the ElevenLabs stream directly into mpv's stdin. mpv begins playback within ~200ms of the first chunk, making voice responses feel immediate.

**Hybrid memory: SQLite + ChromaDB**
SQLite stores time-ordered data: conversation turns, session records, written summaries. ChromaDB stores semantic facts about the user as vector embeddings, retrieved by meaning rather than keyword. After each exchange, a background Gemini call extracts memorable facts without blocking the pipeline. At session start, both stores are queried and the results injected into the system prompt.

**Local screen analysis via Ollama**
Screen analysis is privacy-sensitive — screenshots should not be sent to external APIs. When `capture_screen` is triggered, the screenshot is processed by a local Ollama vision model (llava). The image never leaves the machine. Gemini handles all other inference; Ollama handles vision only.

**Threading model**
The pipeline (STT → LLM → TTS) runs on a background thread. tkinter must run on the main thread on Windows. A `queue.Queue` bridges the two — the pipeline posts status events into the queue, and the HUD polls it every 50ms via `root.after()`, keeping the UI responsive without shared mutable state.

---

## Project Structure

```
jarvis/
│
├── main.py               # Entry point — terminal mode
├── main_ui.py            # Entry point — HUD mode
├── jarvis_core.py        # Pipeline orchestrator: listen → think → speak
├── config.py             # All settings and system prompt / personality
├── stt.py                # Whisper speech-to-text (RealtimeSTT)
├── tts.py                # ElevenLabs TTS → mpv audio stream
├── ptt.py                # Push-to-talk key listener (pynput)
├── wake_word.py          # Wake word detector (openwakeword)
├── ui.py                 # Floating HUD overlay (tkinter)
│
├── tools/
│   ├── __init__.py       # Auto-discovery registry + @register_tool decorator
│   ├── apps.py           # open_app
│   ├── files.py          # create_file, open_file, draft_email
│   ├── web.py            # web_search
│   ├── music.py          # play_music (Spotify + local)
│   ├── datetime_tools.py # get_time, get_date, get_weather
│   ├── system.py         # get_volume, set_volume, get_battery, get_system_status
│   └── screen.py         # capture_screen → routed to local Ollama vision
│
├── memory/
│   ├── __init__.py
│   ├── db.py             # SQLite: turns, sessions, profile
│   ├── store.py          # ChromaDB: semantic fact storage and retrieval
│   ├── manager.py        # Coordinator: context injection, extraction, summarisation
│   ├── view.py           # CLI viewer: inspect stored facts, summaries, history
│   └── reset.py          # CLI tool: wipe memory selectively or entirely
│
├── tests/
│   ├── conftest.py       # Shared pytest configuration
│   ├── test_tools.py     # Tool registry, individual tool logic
│   ├── test_memory_db.py # SQLite turns, sessions, profile
│   ├── test_memory_store.py # ChromaDB fact storage and retrieval
│   ├── test_config.py    # Config validation and defaults
│   └── test_ptt.py       # Key mapping and PTT initialisation
│
└── memory_data/          # Auto-created on first run — add to .gitignore
    ├── jarvis.db         # SQLite database
    └── chroma/           # ChromaDB vector store
```

---

## Setup

### Prerequisites

- Python 3.10+
- Windows 10 or later
- [mpv](https://mpv.io/) — place `mpv.exe` in the project root or add to PATH
- [Ollama](https://ollama.com/) — for local screen analysis
- A Gemini API key — [Google AI Studio](https://aistudio.google.com/)
- An ElevenLabs API key — [ElevenLabs](https://elevenlabs.io/)

### Install dependencies

```bash
pip install google-genai elevenlabs RealtimeSTT pynput psutil pycaw comtypes \
            requests chromadb python-dotenv pillow ollama openwakeword sounddevice
```

### Pull the Ollama vision model

```bash
ollama pull llava
# Or for a lighter/faster option:
ollama pull moondream
```

### Environment variables

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

### Run

```bash
# Terminal mode
python main.py

# With HUD overlay
python main_ui.py
```

**Wake word disabled by default.** To enable, set `wake_word_enabled: bool = True` in `config.py`.

Default PTT key is **F9**. Say **"exit"** or **"shut down"** to close. Say **"goodbye"** to return to sleep (wake word mode).

---

## Adding a New Tool

Drop a file in `tools/` — it's automatically discovered on next startup:

```python
# tools/my_tool.py
from tools import register_tool, schema

@register_tool(
    name="do_something",
    description="What this tool does — shown to Gemini to decide when to use it.",
    parameters=schema(
        input_text="The text to process",
        mode="optional: fast | thorough (default: fast)",
    ),
)
def do_something(args):
    text = args.get("input_text", "")
    mode = args.get("mode", "fast")
    # your logic here
    return "Result as a string."
```

No wiring, no registration step, no changes to any other file.

---

## Memory Management

```bash
# View everything Jarvis has stored
python memory/view.py

# View specific sections
python memory/view.py --facts        # stored facts about you
python memory/view.py --summaries    # session summaries
python memory/view.py --history      # last 10 conversation turns
python memory/view.py --history 30   # last 30 turns

# Clear memory
python memory/reset.py               # wipe everything (prompts for confirmation)
python memory/reset.py --facts       # wipe ChromaDB facts only
python memory/reset.py --history     # wipe SQLite history only
```

---

## Running Tests

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

Tests cover: tool registry, web search URL construction, datetime output, battery states, system status warnings, file creation, screenshot capture, SQLite turns/sessions/profile, ChromaDB storage/deduplication/retrieval, config validation, and PTT key mapping. Hardware, APIs, and audio are excluded from automated tests.

---

## Configuration

All settings live in `config.py` under `AppConfig`:

| Setting | Default | Description |
|---|---|---|
| `gemini_model` | `gemini-2.5-flash` | Gemini model — swap to `gemini-2.5-flash-lite` if rate limited |
| `stt_model` | `base.en` | Whisper model size (tiny/base/small/medium) |
| `ptt_key` | `F9` | Push-to-talk hotkey |
| `wake_word_enabled` | `False` | Enable wake word mode |
| `wake_word_threshold` | `0.55` | Detection confidence threshold (0.0–1.0) |
| `idle_checkin_minutes` | `5` | Minutes before Jarvis checks in unprompted (0 = off) |
| `memory_dir` | `memory_data/` | Where SQLite and ChromaDB data live |
| `mpv_path` | `mpv.exe` | Path to mpv executable |
| `ollama_vision_model` | `llava` | Local vision model for screen analysis |
| `ollama_host` | `http://localhost:11434` | Ollama server address |
| `default_timezone` | `Australia/Sydney` | Fallback timezone |

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| LLM | Gemini 2.5 Flash | Fast inference, large context, reliable native function calling |
| STT | Whisper via RealtimeSTT | Runs fully locally, no API cost, tunable VAD |
| TTS | ElevenLabs Flash v2.5 | Natural voice with streaming support |
| Audio playback | mpv | Sub-300ms start via stdin piping, bypasses Python audio stack |
| Tool calling | Gemini FunctionDeclaration API | Structured and typed — no regex parsing |
| Wake word | openwakeword | Runs locally, low CPU, "hey jarvis" preset available |
| Vision (screen) | Ollama + llava | Local processing — screenshots never leave the machine |
| Conversation memory | SQLite (built-in) | Zero-dependency structured storage |
| Semantic memory | ChromaDB | Local vector store, pip install only, no server |
| HUD | tkinter (built-in) | No extra dependency, sufficient for overlay UI |
| PTT | pynput | Cross-platform key listener |
| System tools | psutil + pycaw | Reliable Windows audio and system metrics |
| Weather | Open-Meteo API | Free, no API key, geocoding included |

---

## Roadmap

- [ ] Tiered model routing — Ollama for simple tasks, Gemini for complex reasoning
- [ ] PyWebView UI — replace tkinter HUD with full HTML/CSS/JS interface
- [ ] Expanded file management — search, move, delete across filesystem

---

## Notes

- `memory_data/` is auto-created on first run. Add it to `.gitignore` — it contains personal conversation data.
- Gemini free tier has daily rate limits. On a 429 error, switch `gemini_model` to `gemini-2.5-flash-lite` or wait for the daily reset.
- mpv must be accessible — place `mpv.exe` in the project root or set `mpv_path` in config to its full path. Falls back to ElevenLabs' built-in player if not found.
- Wake word requires `openwakeword` and `sounddevice`. Disabled by default — enable in `config.py`.

---

*A personal project exploring voice interface design, modular AI architecture, and the engineering trade-offs between cloud and local inference.*
