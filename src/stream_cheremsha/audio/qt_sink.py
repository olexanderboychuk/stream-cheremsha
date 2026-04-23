from __future__ import annotations

import asyncio
import logging
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
        self._pending_fut: asyncio.Future[None] | None = None

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

    async def play_mp3(self, data: bytes) -> None:
        async with self._play_lock:
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

    def shutdown(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
