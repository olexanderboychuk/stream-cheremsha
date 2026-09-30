from __future__ import annotations

from PySide6.QtCore import QSettings

from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager
from stream_cheremsha.soundpad.store import SoundpadStore
from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi


class BoomSink:
    def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        raise RuntimeError("boom")


def _api(tag, tmp_path):
    return SoundpadQmlApi(
        store=SoundpadStore(settings=QSettings("sp-err", tag), root_dir=tmp_path),
        engine=SoundpadAudioEngine(sink=BoomSink()),
        hotkeys=GlobalHotkeyManager(backend=FakeHotkeyBackend()),
    )


def test_missing_file_never_crashes(tmp_path):
    api = _api("e1", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "A", "Меми", "", 1.0, "restart")
    f.unlink()
    api.playSound(sid)  # must not raise


def test_rapid_triggers_bounded_by_cooldown(tmp_path):
    api = _api("e2", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "A", "Меми", "", 1.0, "restart")
    api.updateSoundJson(sid, '{"cooldown_sec": 5.0, "playback_mode": "restart"}')
    e = api._store.get(sid)
    assert e is not None and e.cooldown_sec == 5.0
    assert api._engine.play(e, b"x") in ("PLAYING", "QUEUED")
    assert api._engine.play(e, b"x") == "COOLDOWN"


def test_invalid_audio_rejected(tmp_path):
    api = _api("e3", tmp_path)
    f = tmp_path / "bad.txt"
    f.write_bytes(b"hello")
    assert api.addSound(f.as_uri(), "Bad", "Меми", "", 1.0, "restart") == ""
