"""
Terminal entry point for Jarvis.

Runs the pipeline in a simple loop on the main thread.
No UI — use main_ui.py for the HUD overlay.

Usage:
    python main.py
"""

from config import load_config
from jarvis_core import JarvisApp


def main():
    print("Starting Jarvis...")
    cfg = load_config()
    app = JarvisApp(cfg)
    print("Jarvis is ready. Say 'exit' or press Ctrl+C to quit.\n")

    try:
        while True:
            if not app.run_turn():
                break
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
         # Always runs — writes session summary, closes DB, stops listeners
        app.shutdown()


if __name__ == "__main__":
    main()
