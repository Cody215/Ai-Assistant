# J.A.R.V.I.S

A voice-driven AI desktop assistant. Say "Hey Jarvis" to wake it up, push-to-talk input, and it responds in voice while taking real actions on your computer — opening apps, searching the web, checking your system, playing music, analysing your screen, and more.

Built with Gemini 2.5 Flash, ElevenLabs, and Whisper.

---

## What it can do

**Voice** — Wake word activation ("Hey Jarvis"), push-to-talk input (F9), local Whisper speech recognition, and ElevenLabs voice output streamed through mpv for near-instant audio playback.

**Desktop control** — Open applications, create and open files, draft emails locally (no sending yet, but saves them nicely), search the web across Google, DuckDuckGo, or Bing, and play music via Spotify or local files.

**System awareness** — Read and set volume, check battery status, get CPU/RAM/disk usage with automatic warnings when things look critical.

**Screen analysis** — Ask Jarvis what's on your screen and it captures a screenshot and analyses it using a local Ollama vision model. No data is sent to external servers.

**Persistent memory** — Conversations are logged to SQLite, facts about you are stored in ChromaDB as vector embeddings, and both are injected into the system prompt at startup. Jarvis starts each session already knowing things.

**Floating HUD** — An always-on-top overlay with an animated status ring showing what Jarvis is doing in real time.

**Character** — Dry, calm, quietly competent. Varied greetings, idle check-ins after silence, and memory that informs responses naturally without announcing itself.

---

## Architecture

The pipeline is straightforward: wake word or PTT triggers STT, the transcribed text goes to Gemini, Gemini either responds directly or calls a tool, the result comes back as voice via ElevenLabs and mpv.

A few decisions worth explaining:

**Choice of Model** — Gemini was considered as a viable option for the project. Gemini was one of the few models to give a free tier and usage to test and develop, alongside fast processing, low latency and easy API setup. Whisper was chosen for its free and unlimited private use, with easy integration. 

**Native function calling** — Gemini receives tool definitions as structured `FunctionDeclaration` objects and returns typed `FunctionCall` objects. No regex parsing of JSON in text responses, which was the original approach and was brittle and prone to false positives.

**Plugin tool registry** — Every tool lives in its own file in `tools/`. A `@register_tool` decorator handles both registration and building the Gemini declaration. Drop a new file in the folder, restart, and it works. No wiring required.

**Local screen analysis** — Screenshots go to a local Ollama vision model (llava), not Gemini. The image never leaves your machine. This was chosen to have a bit more privacy and control over what's analysed on your screen.

**Use of Elevenlabs and mpv** - Realistic text-to-speech with customisable voice and easy to install API. During development, Elevenlabs streaming would take an extensive amount of time. This issue was fixed with mpv which drastically dropped the delay.

**Hybrid memory** — SQLite is used for structured history and session summaries while ChromaDB is for semantic retrieval of facts. After each exchange a background call extracts anything worth remembering and stores it without blocking the pipeline.

**Threading** — The pipeline runs on a background thread. tkinter (the HUD) must run on the main thread on Windows. A queue bridges them and the pipeline posts status events, the HUD polls every 50ms.

---

## Setup

**Prerequisites:** Python 3.10+, Windows, [mpv](https://mpv.io/) on PATH, [Ollama](https://ollama.com/) installed.

```bash
# Install dependencies
pip install google-genai elevenlabs RealtimeSTT pynput psutil pycaw comtypes \
            requests chromadb python-dotenv pillow ollama openwakeword sounddevice

# Pull the vision model
ollama pull llava
```

Create a `.env` in the project root:

```
GEMINI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
```

```bash
python main.py        # terminal mode
python main_ui.py     # with HUD overlay
```

Wake word is off by default — enable it with `wake_word_enabled = True` in `config.py`. Say **"exit"** or **"shut down"** to close, **"goodbye"** to sleep.

---

## Adding a tool

Create a file in `tools/` — auto-discovered on next startup:

```python
# tools/my_tool.py
from tools import register_tool, schema

@register_tool(
    name="my_tool",
    description="What this does — Gemini reads this to decide when to use it.",
    parameters=schema(
        input="What the user wants",
        mode="optional: fast | thorough",
    ),
)
def my_tool(args):
    return "result as a string"
```

---

## Tests

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

Covers tool registry, memory database, ChromaDB store, config validation, and PTT key mapping. Hardware and APIs are excluded.

---

## Notes

- `memory_data/` is created automatically. Add it to `.gitignore` — it contains personal session data.
- On a Gemini 429 rate limit, switch to `gemini-2.5-flash-lite` in `config.py` or wait for the daily reset.
- Screen analysis takes ~10 seconds on CPU. Switch to `moondream` in config for a faster but lighter model.
- Memory can be inspected with `python memory/view.py` and cleared with `python memory/reset.py`.

---

## Roadmap

- Tiered model routing — Ollama for simple tasks, Gemini for complex ones
- PyWebView UI — replace tkinter with a proper HTML/CSS interface
- Browser automation via Playwright
- Reminders and time-based alerts
- Potential rename of the project

---

*Personal project — exploring voice interfaces, modular AI architecture, and local vs cloud inference trade-offs.*
