"""Tests for packaged Piper model path resolution."""

from __future__ import annotations

from stream_cheremsha.tts.bundled_piper import bundled_piper_onnx_path, effective_piper_onnx_path


def test_bundled_piper_onnx_path_unknown_returns_none() -> None:
    assert bundled_piper_onnx_path("definitely-not-bundled-voice-id-xyz") is None


def test_effective_prefers_existing_file(tmp_path, monkeypatch) -> None:
    f = tmp_path / "m.onnx"
    f.write_bytes(b"not real onnx")
    got = effective_piper_onnx_path(str(f), "uk-UA")
    assert got is not None
    assert got.resolve() == f.resolve()
