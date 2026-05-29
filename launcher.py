import sys
import threading

import uvicorn


def main():
    host = "127.0.0.1"
    port = 8080

    # Start uvicorn in a background thread so it doesn't block the GUI
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            log_level="info",
        ),
        daemon=True,
    )
    server_thread.start()

    # Launch native desktop window (no browser needed)
    try:
        import webview
        webview.create_window("MailSwift", f"http://{host}:{port}", width=1200, height=800)
        webview.start()
    except ImportError:
        # Fallback for development: open in browser
        import webbrowser
        webbrowser.open(f"http://{host}:{port}")
        server_thread.join()


if __name__ == "__main__":
    main()
