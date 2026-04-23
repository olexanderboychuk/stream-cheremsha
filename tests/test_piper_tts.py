"""Piper TTS unit tests (mock ``PiperVoice``; no real ONNX)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_piper_tts_synthesize_writes_wav(tmp_path: Path) -> None:
    pytest.importorskip("piper")
    model = tmp_path / "uk_UA-tts-medium.onnx"
    model.write_bytes(b"x")

    fake_voice = MagicMock()

    def _synth(text: str, wav_out: object) -> None:
        w = wav_out
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 20)

    fake_voice.synthesize_wav.side_effect = _synth

    with patch("piper.PiperVoice") as pv:
        pv.load.return_value = fake_voice
        from stream_cheremsha.tts.piper_tts import PiperTts

        tts = PiperTts(model)
        out = asyncio.run(tts.synthesize("hello"))

    assert out[:4] == b"RIFF"
    assert b"WAVE" in out[:20]
    pv.load.assert_called_once()


def test_is_piper_package_installed_returns_bool() -> None:
    from stream_cheremsha.tts.piper_tts import is_piper_package_installed

    assert isinstance(is_piper_package_installed(), bool)
