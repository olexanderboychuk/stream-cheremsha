import asyncio
from pathlib import Path
from datetime import datetime, timezone

from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.domain.models import ChatPlatform


class FakeSink:
    def __init__(self) -> None:
        self.mp3_calls: list[bytes] = []

    async def play_mp3(self, data: bytes) -> None:
        self.mp3_calls.append(bytes(data))


class CapturingEngine(PlatformActionsEngine):
    def __init__(self, rules: list[RuleV1]) -> None:
        super().__init__(FakeSink(), rules, status_callback=lambda _msg: None)
        self.dispatched: list[str] = []

    async def _dispatch_actions(self, rule: RuleV1, ev: ChatMessageEvent) -> None:
        _ = ev
        self.dispatched.append(rule.id)


def test_engine_matches_chat_keyword_and_dispatches() -> None:
    rules = [
        RuleV1(
            id='r1',
            enabled=True,
            event={'type': 'chat_keyword', 'params': {'keyword': 'hello'}},
            actions=[{'type': 'noop', 'params': {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author='alice',
        text='hello world',
        received_at=datetime.now(tz=timezone.utc),
    )

    asyncio.run(engine.on_chat_message(ev))

    assert engine.dispatched == ['r1']


def test_engine_does_not_dispatch_when_not_matched() -> None:
    rules = [
        RuleV1(
            id='r1',
            enabled=True,
            event={'type': 'chat_keyword', 'params': {'keyword': 'bye'}},
            actions=[{'type': 'noop', 'params': {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author='alice',
        text='hello world',
        received_at=datetime.now(tz=timezone.utc),
    )

    asyncio.run(engine.on_chat_message(ev))

    assert engine.dispatched == []


def test_engine_executes_play_sound_action(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert sink.mp3_calls == [b"mp3-bytes"]


def test_engine_missing_sound_file_reports_status(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp3"
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "play_sound", "params": {"file_path": str(missing)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert sink.mp3_calls == []
    assert any("not found" in m for m in st)
