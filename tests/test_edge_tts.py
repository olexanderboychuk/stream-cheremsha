from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


def test_filter_voices_by_locale() -> None:
    from stream_cheremsha.tts.edge_tts import EdgeVoice, filter_edge_voices_for_locale

    voices = [
        EdgeVoice(short_name="uk-UA-PolinaNeural", locale="uk-UA", gender="Female"),
        EdgeVoice(short_name="en-US-AriaNeural", locale="en-US", gender="Female"),
        EdgeVoice(short_name="en-GB-RyanNeural", locale="en-GB", gender="Male"),
    ]

    uk = filter_edge_voices_for_locale(voices, "uk-UA")
    assert [v.short_name for v in uk] == ["uk-UA-PolinaNeural"]

    en = filter_edge_voices_for_locale(voices, "en-US")
    assert [v.short_name for v in en] == ["en-US-AriaNeural"]


def test_edge_tts_synthesize_concatenates_audio_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.edge_tts as mod

    captured: dict[str, object] = {}

    class _FakeCommunicate:
        def __init__(self, _text: str, **kwargs: object) -> None:
            captured.update(kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"a"}
            yield {"type": "WordBoundary", "data": None}
            yield {"type": "audio", "data": b"bcd"}

    fake_edge = SimpleNamespace(Communicate=_FakeCommunicate)
    monkeypatch.setattr(mod, "_import_edge_tts", lambda: fake_edge)

    async def _run() -> bytes:
        tts = mod.EdgeTts("uk-UA-PolinaNeural")
        return await tts.synthesize("hi")

    out = asyncio.run(_run())
    assert out == b"abcd"
    assert captured["voice"] == "uk-UA-PolinaNeural"
    assert "rate" not in captured
    assert "volume" not in captured


def test_edge_tts_rejects_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.edge_tts as mod

    fake_edge = SimpleNamespace(Communicate=lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "_import_edge_tts", lambda: fake_edge)

    async def _run() -> None:
        tts = mod.EdgeTts("uk-UA-PolinaNeural")
        with pytest.raises(ValueError, match="empty TTS text"):
            await tts.synthesize("   ")

    asyncio.run(_run())


def test_list_edge_voices_cached_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.tts.edge_tts as mod

    async def slow_list() -> list[dict[str, str]]:
        await asyncio.sleep(3600)
        return []

    fake_edge = SimpleNamespace(list_voices=slow_list)
    monkeypatch.setattr(mod, "_import_edge_tts", lambda: fake_edge)
    monkeypatch.setattr(mod, "_voices_cache", None)
    monkeypatch.setattr(mod, "LIST_VOICES_TIMEOUT_SEC", 0.05)

    async def _run() -> None:
        with pytest.raises(RuntimeError, match="timed out"):
            await mod.list_edge_voices_cached()

    asyncio.run(_run())
