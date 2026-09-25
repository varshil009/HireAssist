"""
One-time (or repeat) project setup from repo root:

    python setup.py

Creates backend/.venv, installs Python deps, runs npm install in frontend/,
and copies backend/.env.example → backend/.env if missing.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV_DIR = BACKEND / ".venv"
REQUIREMENTS = BACKEND / "requirements.txt"
ENV_EXAMPLE = BACKEND / ".env.example"
ENV_FILE = BACKEND / ".env"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def activate_hint() -> str:
    if sys.platform == "win32":
        return r"backend\.venv\Scripts\activate"
    return "source backend/.venv/bin/activate"


def main() -> int:
    if sys.version_info < (3, 9):
        print("Python 3.9+ is required.", file=sys.stderr)
        return 1

    if not REQUIREMENTS.is_file():
        print(f"Missing {REQUIREMENTS}", file=sys.stderr)
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("Node.js/npm not found on PATH. Install Node 18+ and retry.", file=sys.stderr)
        return 1

    if not VENV_DIR.is_dir():
        print(f"Creating virtualenv at {VENV_DIR}")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"Using existing virtualenv at {VENV_DIR}")

    py = venv_python()
    if not py.is_file():
        print(f"Virtualenv python not found: {py}", file=sys.stderr)
        return 1

    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)])

    if ENV_EXAMPLE.is_file() and not ENV_FILE.is_file():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {ENV_FILE} from .env.example — add your GEMINI_API before using AI search.")
    elif ENV_FILE.is_file():
        print(f"Keeping existing {ENV_FILE}")

    print(f"Installing frontend dependencies in {FRONTEND}")
    run([npm, "install"], cwd=FRONTEND)

    print("\nSetup complete. Next:")
    print("  1. Edit backend/.env and set GEMINI_API (for AI search).")
    print(f"  2. Activate venv: {activate_hint()}")
    print("  3. python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
