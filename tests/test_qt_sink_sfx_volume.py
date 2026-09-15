from __future__ import annotations

import asyncio

from stream_cheremsha.audio import qt_sink


def test_try_apply_volume_identity_near_full_volume() -> None:
    raw = b"\xff\xd3fake-mp3"
    assert qt_sink._try_apply_volume(raw, 1.0) is raw
    assert qt_sink._try_apply_volume(raw, 100.0) is raw


def test_try_apply_volume_returns_same_when_ffmpeg_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(qt_sink.shutil, "which", lambda _: None)
    raw = b"\xff\xd3fake-mp3"
    assert qt_sink._try_apply_volume(raw, 0.35) is raw


def test_try_apply_volume_uses_linear_gain_filter(monkeypatch) -> None:
    monkeypatch.setattr(qt_sink.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    seen: dict[str, object] = {}

    def fake_filter(data: bytes, audio_filter: str) -> bytes | None:
        seen["filter"] = audio_filter
        return b"scaled-bytes"

    monkeypatch.setattr(qt_sink, "_ffmpeg_try_filter_encodings", fake_filter)
    raw = b"\xff\xd3fake-mp3"
    out = qt_sink._try_apply_volume(raw, 0.35)
    assert out == b"scaled-bytes"
    assert seen["filter"] == "volume=0.350"


def test_try_apply_volume_falls_back_to_original_on_ffmpeg_failure(monkeypatch) -> None:
    monkeypatch.setattr(qt_sink.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(qt_sink, "_ffmpeg_try_filter_encodings", lambda _d, _f: None)
    raw = b"\xff\xd3fake-mp3"
    assert qt_sink._try_apply_volume(raw, 0.2) is raw


def test_sequential_sfx_uses_dsp_volume_and_skips_tts_boost(monkeypatch) -> None:
    sink = qt_sink.QtAudioSink()
    calls: dict[str, object] = {}

    async def fake_locked(data: bytes, *, tts_boost: bool = True) -> None:
        calls["data"] = data
        calls["tts_boost"] = tts_boost

    touched_volume: list[float] = []
    ready_calls: list[None] = []

    def fake_ensure_ready() -> None:
        ready_calls.append(None)

    monkeypatch.setattr(qt_sink, "_try_apply_volume", lambda _d, _v: b"scaled-bytes")
    monkeypatch.setattr(sink, "ensure_ready", fake_ensure_ready)
    monkeypatch.setattr(sink, "_play_mp3_locked", fake_locked)
    # If the code touches output volume, this fake audio records it.
    monkeypatch.setattr(sink, "_audio", None)

    asyncio.run(sink.play_mp3_with_volume(b"raw-bytes", 0.35))

    assert calls["data"] == b"scaled-bytes"
    assert calls["tts_boost"] is False
    assert ready_calls == [None]
    assert touched_volume == []


def test_sequential_sfx_falls_back_to_output_volume_without_ffmpeg(monkeypatch) -> None:
    sink = qt_sink.QtAudioSink()
    volumes: list[float] = []

    class FakeAudio:
        def volume(self) -> float:
            return 1.0

        def setVolume(self, v: float) -> None:  # noqa: N802 (Qt API name)
            volumes.append(float(v))

    calls: dict[str, object] = {}

    async def fake_locked(data: bytes, *, tts_boost: bool = True) -> None:
        calls["data"] = data
        calls["tts_boost"] = tts_boost
        # Output volume must already be set while the clip plays.
        calls["volume_during_play"] = list(volumes)

    monkeypatch.setattr(sink, "ensure_ready", lambda: None)
    monkeypatch.setattr(sink, "_play_mp3_locked", fake_locked)
    monkeypatch.setattr(sink, "_audio", FakeAudio())
    monkeypatch.setattr(qt_sink.shutil, "which", lambda _: None)

    asyncio.run(sink.play_mp3_with_volume(b"raw-bytes", 0.35))

    assert calls["data"] == b"raw-bytes"
    assert calls["tts_boost"] is False
    assert calls["volume_during_play"] == [0.35]
    # Volume restored after playback.
    assert volumes == [0.35, 1.0]
