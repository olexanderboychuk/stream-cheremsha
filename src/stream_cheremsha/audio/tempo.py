from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Final

logger = logging.getLogger(__name__)

# ffmpeg's atempo filter is limited to 0.5..2.0 per instance; clamp to that range so a
# single pass always works (and pitch is preserved, unlike a raw sample-rate change).
MIN_TEMPO: Final[float] = 0.5
MAX_TEMPO: Final[float] = 2.0
_NO_OP_EPS: Final[float] = 1e-3


def apply_speed_to_audio(data: bytes, factor: float) -> bytes:
    """Re-encode ``data`` so it plays at ``factor``x speed (pitch preserved via ffmpeg atempo).

    Returns the original bytes unchanged when the factor is ~1.0, ffmpeg is unavailable, or the
    conversion fails — speed control is best-effort and never blocks playback.
    """
    if not data:
        return data
    if abs(factor - 1.0) < _NO_OP_EPS:
        return data
    f = max(MIN_TEMPO, min(MAX_TEMPO, float(factor)))

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.debug("ffmpeg not found; TTS speed (atempo=%.3f) skipped", f)
        return data

    # Hide the transient console window on Windows so it cannot steal focus from fullscreen games.
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    encodings = (
        ["-codec:a", "libmp3lame", "-q:a", "3", "-f", "mp3", "pipe:1"],
        ["-f", "wav", "-c:a", "pcm_s16le", "pipe:1"],
    )
    for tail in encodings:
        try:
            proc = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-i",
                    "pipe:0",
                    "-af",
                    f"atempo={f:.4f}",
                    *tail,
                ],
                input=data,
                capture_output=True,
                timeout=60,
                check=False,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except OSError as e:
            logger.debug("ffmpeg atempo run failed: %s", e)
            return data
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        logger.debug(
            "ffmpeg atempo rc=%s stderr=%r",
            proc.returncode,
            (proc.stderr or b"")[:200],
        )
    return data
