from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import httpx

from stream_cheremsha import l10n
from stream_cheremsha.config.constants import CHAT_QUEUE_MAX, TTS_QUEUE_MAX
from stream_cheremsha.domain.models import ChatMessage
from stream_cheremsha.domain.protocols import AudioSink, TextToSpeech
from stream_cheremsha.pipeline.chunking import chunk_text, merge_short_subchunks
from stream_cheremsha.pipeline.filters import filter_for_tts

logger = logging.getLogger(__name__)


class StreamCoordinator:
    """Bounded chat → filter → chunk → TTS → audio pipeline."""

    def __init__(
        self,
        tts: TextToSpeech,
        audio_sink: AudioSink,
        on_chat: Callable[[ChatMessage], None],
        on_status: Callable[[str], None],
        should_tts: Callable[[ChatMessage], bool] | None = None,
        get_locale: Callable[[], str] | None = None,
    ) -> None:
        self._tts = tts
        self._sink = audio_sink
        self._on_chat = on_chat
        self._on_status = on_status
        self._should_tts = should_tts or (lambda _msg: True)
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self.chat_in: asyncio.Queue[ChatMessage] = asyncio.Queue(maxsize=CHAT_QUEUE_MAX)
        self.tts_jobs: asyncio.Queue[str] = asyncio.Queue(maxsize=TTS_QUEUE_MAX)
        self._running = False
        self._ingest_task: asyncio.Task[None] | None = None
        self._tts_task: asyncio.Task[None] | None = None

    def _status(self, msg: str) -> None:
        self._on_status(msg)

    def set_tts(self, tts: TextToSpeech) -> None:
        """Swap the TTS backend while workers keep running."""
        self._tts = tts

    def set_should_tts(self, predicate: Callable[[ChatMessage], bool]) -> None:
        """Swap the predicate used to route chat into TTS."""
        self._should_tts = predicate

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
        self._tts_task = asyncio.create_task(self._tts_loop(), name="cheremsha-tts")

    async def stop_workers(self) -> None:
        self._running = False
        tasks = [t for t in (self._ingest_task, self._tts_task) if t is not None]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._ingest_task = None
        self._tts_task = None
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

    def clear_queues(self) -> None:
        """Drop pending chat and TTS work items (does not stop an in-flight TTS synth)."""
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

    async def flush_tts(self) -> None:
        """Stop in-flight TTS task, drop queues, and resume workers if running."""
        self.clear_queues()
        t = self._tts_task
        if t is None or t.done():
            return
        t.cancel()
        await asyncio.gather(t, return_exceptions=True)
        if self._running:
            self._tts_task = asyncio.create_task(self._tts_loop(), name="cheremsha-tts")

    async def _ingest_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self.chat_in.get(), timeout=0.35)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            if not self._should_tts(msg):
                continue
            text = filter_for_tts(msg)
            if text is None:
                continue
            for chunk in merge_short_subchunks(chunk_text(text)):
                if not self._running:
                    break
                try:
                    self.tts_jobs.put_nowait(chunk)
                except asyncio.QueueFull:
                    self._status(l10n.tr(self._get_locale(), "coord.tts_queue_full"))
                    break

    async def _tts_loop(self) -> None:
        while self._running:
            try:
                chunk = await asyncio.wait_for(self.tts_jobs.get(), timeout=0.35)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            try:
                audio = await self._tts.synthesize(chunk)
                await self._sink.play_mp3(audio)
            except OSError as e:
                logger.warning("Audio playback failed: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.audio_error", err=str(e)))
            except httpx.HTTPError as e:
                logger.warning("TTS HTTP error: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_http_error", err=str(e)))
            except ValueError as e:
                logger.warning("TTS error: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_error", err=str(e)))
            except Exception as e:
                logger.warning("TTS failed: %s", e)
                self._status(l10n.tr(self._get_locale(), "coord.tts_error", err=str(e)))
