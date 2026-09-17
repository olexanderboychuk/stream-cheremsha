from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator


class _MockTts:
    def __init__(self, synth_delay: float = 0.05) -> None:
        self.synth_delay = synth_delay
        self.synth_calls: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.synth_calls.append(text)
        if self.synth_delay > 0:
            await asyncio.sleep(self.synth_delay)
        return f"audio:{text}".encode()


class _MockSink:
    def __init__(self, play_delay: float = 0.05) -> None:
        self.play_delay = play_delay
        self.played_clips: list[bytes] = []

    async def play_mp3(self, data: bytes) -> None:
        self.played_clips.append(data)
        if self.play_delay > 0:
            await asyncio.sleep(self.play_delay)


@pytest.mark.asyncio
async def test_coordinator_pipelining_synth_and_playback() -> None:
    tts = _MockTts(synth_delay=0.04)
    sink = _MockSink(play_delay=0.08)

    coord = StreamCoordinator(
        tts=tts,
        audio_sink=sink,
        on_chat=lambda _m: None,
        on_status=lambda _s: None,
    )
    await coord.start_workers()
    try:
        # Enqueue two messages
        await coord.enqueue_chat(
            ChatMessage(
                author="alice",
                text="first chunk",
                platform=ChatPlatform.TWITCH,
                received_at=datetime.now(UTC),
            )
        )
        await coord.enqueue_chat(
            ChatMessage(
                author="bob",
                text="second chunk",
                platform=ChatPlatform.TWITCH,
                received_at=datetime.now(UTC),
            )
        )

        # Wait for processing
        await asyncio.sleep(0.3)

        # Both chunks should have been synthesized and played in order
        assert len(tts.synth_calls) >= 2
        assert len(sink.played_clips) >= 2
        assert (
            sink.played_clips[0] == b"audio:alice: first chunk"
            or b"first chunk" in sink.played_clips[0]
        )
    finally:
        await coord.stop_workers()


@pytest.mark.asyncio
async def test_coordinator_flush_drops_both_text_and_audio() -> None:
    tts = _MockTts(synth_delay=0.1)
    sink = _MockSink(play_delay=0.2)

    coord = StreamCoordinator(
        tts=tts,
        audio_sink=sink,
        on_chat=lambda _m: None,
        on_status=lambda _s: None,
    )
    await coord.start_workers()
    try:
        # Put items directly into queues
        coord.tts_jobs.put_nowait("pending text 1")
        coord.tts_jobs.put_nowait("pending text 2")
        coord.audio_jobs.put_nowait(b"pending audio 1")

        assert coord.tts_jobs.qsize() == 2
        assert coord.audio_jobs.qsize() == 1

        await coord.flush_tts()

        # Both queues should be cleared
        assert coord.tts_jobs.empty()
        assert coord.audio_jobs.empty()
    finally:
        await coord.stop_workers()
