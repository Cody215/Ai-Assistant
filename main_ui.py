# main_ui.py
"""
Launches Jarvis with the HUD overlay.

The Jarvis pipeline runs on a background thread.
The HUD (tkinter) runs on the main thread — required on Windows.

Use main.py instead if you want terminal-only mode.
"""

import threading
from config import load_config
from jarvis_core import JarvisApp
from ui import JarvisHUD


def _run_pipeline(app: JarvisApp):
    try:
        while True:
            if not app.run_turn():
                break
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()


def main():
    print("Starting Jarvis with HUD...")
    cfg = load_config()
    hud = JarvisHUD()
    app = JarvisApp(cfg, hud=hud)

    # Pipeline runs in background thread
    t = threading.Thread(target=_run_pipeline, args=(app,), daemon=True)
    t.start()

    print("HUD active. Close the overlay or say 'exit' to quit.\n")

    # tkinter must run on the main thread
    hud.run()


if __name__ == "__main__":
    main()
