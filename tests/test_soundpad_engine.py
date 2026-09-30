from __future__ import annotations

from pynput.keyboard import Key
from PySide6.QtCore import QSettings

from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
from stream_cheremsha.soundpad.hotkeys import GlobalHotkeyManager, PynputHotkeyBackend
from stream_cheremsha.soundpad.models import PlaybackMode, SoundEntry
from stream_cheremsha.soundpad.store import SoundpadStore
from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi

# NOTE: the `qapp` session fixture lives in tests/conftest.py (exactly one
# QApplication per pytest process). Do NOT define module-scoped duplicates:
# they get garbage-collected mid-session, breaking later suites.


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


async def _pump_until(pred, timeout=2.0):
    import asyncio

    for _ in range(int(timeout / 0.01)):
        if pred():
            return True
        await asyncio.sleep(0.01)
    return pred()


def test_stop_halts_audible_playback_via_sink_voice_stop():
    """stop() must halt the audible voice, not just clear bookkeeping."""
    import asyncio

    state = {"started": False}
    stopped_prefixes: list[str] = []

    class VoiceSink:
        async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
            state["started"] = True
            await asyncio.sleep(30)  # simulates an audible clip
            return True

        def stop_sfx_by_key_prefix(self, prefix):
            stopped_prefixes.append(prefix)

    async def main():
        eng = SoundpadAudioEngine(sink=VoiceSink())
        e = _e(i="s1", mode=PlaybackMode.OVERLAP)
        assert eng.play(e, b"123") == "PLAYING"
        assert await _pump_until(lambda: state["started"])
        assert eng.is_playing("s1")
        eng.stop("s1")
        assert stopped_prefixes == ["soundpad:s1:"]
        assert not eng.is_playing("s1")
        assert await _pump_until(lambda: eng._play_tasks.get("s1") is None)

    asyncio.run(main())


def test_stop_cancels_tasks_when_sink_has_no_voice_stop():
    """Legacy sinks without stop_sfx_by_key_prefix still halt via cancel."""
    import asyncio

    state = {"started": False, "cancelled": False}

    class LegacySink:
        async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
            state["started"] = True
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                state["cancelled"] = True
                raise
            return True

    async def main():
        eng = SoundpadAudioEngine(sink=LegacySink())
        e = _e(i="s2", mode=PlaybackMode.OVERLAP)
        assert eng.play(e, b"123") == "PLAYING"
        assert await _pump_until(lambda: state["started"])
        eng.stop("s2")
        assert await _pump_until(lambda: state["cancelled"])
        assert not eng.is_playing("s2")

    asyncio.run(main())


def test_stop_all_halts_every_voice():
    import asyncio

    stopped: list[str] = []

    class VoiceSink:
        async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
            await asyncio.sleep(30)
            return True

        def stop_sfx_by_key_prefix(self, prefix):
            stopped.append(prefix)

    async def main():
        eng = SoundpadAudioEngine(sink=VoiceSink())
        assert eng.play(_e(i="a", mode=PlaybackMode.OVERLAP), b"1") == "PLAYING"
        assert eng.play(_e(i="b", mode=PlaybackMode.OVERLAP), b"2") == "PLAYING"
        assert await _pump_until(lambda: len(eng._play_tasks) == 2)
        eng.stop_all()
        assert sorted(stopped) == ["soundpad:a:", "soundpad:b:"]
        assert eng.active_ids() == []

    asyncio.run(main())


def test_hold_repeats_while_held_and_stops_on_release():
    import asyncio

    async def main():
        class HoldSink:
            def __init__(self):
                self.calls = 0
                self.finish = asyncio.Event()

            async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
                self.calls += 1
                await self.finish.wait()
                return True

        eng = SoundpadAudioEngine(sink=HoldSink())
        e = _e(i="h", mode=PlaybackMode.HOLD)
        eng.set_hold("h", True)
        assert eng.play(e, b"123") == "PLAYING"
        assert await _pump_until(lambda: eng._play_tasks.get("h") is not None)
        assert eng.is_playing("h")
        # Finishing an iteration replays while the key is held.
        eng._sink.finish.set()
        assert await _pump_until(lambda: eng._sink.calls >= 2)
        assert eng.is_playing("h")
        # Release stops the loop: no further replays after the in-flight one.
        eng.set_hold("h", False)
        eng.stop("h")
        await asyncio.sleep(0.05)
        frozen = eng._sink.calls
        await asyncio.sleep(0.05)
        assert eng._sink.calls == frozen
        assert not eng.is_playing("h")

    asyncio.run(main())


def test_stop_while_held_does_not_resume():
    """Explicit stop wins over a held key (no resume until re-press)."""
    import asyncio

    async def main():
        class HoldSink:
            def __init__(self):
                self.calls = 0
                self.finish = asyncio.Event()

            async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
                self.calls += 1
                await self.finish.wait()
                return True

        eng = SoundpadAudioEngine(sink=HoldSink())
        e = _e(i="h", mode=PlaybackMode.HOLD)
        eng.set_hold("h", True)
        assert eng.play(e, b"123") == "PLAYING"
        assert await _pump_until(lambda: eng._sink.calls == 1)
        eng.stop("h")  # no set_hold(False): stop itself must clear the hold
        eng._sink.finish.set()
        await asyncio.sleep(0.05)
        assert eng._sink.calls == 1
        assert not eng.is_playing("h")
        assert "h" not in eng._held

    asyncio.run(main())


