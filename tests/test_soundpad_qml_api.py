from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager
from stream_cheremsha.soundpad.store import SoundpadStore
from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi


class FakeSink:
    async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        return True


def _api(tag, tmp_path):
    store = SoundpadStore(settings=QSettings("sp-qml", tag), root_dir=tmp_path)
    eng = SoundpadAudioEngine(sink=FakeSink())
    hk = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    return SoundpadQmlApi(store=store, engine=eng, hotkeys=hk)


def test_add_list_remove(tmp_path):
    api = _api("t1", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"RIFF....fake")
    sid = api.addSound(f.as_uri(), "Airhorn", "Меми", "F2", 1.0)
    assert sid != ""
    items = json.loads(api.soundsJson())
    assert any(i["id"] == sid for i in items)
    assert api.removeSound(sid) is True


def test_assign_conflict(tmp_path):
    api = _api("t2", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    api.addSound(f.as_uri(), "A", "Меми", "F2", 1.0)
    b = api.addSound(f.as_uri(), "B", "Меми", "", 1.0)
    assert api.assignHotkey(b, "F2").startswith("conflict:")
    assert api.assignHotkey(b, "F3") == "ok"


def test_reject_bad_extension(tmp_path):
    api = _api("t3", tmp_path)
    f = tmp_path / "evil.exe"
    f.write_bytes(b"xx")
    assert api.addSound(f.as_uri(), "Evil", "Меми", "", 1.0) == ""
