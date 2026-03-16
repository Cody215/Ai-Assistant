"""
HUD entry point for Jarvis.

Runs the pipeline on a background thread while the HUD (tkinter)
runs on the main thread — required by tkinter on Windows.

The two threads communicate via a queue.Queue inside JarvisHUD.
The pipeline posts UIEvent objects into the queue; the HUD polls
it every 50ms via root.after() and updates the display.

Usage:
    python main_ui.py
"""

import threading
from config import load_config
from jarvis_core import JarvisApp
from ui import JarvisHUD


def _run_pipeline(app: JarvisApp, hud: JarvisHUD):
    try:
        while True:
            if not app.run_turn():
                break
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
        # Close the HUD window cleanly from the pipeline thread
        try:
            hud._root.after(0, hud._root.destroy)
        except Exception:
            pass


def main():
    print("Starting Jarvis with HUD...")
    cfg = load_config()
    # HUD must be created on the main thread before the pipeline starts
    hud = JarvisHUD()
    app = JarvisApp(cfg, hud=hud)
    # Pipeline on background thread, daemon=True so it dies if main thread dies
    t = threading.Thread(target=_run_pipeline, args=(app, hud), daemon=True)
    t.start()

    print("HUD active. Say 'exit' to quit or close the overlay.\n")
     # tkinter mainloop must run on the main thread — blocks here until window closes
    hud.run()


if __name__ == "__main__":
    main()
