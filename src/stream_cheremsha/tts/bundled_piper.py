"""Piper ``.onnx`` models shipped inside the install / frozen app (no extra download).

Release build: place ``{voice_id}.onnx`` (and usually the matching ``.onnx.json``) under
``src/stream_cheremsha/data/piper/`` before building the wheel or PyInstaller bundle.
The filename stem must match the voice id from :mod:`stream_cheremsha.tts.piper_voices`
(e.g. ``uk_UA-ukrainian_tts-medium.onnx``).

PyInstaller: add ``collect_data_files("stream_cheremsha")`` (or include ``data/piper``) so
``importlib.resources`` and/or ``sys._MEIPASS`` paths resolve.
"""

from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path


def bundled_piper_onnx_path(voice_id: str) -> Path | None:
    """Return path to a packaged ``.onnx`` for ``voice_id``, or ``None`` if not shipped."""
    stem = (voice_id or "").strip().replace("\\", "/").split("/")[-1]
    if not stem:
        return None
    name = f"{stem}.onnx"
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meip = Path(sys._MEIPASS)
        for sub in (
            meip / "stream_cheremsha" / "data" / "piper" / name,
            meip / "data" / "piper" / name,
        ):
            if sub.is_file():
                return sub.resolve()
    try:
        node = importlib.resources.files("stream_cheremsha") / "data" / "piper" / name
        if node.is_file():
            with importlib.resources.as_file(node) as p:
                return Path(p).resolve()
    except (OSError, TypeError, ValueError, FileNotFoundError, NotADirectoryError):
        pass
    return None


def effective_piper_onnx_path(
    raw_settings_path: str,
    tts_lang: str,
) -> Path | None:
    """Prefer a valid path from settings; otherwise a bundled file for ``tts_lang``."""
    s = (raw_settings_path or "").strip()
    if s:
        p = Path(s).expanduser()
        if p.is_file():
            return p.resolve()
    from stream_cheremsha.tts.piper_voices import piper_voice_id_for_tts_language

    vid = piper_voice_id_for_tts_language(tts_lang)
    if not vid:
        return None
    b = bundled_piper_onnx_path(vid)
    if b is not None:
        return b
    return None
