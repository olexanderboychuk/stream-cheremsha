from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx

from stream_cheremsha import l10n
from stream_cheremsha.config.constants import AUDIO_QUEUE_MAX, CHAT_QUEUE_MAX, TTS_QUEUE_MAX
from stream_cheremsha.domain.models import ChatMessage
from stream_cheremsha.domain.protocols import AudioSink, TextToSpeech
from stream_cheremsha.pipeline.chunking import chunk_text, merge_short_subchunks
from stream_cheremsha.pipeline.filters import filter_for_tts

logger = logging.getLogger(__name__)


class StreamCoordinator:
    """Bounded chat → filter → chunk → TTS synthesis → audio playback pipeline."""

    def __init__(
        self,
        tts: TextToSpeech,
        audio_sink: AudioSink,
        on_chat: Callable[[ChatMessage], None],
        on_status: Callable[[str], None],
        should_tts: Callable[[ChatMessage], bool] | None = None,
        get_locale: Callable[[], str] | None = None,
        pre_tts: Callable[[str, str], Awaitable[str]] | None = None,
    ) -> None:
        self._tts = tts
        self._sink = audio_sink
        self._on_chat = on_chat
        self._on_status = on_status
        self._should_tts = should_tts or (lambda _msg: True)
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._pre_tts = pre_tts
        self.chat_in: asyncio.Queue[ChatMessage] = asyncio.Queue(maxsize=CHAT_QUEUE_MAX)
        self.tts_jobs: asyncio.Queue[str] = asyncio.Queue(maxsize=TTS_QUEUE_MAX)
        self.audio_jobs: asyncio.Queue[bytes] = asyncio.Queue(maxsize=AUDIO_QUEUE_MAX)
        self._running = False
        self._ingest_task: asyncio.Task[None] | None = None
        self._synth_task: asyncio.Task[None] | None = None
        self._play_task: asyncio.Task[None] | None = None

    @property
    def _tts_task(self) -> asyncio.Task[None] | None:
        """Compatibility property for legacy references to the synthesis task."""
        return self._synth_task

    def _status(self, msg: str) -> None:
        self._on_status(msg)

    def set_tts(self, tts: TextToSpeech) -> None:
        """Swap the TTS backend while workers keep running."""
        self._tts = tts

    def set_should_tts(self, predicate: Callable[[ChatMessage], bool]) -> None:
        """Swap the predicate used to route chat into TTS."""
        self._should_tts = predicate

    def set_pre_tts(self, fn: Callable[[str, str], Awaitable[str]] | None) -> None:
        """Optional async (filtered_text, author) -> text to enqueue for TTS (e.g. moderation)."""
        self._pre_tts = fn

    async def enqueue_chat(self, message: ChatMessage) -> None:
        try:
            self.chat_in.put_nowait(message)
        except asyncio.QueueFull:
            self._status(l10n.tr(self._get_locale(), "coord.chat_queue_full"))
            return
        self._on_chat(message)

    async def start_workers(self) -> None:
        if self._running:
            return
        self._running = True
        self._ingest_task = asyncio.create_task(self._ingest_loop(), name="cheremsha-ingest")
        self._synth_task = asyncio.create_task(self._synth_loop(), name="cheremsha-synth")
        self._play_task = asyncio.create_task(self._play_loop(), name="cheremsha-play")

    async def stop_workers(self) -> None:
        self._running = False
        tasks = [t for t in (self._ingest_task, self._synth_task, self._play_task) if t is not None]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._ingest_task = None
        self._synth_task = None
        self._play_task = None
        self.clear_queues()

    def clear_queues(self) -> None:
        """Drop pending chat, TTS text chunks, and synthesized audio clips."""
        while not self.chat_in.empty():
            try:
                self.chat_in.get_nowait()
            except asyncio.QueueEmpty:
                break
        while not self.tts_jobs.empty():
            try:
                self.tts_jobs.get_nowait()
            except asyncio.QueueEmpty:
                break
        while not self.audio_jobs.empty():
            try:
                self.audio_jobs.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def flush_tts(self) -> None:
        """Stop in-flight TTS synthesis and playback, drop queues, and resume workers if running."""
        self.clear_queues()
        tasks = [t for t in (self._synth_task, self._play_task) if t is not None and not t.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.clear_queues()
        if self._running:
            self._synth_task = asyncio.create_task(self._synth_loop(), name="cheremsha-synth")
            self._play_task = asyncio.create_task(self._play_loop(), name="cheremsha-play")

    async def _ingest_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self.chat_in.get(), timeout=0.35)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            try:
                if not self._should_tts(msg):
                    continue
                text = filter_for_tts(msg)
                if text is None:
                    continue
                if self._pre_tts is not None:
                    text = await self._pre_tts(text, msg.author)
                    text = (text or "").strip()
                    if not text:
                        continue
                chunks = merge_short_subchunks(chunk_text(text))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("TTS ingest failed for chat message: %s", e)
                continue
            for chunk in chunks:
                if not self._running:
                    break
                try:
                    self.tts_jobs.put_nowait(chunk)
                except asyncio.QueueFull:
                    self._status(l10n.tr(self._get_locale(), "coord.tts_queue_full"))
                    break

    async def _synth_loop(self) -> None:
        while self._running:
            try:
                chunk = await asyncio.wait_for(self.tts_jobs.get(), timeout=0.35)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            try:
                audio = await self._tts.synthesize(chunk)
            except httpx.HTTPError as e:
                logger.warning("TTS HTTP error: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_http_error", err=str(e)))
                continue
            except ValueError as e:
                logger.warning("TTS error: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_error", err=str(e)))
                continue
            except Exception as e:
                logger.warning("TTS failed: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_error", err=str(e)))
                continue

            if not audio:
                continue

            while self._running:
                try:
                    await asyncio.wait_for(self.audio_jobs.put(audio), timeout=0.35)
                    break
                except TimeoutError:
                    continue
                except asyncio.CancelledError:
                    raise

    async def _play_loop(self) -> None:
        while self._running:
            try:
                audio = await asyncio.wait_for(self.audio_jobs.get(), timeout=0.35)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            try:
                await self._sink.play_mp3(audio)
            except OSError as e:
                logger.warning("Audio playback failed: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.audio_error", err=str(e)))
            except Exception as e:
                logger.warning("Audio playback failed: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.audio_error", err=str(e)))
