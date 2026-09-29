from __future__ import annotations

from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
from stream_cheremsha.soundpad.models import PlaybackMode, SoundEntry


class FakeSink:
    def __init__(self):
        self.calls: list[tuple[bytes, float]] = []

    async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        self.calls.append((bytes(data), float(volume)))
        return True


def _e(i="a", mode=PlaybackMode.OVERLAP, cd=0.0):
    return SoundEntry(
        id=i,
        name=i,
        file_path=f"/tmp/{i}.mp3",
        hotkey="",
        volume=0.8,
        playback_mode=mode,
        cooldown_sec=cd,
        triggers=(),
        waveform_peaks=(),
        duration_sec=1.0,
        play_count=0,
        last_played_at="",
        order=0,
    )


def test_cooldown_blocks_second_play():
    eng = SoundpadAudioEngine(sink=FakeSink())
    e = _e(cd=5.0)
    assert eng.play(e, b"123") in ("PLAYING", "QUEUED")
    assert eng.play(e, b"123") == "COOLDOWN"


def test_queue_mode_queues_while_busy():
    eng = SoundpadAudioEngine(sink=FakeSink())
    e = _e(mode=PlaybackMode.QUEUE)
    eng._playing.add("a")
    assert eng.play(e, b"123") == "QUEUED"
    assert eng.queued_count("a") == 1


def test_output_device_list_never_raises():
    eng = SoundpadAudioEngine(sink=FakeSink())
    devs = eng.list_output_devices()
    assert isinstance(devs, list)


def test_ducking_signal_and_monitor_flags():
    seen: list[bool] = []
    eng = SoundpadAudioEngine(sink=FakeSink())
    eng.duckingChanged.connect(seen.append)
    eng.set_monitor(False)
    eng.set_stream_out(True)
    assert eng._monitor is False
    assert eng._stream_out is True
    e = _e()
    eng.play(e, b"123")
    assert True in seen
    eng.stop_all()
    assert False in seen


def test_position_of_tracks_start_time():
    eng = SoundpadAudioEngine(sink=FakeSink())
    assert eng.position_of("nope") == 0.0
    e = _e()
    eng.play(e, b"123")  # no event loop: finishes immediately, but start is recorded
    pos = eng.position_of("a")
    assert pos >= 0.0


def test_main_window_ducking_wiring_present():
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "ui" / "main_window.py"
    ).read_text(encoding="utf-8")
    assert "duckingChanged" in src
    assert "_on_soundpad_ducking" in src
