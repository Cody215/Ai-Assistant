# main.py
from config import load_config
from jarvis_core import JarvisApp


def main():
    print("Starting Jarvis...")
    cfg = load_config()
    app = JarvisApp(cfg)
    print(f"Jarvis is ready. Say 'exit' or press Ctrl+C to quit.\n")

    try:
        while True:
            if not app.run_turn():
                break
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
