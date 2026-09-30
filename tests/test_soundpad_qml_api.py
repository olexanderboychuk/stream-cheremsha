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
    sid = api.addSound(f.as_uri(), "Airhorn", "Меми", "F2", 1.0, "restart")
    assert sid != ""
    items = json.loads(api.soundsJson())
    assert any(i["id"] == sid for i in items)
    assert api.removeSound(sid) is True


def test_assign_conflict(tmp_path):
    api = _api("t2", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    api.addSound(f.as_uri(), "A", "Меми", "F2", 1.0, "restart")
    b = api.addSound(f.as_uri(), "B", "Меми", "", 1.0, "restart")
    assert api.assignHotkey(b, "F2").startswith("conflict:")
    assert api.assignHotkey(b, "F3") == "ok"


def test_reject_bad_extension(tmp_path):
    api = _api("t3", tmp_path)
    f = tmp_path / "evil.exe"
    f.write_bytes(b"xx")
    assert api.addSound(f.as_uri(), "Evil", "Меми", "", 1.0, "restart") == ""


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
    sid = api.addSound(f.as_uri(), "A", "Меми", "", 1.0, "restart")

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


def test_hold_press_release_cycle(tmp_path, qapp):
    api = _api("hold1", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "H", "Меми", "F9", 1.0, "restart")
    assert api.updateSoundJson(sid, json.dumps({"playback_mode": "hold"})) is True
    assert any(i["playback_mode"] == "hold" for i in json.loads(api.soundsJson()))

    changed: list[None] = []
    api.soundsChanged.connect(lambda: changed.append(None))
    hk = api._hotkeys
    # Press arms the hold (no running loop here: finishes immediately).
    hk.simulate_press(sid)
    assert sid in api._engine._held
    qapp.processEvents()
    assert len(changed) >= 1
    # Release disarms and stops.
    changed.clear()
    hk.simulate_release(sid)
    assert sid not in api._engine._held
    assert not api._engine.is_playing(sid)
    qapp.processEvents()
    assert len(changed) >= 1


def test_hold_full_stack_press_loop_release(tmp_path):
    """Press → hold loop → release across manager + API + engine."""
    import asyncio

    api = _api("hold2", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "H", "Меми", "F9", 1.0, "restart")
    assert api.updateSoundJson(sid, json.dumps({"playback_mode": "hold"})) is True

    async def main():
        calls = {"n": 0}
        finish = asyncio.Event()
        started = asyncio.Event()

        async def fake_play(data, volume, *, dedupe_key=""):
            calls["n"] += 1
            started.set()
            await finish.wait()
            return True

        api._engine._sink.play_mp3_parallel_with_volume_deduped = fake_play
        hk = api._hotkeys
        hk.simulate_press(sid)
        for _ in range(200):
            if api._engine.is_playing(sid):
                break
            await asyncio.sleep(0.01)
        assert api._engine.is_playing(sid)
        finish.set()  # end iteration 1 -> must replay while held
        for _ in range(200):
            if calls["n"] >= 2:
                break
            await asyncio.sleep(0.01)
        assert calls["n"] >= 2
        hk.simulate_release(sid)
        await asyncio.sleep(0.05)
        frozen = calls["n"]
        await asyncio.sleep(0.05)
        assert calls["n"] == frozen
        assert not api._engine.is_playing(sid)

    asyncio.run(main())


def test_add_sound_with_mode_and_owner_lookup(tmp_path):
    api = _api("modetest", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "H", "Меми", "F9", 1.0, "hold")
    assert sid != ""
    items = {i["id"]: i for i in json.loads(api.soundsJson())}
    assert items[sid]["playback_mode"] == "hold"
    # Live conflict lookup for the add dialog.
    assert api.hotkeyOwnerName("F9") == "H"
    assert api.hotkeyOwnerName("F10") == ""
    assert api.hotkeyOwnerName("") == ""
    assert api.hotkeyOwnerName("not a key !@#") == ""
    # Unknown mode falls back to restart, never rejects the file.
    sid2 = api.addSound(f.as_uri(), "H2", "Меми", "", 1.0, "bogus")
    assert sid2 != ""
    items = {i["id"]: i for i in json.loads(api.soundsJson())}
    assert items[sid2]["playback_mode"] == "restart"


def test_tap_release_keeps_normal_mode_playing(tmp_path):
    """Regression: releasing a hotkey must NOT cut normal-mode clips.

    Only HOLD loops stop on key-up; a quick tap of restart/overlap/etc.
    plays the full clip.
    """
    import asyncio

    api = _api("tapkeep", tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")
    sid = api.addSound(f.as_uri(), "T", "Меми", "F9", 1.0, "restart")

    async def main():
        started = asyncio.Event()
        finished = asyncio.Event()

        async def fake_play(data, volume, *, dedupe_key=""):
            started.set()
            await finished.wait()
            return True

        api._engine._sink.play_mp3_parallel_with_volume_deduped = fake_play
        hk = api._hotkeys
        hk.simulate_press(sid)
        for _ in range(200):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert api._engine.is_playing(sid)
        hk.simulate_release(sid)  # quick tap: key already up
        await asyncio.sleep(0.05)
        assert api._engine.is_playing(sid), "release cut a restart clip"
        assert sid not in api._engine._held
        finished.set()
        await asyncio.sleep(0.05)
        assert not api._engine.is_playing(sid)

    asyncio.run(main())
