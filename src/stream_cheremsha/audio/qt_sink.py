from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

logger = logging.getLogger(__name__)

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
            timeout=60,
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
    # Simple volume first (ffmpeg-free friendly); then dynamics / loudnorm; then stronger gain.
    filters = (
        f"volume={g}dB",
        f"volume={g}dB,dynaudnorm=f=100:g=21:m=60.0",
        "loudnorm=I=-14:LRA=11:TP=-1.5",
        f"volume={g + 8}dB",
    )
    for af in filters:
        out = _ffmpeg_try_filter_encodings(data, af)
        if out is not None:
            return out
    return data


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
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._play_lock = asyncio.Lock()
        self._sound_dedupe_lock = asyncio.Lock()
        self._sound_dedupe_keys: set[str] = set()
        self._pending_fut: asyncio.Future[None] | None = None
        self._parallel_tasks: set[asyncio.Task[None]] = set()

        self._player.errorOccurred.connect(self._on_player_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._tts_gain_db = _DEFAULT_TTS_GAIN_DB

    def set_tts_gain_db(self, db: int) -> None:
        """Base dB boost for ffmpeg TTS chain (0–36)."""
        self._tts_gain_db = max(0, min(36, int(db)))

    def set_output_device_by_description(self, description: str | None) -> None:
        """Match QAudioDevice.description(); None or empty keeps default."""
        if not description:
            return
        for dev in QMediaDevices.audioOutputs():
            if dev.description() == description:
                self._audio.setDevice(dev)
                return
        logger.warning("Audio device %r not found, using default", description)

    def set_volume(self, linear: float) -> None:
        self._audio.setVolume(max(0.0, min(1.0, linear)))

    def get_volume(self) -> float:
        return float(self._audio.volume())

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        fut = self._pending_fut
        if fut is not None and not fut.done():
            fut.set_exception(RuntimeError(f"QMediaPlayer error {error!s}: {error_string}"))

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        fut = self._pending_fut
        if fut is not None and not fut.done():
            fut.set_result(None)

    def pause(self) -> None:
        """Pause current playback (best-effort)."""
        try:
            self._player.pause()
        except RuntimeError:
            return

    def resume(self) -> None:
        """Resume current playback (best-effort)."""
        try:
            self._player.play()
        except RuntimeError:
            return

    async def _play_mp3_locked(self, data: bytes) -> None:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()
        self._pending_fut = fut

        boosted = await asyncio.to_thread(_try_louder_mp3, data, self._tts_gain_db)
        if boosted is data:
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

        self._player.setSource(QUrl.fromLocalFile(str(file_path)))
        self._player.play()
        try:
            await fut
        finally:
            self._pending_fut = None
            self._player.stop()
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
            async with self._play_lock:
                prev = float(self._audio.volume())
                self._audio.setVolume(max(0.0, min(1.0, float(linear))))
                try:
                    await self._play_mp3_locked(data)
                finally:
                    self._audio.setVolume(prev)
            return True
        finally:
            async with self._sound_dedupe_lock:
                self._sound_dedupe_keys.discard(k)

    async def play_mp3_with_volume(self, data: bytes, linear: float) -> None:
        """Play one clip at the given volume (atomic with playback lock)."""
        async with self._play_lock:
            prev = float(self._audio.volume())
            self._audio.setVolume(max(0.0, min(1.0, float(linear))))
            try:
                await self._play_mp3_locked(data)
            finally:
                self._audio.setVolume(prev)

    async def _play_mp3_parallel(self, data: bytes, linear: float) -> None:
        """Play one clip without waiting on the FIFO lock (allows overlap)."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()

        boosted = await asyncio.to_thread(_try_louder_mp3, data, self._tts_gain_db)
        file_path = await asyncio.to_thread(_write_temp_audio, boosted)

        player = QMediaPlayer(self)
        audio = QAudioOutput(self)
        player.setAudioOutput(audio)
        audio.setVolume(max(0.0, min(1.0, float(linear))))

        def _done_ok() -> None:
            if not fut.done():
                fut.set_result(None)

        def _done_err(_err: QMediaPlayer.Error, error_string: str) -> None:
            if not fut.done():
                fut.set_exception(RuntimeError(f"QMediaPlayer error: {error_string}"))

        player.mediaStatusChanged.connect(
            lambda st: _done_ok() if st == QMediaPlayer.MediaStatus.EndOfMedia else None
        )
        player.errorOccurred.connect(_done_err)

        player.setSource(QUrl.fromLocalFile(str(file_path)))
        player.play()
        try:
            await fut
        finally:
            try:
                player.stop()
            except RuntimeError:
                pass
            try:
                file_path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug("Temp audio cleanup: %s", e)
            player.deleteLater()
            audio.deleteLater()

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
        self._player.stop()
        self._player.setSource(QUrl())
