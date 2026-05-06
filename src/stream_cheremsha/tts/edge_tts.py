from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Final

logger = logging.getLogger(__name__)

# Microsoft voice list is a network call; without a cap the UI can stay on
# "loading voices" forever when the connection stalls.
LIST_VOICES_TIMEOUT_SEC: Final[float] = 45.0


def _import_edge_tts() -> Any:
    # Keep import lazy so the app can still start even if the dependency
    # is missing in some dev environments.
    import edge_tts  # noqa: PLC0415

    return edge_tts


@dataclass(frozen=True, slots=True)
class EdgeVoice:
    short_name: str
    locale: str
    gender: str | None = None

    @property
    def label(self) -> str:
        g = f" ({self.gender})" if self.gender else ""
        return f"{self.short_name}{g}"


def filter_edge_voices_for_locale(voices: list[EdgeVoice], locale: str) -> list[EdgeVoice]:
    want = (locale or "").strip()
    if not want:
        return []
    return [v for v in voices if v.locale == want]


_voices_cache_lock = asyncio.Lock()
_voices_cache: list[EdgeVoice] | None = None


async def list_edge_voices_cached() -> list[EdgeVoice]:
    """Fetch Edge voices once per app session and cache in memory."""
    global _voices_cache
    if _voices_cache is not None:
        logger.debug("Edge TTS: using cached voice list (%d voices)", len(_voices_cache))
        return _voices_cache
    async with _voices_cache_lock:
        if _voices_cache is not None:
            logger.debug("Edge TTS: using cached voice list (%d voices)", len(_voices_cache))
            return _voices_cache

        edge_tts = _import_edge_tts()
        t0 = time.monotonic()
        logger.info(
            "Edge TTS: fetching voice list (timeout %.0fs)",
            LIST_VOICES_TIMEOUT_SEC,
        )
        try:
            raw = await asyncio.wait_for(
                edge_tts.list_voices(),
                timeout=LIST_VOICES_TIMEOUT_SEC,
            )
        except TimeoutError as e:
            logger.warning(
                "Edge TTS: list_voices timed out after %.0fs",
                LIST_VOICES_TIMEOUT_SEC,
            )
            raise RuntimeError(
                f"Edge TTS: list_voices timed out after {LIST_VOICES_TIMEOUT_SEC:.0f}s",
            ) from e
        except Exception as e:
            logger.warning(
                "Edge TTS: list_voices failed (%s): %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
            raise

        if not isinstance(raw, list):
            logger.warning(
                "Edge TTS: list_voices returned %s, expected list",
                type(raw).__name__,
            )
            raw_list: list[Any] = []
        else:
            raw_list = raw

        out: list[EdgeVoice] = []
        skipped = 0
        for r in raw_list:
            if not isinstance(r, dict):
                skipped += 1
                continue
            short = str(r.get("ShortName", "")).strip()
            loc = str(r.get("Locale", "")).strip()
            if not short or not loc:
                skipped += 1
                continue
            gender = str(r.get("Gender", "")).strip() or None
            out.append(EdgeVoice(short_name=short, locale=loc, gender=gender))

        elapsed = time.monotonic() - t0
        logger.info(
            "Edge TTS: voice list OK in %.2fs (%d API rows, %d voices, %d skipped)",
            elapsed,
            len(raw_list),
            len(out),
            skipped,
        )

        _voices_cache = out
        return out


class EdgeTts:
    """Synthesize speech via `edge-tts` (returns MP3 bytes)."""

    ENGINE_ID: Final[str] = "edge"

    def __init__(self, voice: str, *, rate: str | None = None, volume: str | None = None) -> None:
        v = (voice or "").strip()
        if not v:
            raise ValueError("Edge voice is required")
        self._voice = v
        self._rate = rate
        self._volume = volume

    @property
    def voice(self) -> str:
        return self._voice

    async def synthesize(self, text: str) -> bytes:
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty TTS text")

        edge_tts = _import_edge_tts()
        kwargs: dict[str, object] = {"voice": self._voice}
        if self._rate is not None:
            kwargs["rate"] = self._rate
        if self._volume is not None:
            kwargs["volume"] = self._volume
        communicate = edge_tts.Communicate(stripped, **kwargs)

        chunks: list[bytes] = []
        async for ev in communicate.stream():
            if not isinstance(ev, dict):
                continue
            if ev.get("type") != "audio":
                continue
            data = ev.get("data", b"")
            if isinstance(data, (bytes, bytearray)) and data:
                chunks.append(bytes(data))

        out = b"".join(chunks)
        if not out:
            raise ValueError("Edge returned empty audio")
        return out

    async def aclose(self) -> None:
        return
