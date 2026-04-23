from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from stream_cheremsha.domain.models import ChatMessage


class TextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Return audio bytes (MP3 from Google, WAV from Piper, etc.)."""

    async def aclose(self) -> None:
        """Release network or native resources."""


class AudioSink(Protocol):
    async def play_mp3(self, data: bytes) -> None:
        """Play one MP3 clip to completion before returning."""


StatusCallback = Callable[[str], None]
ChatCallback = Callable[[ChatMessage], None]
