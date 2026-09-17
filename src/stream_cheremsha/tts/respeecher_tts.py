from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from typing import Any

from stream_cheremsha.domain.protocols import TextToSpeech

logger = logging.getLogger(__name__)

# 13 Ukrainian voices from specification
REPEECHER_VOICES: dict[str, str] = {
    "olesia-conversation": "Олеся (розмова)",
    "olesia-media": "Олеся (медіа)",
    "olesia-announcement": "Олеся (оголошення)",
    "oleksandr-radio": "Олександр (радіо)",
    "oleksandr-commercial": "Олександр (комерційний)",
    "kseniia-conversation": "Ксенія (розмова)",
    "roksolana-conversation": "Роксолана (розмова)",
    "yevhen-commercial": "Євген (комерційний)",
    "yevhen-audiobook": "Євген (аудіокнига)",
    "dmytro-conversation": "Дмитро (розмова)",
    "ihoreo-media": "Ігор (медіа)",
    "ihoreo-conversation": "Ігор (розмова)",
    "mariia-audiobook": "Марія (аудіокнига)",
}

# ReSpeecher WebSocket configuration
WSS_URL: str = "wss://space.respeecher.com/v1/public/tts/ua-rt/tts/websocket?source=lp"

# Required HTTP headers for ReSpeecher API
HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://respeecher.com",
    "Host": "space.respeecher.com",
    "Referer": "https://respeecher.com/",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8",
}

# Text limit per request
MAX_CHARS: int = 450

# Audio configuration (matches ReSpeecher Space RT defaults)
SAMPLE_RATE: int = 22050  # Can be changed to 24000 or 44100 if needed
CHANNELS: int = 1  # Mono


class ReSpeecherVoice:
    """Voice descriptor for ReSpeecher."""

    __slots__ = ("id", "label")

    def __init__(self, id: str, label: str) -> None:
        self.id = id
        self.label = label


