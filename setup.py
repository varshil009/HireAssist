"""
One-time (or repeat) project setup from repo root:

    python setup.py

On Windows, if your default `python` is 3.14+, use:

    py -3.9 setup.py

Creates backend/.venv with a supported Python (3.9–3.13), installs deps, npm install,
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

# pydantic/FastAPI wheels may be missing on 3.14+ (pip tries to compile Rust → needs MSVC).
MAX_SUPPORTED_VENV = (3, 13)


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


def python_version_tuple(exe: Path | str) -> tuple[int, int] | None:
    try:
        out = subprocess.check_output(
            [str(exe), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        a, b = out.strip().split()
        return int(a), int(b)
    except (subprocess.CalledProcessError, OSError, ValueError):
        return None


def version_too_new(ver: tuple[int, int]) -> bool:
    return ver > MAX_SUPPORTED_VENV


def find_windows_py_launcher(*versions: str) -> list[str] | None:
    py = shutil.which("py")
    if not py:
        return None
    for v in versions:
        cmd = [py, f"-{v}"]
        if subprocess.run(cmd + ["-c", "pass"], capture_output=True).returncode == 0:
            return cmd
    return None


def python_to_create_venv() -> list[str]:
    """Pick an interpreter for `python -m venv` (prebuilt wheels on Windows)."""
    current = (sys.version_info.major, sys.version_info.minor)
    if not version_too_new(current):
        return [sys.executable]

    print(
        f"Your default Python is {current[0]}.{current[1]}. "
        f"HireAssist needs {MAX_SUPPORTED_VENV[0]}.{MAX_SUPPORTED_VENV[1]} or older for pip wheels "
        "(3.14 often tries to compile pydantic-core and fails without Visual Studio Build Tools).",
        file=sys.stderr,
    )

    if sys.platform == "win32":
        launcher = find_windows_py_launcher("3.12", "3.11", "3.10", "3.9", "3.13")
        if launcher:
            out = subprocess.check_output(
                launcher + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
                text=True,
            )
            maj, min_ = out.strip().split()
            print(f"Using Python {maj}.{min_} via: {' '.join(launcher)}")
            return launcher

    print(
        "Install Python 3.9–3.12 from python.org, then run setup with that interpreter, e.g.\n"
        "  Windows: py -3.9 setup.py\n"
        "  Or:      C:\\Path\\To\\Python39\\python.exe setup.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


def ensure_venv() -> None:
    py_exe = venv_python()
    if VENV_DIR.is_dir() and py_exe.is_file():
        ver = python_version_tuple(py_exe)
        if ver and version_too_new(ver):
            print(
                f"\nExisting {VENV_DIR} uses Python {ver[0]}.{ver[1]}, which is too new for pinned wheels.\n"
                "Delete the folder and run setup again:\n"
                "  Remove-Item -Recurse -Force backend\\.venv\n"
                "  py -3.9 setup.py\n",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f"Using existing virtualenv at {VENV_DIR}")
        return

    print(f"Creating virtualenv at {VENV_DIR}")
    creator = python_to_create_venv()
    run(creator + ["-m", "venv", str(VENV_DIR)])


def main() -> int:
    if not REQUIREMENTS.is_file():
        print(f"Missing {REQUIREMENTS}", file=sys.stderr)
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("Node.js/npm not found on PATH. Install Node 18+ and retry.", file=sys.stderr)
        return 1

    ensure_venv()

    py = venv_python()
    if not py.is_file():
        print(f"Virtualenv python not found: {py}", file=sys.stderr)
        return 1

    ver = python_version_tuple(py)
    if ver:
        print(f"Virtualenv Python: {ver[0]}.{ver[1]}")

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
