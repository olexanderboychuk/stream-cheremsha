from __future__ import annotations

import asyncio
import logging
import time

from PySide6.QtCore import QObject, Signal

from stream_cheremsha.soundpad.models import PlaybackMode, SoundEntry

logger = logging.getLogger(__name__)


class SoundpadAudioEngine(QObject):
    playbackStarted = Signal(str)
    playbackFinished = Signal(str)
    duckingChanged = Signal(bool)

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
            t = asyncio.get_running_loop().create_task(self._run(entry, bytes(audio_bytes), vol))
            self._tasks.add(t)
            t.add_done_callback(lambda tt: self._tasks.discard(tt))
        else:
            # No running loop (unit tests): record intent, finish immediately.
            self._finish(entry.id)
        return "PLAYING"

    def stop(self, sound_id: str) -> None:
        self._queues.pop(sound_id, None)
        if sound_id in self._playing:
            self._finish(sound_id)

    def stop_all(self) -> None:
        self._queues.clear()
        for sid in sorted(self._playing):
            self._finish(sid)

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
