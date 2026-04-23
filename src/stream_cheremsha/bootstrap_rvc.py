"""Install editable ``[rvc]`` (fairseq-fixed, torch, …) then ``rvc-python`` with ``--no-deps``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RVC_PYTHON = "rvc-python==0.1.5"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    root = _repo_root()
    py = sys.executable
    extra = f"{root}[rvc]"
    steps: list[list[str]] = [
        [py, "-m", "pip", "install", "-e", extra],
        [py, "-m", "pip", "install", RVC_PYTHON, "--no-deps"],
    ]
    print("RVC: install -e [rvc], then rvc-python --no-deps.", flush=True)
    print("If upgrading: pip uninstall -y fairseq first.\n", flush=True)
    for cmd in steps:
        print(" ", " ".join(cmd), flush=True)
        code = subprocess.call(cmd)
        if code != 0:
            return int(code)
    print("\nDone. Restart the app and enable RVC.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
