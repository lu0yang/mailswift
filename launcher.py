import os
import sys
import threading
import webbrowser

import uvicorn


def main():
    # PyInstaller sets sys.frozen; our backend code uses this to locate
    # the frontend dist relative to the executable
    host = "127.0.0.1"
    port = 8080

    # Open browser after a short delay
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    # Prevent multiprocessing issues in frozen builds
    if getattr(sys, "frozen", False):
        # uvicorn multiprocessing doesn't work in frozen builds
        workers = 1
    else:
        workers = 1

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
