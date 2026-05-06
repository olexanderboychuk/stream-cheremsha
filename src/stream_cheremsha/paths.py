from __future__ import annotations

import sys
from pathlib import Path

# Used to locate the package data root in dev and in Nuitka standalone layouts.
_SPLASH_QML = Path("qml") / "SplashScreen.qml"


def stream_cheremsha_root() -> Path:
    """
    Directory that contains ``qml/`` and ``assets/`` (the ``stream_cheremsha`` tree).

    In a normal checkout this is the package directory next to this file. In Nuitka
    standalone builds, entry ``app/main.py`` may live outside the package prefix, so
    ``Path(__file__)`` there is not a reliable anchor; this module always resolves
    relative to ``paths.py`` and falls back to searching next to the executable.
    """
    pkg_dir = Path(__file__).resolve().parent
    if (pkg_dir / _SPLASH_QML).is_file():
        return pkg_dir

    exe_dir = Path(sys.argv[0]).resolve().parent
    bases: list[Path] = [exe_dir]
    if exe_dir.is_dir():
        bases.extend(p for p in exe_dir.iterdir() if p.is_dir() and p.suffix == ".dist")

    for base in bases:
        for rel in (Path("stream_cheremsha"), Path()):
            root = base / rel if rel.parts else base
            if (root / _SPLASH_QML).is_file():
                return root.resolve()

    return pkg_dir
