from __future__ import annotations

import time


def test_stall_detection_threshold() -> None:
    stall_sec = 15.0
    beat_sec = 2.0
    last_beat = time.monotonic()
    assert time.monotonic() - last_beat < stall_sec

    stale_last_beat = time.monotonic() - (stall_sec + beat_sec)
    assert time.monotonic() - stale_last_beat >= stall_sec
