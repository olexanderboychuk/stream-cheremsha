from __future__ import annotations

from PySide6.QtCore import QSettings

from stream_cheremsha.soundpad.models import PlaybackMode, SoundEntry
from stream_cheremsha.soundpad.store import SoundpadStore


def _entry(i="a", name="Airhorn", hotkey="F2", cat="Меми", order=0):
    return SoundEntry(
        id=i, name=name, file_path=f"/tmp/{i}.mp3", category=cat,
        hotkey=hotkey, volume=1.0, playback_mode=PlaybackMode.RESTART,
        cooldown_sec=0.0, triggers=(), waveform_peaks=(0.1, 0.9),
        duration_sec=1.2, play_count=0, last_played_at="",
        order=order, enabled=True, monitor=True, stream_out=True)


def test_upsert_list_persist_roundtrip(tmp_path):
    s = SoundpadStore(settings=QSettings("sp-test-store", "t1"), root_dir=tmp_path)
    assert s.upsert(_entry()) == []
    assert s.get("a") is not None and s.get("a").name == "Airhorn"
    s2 = SoundpadStore(settings=QSettings("sp-test-store", "t1"), root_dir=tmp_path)
    assert s2.get("a") is not None and s2.get("a").hotkey == "F2"


def test_search_filter_reorder(tmp_path):
    s = SoundpadStore(settings=QSettings("sp-test-store", "t2"), root_dir=tmp_path)
    s.upsert(_entry("a", "Airhorn", "F2", "Меми", 0))
    s.upsert(_entry("b", "Bonk", "F3", "Реакції", 1))
    assert [e.id for e in s.search("bonk")] == ["b"]
    assert [e.id for e in s.search("F2")] == ["a"]
    assert [e.id for e in s.by_category("Меми")] == ["a"]
    s.reorder(["b", "a"])
    assert [e.id for e in s.list_all()] == ["b", "a"]


def test_duplicate_move_remove(tmp_path):
    s = SoundpadStore(settings=QSettings("sp-test-store", "t3"), root_dir=tmp_path)
    s.upsert(_entry())
    dup = s.duplicate("a")
    assert dup is not None and dup.id != "a" and dup.hotkey == ""
    assert s.move("a", "Голоси") is True
    assert s.get("a").category == "Голоси"
    assert s.remove("a") is True and s.get("a") is None
