"""Piper voice ids (for ``python -m piper.download_voices``) per UI TTS language tag."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# BCP-47 style tags used by Google TTS ``tl`` and our settings ``tts/output_language``.
PIPER_VOICE_ID_BY_TTS_LANG: Final[dict[str, str]] = {
    "uk-UA": "uk_UA-ukrainian_tts-medium",
    "en-US": "en_US-lessac-medium",
    "en-GB": "en_GB-alan-medium",
    "de-DE": "de_DE-thorsten-medium",
    "pl-PL": "pl_PL-gosia-medium",
}

TTS_LANG_OPTIONS: Final[tuple[str, ...]] = tuple(PIPER_VOICE_ID_BY_TTS_LANG.keys())


def piper_voice_id_for_tts_language(tts_lang: str) -> str | None:
    """Return Piper download id for ``tts_lang``, or ``None`` if unknown."""
    key = (tts_lang or "").strip()
    return PIPER_VOICE_ID_BY_TTS_LANG.get(key)


def default_piper_download_root() -> Path:
    """Directory under XDG data (or home) where we store downloaded ``.onnx`` files."""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return (base / "stream-cheremsha" / "piper-voices").resolve()