class ReSpeecherTts:
    """ReSpeecher Text-To-Speech via WebSocket.

    Follows the TextToSpeech protocol. Per-request WebSocket lifecycle:
      open -> send payload -> collect Float32 chunks -> close.
    Never keep the socket open indefinitely to avoid server suspicion.
    """

    # Engine identifier for protocol and settings persistence
    ENGINE_ID: str = "respeecher"

    # Default voice for Ukrainian; can be overridden per-language in settings
    DEFAULT_VOICE_ID: str = "olesia-conversation"

    def __init__(
        self,
        voice: str = DEFAULT_VOICE_ID,
        *,
        rate_percent: int = 100,
        fallback_tts: TextToSpeech | None = None,
        min_interval_sec: float = 0.4,
    ) -> None:
        # Validate voice exists in our supported list
        if voice not in REPEECHER_VOICES:
            logger.warning(
                "ReSpeecher voice %s not in supported list; defaulting to %s",
                voice,
                self.DEFAULT_VOICE_ID,
            )
            voice = self.DEFAULT_VOICE_ID
        self._voice = voice
        self._rate_percent = max(50, min(200, rate_percent))
        self._fallback_tts = fallback_tts
        self._min_interval_sec = min_interval_sec

        # State tracking
        self._consecutive_failures: int = 0
        # Monotonic timestamp after which Respeecher may be retried (0 = ready immediately).
        # Using time-based recovery instead of permanent stage locks so a brief
        # connectivity blip on Windows doesn't disable Respeecher for the whole session.
        self._backoff_until: float = 0.0
        self._last_request_time: float = 0.0

        # Build voice descriptor objects
        self._voice_obj = ReSpeecherVoice(id=voice, label=REPEECHER_VOICES[voice])

    def voice(self) -> str:
        """Return the current voice ID."""
        return self._voice

    def rate_percent(self) -> int:
        """Return the current rate percent (50-200)."""
        return self._rate_percent

    # ------------------------------------------------------------------
    # Protocol interface
    # ------------------------------------------------------------------

    async def synthesize(self, text: str) -> bytes:
        """Return audio bytes (WAV, 22050 Hz, mono, Int16) for the given text."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty TTS text")

        # Enforce 450-char limit - split into sub-chunks if needed
        chunks_text: list[str] = []
        if len(stripped) <= MAX_CHARS:
            chunks_text = [stripped]
        else:
            # Simple word-level split respecting the limit
            words = stripped.split()
            current: list[str] = []
            for w in words:
                if len(" ".join(current + [w])) <= MAX_CHARS:
                    current.append(w)
                else:
                    if current:
                        chunks_text.append(" ".join(current))
                    current = [w]
            if current:
                chunks_text.append(" ".join(current))

        # If we have multiple chunks, synthesize sequentially with delays
        if len(chunks_text) == 1:
            return await self._synthesize_single(chunks_text[0])
        else:
            # Synthesize each chunk and concatenate WAV bytes
            all_frames: list[bytes] = []
            for i, chunk in enumerate(chunks_text):
                if i > 0:
                    # Random delay between 1.5-4.0s between chunks
                    await asyncio.sleep(random.uniform(1.5, 4.0))
                wav = await self._synthesize_single(chunk)
                all_frames.append(wav)
            # Concatenate all frames
            return b"".join(all_frames)

    async def _synthesize_single(self, text: str) -> bytes:
        """Synthesize a single chunk via the ReSpeecher WebSocket."""
        import numpy as np  # noqa: PLC0415 — ~43ms; runtime only, never at startup.

        # Rate-limit: enforce minimum interval since last request
        now = time.monotonic()
        wait = self._min_interval_sec - (now - self._last_request_time)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_time = time.monotonic()

        # Time-based backoff: if we're still within a backoff window, use the
        # fallback engine instead of hammering Respeecher with doomed requests.
        # Unlike a permanent stage lock, this resets automatically once the
        # window expires — a brief connectivity blip on Windows won't disable
        # Respeecher for the whole session.
        remaining = self._backoff_until - time.monotonic()
        if remaining > 0:
            if self._fallback_tts is not None:
                logger.debug(
                    "ReSpeecher backoff active for %.0fs more; using fallback",
                    remaining,
                )
                return await self._fallback_tts.synthesize(text)
            # No fallback — wait out the backoff window, then try Respeecher again
            logger.info(
                "ReSpeecher backoff active for %.0fs more; waiting (no fallback configured)",
                remaining,
            )
            await asyncio.sleep(remaining)

        # Open WebSocket connection with full headers
        websocket: Any | None = None
        try:
            import websockets

            # Build payload per the spec example
            payload = {
                "transcript": text,
                "voice": {"id": self._voice},
                "sampling_params": {
                    "seed": None,
                    "frequency_penalty": 0,
                    "repetition_penalty": 1.25,
                    "presence_penalty": 0,
                    "temperature": 0.4,
                    "min_p": 0,
                    "top_k": -1,
                    "top_p": 0.8,
                },
                "recaptchaToken": "",
            }

            # Connect with additional headers - websockets library supports additional_headers
            extra_headers: list[tuple[str, str]] = []
            for k, v in HEADERS.items():
                extra_headers.append((k, v))

            websocket = await websockets.connect(
                WSS_URL,
                additional_headers=extra_headers,
            )

            # Send payload
            await websocket.send(json.dumps(payload))

            # Collect Float32 PCM chunks
            float32_chunks: list[np.ndarray] = []

            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                # Chunk of audio data
                if data.get("type") == "chunk":
                    try:
                        chunk_bytes = base64.b64decode(data["data"])
                        # Decode as Float32 (little-endian)
                        float_data = np.frombuffer(chunk_bytes, dtype=np.float32)
                        float32_chunks.append(float_data)
                    except Exception as e:
                        logger.debug("Failed to decode chunk: %s", e)

                # Done signal
                elif data.get("type") == "done" or data.get("done") is True:
                    break

            if not float32_chunks:
                logger.warning("ReSpeecher: no audio chunks received for text (len=%d)", len(text))
                raise RuntimeError("ReSpeecher: no audio data received")

            # Concatenate all Float32 arrays
            audio_float32 = np.concatenate(float32_chunks)

            # Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
            audio_int16 = np.clip(audio_float32 * 32767, -32768, 32767).astype(np.int16)

            # Write WAV bytes (mono, 22050 Hz, 16-bit PCM)
            import io
            import wave

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(2)  # 2 bytes = 16-bit Int
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(audio_int16.tobytes())

            wav_bytes = wav_buffer.getvalue()

            # Success: reset failure counter and backoff window
            self._consecutive_failures = 0
            self._backoff_until = 0.0

            return wav_bytes

        except Exception as e:
            self._consecutive_failures += 1
            logger.warning(
                "ReSpeecher synthesize error (failure #%d): %s",
                self._consecutive_failures,
                e,
            )

            # Exponential backoff schedule (seconds): 1 failure → 5s, 2 → 30s,
            # 3 → 2 min, 4+ → 5 min.  Each window expires on its own so the
            # engine recovers automatically without a restart.
            _BACKOFF_SCHEDULE = (5, 30, 120, 300)
            idx = min(self._consecutive_failures - 1, len(_BACKOFF_SCHEDULE) - 1)
            wait_secs = _BACKOFF_SCHEDULE[idx]
            self._backoff_until = time.monotonic() + wait_secs
            logger.info(
                "ReSpeecher backoff: %.0fs window set after failure #%d",
                wait_secs,
                self._consecutive_failures,
            )

            # Use fallback immediately for this request if available
            if self._fallback_tts is not None:
                logger.info("ReSpeecher: using fallback TTS for this request")
                return await self._fallback_tts.synthesize(text)

            # No fallback configured — re-raise so the coordinator can log it
            raise

        finally:
            # Always close the socket when done - never leave it open
            if websocket is not None:
                try:
                    await websocket.close()
                except Exception:
                    pass  # best-effort close

    async def aclose(self) -> None:
        """Release any network or native resources."""
        # WebSocket connections are per-request and closed in synthesize()
        # Any global cleanup can happen here later
        pass

    def is_healthy(self) -> bool:
        """Return True if the engine is not in an active backoff window."""
        return time.monotonic() >= self._backoff_until


class RandomizedReSpeecherTts:
    """ReSpeecher TTS wrapper that randomly selects a voice for each synthesis."""

    ENGINE_ID: str = "respeecher-random"
    DEFAULT_VOICE_ID: str = ReSpeecherTts.DEFAULT_VOICE_ID

    def __init__(
        self,
        *,
        rate_percent: int = 100,
        fallback_tts: TextToSpeech | None = None,
        min_interval_sec: float = 0.4,
    ) -> None:
        self._rate_percent = max(50, min(200, rate_percent))
        self._fallback_tts = fallback_tts
        self._min_interval_sec = min_interval_sec
        self._voices = list(REPEECHER_VOICES.keys())

    @property
    def voice(self) -> str:
        """Return a randomly selected voice ID."""
        return random.choice(self._voices)

    @property
    def rate_percent(self) -> int:
        """Return the current rate percent (50-200)."""
        return self._rate_percent

    async def synthesize(self, text: str) -> bytes:
        """Return audio bytes (WAV, 22050 Hz, mono, Int16) for the given text."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty TTS text")

        voice = self.voice
        if voice not in REPEECHER_VOICES:
            logger.warning(
                "ReSpeecher random voice %r not in supported list; defaulting to %r",
                voice,
                self.DEFAULT_VOICE_ID,
            )
            voice = self.DEFAULT_VOICE_ID

        # Delegate to a per-request ReSpeecherTts so the backoff state is
        # isolated per synthesis call and doesn't bleed across randomized voices.
        tts = ReSpeecherTts(
            voice=voice,
            rate_percent=self._rate_percent,
            fallback_tts=self._fallback_tts,
            min_interval_sec=self._min_interval_sec,
        )
        return await tts.synthesize(text)

    async def aclose(self) -> None:
        """Release any network or native resources."""
        pass

    def is_healthy(self) -> bool:
        """Return True if the engine is not in a backoff penalty stage."""
        return True

    def voice_static(self) -> str:
        """Return the default voice ID for this engine."""
        return self.DEFAULT_VOICE_ID
