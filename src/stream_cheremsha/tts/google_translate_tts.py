from __future__ import annotations

import asyncio
import time
from typing import Final

import httpx

from stream_cheremsha.audio.tempo import apply_speed_to_audio
from stream_cheremsha.config.constants import TTS_MIN_INTERVAL_SEC

_TRANSLATE_TTS_URL: Final[str] = "https://translate.google.com/translate_tts"
_UA: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class GoogleTranslateTts:
    """Unofficial Google Translate TTS (uk-UA)."""

    ENGINE_ID: Final[str] = "google"

    def __init__(
        self,
        language: str = "uk-UA",
        min_interval_sec: float = TTS_MIN_INTERVAL_SEC,
        rate_percent: int = 100,
    ) -> None:
        self._language = language
        self._min_interval = min_interval_sec
        # 100 = normal speed; Google has no native rate control, so speed is applied via ffmpeg.
        self._rate_percent = max(50, min(200, int(rate_percent)))
        self._client = httpx.AsyncClient(
            headers={"User-Agent": _UA},
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )
        self._lock = asyncio.Lock()
        self._last_end = 0.0

    @property
    def language(self) -> str:
        return self._language

    @property
    def rate_percent(self) -> int:
        return self._rate_percent

    async def aclose(self) -> None:
        await self._client.aclose()

    async def synthesize(self, text: str) -> bytes:
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty TTS text")

        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_end)
            if wait > 0:
                await asyncio.sleep(wait)
            params = {
                "ie": "UTF-8",
                "tl": self._language,
                "client": "tw-ob",
                "q": stripped,
            }
            response = await self._client.get(_TRANSLATE_TTS_URL, params=params)
            self._last_end = time.monotonic()

        if response.status_code != 200:
            raise ValueError(f"TTS HTTP {response.status_code}")

        data = response.content
        if not data:
            raise ValueError("empty TTS response body")
        if self._rate_percent != 100:
            data = await asyncio.to_thread(
                apply_speed_to_audio,
                data,
                self._rate_percent / 100.0,
            )
        return data
