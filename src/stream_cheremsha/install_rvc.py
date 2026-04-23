"""Install ``rvc-python`` with ``pip`` ``--no-deps`` (avoids bad upstream numpy/faiss pins)."""

from __future__ import annotations

import subprocess
import sys

RVC_PYTHON = "rvc-python==0.1.5"


def main() -> int:
    cmd = [sys.executable, "-m", "pip", "install", RVC_PYTHON, "--no-deps"]
    print("Installing RVC (PyPI cannot resolve this in one graph with this app; using --no-deps):")
    print(" ", " ".join(cmd), flush=True)
    return int(subprocess.call(cmd))


if __name__ == "__main__":
    raise SystemExit(main())
