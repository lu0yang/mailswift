"""
MailSwift - PyWebview desktop application entry point.

Launches a local FastAPI server and displays the Vue frontend
in a native webview window.
"""

import os
import sys
import threading
import logging
from pathlib import Path

import webview
import uvicorn

from backend.database import init_db
from backend.main import app as fastapi_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve paths
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
API_PORT = 8080


def serve_frontend_asset(path: str) -> str:
    """Read a built frontend asset and return its content."""
    file_path = FRONTEND_DIST / path
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def get_frontend_html() -> str:
    """Load the built index.html and inject base href for file:// compatibility."""
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        return "<h1>Frontend not built. Run: cd frontend && npm run build</h1>"

    html = index_path.read_text(encoding="utf-8")
    # Replace relative paths with inline content for webview compatibility
    html = html.replace('./assets/', str(FRONTEND_DIST / 'assets' / ''))
    return html


def start_api_server():
    """Start the FastAPI server in a daemon thread."""
    init_db()
    uvicorn.run(fastapi_app, host="127.0.0.1", port=API_PORT, log_level="warning")


def main():
    logger.info("Starting MailSwift...")

    # Start FastAPI in background thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # Create and show the webview window
    window = webview.create_window(
        title="MailSwift",
        url=f"http://127.0.0.1:{API_PORT}",
        width=860,
        height=680,
        min_size=(720, 540),
        resizable=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
