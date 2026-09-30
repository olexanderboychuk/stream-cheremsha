from __future__ import annotations

from stream_cheremsha.soundpad.models import (
    PlaybackMode,
    SoundEntry,
    normalize_hotkey,
    validate_sound_entry,
)


def test_normalize_hotkey_upper_and_spacing():
    assert normalize_hotkey("ctrl + alt + 1") == "Ctrl+Alt+1"
    assert normalize_hotkey("f2") == "F2"


def test_validate_rejects_bad_volume_and_missing_file():
    e = SoundEntry(
        id="a",
        name="Airhorn",
        file_path="",
        category="Меми",
        hotkey="F2",
        volume=1.5,
        playback_mode=PlaybackMode.RESTART,
        cooldown_sec=0.0,
        triggers=(),
        waveform_peaks=(),
        duration_sec=0.0,
        play_count=0,
        last_played_at="",
        order=0,
        enabled=True,
        monitor=True,
        stream_out=True,
    )
    errs = validate_sound_entry(e)
    assert any("file_path" in m for m in errs)
    assert any("volume" in m for m in errs)


def test_validate_ok_minimal():
    e = SoundEntry(
        id="a",
        name="Airhorn",
        file_path="/tmp/a.mp3",
        category="Меми",
        hotkey="F2",
        volume=1.0,
        playback_mode=PlaybackMode.OVERLAP,
        cooldown_sec=2.0,
        triggers=(),
        waveform_peaks=(),
        duration_sec=1.2,
        play_count=0,
        last_played_at="",
        order=0,
        enabled=True,
        monitor=True,
        stream_out=True,
    )
    assert validate_sound_entry(e) == []
