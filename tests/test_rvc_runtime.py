"""RVC runtime helper (no rvc-python required)."""

from __future__ import annotations

import asyncio

from stream_cheremsha.tts.rvc_wav import RvcRuntime, apply_rvc_if_active


def test_apply_rvc_inactive_passthrough() -> None:
    r = RvcRuntime()
    raw = b"not-wav"
    out = asyncio.run(apply_rvc_if_active(r, raw))
    assert out is raw


def test_apply_rvc_no_chain_empty() -> None:
    r = RvcRuntime()
    out = asyncio.run(apply_rvc_if_active(r, b""))
    assert out == b""
