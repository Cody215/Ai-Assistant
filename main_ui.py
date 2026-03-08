# main_ui.py
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
    hud = JarvisHUD()
    app = JarvisApp(cfg, hud=hud)

    t = threading.Thread(target=_run_pipeline, args=(app, hud), daemon=True)
    t.start()

    print("HUD active. Say 'exit' to quit or close the overlay.\n")
    hud.run()


if __name__ == "__main__":
    main()
