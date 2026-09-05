from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from typing import Any

import numpy as np

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
        self._backoff_stage: int = 0  # 0=healthy, 1=30s, 2=2m, 3=5m
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
        # Rate-limit: enforce minimum interval since last request
        now = time.monotonic()
        wait = self._min_interval_sec - (now - self._last_request_time)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_time = time.monotonic()

        # If we have a fallback and we're in a bad backoff state, try fallback immediately
        if self._backoff_stage >= 3 and self._fallback_tts is not None:
            logger.warning(
                "ReSpeecher in severe backoff (%d stages); falling back to engine %s",
                self._backoff_stage,
                getattr(self._fallback_tts, "ENGINE_ID", "unknown"),
            )
            return await self._fallback_tts.synthesize(text)

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
            # print("Запит відправлено, збираємо Float32 PCM...")  # debug

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

            # If we never received any chunks, something went wrong
            if not float32_chunks:
                # Check if it was a close/error code
                # Codes 1008 (Policy Violation), 1011 (Internal Server Error),
                # 429 (Too Many Requests), 403 (Forbidden) should trigger backoff
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
            # logger.info("ReSpeecher: generated %d bytes WAV", len(wav_bytes))

            # Success: reset failure counter
            self._consecutive_failures = 0
            self._backoff_stage = 0

            return wav_bytes

        except Exception as e:
            # Track failure and apply exponential backoff
            self._consecutive_failures += 1
            logger.warning(
                "ReSpeecher synthesize error (failure #%d): %s",
                self._consecutive_failures,
                e,
                exc_info=True,
            )

            # Determine backoff stage based on consecutive failures
            if self._consecutive_failures >= 3:
                if self._backoff_stage == 0:
                    self._backoff_stage = 1  # First failure -> 30s pause
                elif self._backoff_stage == 1:
                    self._backoff_stage = 2  # Second -> 2 min
                elif self._backoff_stage == 2:
                    self._backoff_stage = 3  # Third -> 5 min

                # If we have a fallback engine, use it after backoff stages
                if self._fallback_tts is not None and self._backoff_stage >= 3:
                    logger.info(
                        "Switching to fallback TTS engine after %d ReSpeecher failures",
                        self._consecutive_failures,
                    )
                    return await self._fallback_tts.synthesize(text)
                else:
                    # Wait according to backoff stage before retry
                    # (caller should respect this, but we log the wait time)
                    wait_secs = [0, 30, 120, 300][self._backoff_stage]
                    logger.info(
                        "ReSpeecher backoff stage %d: waiting %.1fs before next attempt",
                        self._backoff_stage,
                        wait_secs,
                    )
            elif self._consecutive_failures == 1:
                # First failure: brief pause, then try fallback if available
                if self._fallback_tts is not None:
                    logger.info(
                        "First ReSpeecher failure; attempting fallback TTS",
                    )
                    return await self._fallback_tts.synthesize(text)

            # Re-raise so caller can decide (engine manager will handle backoff/switch)
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
        """Return True if the engine is not in a backoff penalty stage."""
        return self._backoff_stage == 0


class RandomizedReSpeecherTts:
    """ReSpeecher TTS wrapper that randomly selects a voice for each synthesis."""

    ENGINE_ID: str = "respeecher-random"

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

        # If we have a fallback and random voice, synthesize with random voice
        voice = self.voice

        # Validate voice is in our supported list
        if voice not in REPEECHER_VOICES:
            logger.warning(
                "ReSpeecher random voice %s not in supported list; defaulting to %s",
                voice,
                self.DEFAULT_VOICE_ID,
            )
            voice = self.DEFAULT_VOICE_ID

        # Use the ReSpeecherTts implementation with the randomly selected voice
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
