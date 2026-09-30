from __future__ import annotations

import shutil
import subprocess

from stream_cheremsha.soundpad.waveform import extract_waveform_peaks, probe_duration_sec


def test_missing_file_returns_empty():
    assert extract_waveform_peaks("/nonexistent/a.mp3", 32) == []
    assert probe_duration_sec("/nonexistent/a.mp3") == 0.0


def test_invalid_file_returns_empty(tmp_path):
    p = tmp_path / "bad.mp3"
    p.write_bytes(b"not audio at all")
    assert extract_waveform_peaks(str(p), 32) == []


def test_buckets_count_and_range(tmp_path):
    if shutil.which("ffmpeg") is None:
        return
    p = tmp_path / "tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(p),
        ],
        check=True,
    )
    peaks = extract_waveform_peaks(str(p), 48)
    assert len(peaks) == 48
    assert all(0.0 <= v <= 1.0 for v in peaks)
    assert max(peaks) > 0.1
