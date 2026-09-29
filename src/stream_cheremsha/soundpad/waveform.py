from __future__ import annotations

import array
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def probe_duration_sec(path: str | Path) -> float:
    ffprobe = shutil.which("ffprobe")
    p = Path(str(path))
    if ffprobe is None or not p.is_file():
        return 0.0
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(p),
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0.0
    try:
        return max(0.0, float((proc.stdout or b"").decode().strip() or 0.0))
    except ValueError:
        return 0.0


def extract_waveform_peaks(path: str | Path, buckets: int = 64) -> list[float]:
    n = max(8, min(256, int(buckets or 64)))
    p = Path(str(path))
    if not p.is_file():
        return []
    try:
        size = p.stat().st_size
    except OSError:
        return []
    if size <= 0 or size > 200 * 1024 * 1024:
        return []
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return []
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-i",
                str(p),
                "-ac",
                "1",
                "-ar",
                "8000",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "pipe:1",
            ],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("waveform ffmpeg failed: %s", e)
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []
    raw = proc.stdout
    if len(raw) % 2 != 0:
        raw = raw[:-1]
    samples = array.array("h")
    try:
        samples.frombytes(raw)
    except ValueError:
        return []
    if not samples:
        return []
    total = len(samples)
    peaks: list[float] = []
    peak_max = 32768.0
    for i in range(n):
        s0 = (total * i) // n
        s1 = max(s0 + 1, (total * (i + 1)) // n)
        chunk = samples[s0:s1]
        m = 0
        for v in chunk[:: max(1, len(chunk) // 200)]:
            a = abs(int(v))
            if a > m:
                m = a
        peaks.append(round(min(1.0, m / peak_max), 3))
    return peaks


async def aextract_waveform_peaks(path: str | Path, buckets: int = 64) -> list[float]:
    return await asyncio.to_thread(extract_waveform_peaks, path, buckets)
