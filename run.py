"""
Start backend + frontend dev servers from repo root.

After setup, activate the backend venv, then:

    backend\\.venv\\Scripts\\activate    # Windows (repo root)
    python run.py

Press Ctrl+C to stop both.
"""
from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
VENV_DIR = ROOT / "backend" / ".venv"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def activate_hint() -> str:
    if sys.platform == "win32":
        return r"backend\.venv\Scripts\activate"
    return "source backend/.venv/bin/activate"


def in_project_venv() -> bool:
    try:
        return Path(sys.executable).resolve() == venv_python().resolve()
    except OSError:
        return False


def main() -> int:
    if not venv_python().is_file():
        print("Backend venv not found. From repo root run: python setup.py", file=sys.stderr)
        return 1

    if not in_project_venv():
        print(
            "Activate the backend virtualenv first, then run this script again:\n"
            f"  {activate_hint()}\n"
            "  python run.py",
            file=sys.stderr,
        )
        return 1

    py = Path(sys.executable)

    npm = shutil.which("npm")
    if not npm:
        print("npm not found. Install Node.js and run: python setup.py", file=sys.stderr)
        return 1

    if not (FRONTEND / "node_modules").is_dir():
        print("Frontend node_modules missing. Run: python setup.py", file=sys.stderr)
        return 1

    procs: list[subprocess.Popen] = []

    def stop_all() -> None:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        deadline = time.time() + 8
        for p in procs:
            if p.poll() is None and time.time() < deadline:
                try:
                    p.wait(timeout=max(0, deadline - time.time()))
                except subprocess.TimeoutExpired:
                    p.kill()

    def on_signal(_signum, _frame) -> None:
        stop_all()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_signal)

    print("Starting backend (http://127.0.0.1:8000) …")
    backend = subprocess.Popen(
        [str(py), str(ROOT / "main.py")],
        cwd=str(ROOT),
    )
    procs.append(backend)

    print("Starting frontend (http://localhost:5173) …")
    frontend = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(FRONTEND),
    )
    procs.append(frontend)

    print("\nHireAssist running. Open http://localhost:5173")
    print("Press Ctrl+C to stop both servers.\n")

    try:
        while True:
            for p in procs:
                code = p.poll()
                if code is not None and code != 0:
                    print(f"A server exited with code {code}. Shutting down.", file=sys.stderr)
                    stop_all()
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_all()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
