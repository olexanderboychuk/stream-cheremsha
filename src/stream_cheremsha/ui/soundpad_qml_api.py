from __future__ import annotations

import asyncio
import copy
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QObject,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QFileDialog, QWidget

from stream_cheremsha import l10n
from stream_cheremsha.soundpad.models import (
    ALLOWED_AUDIO_SUFFIXES,
    PlaybackMode,
    SoundEntry,
    normalize_hotkey,
)

logger = logging.getLogger(__name__)
_MAX_BYTES = 200 * 1024 * 1024

_LIBRARY_L10N_KEYS = (
    "button",
    "title",
    "subtitle",
    "add",
    "added",
    "loading",
    "error_title",
    "retry",
    "empty_title",
    "page",
    "prev",
    "next",
)


def file_url_to_path(file_url: str) -> Path | None:
    s = str(file_url or "").strip()
    if not s:
        return None
    if s.startswith("file://"):
        try:
            p = unquote(urlparse(s).path)
            return Path(p)
        except (ValueError, OSError):
            return None
    return Path(s)


def _loop_running() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


class SoundpadQmlApi(QObject):
    soundsChanged = Signal()
    nowPlayingChanged = Signal(str, float, float)
    hotkeyConflict = Signal(str, str)
    importNeeded = Signal(str)
    stringsChanged = Signal()  # locale changed; QML re-reads libraryStrings

    def __init__(self, *, store, engine, hotkeys, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._engine = engine
        self._hotkeys = hotkeys
        self._meta_tasks: set[asyncio.Task] = set()
        try:
            self._hotkeys.hotkeyPressed.connect(self._on_hotkey_pressed)
        except RuntimeError:
            pass
        try:
            self._hotkeys.hotkeyReleased.connect(self._on_hotkey_released)
        except RuntimeError:
            pass
        # Now-playing position ticker: 250 ms, only runs while a sound is active.
        self._np_timer = QTimer(self)
        self._np_timer.setInterval(250)
        try:
            self._np_timer.timeout.connect(self._tick_now_playing)
            self._engine.playbackStarted.connect(self._on_playback_started)
            self._engine.playbackFinished.connect(self._on_playback_finished)
        except RuntimeError:
            pass
        self._locale = l10n.normalize_locale(l10n.DEFAULT_LOCALE)

    def _on_hotkey_pressed(self, sound_id: str) -> None:
        try:
            e = self._store.get(sound_id)
            if e is not None and e.playback_mode == PlaybackMode.HOLD:
                # Arm BEFORE playing: a short clip may finish (and must
                # replay) before any other event runs. UI clicks don't arm:
                # a card click on a hold sound is a single shot.
                try:
                    self._engine.set_hold(sound_id, True)
                except (AttributeError, RuntimeError):
                    pass
            self.playSound(sound_id)
        except (RuntimeError, ValueError, OSError) as e:
            logger.debug("hotkey play failed: %s", e)

    def _on_hotkey_released(self, sound_id: str) -> None:
        """Hotkey physically released: end a hold-to-play loop, if any.

        Other modes intentionally ignore releases: a tapped hotkey must play
        the full clip (stopping it on key-up would cut every quick tap).
        """
        try:
            e = self._store.get(sound_id)
            if e is None or e.playback_mode != PlaybackMode.HOLD:
                return
            self._engine.set_hold(sound_id, False)
        except (AttributeError, RuntimeError):
            return
        try:
            self.stopSound(sound_id)
        except (RuntimeError, ValueError, OSError) as e:
            logger.debug("hotkey release stop failed: %s", e)

    def _on_playback_started(self, _sound_id: str) -> None:
        if self._engine.active_ids():
            self._np_timer.start()

    def _on_playback_finished(self, _sound_id: str) -> None:
        if not self._engine.active_ids():
            self._np_timer.stop()

    def _tick_now_playing(self) -> None:
        for sid in self._engine.active_ids():
            try:
                position = float(self._engine.position_of(sid))
            except (AttributeError, RuntimeError):
                continue
            entry = self._store.get(sid)
            duration = float(entry.duration_sec or 0.0) if entry is not None else 0.0
            self.nowPlayingChanged.emit(sid, position, duration)

    def _payload(self) -> list[dict]:
        from stream_cheremsha.soundpad.store import _entry_to_dict

        playing = set(self._engine.active_ids()) if self._engine else set()
        out = []
        for e in self._store.list_all():
            d = _entry_to_dict(e)
            d["playing"] = e.id in playing
            d["broken"] = not Path(e.file_path).is_file()
            out.append(d)
        return out

    @Slot(result=str)
    def soundsJson(self) -> str:
        return json.dumps(self._payload(), ensure_ascii=False)

    def _owner_of(self, combo: str, exclude: str = "") -> str | None:
        for sid, hk in self._hotkeys.list_hotkeys().items():
            if hk == combo and sid != exclude:
                return sid
        return None

    def _validate_file(self, p: Path | None) -> str:
        if p is None or not p.is_file():
            return "missing file"
        if p.suffix.lower() not in ALLOWED_AUDIO_SUFFIXES:
            return f"unsupported format {p.suffix}"
        try:
            size = p.stat().st_size
        except OSError:
            return "unreadable file"
        if size <= 0 or size > _MAX_BYTES:
            return "bad file size"
        return ""

    def _compute_metadata(self, path: Path) -> tuple[tuple[float, ...], float]:
        from stream_cheremsha.soundpad.waveform import extract_waveform_peaks, probe_duration_sec

        peaks = tuple(extract_waveform_peaks(path, 64))
        dur = float(probe_duration_sec(path))
        return peaks, dur

    def _apply_metadata(self, sound_id: str, path: Path) -> None:
        try:
            peaks, dur = self._compute_metadata(path)
        except (RuntimeError, OSError, ValueError):
            return
        e = self._store.get(sound_id)
        if e is None:
            return
        nxt = copy.deepcopy(e)
        nxt.waveform_peaks = tuple(peaks)
        nxt.duration_sec = dur
        if not self._store.upsert(nxt):
            self.soundsChanged.emit()

    async def _apply_metadata_async(self, sound_id: str, path: Path) -> None:
        try:
            peaks, dur = await asyncio.to_thread(self._compute_metadata, path)
        except (RuntimeError, OSError, ValueError):
            return
        e = self._store.get(sound_id)
        if e is None:
            return
        nxt = copy.deepcopy(e)
        nxt.waveform_peaks = tuple(peaks)
        nxt.duration_sec = dur
        if not self._store.upsert(nxt):
            self.soundsChanged.emit()

    def _schedule_metadata(self, sound_id: str, path: Path) -> None:
        if _loop_running():
            t = asyncio.get_running_loop().create_task(self._apply_metadata_async(sound_id, path))
            self._meta_tasks.add(t)
            t.add_done_callback(lambda tt: self._meta_tasks.discard(tt))
        else:
            # No running loop (unit tests): compute inline.
            self._apply_metadata(sound_id, path)

    @Property("QVariantMap", notify=stringsChanged)
    def libraryStrings(self) -> dict[str, str]:  # noqa: ANN201 - PySide pattern
        out = {}
        for short in _LIBRARY_L10N_KEYS:
            try:
                out[short] = l10n.tr(self._locale, f"soundpad.library.{short}")
            except KeyError:
                out[short] = ""
        return out

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        k = (key or "").strip()
        if not k:
            return ""
        try:
            return l10n.tr(self._locale, k)
        except KeyError:
            return k

    def set_locale(self, locale: str) -> None:
        nl = l10n.normalize_locale(locale)
        if nl == self._locale:
            return
        self._locale = nl
        self.stringsChanged.emit()

    @Slot(str, str, str, str, float, str, result=str)
    def addSound(
        self, fileUrl: str, name: str, category: str, hotkey: str, volume: float, mode: str
    ) -> str:
        p = file_url_to_path(fileUrl)
        err = self._validate_file(p)
        if err:
            logger.warning("soundpad import rejected: %s", err)
            return ""
        assert p is not None
        try:
            kind = PlaybackMode(str(mode or "restart"))
        except ValueError:
            kind = PlaybackMode.RESTART
        sid = f"sp-{uuid.uuid4().hex[:8]}"
        entry = SoundEntry(
            id=sid,
            name=(name or p.stem).strip()[:80] or p.stem,
            file_path=str(p),
            category=(category or "Custom").strip() or "Custom",
            hotkey=normalize_hotkey(hotkey or ""),
            volume=max(0.0, min(1.0, float(volume if volume else 1.0))),
            playback_mode=kind,
            cooldown_sec=0.0,
            triggers=(),
            waveform_peaks=(),
            duration_sec=0.0,
            play_count=0,
            last_played_at="",
            order=self._store.next_order(),
        )
        errs = self._store.upsert(entry)
        if errs:
            return ""
        if entry.hotkey and not self._hotkeys.register_hotkey(sid, entry.hotkey):
            entry.hotkey = ""
            self._store.upsert(entry)
        self.soundsChanged.emit()
        self._schedule_metadata(sid, p)
        return sid

    @Slot(str, result=str)
    def hotkeyOwnerName(self, combo: str) -> str:
        """Display name of the sound owning ``combo`` (live conflict check).

        Returns "" when the combo is free/invalid — used by the add dialog
        to warn before saving instead of silently dropping the hotkey.
        """
        norm = normalize_hotkey(combo or "")
        if not norm:
            return ""
        owner = self._owner_of(norm)
        if owner is None:
            return ""
        e = self._store.get(owner)
        return str(e.name or owner) if e is not None else owner

    def _emit_sounds_changed_soon(self) -> None:
        """Refresh the grid UI without delaying audible output.

        Full rebuilds cost tens of ms and latency-critical emits run
        synchronously on the GUI thread BEFORE the playback task gets its
        first step — every ms delays the sound 1:1. A zero-delay singleShot
        lets the audio task run first (the QML debouncer coalesces bursts
        anyway). Falls back to synchronous emit with no event loop.
        """
        if QCoreApplication.instance() is None:
            self.soundsChanged.emit()
        else:
            QTimer.singleShot(0, self.soundsChanged.emit)

    @Slot(str, str, result=bool)
    def updateSoundJson(self, sound_id: str, patch_json: str) -> bool:
        cur = self._store.get(sound_id)
        if cur is None:
            return False
        try:
            patch = json.loads(patch_json or "{}")
        except ValueError:
            return False
        nxt = copy.deepcopy(cur)
        for k in (
            "name",
            "category",
            "hotkey",
            "volume",
            "cooldown_sec",
            "playback_mode",
            "enabled",
        ):
            if k in patch:
                setattr(nxt, k, patch[k])
        try:
            nxt.hotkey = normalize_hotkey(str(nxt.hotkey or ""))
            nxt.volume = max(0.0, min(1.0, float(nxt.volume)))
            nxt.cooldown_sec = max(0.0, float(nxt.cooldown_sec))
            if isinstance(nxt.playback_mode, str):
                nxt.playback_mode = PlaybackMode(str(nxt.playback_mode))
        except (ValueError, TypeError):
            return False
        # Conflict check BEFORE persisting so the store never holds a hotkey
        # that another sound owns.
        if "hotkey" in patch and nxt.hotkey:
            owner = self._owner_of(nxt.hotkey, exclude=sound_id)
            if owner is not None:
                self.hotkeyConflict.emit(sound_id, owner)
                return False
        if self._store.upsert(nxt):
            return False
        if "hotkey" in patch:
            if nxt.hotkey:
                if not self._hotkeys.register_hotkey(sound_id, nxt.hotkey):
                    cleared = copy.deepcopy(nxt)
                    cleared.hotkey = ""
                    self._store.upsert(cleared)
            else:
                self._hotkeys.clear_hotkey(sound_id)
        self.soundsChanged.emit()
        return True

    @Slot(str, result=bool)
    def removeSound(self, sound_id: str) -> bool:
        self._hotkeys.clear_hotkey(sound_id)
        ok = self._store.remove(sound_id)
        if ok:
            self.soundsChanged.emit()
        return ok

    @Slot(str, result=str)
    def duplicateSound(self, sound_id: str) -> str:
        dup = self._store.duplicate(sound_id)
        if dup is None:
            return ""
        self.soundsChanged.emit()
        return dup.id

    @Slot(str)
    def playSound(self, sound_id: str) -> None:
        e = self._store.get(sound_id)
        if e is None or not e.enabled:
            return
        try:
            data = Path(e.file_path).read_bytes()
        except OSError as ex:
            logger.warning("soundpad missing file %s: %s", sound_id, ex)
            return
        try:
            result = self._engine.play(e, data)
        except (RuntimeError, OSError) as ex:
            logger.warning("soundpad play failed %s: %s", sound_id, ex)
            return
        if result in ("PLAYING", "QUEUED"):
            e.play_count += 1
            e.last_played_at = datetime.now(UTC).isoformat(timespec="seconds")
            self._store.upsert(e)
        self._emit_sounds_changed_soon()

    @Slot(str)
    def stopSound(self, sound_id: str) -> None:
        self._engine.stop(sound_id)
        self._emit_sounds_changed_soon()

    @Slot()
    def stopAll(self) -> None:
        self._engine.stop_all()
        self._emit_sounds_changed_soon()

    @Slot(str, str, result=str)
    def assignHotkey(self, sound_id: str, combo: str) -> str:
        norm = normalize_hotkey(combo)
        if not norm:
            return "error:empty"
        owner = self._owner_of(norm, exclude=sound_id)
        if owner is not None:
            return f"conflict:{owner}"
        if not self._hotkeys.register_hotkey(sound_id, norm):
            return "error:backend rejected"
        e = self._store.get(sound_id)
        if e is not None:
            e.hotkey = norm
            self._store.upsert(e)
        self.soundsChanged.emit()
        return "ok"

    @Slot(str, result=bool)
    def clearHotkey(self, sound_id: str) -> bool:
        self._hotkeys.clear_hotkey(sound_id)
        e = self._store.get(sound_id)
        if e is not None and e.hotkey:
            e.hotkey = ""
            self._store.upsert(e)
        self.soundsChanged.emit()
        return True

    @Slot(float)
    def setGlobalVolume(self, v: float) -> None:
        self._store.set_global_volume(float(v))
        self._engine.set_global_volume(float(v))

    @Slot(str)
    def setOutputDevice(self, desc: str) -> None:
        self._engine.set_output_device(str(desc or ""))

    @Slot(result=str)
    def outputDevices(self) -> str:
        return json.dumps(self._engine.list_output_devices(), ensure_ascii=False)

    @Slot(bool)
    def setMonitor(self, b: bool) -> None:
        self._engine.set_monitor(bool(b))
        self._store.set_monitor(bool(b))

    @Slot(bool)
    def setStreamOut(self, b: bool) -> None:
        self._engine.set_stream_out(bool(b))
        self._store.set_stream_out(bool(b))

    @Slot(result=str)
    def globalStateJson(self) -> str:
        state = {
            "volume": float(self._store.global_volume()),
            "output_device": str(self._engine.output_device() or ""),
            "monitor": bool(self._store.monitor()),
            "stream_out": bool(self._store.stream_out()),
        }
        return json.dumps(state, ensure_ascii=False)

    @Slot(result=str)
    def pickAudioFile(self) -> str:
        """Native system picker for an audio clip; file:// URL or "".

        Same convention as the actions API pickers: Python QFileDialog with
        the main window as parent, so the OS-native dialog appears instead
        of the QML fallback.
        """
        parent = self.parent()
        if not isinstance(parent, QWidget):
            parent = None
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Оберіть аудіофайл",
            "",
            "Аудіо (*.mp3 *.wav *.ogg);;MP3 (*.mp3);;WAV (*.wav);;OGG (*.ogg)",
        )
        if not path:
            return ""
        return QUrl.fromLocalFile(path).toString()

    @Slot(str, result=str)
    def importDroppedUrls(self, urls_json: str) -> str:
        try:
            urls = json.loads(urls_json or "[]")
        except ValueError:
            return "[]"
        first: list[str] = []
        for u in urls if isinstance(urls, list) else []:
            p = file_url_to_path(str(u))
            if p is not None and p.suffix.lower() in ALLOWED_AUDIO_SUFFIXES and p.is_file():
                first.append(str(u))
        if first:
            self.importNeeded.emit(first[0])
        return json.dumps(first, ensure_ascii=False)
