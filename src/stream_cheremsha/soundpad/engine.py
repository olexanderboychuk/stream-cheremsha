from __future__ import annotations

import asyncio
import logging
import time

from PySide6.QtCore import QObject, Signal

from stream_cheremsha.soundpad.models import PlaybackMode, SoundEntry

logger = logging.getLogger(__name__)

_PREVIEW_PREFIX = "soundpad-preview:"


class SoundpadAudioEngine(QObject):
    playbackStarted = Signal(str)
    playbackFinished = Signal(str)
    duckingChanged = Signal(bool)
    previewFinished = Signal()  # a library preview ended naturally (not stopped)

    def __init__(self, sink=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sink = sink
        self._global_volume = 0.78
        self._monitor = True
        self._stream_out = True
        self._output_device = ""
        self._playing: set[str] = set()
        self._queues: dict[str, list[tuple[SoundEntry, bytes]]] = {}
        self._last_start: dict[str, float] = {}
        self._tasks: set[asyncio.Task] = set()
        # In-flight _run tasks per sound, so stop() can cancel the actual
        # audible playback instead of only clearing bookkeeping.
        self._play_tasks: dict[str, set[asyncio.Task]] = {}
        # Physically-held hotkeys per sound id (hold-to-play mode).
        self._held: set[str] = set()
        self._preview_tasks: set[asyncio.Task] = set()

    def set_hold(self, sound_id: str, held: bool) -> None:
        """Track whether a hold-mode hotkey is physically down."""
        if held:
            self._held.add(sound_id)
        else:
            self._held.discard(sound_id)

    def warmup(self) -> None:
        """Create the audio backend now, off the hotkey-press path.

        First-ever backend creation (FFmpeg plugin + players) costs 100ms+
        and must not happen between key-press and audible output. Idempotent
        and safe to call when audio is unavailable (logs and no-ops).
        """
        try:
            self._ensure_sink()
        except (RuntimeError, OSError) as e:
            logger.debug("soundpad sink warmup skipped: %s", e)

    def _spawn_run(self, entry: SoundEntry, data: bytes, vol: float) -> None:
        t = asyncio.get_running_loop().create_task(self._run(entry, bytes(data), vol))
        self._tasks.add(t)
        self._play_tasks.setdefault(entry.id, set()).add(t)

        def _drop(tt: asyncio.Task, _sid: str = entry.id) -> None:
            self._tasks.discard(tt)
            pending = self._play_tasks.get(_sid)
            if pending is not None:
                pending.discard(tt)
                if not pending:
                    self._play_tasks.pop(_sid, None)

        t.add_done_callback(_drop)

    def _ensure_sink(self):
        if self._sink is None:
            from stream_cheremsha.audio.qt_sink import QtAudioSink

            self._sink = QtAudioSink(self)
        ensure = getattr(self._sink, "ensure_ready", None)
        if callable(ensure):
            try:
                ensure()
            except RuntimeError:
                pass
        return self._sink

    def set_global_volume(self, v: float) -> None:
        self._global_volume = max(0.0, min(1.0, float(v)))

    def set_monitor(self, b: bool) -> None:
        self._monitor = bool(b)

    def set_stream_out(self, b: bool) -> None:
        self._stream_out = bool(b)

    def set_output_device(self, description: str) -> None:
        self._output_device = str(description or "")
        if self._sink is not None:
            fn = getattr(self._sink, "set_output_device_by_description", None)
            if callable(fn):
                try:
                    fn(self._output_device or None)
                except (RuntimeError, ValueError) as e:
                    logger.warning("soundpad output device failed: %s", e)

    def list_output_devices(self) -> list[str]:
        try:
            from PySide6.QtMultimedia import QMediaDevices

            return [d.description() for d in QMediaDevices.audioOutputs()]
        except (RuntimeError, ImportError) as e:
            logger.debug("output enumeration failed: %s", e)
            return []

    def is_playing(self, sound_id: str) -> bool:
        return sound_id in self._playing

    def active_ids(self) -> list[str]:
        return sorted(self._playing)

    def position_of(self, sound_id: str) -> float:
        """Elapsed seconds since this sound started (0.0 if not tracked)."""
        last = self._last_start.get(sound_id)
        if last is None:
            return 0.0
        return max(0.0, time.monotonic() - last)

    def output_device(self) -> str:
        return self._output_device

    def queued_count(self, sound_id: str) -> int:
        return len(self._queues.get(sound_id, []))

    def can_play(self, entry: SoundEntry, now: float | None = None) -> tuple[bool, float]:
        now = time.monotonic() if now is None else float(now)
        cd = max(0.0, float(entry.cooldown_sec or 0.0))
        last = self._last_start.get(entry.id, 0.0)
        wait = (last + cd) - now
        if wait > 0:
            return False, round(wait, 2)
        return True, 0.0

    def play(self, entry: SoundEntry, audio_bytes: bytes) -> str:
        if not entry.enabled or not bytes(audio_bytes or b""):
            return "BLOCKED"
        ok, _wait = self.can_play(entry)
        if not ok:
            return "COOLDOWN"
        mode = (
            entry.playback_mode
            if isinstance(entry.playback_mode, PlaybackMode)
            else PlaybackMode.RESTART
        )
        if mode == PlaybackMode.QUEUE and entry.id in self._playing:
            self._queues.setdefault(entry.id, []).append((entry, bytes(audio_bytes)))
            return "QUEUED"
        if mode in (PlaybackMode.RESTART, PlaybackMode.REPLACE):
            self.stop(entry.id)
        self._last_start[entry.id] = time.monotonic()
        self._playing.add(entry.id)
        self.playbackStarted.emit(entry.id)
        self.duckingChanged.emit(True)
        vol = max(0.0, min(1.0, float(entry.volume) * float(self._global_volume)))
        if _loop_running():
            self._spawn_run(entry, bytes(audio_bytes), vol)
        else:
            # No running loop (unit tests): record intent, finish immediately.
            self._finish(entry.id)
        return "PLAYING"

    def stop(self, sound_id: str) -> None:
        self._queues.pop(sound_id, None)
        # An explicit stop always wins over a held key: no resume until the
        # key is physically pressed again.
        self._held.discard(sound_id)
        # Cancel in-flight playback tasks (sinks without a per-voice stop API
        # halt via CancelledError unwinding through their cleanup).
        for t in list(self._play_tasks.pop(sound_id, set())):
            if not t.done():
                try:
                    t.cancel()
                except RuntimeError:
                    pass
        # Halt the audible voice on the sink. player.stop() drives the sink's
        # StoppedState handler, so the awaiting coroutine tears down cleanly
        # (disconnects, source reset, temp cleanup, player + dedupe release).
        # Other sounds' overlapping voices are untouched.
        stop_voice = getattr(self._sink, "stop_sfx_by_key_prefix", None)
        if callable(stop_voice):
            try:
                stop_voice(f"soundpad:{sound_id}:")
            except RuntimeError:
                pass
        if sound_id in self._playing:
            self._finish(sound_id)

    def play_preview(self, data: bytes) -> str:
        """Play raw audio as a one-shot library preview (restart semantics)."""
        if not bytes(data or b""):
            return "BLOCKED"
        self.stop_preview()
        vol = max(0.0, min(1.0, float(self._global_volume)))

        async def _run() -> None:
            cancelled = False
            try:
                sink = self._ensure_sink()
                fn = getattr(sink, "play_mp3_parallel_with_volume_deduped", None)
                if callable(fn):
                    await fn(data, vol, dedupe_key=_PREVIEW_PREFIX + "active")
                else:
                    await sink.play_mp3_with_volume(data, vol)
            except asyncio.CancelledError:
                cancelled = True
                raise
            except (RuntimeError, OSError) as e:
                logger.warning("soundpad preview failed: %s", e)
            finally:
                if not cancelled:
                    self.previewFinished.emit()

        if _loop_running():
            t = asyncio.get_running_loop().create_task(_run())
            self._preview_tasks.add(t)
            t.add_done_callback(self._preview_tasks.discard)
        # No running loop (unit tests): nothing audible; state stays consistent.
        return "PLAYING"

    def stop_preview(self) -> None:
        had = bool(self._preview_tasks)  # guard: don't touch the sink when idle
        for t in list(self._preview_tasks):
            if not t.done():
                try:
                    t.cancel()
                except RuntimeError:
                    pass
        self._preview_tasks.clear()
        if had:
            stop_voice = getattr(self._sink, "stop_sfx_by_key_prefix", None)
            if callable(stop_voice):
                try:
                    stop_voice(_PREVIEW_PREFIX)
                except RuntimeError:
                    pass

    def stop_all(self) -> None:
        self.stop_preview()
        self._queues.clear()
        for sid in sorted(set(self._playing) | set(self._play_tasks)):
            self.stop(sid)
        self._held.clear()

    async def _run(self, entry: SoundEntry, data: bytes, vol: float) -> None:
        try:
            sink = self._ensure_sink()
            fn = getattr(sink, "play_mp3_parallel_with_volume_deduped", None)
            if callable(fn):
                await fn(data, vol, dedupe_key=f"soundpad:{entry.id}:{entry.playback_mode.value}")
            else:
                await sink.play_mp3_with_volume(data, vol)
        except (RuntimeError, OSError) as e:
            logger.warning("soundpad playback failed for %s: %s", entry.id, e)
        finally:
            nxt = self._queues.get(entry.id)
            if nxt:
                nxt_entry, nxt_data = nxt.pop(0)
                self._last_start[entry.id] = time.monotonic()
                v2 = max(0.0, min(1.0, float(nxt_entry.volume) * float(self._global_volume)))
                t = asyncio.get_running_loop().create_task(self._run(nxt_entry, nxt_data, v2))
                self._tasks.add(t)
                t.add_done_callback(lambda tt: self._tasks.discard(tt))
            elif (
                entry.playback_mode
                if isinstance(entry.playback_mode, PlaybackMode)
                else PlaybackMode.RESTART
            ) == PlaybackMode.HOLD and entry.id in self._held:
                # Hold-to-play: key still down → repeat immediately (bypasses
                # cooldown so the loop is continuous; the initial press still
                # respects it). Volume is re-read for live slider changes.
                # stop()/release discards _held first, so this never fires
                # after an explicit stop.
                self._last_start[entry.id] = time.monotonic()
                v3 = max(0.0, min(1.0, float(entry.volume) * float(self._global_volume)))
                self._spawn_run(entry, data, v3)
            else:
                self._finish(entry.id)

    def _finish(self, sound_id: str) -> None:
        self._playing.discard(sound_id)
        self.playbackFinished.emit(sound_id)
        if not self._playing:
            self.duckingChanged.emit(False)


def _loop_running() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False
