"""Local TTS via the ``piper-tts`` PyPI package (``PiperVoice``)."""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)


def is_piper_package_installed() -> bool:
    try:
        import piper  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


class PiperTts:
    """Synthesize speech to WAV bytes using ``PiperVoice.synthesize_wav``."""

    ENGINE_ID: Final[str] = "piper"

    def __init__(self, model_path: str | Path, *, use_cuda: bool = False) -> None:
        if not is_piper_package_installed():
            raise ImportError("Install the piper-tts package: pip install piper-tts")
        from piper import PiperVoice  # noqa: PLC0415

        path = Path(model_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Piper ONNX model not found: {path}")

        self._model_path = path
        self._use_cuda = bool(use_cuda)
        self._voice: PiperVoice | None = PiperVoice.load(str(path), use_cuda=self._use_cuda)
        logger.info("Piper voice loaded: %s (cuda=%s)", self._model_path, self._use_cuda)

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def use_cuda(self) -> bool:
        return self._use_cuda

    async def synthesize(self, text: str) -> bytes:
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty TTS text")
        voice = self._voice
        if voice is None:
            raise RuntimeError("Piper voice was unloaded")

        def _to_wav() -> bytes:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_out:
                voice.synthesize_wav(stripped, wav_out)
            data = buf.getvalue()
            if not data:
                raise ValueError("Piper returned empty WAV")
            return data

        return await asyncio.to_thread(_to_wav)

    async def aclose(self) -> None:
        if self._voice is None:
            return

        def _drop() -> None:
            self._voice = None

        await asyncio.to_thread(_drop)
