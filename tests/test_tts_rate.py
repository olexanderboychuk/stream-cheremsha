from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


def test_apply_speed_noop_for_normal_factor() -> None:
    from stream_cheremsha.audio.tempo import apply_speed_to_audio

    data = b"\x00\x01\x02"
    assert apply_speed_to_audio(data, 1.0) is data
    assert apply_speed_to_audio(b"", 1.5) == b""


def test_apply_speed_returns_original_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.audio.tempo as mod

    monkeypatch.setattr(mod.shutil, "which", lambda _name: None)
    data = b"abc"
    assert mod.apply_speed_to_audio(data, 1.5) is data


def test_google_tts_clamps_rate_percent() -> None:
    from stream_cheremsha.tts.google_translate_tts import GoogleTranslateTts

    assert GoogleTranslateTts(rate_percent=10).rate_percent == 50
    assert GoogleTranslateTts(rate_percent=500).rate_percent == 200
    assert GoogleTranslateTts().rate_percent == 100


def test_google_tts_applies_speed_when_rate_set(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.google_translate_tts as mod

    calls: list[float] = []

    def _fake_speed(data: bytes, factor: float) -> bytes:
        calls.append(factor)
        return b"sped-up"

    monkeypatch.setattr(mod, "apply_speed_to_audio", _fake_speed)

    async def _run() -> bytes:
        tts = mod.GoogleTranslateTts(rate_percent=150)
        fake_resp = SimpleNamespace(status_code=200, content=b"raw-mp3")

        async def _get(_url: str, params: dict[str, str]) -> SimpleNamespace:
            return fake_resp

        tts._client = SimpleNamespace(get=_get)  # noqa: SLF001
        tts._min_interval = 0.0  # noqa: SLF001
        return await tts.synthesize("hello")

    out = asyncio.run(_run())
    assert out == b"sped-up"
    assert calls == [1.5]


def test_google_tts_skips_speed_at_normal_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.google_translate_tts as mod

    def _boom(_data: bytes, _factor: float) -> bytes:
        raise AssertionError("speed must not be applied at 100%")

    monkeypatch.setattr(mod, "apply_speed_to_audio", _boom)

    async def _run() -> bytes:
        tts = mod.GoogleTranslateTts(rate_percent=100)
        fake_resp = SimpleNamespace(status_code=200, content=b"raw-mp3")

        async def _get(_url: str, params: dict[str, str]) -> SimpleNamespace:
            return fake_resp

        tts._client = SimpleNamespace(get=_get)  # noqa: SLF001
        tts._min_interval = 0.0  # noqa: SLF001
        return await tts.synthesize("hello")

    assert asyncio.run(_run()) == b"raw-mp3"


def test_edge_tts_passes_rate_to_communicate(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.edge_tts as mod

    captured: dict[str, object] = {}

    class _FakeCommunicate:
        def __init__(self, _text: str, **kwargs: object) -> None:
            captured.update(kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    fake_edge = SimpleNamespace(Communicate=_FakeCommunicate)
    monkeypatch.setattr(mod, "_import_edge_tts", lambda: fake_edge)

    async def _run() -> None:
        tts = mod.EdgeTts("uk-UA-PolinaNeural", rate="+25%")
        assert tts.rate == "+25%"
        await tts.synthesize("hi")

    asyncio.run(_run())
    assert captured["rate"] == "+25%"
