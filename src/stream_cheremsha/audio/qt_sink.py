from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

logger = logging.getLogger(__name__)

# Qt6 Multimedia on PipeWire (pw_thread_loop_lock + protocol-native event
# handling) segfaults when two threads race inside backend creation, and can
# also crash on first QAudioOutput construction while the PipeWire registry is
# still changing. All QAudioOutput/QMediaPlayer constructions below are
# serialized through this lock so Python never has two concurrent contenders
# for the PipeWire thread loop. This cannot fix the upstream Qt/PipeWire bug
# itself (see note in ensure_ready), it only removes our own trigger.
_BACKEND_LOCK = threading.Lock()

# Google Translate MP3 is often very quiet; ffmpeg applies gain before playback.
_DEFAULT_TTS_GAIN_DB = 14
_ffmpeg_log_state = {"no_path_logged": False}


def _ffmpeg_run(
    data: bytes,
    audio_filter: str,
    *,
    encoding: str,
) -> bytes | None:
    """Run ffmpeg once. ``encoding`` is ``\"mp3\"`` (libmp3lame) or ``\"wav\"`` (pcm_s16le)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not data:
        return None
    if encoding == "mp3":
        tail = ["-codec:a", "libmp3lame", "-q:a", "3", "-f", "mp3", "pipe:1"]
    elif encoding == "wav":
        tail = ["-f", "wav", "-c:a", "pcm_s16le", "pipe:1"]
    else:
        return None

    # On Windows, a subprocess can momentarily steal focus by flashing a console window.
    # Hide the ffmpeg window to avoid focus loss in fullscreen games.
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-i",
                "pipe:0",
                "-af",
                audio_filter,
                *tail,
            ],
            input=data,
            capture_output=True,
            timeout=15,
            check=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
    except OSError as e:
        logger.debug("ffmpeg run failed: %s", e)
        return None
    if proc.returncode != 0 or not proc.stdout:
        logger.debug(
            "ffmpeg rc=%s enc=%s stderr=%r",
            proc.returncode,
            encoding,
            (proc.stderr or b"")[:300],
        )
        return None
    return proc.stdout


def _ffmpeg_try_filter_encodings(data: bytes, audio_filter: str) -> bytes | None:
    """Try mp3 (lame) then WAV (always available in typical ffmpeg builds)."""
    for enc in ("mp3", "wav"):
        out = _ffmpeg_run(data, audio_filter, encoding=enc)
        if out is not None:
            return out
    return None


def _try_louder_mp3(data: bytes, gain_db: int) -> bytes:
    """Return amplified audio bytes, or original ``data`` if ffmpeg cannot help."""
    if not data:
        return data
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        if not _ffmpeg_log_state["no_path_logged"]:
            logger.warning(
                "ffmpeg не знайдено у PATH — TTS без підсилення. "
                "Додайте ffmpeg до PATH для цього процесу (див. which ffmpeg у тому ж терміналі, "
                "звідки запускаєте додаток).",
            )
            _ffmpeg_log_state["no_path_logged"] = True
        return data

    g = max(0, min(36, int(gain_db)))
    # adelay=150|150: prepend 150 ms of silence before each TTS clip.
    # PipeWire (and some ALSA drivers) need ~100-200 ms to initialise the
    # output stream; without this padding the audio device "eats" the very
    # first word of every clip (e.g. "vault gifts are very expensive" starts
    # playing only from "gifts...").  The silence is inaudible and adds only
    # ~0.15 s per utterance — an acceptable trade-off.
    pre = "adelay=150|150"
    filters = (
        f"{pre},volume={g}dB",
        f"{pre},volume={g}dB,dynaudnorm=f=100:g=21:m=60.0",
        f"{pre},loudnorm=I=-14:LRA=11:TP=-1.5",
        f"{pre},volume={g + 8}dB",
    )
    for af in filters:
        out = _ffmpeg_try_filter_encodings(data, af)
        if out is not None:
            return out
    return data


def _try_apply_volume(data: bytes, linear: float) -> bytes:
    """Return ``data`` scaled by ``linear`` (0.0–1.0) gain, or original if ffmpeg can't help.

    Identity is returned by reference when ``linear`` is ~1.0 so callers can detect
    "no DSP needed" via ``out is data``. Returns a *new* bytes object on success,
    ``data`` itself when ffmpeg is unavailable.
    """
    if not data:
        return data
    v = max(0.0, min(1.0, float(linear)))
    if v >= 0.999:
        return data
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return data
    out = _ffmpeg_try_filter_encodings(data, f"volume={v:.3f}")
    return out if out is not None else data


def _write_temp_audio(data: bytes) -> Path:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        suffix = ".wav"
    else:
        suffix = ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, prefix="cheremsha_", delete=False) as f:
        f.write(data)
        return Path(f.name)


class QtAudioSink(QObject):
    """Sequential MP3/WAV playback via Qt Multimedia (temp file + QMediaPlayer)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # QtMultimedia backends (QMediaPlayer/QAudioOutput) cost ~130ms
        # (FFmpeg plugin load + audio device query) and are created lazily via
        # ensure_ready() — never during MainWindow construction. All runtime
        # entry points ensure them; pure setters work without backends.
        self._player: QMediaPlayer | None = None
        self._audio: QAudioOutput | None = None
        self._sfx_player: QMediaPlayer | None = None
        self._sfx_audio: QAudioOutput | None = None
        self._sfx_lock = asyncio.Lock()
        self._play_lock = asyncio.Lock()
        self._sound_dedupe_lock = asyncio.Lock()
        self._sound_dedupe_keys: set[str] = set()
        self._pending_fut: asyncio.Future[None] | None = None
        # Guard so StoppedState fired by setSource() doesn't prematurely resolve
        # _pending_fut before play() has been called (Qt fires StoppedState on
        # every setSource when the player transitions from its current state).
        self._tts_play_started: bool = False
        self._parallel_tasks: set[asyncio.Task[None]] = set()
        self._tts_gain_db = _DEFAULT_TTS_GAIN_DB
        self._pending_volume: float | None = None

    def ensure_ready(self) -> None:
        """Create QtMultimedia backends if needed. Idempotent; post-show only."""
        if self._player is not None and self._audio is not None:
            return
        # NOTE: first QAudioOutput construction can still SEGV inside
        # libpipewire-module-protocol-native (upstream Qt6/PipeWire race, not
        # catchable from Python). Serializing here removes concurrent creation
        # from our side; if the crash persists, workarounds are: update
        # pipewire + Qt6, or run with QT_MEDIA_BACKEND=gstreamer.
        with _BACKEND_LOCK:
            if self._player is not None and self._audio is not None:
                return
            player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            player.setAudioOutput(audio)
            player.errorOccurred.connect(self._on_player_error)
            player.mediaStatusChanged.connect(self._on_media_status)
            player.playbackStateChanged.connect(self._on_playback_state)
            self._player = player
            self._audio = audio

            # Separate dedicated SFX player + audio output so SFX never
            # hijacks self._audio or disrupts TTS playback.
            sfx_player = QMediaPlayer(self)
            sfx_audio = QAudioOutput(self)
            sfx_player.setAudioOutput(sfx_audio)
            self._sfx_player = sfx_player
            self._sfx_audio = sfx_audio

            if self._pending_volume is not None:
                audio.setVolume(self._pending_volume)
                self._pending_volume = None

    def set_tts_gain_db(self, db: int) -> None:
        """Base dB boost for ffmpeg TTS chain (0–36)."""
        self._tts_gain_db = max(0, min(36, int(db)))

    def set_output_device_by_description(self, description: str | None) -> None:
        """Match QAudioDevice.description(); None or empty keeps default."""
        if not description:
            return
        self.ensure_ready()
        if self._audio is None:
            return
        try:
            for dev in QMediaDevices.audioOutputs():
                if dev.description() == description:
                    self._audio.setDevice(dev)
                    if self._sfx_audio is not None:
                        self._sfx_audio.setDevice(dev)
                    return
            logger.warning("Audio device %r not found, using default", description)
        except Exception as e:
            logger.warning("Error matching audio device by description %r: %s", description, e)

    def set_volume(self, linear: float) -> None:
        v = max(0.0, min(1.0, float(linear)))
        if self._audio is None:
            self._pending_volume = v
            return
        self._audio.setVolume(v)

    def get_volume(self) -> float:
        if self._audio is None:
            return float(self._pending_volume) if self._pending_volume is not None else 1.0
        return float(self._audio.volume())

    @staticmethod
    def _safe_resolve_fut(
        fut: asyncio.Future[None] | None,
        *,
        exception: Exception | None = None,
    ) -> None:
        if fut is None or fut.done():
            return
        try:
            loop = fut.get_loop()
        except RuntimeError:
            return
        if loop.is_closed():
            return
        if exception is not None:
            loop.call_soon_threadsafe(
                lambda: None if fut.done() else fut.set_exception(exception),
            )
        else:
            loop.call_soon_threadsafe(
                lambda: None if fut.done() else fut.set_result(None),
            )

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        logger.warning("TTS QMediaPlayer error %s: %s", error, error_string)
        self._safe_resolve_fut(
            self._pending_fut,
            exception=RuntimeError(f"QMediaPlayer error {error!s}: {error_string}"),
        )

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._safe_resolve_fut(self._pending_fut)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            logger.warning("TTS QMediaPlayer reported InvalidMedia")
            self._safe_resolve_fut(
                self._pending_fut,
                exception=RuntimeError("QMediaPlayer reported InvalidMedia"),
            )

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        # Only resolve when the player actually started (play() was called);
        # setSource() alone fires StoppedState which must NOT resolve the future.
        if state == QMediaPlayer.PlaybackState.StoppedState and self._tts_play_started:
            self._safe_resolve_fut(self._pending_fut)

    def pause(self) -> None:
        """Pause current playback (best-effort)."""
        if self._player is None:
            return
        try:
            self._player.pause()
        except RuntimeError:
            return

    def resume(self) -> None:
        """Resume current playback (best-effort)."""
        if self._player is None:
            return
        try:
            self._player.play()
        except RuntimeError:
            return

    async def _play_mp3_locked(self, data: bytes, *, tts_boost: bool = True) -> None:
        self.ensure_ready()
        assert self._player is not None

        # Defensively ensure _player still has _audio attached
        if self._audio is not None and self._player.audioOutput() != self._audio:
            self._player.setAudioOutput(self._audio)

        if tts_boost:
            boosted = await asyncio.to_thread(_try_louder_mp3, data, self._tts_gain_db)
        else:
            # SFX: play as-authored (caller already applied user volume); never run the
            # TTS loudness chain (gain + dynaudnorm/loudnorm) which would normalize away
            # the user's volume setting.
            boosted = data
        if boosted is data and tts_boost:
            ff = shutil.which("ffmpeg")
            logger.warning(
                "TTS: підсилення ffmpeg не застосовано (%s B, base=%s dB, ffmpeg=%r). "
                "Часто бракує libmp3lame у ffmpeg-free — спробуйте повний ffmpeg або "
                "перевірте вихід: ffmpeg -h encoder=libmp3lame",
                len(data),
                self._tts_gain_db,
                ff,
            )
        else:
            enc = "WAV" if boosted[:4] == b"RIFF" else "MP3"
            logger.info(
                "TTS: ffmpeg ok (%s B -> %s B, %s, base_gain=%s dB)",
                len(data),
                len(boosted),
                enc,
                self._tts_gain_db,
            )

        file_path = await asyncio.to_thread(_write_temp_audio, boosted)

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()

        # Calculate a reasonable watchdog timeout:
        # e.g., conservative estimate: 128kbps MP3 is 16KB/s, 22kHz 16-bit WAV is 44KB/s.
        # Allow at least 8 seconds + 1 second per 4KB. Cap minimum at 10.0s.
        timeout_sec = max(10.0, 8.0 + (len(boosted) / 4000.0))

        # setSource() fires StoppedState (and sometimes buffering signals) before play().
        # Set _pending_fut and _tts_play_started only AFTER setSource to avoid
        # those early signals resolving the future before audio has started.
        self._tts_play_started = False
        self._player.setSource(QUrl.fromLocalFile(str(file_path)))
        self._pending_fut = fut
        self._tts_play_started = True
        self._player.play()
        try:
            await asyncio.wait_for(fut, timeout=timeout_sec)
        except TimeoutError:
            logger.warning(
                "TTS playback watchdog timed out after %.1fs for %s B clip; stopping",
                timeout_sec,
                len(boosted),
            )
        finally:
            self._tts_play_started = False
            self._pending_fut = None
            try:
                self._player.stop()
                self._player.setSource(QUrl())
            except RuntimeError:
                pass
            try:
                file_path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug("Temp audio cleanup: %s", e)

    async def play_mp3(self, data: bytes) -> None:
        async with self._play_lock:
            await self._play_mp3_locked(data)

    async def play_mp3_with_volume_deduped(
        self, data: bytes, linear: float, *, dedupe_key: str
    ) -> bool:
        """Play one clip at ``linear`` volume.

        Returns False if ``dedupe_key`` is already playing or queued.

        Reserves ``dedupe_key`` before waiting on the playback lock so duplicate files are not
        appended to the sink FIFO when the same path is already in line to play.
        """
        k = (dedupe_key or "").strip()
        if not k:
            await self.play_mp3_with_volume(data, linear)
            return True
        k = os.path.normcase(k)
        async with self._sound_dedupe_lock:
            if k in self._sound_dedupe_keys:
                return False
            self._sound_dedupe_keys.add(k)
        try:
            await self.play_mp3_with_volume(data, linear)
            return True
        finally:
            async with self._sound_dedupe_lock:
                self._sound_dedupe_keys.discard(k)

    async def _play_sequential_with_volume(self, data: bytes, linear: float) -> None:
        """Sequential SFX playback: volume is baked into the audio via ffmpeg.

        Falls back to the legacy QAudioOutput volume switch only when ffmpeg cannot
        scale (missing/failed) — the DSP path is backend-independent and immune to
        output-volume races.
        """
        v = max(0.0, min(1.0, float(linear)))
        scaled = await asyncio.to_thread(_try_apply_volume, data, v)
        if scaled is not data:
            self.ensure_ready()
            async with self._play_lock:
                await self._play_mp3_locked(scaled, tts_boost=False)
            return
        self.ensure_ready()
        assert self._audio is not None
        async with self._play_lock:
            prev = float(self._audio.volume())
            self._audio.setVolume(v)
            try:
                await self._play_mp3_locked(data, tts_boost=False)
            finally:
                self._audio.setVolume(prev)

    async def play_mp3_with_volume(self, data: bytes, linear: float) -> None:
        """Play one clip at the given volume (atomic with playback lock)."""
        await self._play_sequential_with_volume(data, linear)

    async def _play_mp3_parallel(self, data: bytes, linear: float) -> None:
        """Play one clip without waiting on the FIFO lock (allows overlap with TTS)."""
        self.ensure_ready()
        assert self._sfx_player is not None
        assert self._sfx_audio is not None

        v = max(0.0, min(1.0, float(linear)))
        scaled = await asyncio.to_thread(_try_apply_volume, data, v)
        if scaled is data:
            # No DSP scaling (volume ~100% or ffmpeg unavailable): keep legacy behavior
            # of putting the level on this clip's own QAudioOutput.
            file_path = await asyncio.to_thread(_write_temp_audio, data)
            out_volume = v
        else:
            # Volume already baked into the bytes; play at unity output volume.
            # SFX must not go through the TTS loudness chain.
            file_path = await asyncio.to_thread(_write_temp_audio, scaled)
            out_volume = 1.0

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()

        def _on_sfx_status(st: QMediaPlayer.MediaStatus) -> None:
            if st == QMediaPlayer.MediaStatus.EndOfMedia:
                self._safe_resolve_fut(fut)
            elif st == QMediaPlayer.MediaStatus.InvalidMedia:
                self._safe_resolve_fut(fut, exception=RuntimeError("SFX InvalidMedia"))

        def _on_sfx_error(_err: QMediaPlayer.Error, error_string: str) -> None:
            self._safe_resolve_fut(fut, exception=RuntimeError(f"SFX error: {error_string}"))

        def _on_sfx_state(st: QMediaPlayer.PlaybackState) -> None:
            if st == QMediaPlayer.PlaybackState.StoppedState:
                self._safe_resolve_fut(fut)

        async with self._sfx_lock:
            player = self._sfx_player
            audio = self._sfx_audio

            if player.audioOutput() != audio:
                player.setAudioOutput(audio)

            if scaled is data:
                audio.setVolume(max(0.0, min(1.0, float(out_volume))))
            else:
                audio.setVolume(1.0)

            conn_status = player.mediaStatusChanged.connect(_on_sfx_status)
            conn_err = player.errorOccurred.connect(_on_sfx_error)
            conn_state = player.playbackStateChanged.connect(_on_sfx_state)

            timeout_sec = max(10.0, 8.0 + (len(data) / 4000.0))
            player.setSource(QUrl.fromLocalFile(str(file_path)))
            player.play()
            try:
                await asyncio.wait_for(fut, timeout=timeout_sec)
            except TimeoutError:
                logger.warning("SFX playback watchdog timed out after %.1fs; stopping", timeout_sec)
            finally:
                try:
                    player.mediaStatusChanged.disconnect(conn_status)
                except (RuntimeError, TypeError):
                    pass
                try:
                    player.errorOccurred.disconnect(conn_err)
                except (RuntimeError, TypeError):
                    pass
                try:
                    player.playbackStateChanged.disconnect(conn_state)
                except (RuntimeError, TypeError):
                    pass
                try:
                    player.stop()
                    player.setSource(QUrl())
                except RuntimeError:
                    pass
                try:
                    file_path.unlink(missing_ok=True)
                except OSError as e:
                    logger.debug("Temp audio cleanup: %s", e)

    async def play_mp3_parallel_with_volume(self, data: bytes, linear: float) -> None:
        """Public API: play immediately, even if others queued."""
        t = asyncio.create_task(self._play_mp3_parallel(data, linear), name="audio-parallel")
        self._parallel_tasks.add(t)

        def _done(_t: asyncio.Task[None]) -> None:
            self._parallel_tasks.discard(_t)

        t.add_done_callback(_done)
        await t

    async def play_mp3_parallel_with_volume_deduped(
        self, data: bytes, linear: float, *, dedupe_key: str
    ) -> bool:
        """Parallel play with dedupe; returns False if already playing/queued."""
        k = (dedupe_key or "").strip()
        if not k:
            await self.play_mp3_parallel_with_volume(data, linear)
            return True
        k = os.path.normcase(k)
        async with self._sound_dedupe_lock:
            if k in self._sound_dedupe_keys:
                return False
            self._sound_dedupe_keys.add(k)
        try:
            await self.play_mp3_parallel_with_volume(data, linear)
            return True
        finally:
            async with self._sound_dedupe_lock:
                self._sound_dedupe_keys.discard(k)

    def shutdown(self) -> None:
        fut = self._pending_fut
        self._pending_fut = None
        if fut is not None and not fut.done():
            fut.cancel()
        if self._player is not None:
            try:
                self._player.stop()
                self._player.setSource(QUrl())
            except RuntimeError:
                pass
        if self._sfx_player is not None:
            try:
                self._sfx_player.stop()
                self._sfx_player.setSource(QUrl())
            except RuntimeError:
                pass

