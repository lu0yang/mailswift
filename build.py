"""
MailSwift - PyInstaller build script.

Run this to package the application into a single .exe file.

Usage:
    1. Build frontend:  cd frontend && npm run build
    2. Install deps:    pip install pyinstaller
    3. Build:           python build.py

The output .exe will be in the dist/ directory.
"""

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def build_frontend():
    """Build the Vue frontend."""
    frontend_dir = BASE_DIR / "frontend"
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    print("Frontend built successfully.")


def build_app():
    """Package the app with PyInstaller."""
    icon_path = BASE_DIR / "app.ico"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "MailSwift",
        "--onefile",
        "--windowed",
        "--clean",
        "--add-data", f"{BASE_DIR / 'frontend' / 'dist'}{';' if sys.platform == 'win32' else ':'}frontend/dist",
        str(BASE_DIR / "app.py"),
    ]

    if icon_path.exists():
        cmd.insert(3, f"--icon={icon_path}")

    subprocess.run(cmd, check=True)
    print("\nBuild complete! Output: dist/MailSwift.exe")


def clean():
    """Remove build artifacts."""
    import shutil
    for d in ["build", "dist", "__pycache__"]:
        p = BASE_DIR / d
        if p.exists():
            shutil.rmtree(p)
    for spec in BASE_DIR.glob("*.spec"):
        spec.unlink()
    print("Cleaned.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MailSwift build script")
    parser.add_argument("action", nargs="?", default="all",
                        choices=["all", "frontend", "app", "clean"],
                        help="What to build")
    args = parser.parse_args()

    if args.action in ("all", "frontend"):
        build_frontend()

    if args.action in ("all", "app"):
        build_app()

    if args.action == "clean":
        clean()
