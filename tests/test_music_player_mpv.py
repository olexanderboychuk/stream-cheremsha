from __future__ import annotations

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock

import pytest

from stream_cheremsha.music.player import MusicPlayer
from stream_cheremsha.music.queue_controller import MusicQueueController


class _FakeSink:
    async def play_mp3(self, _data: bytes) -> None:
        return


@pytest.mark.asyncio
async def test_kill_mpv_does_not_deadlock_when_ipc_pipe_exists() -> None:
    """Regression: _kill_mpv used to await _mpv_send while holding _mpv_lock."""
    q = MusicQueueController(instance="main")
    mp = MusicPlayer(queue=q, sink=_FakeSink(), backend="mpv")

    proc = MagicMock()
    proc.pid = 4242
    proc.returncode = None

    async def _wait() -> int:
        await asyncio.sleep(0.05)
        proc.returncode = 0
        return 0

    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock(side_effect=_wait)

    mp._mpv_proc = proc  # noqa: SLF001
    mp._mpv_ipc = r"\\.\pipe\test-deadlock"  # noqa: SLF001
    mp._mpv_pipe_w = io.BytesIO()  # noqa: SLF001

    await asyncio.wait_for(mp._kill_mpv(), timeout=1.0)

    assert mp._mpv_proc is None  # noqa: SLF001
    assert mp._mpv_ipc == ""  # noqa: SLF001
    proc.terminate.assert_called_once()
