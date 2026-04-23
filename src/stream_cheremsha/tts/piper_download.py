"""Download Piper voice files via the ``piper-tts`` CLI module."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _pick_onnx_file(search_root: Path, voice_id: str) -> Path | None:
    """Pick the best ``.onnx`` under ``search_root`` after a download."""
    candidates = sorted(search_root.rglob("*.onnx"), key=lambda p: len(str(p)))
    if not candidates:
        return None
    stem = voice_id.split("/")[-1]
    for p in candidates:
        if p.stem == stem or stem in p.stem:
            return p.resolve()
    return candidates[0].resolve()


async def download_piper_voice(voice_id: str, cache_root: Path) -> Path:
    """Run ``python -m piper.download_voices <voice_id>`` and return path to ``.onnx``."""
    cache_root.mkdir(parents=True, exist_ok=True)
    work = (cache_root / voice_id.replace("/", "_")).resolve()
    work.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "piper.download_voices",
        voice_id,
        cwd=str(work),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = (stdout or b"").decode(errors="replace")
    err = (stderr or b"").decode(errors="replace")
    if proc.returncode != 0:
        msg = err.strip() or out.strip() or f"exit {proc.returncode}"
        logger.warning("piper.download_voices failed: %s", msg[:2000])
        raise RuntimeError(msg[:2000])

    onnx = _pick_onnx_file(work, voice_id)
    if onnx is None or not onnx.is_file():
        raise RuntimeError(f"No .onnx file found under {work} after download")
    logger.info("Piper voice ready: %s", onnx)
    return onnx