def test_hold_initial_press_respects_cooldown():
    eng = SoundpadAudioEngine(sink=FakeSink())
    e = _e(i="h", mode=PlaybackMode.HOLD, cd=5.0)
    assert eng.play(e, b"123") in ("PLAYING", "QUEUED")
    assert eng.play(e, b"123") == "COOLDOWN"


def test_warmup_is_idempotent_and_safe_without_audio():
    eng = SoundpadAudioEngine(sink=FakeSink())
    eng.warmup()
    assert eng._sink is not None
    eng.warmup()
    eng.stop_all()  # idle stop-all must not raise
    assert eng.active_ids() == []


def test_hold_survives_autorepeat_storm_full_stack(qapp, tmp_path):
    """End-to-end: backend hooks -> manager -> API -> engine with a running
    loop. Synthetic X11 repeat pairs mid-hold must not stop the loop; only
    the final idle-50ms release stops it."""
    import asyncio

    store = SoundpadStore(settings=QSettings("sp-storm", "full"), root_dir=tmp_path)
    f = tmp_path / "a.mp3"
    f.write_bytes(b"x")

    async def main():
        from stream_cheremsha.soundpad.engine import SoundpadAudioEngine

        class HoldSink:
            def __init__(self):
                self.calls = 0
                self.finish = asyncio.Event()

            async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
                self.calls += 1
                await self.finish.wait()
                return True

        eng = SoundpadAudioEngine(sink=HoldSink())
        be = PynputHotkeyBackend(on_fire=lambda c: None)
        hk = GlobalHotkeyManager(backend=be)
        api = SoundpadQmlApi(store=store, engine=eng, hotkeys=hk)
        sid = api.addSound(f.as_uri(), "H", "Меми", "F9", 1.0, "hold")
        # Seed mappings directly: no listener thread in unit tests.
        be._combos["F9"] = frozenset({"f9"})
        hk._combo_owner["F9"] = sid
        hk._ids[sid] = "F9"

        be._on_key_down(Key.f9)
        assert await _pump_until(lambda: eng.is_playing(sid))
        # Auto-repeat storm while the first iteration is still audible.
        for _ in range(5):
            be._on_key_up(Key.f9)
            be._on_key_down(Key.f9)
        await asyncio.sleep(0.02)
        assert eng.is_playing(sid)
        assert sid in eng._held
        # End the iteration: must replay (hold intact), not stop.
        eng._sink.finish.set()
        assert await _pump_until(lambda: eng._sink.calls >= 2)
        assert eng.is_playing(sid)
        # Real lift: debounced release stops the loop exactly once.
        import threading as _th
        got = []
        hk.hotkeyReleased.connect(got.append)
        be._on_key_up(Key.f9)
        await asyncio.sleep(0.15)
        print('DIAG storm delivered:', got)
        print('DIAG storm pending:', {k: v.is_alive() for k, v in be._pending_release.items()})
        print('DIAG storm threads:', sorted(t.name for t in _th.enumerate()))
        qapp.processEvents()
        qapp.processEvents()
        print('DIAG storm delivered2:', got)
        assert not eng.is_playing(sid)
        frozen = eng._sink.calls
        await asyncio.sleep(0.05)
        assert eng._sink.calls == frozen
        be.stop()  # cancel any pending release timer: nothing may outlive the test

    asyncio.run(main())


def test_play_preview_uses_sink():
    import asyncio

    sink = FakeSink()
    eng = SoundpadAudioEngine(sink=sink)

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.01)

    asyncio.run(main())
    assert len(sink.calls) == 1
    data, vol = sink.calls[0]
    assert data == b"abc" and 0.0 <= vol <= 1.0


def test_play_preview_rejects_empty():
    eng = SoundpadAudioEngine(sink=FakeSink())
    assert eng.play_preview(b"") == "BLOCKED"


def test_preview_finished_emits_once_on_natural_end():
    import asyncio

    sink = FakeSink()
    eng = SoundpadAudioEngine(sink=sink)
    finished: list[int] = []
    eng.previewFinished.connect(lambda: finished.append(1))

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.02)

    asyncio.run(main())
    assert finished == [1]


def test_stop_preview_cancels_without_emit():
    import asyncio

    class SlowSink(FakeSink):
        async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
            self.calls.append((bytes(data), float(volume)))
            await asyncio.sleep(5)  # long playback
            return True

    sink = SlowSink()
    eng = SoundpadAudioEngine(sink=sink)
    finished: list[int] = []
    eng.previewFinished.connect(lambda: finished.append(1))

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.01)  # let it start
        eng.stop_preview()
        await asyncio.sleep(0.02)  # let cancellation unwind

    asyncio.run(main())
    assert len(sink.calls) == 1
    assert finished == []  # cancelled playback must not report "finished"


def test_stop_all_stops_preview_without_error():
    eng = SoundpadAudioEngine(sink=FakeSink())
    eng.stop_all()  # must not raise even with no preview running
