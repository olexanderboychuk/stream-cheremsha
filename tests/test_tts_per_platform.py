from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator


class _NoopSink:
    async def play_mp3(self, _data: bytes) -> None:  # noqa: D401, ANN001
        return


class _NoopTts:
    async def synthesize(self, _text: str) -> bytes:  # noqa: D401, ANN001
        return b""


def test_coordinator_skips_tts_for_platform() -> None:
    async def _run() -> None:
        seen: list[ChatMessage] = []

        def _on_chat(msg: ChatMessage) -> None:
            seen.append(msg)

        def _on_status(_s: str) -> None:
            return

        coord = StreamCoordinator(
            tts=_NoopTts(),  # type: ignore[arg-type]
            audio_sink=_NoopSink(),  # type: ignore[arg-type]
            on_chat=_on_chat,
            on_status=_on_status,
            should_tts=lambda m: m.platform != ChatPlatform.TIKTOK,
        )
        await coord.start_workers()
        try:
            await coord.enqueue_chat(
                ChatMessage(
                    author="a",
                    text="hello",
                    platform=ChatPlatform.TIKTOK,
                    received_at=datetime.now(UTC),
                ),
            )
            await asyncio.sleep(0.05)
            assert coord.tts_jobs.qsize() == 0
            assert len(seen) == 1  # still arrives to UI chat
        finally:
            await coord.stop_workers()

    asyncio.run(_run())
