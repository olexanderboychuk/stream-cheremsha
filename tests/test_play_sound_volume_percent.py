from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

import stream_cheremsha.actions.engine as eng_mod
from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.domain.models import ChatPlatform


class FakeSink:
    async def play_mp3(self, data: bytes) -> None:
        _ = data


def test_play_sound_volume_percent_passed_to_playback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")

    got: dict[str, object] = {}

    async def fake_play_sound_from_file(
        path: str,
        *,
        sink: object,
        volume_percent: int = 100,
        skip_queue_if_same: bool = False,
        play_immediately: bool = False,
    ) -> None:
        _ = skip_queue_if_same
        _ = play_immediately
        got["path"] = path
        got["volume_percent"] = volume_percent
        _ = sink

    monkeypatch.setattr(eng_mod, "play_sound_from_file", fake_play_sound_from_file)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p), "volume_percent": 35}}],
        ),
    ]
    engine = PlatformActionsEngine(FakeSink(), rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert got["path"] == str(p)
    assert got["volume_percent"] == 35


def test_play_sound_volume_is_not_racy_between_concurrent_actions(tmp_path: Path) -> None:
    """
    Regression: volume must apply to *the* sound being played, not be overwritten by another action
    that set sink volume while waiting on sink's internal playback lock.
    """

    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")

    class VolumeAwareSink:
        def __init__(self) -> None:
            self.started: list[float] = []
            self._lock = asyncio.Lock()
            self._release_first: asyncio.Event | None = None

        async def play_mp3(self, data: bytes) -> None:
            _ = data
            async with self._lock:
                self.started.append(1.0)
                if len(self.started) == 1:
                    self._release_first = asyncio.Event()
                    await self._release_first.wait()

        async def play_mp3_with_volume(self, data: bytes, linear: float) -> None:
            _ = data
            async with self._lock:
                self.started.append(float(linear))
                if len(self.started) == 1:
                    self._release_first = asyncio.Event()
                    await self._release_first.wait()

        def release_first(self) -> None:
            if self._release_first is not None:
                self._release_first.set()

    sink = VolumeAwareSink()

    async def run_two() -> None:
        from stream_cheremsha.actions.actions_play_sound import play_sound_from_file

        t1 = asyncio.create_task(play_sound_from_file(str(p), sink=sink, volume_percent=10))
        await asyncio.sleep(0)  # allow t1 to set volume, then block in play_mp3
        t2 = asyncio.create_task(play_sound_from_file(str(p), sink=sink, volume_percent=90))
        await asyncio.sleep(0)  # allow t2 to run and potentially overwrite volume
        sink.release_first()
        await asyncio.gather(t1, t2)

    asyncio.run(run_two())

    # Each playback must start at its configured linear volume.
    assert sink.started == [0.10, 0.90]
