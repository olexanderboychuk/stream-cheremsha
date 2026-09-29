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


def test_monitor_stream_out_persist_and_state(tmp_path):
    api = _api("t4", tmp_path)
    st0 = json.loads(api.globalStateJson())
    assert st0["monitor"] is True and st0["stream_out"] is True
    assert 0.0 <= st0["volume"] <= 1.0
    api.setMonitor(False)
    api.setStreamOut(True)
    st1 = json.loads(api.globalStateJson())
    assert st1["monitor"] is False and st1["stream_out"] is True
    # Persisted under the documented QSettings keys (re-read via a fresh store).
    reloaded = SoundpadStore(settings=QSettings("sp-qml", "t4"), root_dir=tmp_path)
    assert reloaded.monitor() is False
    assert reloaded.stream_out() is True


def test_ticker_gating_and_emission(tmp_path):
    import time as _time

    api = _api("t5", tmp_path)
    eng = api._engine
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "A", "Меми", "", 1.0)

    # Gating: handlers start/stop the ticker based on active ids.
    class _FakeTimer:
        def __init__(self):
            self.started = 0
            self.stopped = 0

        def start(self):
            self.started += 1

        def stop(self):
            self.stopped += 1

    fake = _FakeTimer()
    api._np_timer = fake
    eng.playbackStarted.emit(sid)  # no active ids yet -> stays stopped
    assert fake.started == 0 and fake.stopped == 0

    # Simulate an active playback with a known start time (~1.25 s ago).
    eng._last_start[sid] = _time.monotonic() - 1.25
    eng._playing.add(sid)
    eng.playbackStarted.emit(sid)  # active -> ticker starts
    assert fake.started == 1

    seen: list[tuple[str, float, float]] = []
    api.nowPlayingChanged.connect(lambda i, p, d: seen.append((i, p, d)))
    api._tick_now_playing()
    assert len(seen) == 1
    i, pos, dur = seen[0]
    assert i == sid
    assert 1.2 <= pos <= 1.6
    assert dur >= 0.0

    eng._finish(sid)  # active set empty -> ticker stops
    assert fake.stopped == 1
