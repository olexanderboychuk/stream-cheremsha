from __future__ import annotations

import asyncio

import pytest

from stream_cheremsha.music.player import MusicPlayer
from stream_cheremsha.music.queue_controller import MusicQueueController


class _FakeSink:
    def __init__(self) -> None:
        self.volume = 1.0
        self.playing = False

    def set_volume(self, linear: float) -> None:
        self.volume = float(linear)

    async def play_mp3(self, _data: bytes) -> None:
        self.playing = True
        try:
            # Simulate "playing until cancelled" (skip/stop).
            await asyncio.Event().wait()
        finally:
            self.playing = False


@pytest.mark.asyncio
async def test_music_player_skip_does_not_stop_supervisor_loop() -> None:
    q = MusicQueueController(instance="main")
    sink = _FakeSink()

    def resolver(_vid: str):
        return type("R", (), {"title": "", "audio_bytes": b"RIFFxxxxWAVE"})()

    mp = MusicPlayer(queue=q, sink=sink, resolver=resolver)
    await mp.start()
    try:
        await q.enqueue(video_id="a" * 11, requested_by="u1")
        await q.enqueue(video_id="b" * 11, requested_by="u2")

        # Wait until queue is in expected initial state.
        async def _wait_initial() -> None:
            deadline = asyncio.get_running_loop().time() + 0.5
            while True:
                cur0, q0 = await q.list_queue(limit=10)
                if cur0 is not None and cur0.video_id == "a" * 11 and len(q0) == 1 and q0[0].video_id == "b" * 11:
                    return
                if asyncio.get_running_loop().time() >= deadline:
                    raise AssertionError(f"unexpected initial queue: cur={cur0} q={[t.video_id for t in q0]}")
                await asyncio.sleep(0)

        await _wait_initial()
        await asyncio.wait_for(mp.skip_now(), timeout=1.0)

        # Supervisor loop should still be running and should pick up next track.
        async def _wait_current_b() -> None:
            deadline = asyncio.get_running_loop().time() + 0.5
            while True:
                cur, _ = await q.list_queue(limit=10)
                if cur is not None and cur.video_id == "b" * 11:
                    return
                if asyncio.get_running_loop().time() >= deadline:
                    raise AssertionError(f"unexpected post-skip current: {cur}")
                await asyncio.sleep(0)

        await _wait_current_b()
        assert mp.running
    finally:
        await asyncio.wait_for(mp.stop(), timeout=1.0)
