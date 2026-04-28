import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
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


def test_engine_matches_gift_received_and_executes_action(tmp_path: Path) -> None:
    p = tmp_path / "gift.mp3"
    p.write_bytes(b"gift-mp3")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "gift_received", "params": {"gift_name": "Rose", "min_count": 2}},
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TWITCH,
        sender="bob",
        gift_id="",
        gift_name="rose",
        count=2,
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"gift-mp3"]


def test_engine_executes_write_file_action(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    out.write_text("OLD\n", encoding="utf-8")
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "write_file", "params": {"file_path": str(out), "text": "hi\\n"}}],
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
    assert out.read_text(encoding="utf-8") == "hi\\n"
    assert st == []


def test_engine_write_file_append_mode(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    out.write_text("OLD\n", encoding="utf-8")
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[
                {
                    "type": "write_file",
                    "params": {"file_path": str(out), "text": "hi\\n", "mode": "append"},
                }
            ],
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
    assert out.read_text(encoding="utf-8") == "OLD\nhi\\n\n"
    assert st == []


def test_engine_write_file_append_adds_newline_between_entries(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    # No trailing newline on purpose.
    out.write_text("OLD", encoding="utf-8")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[
                {
                    "type": "write_file",
                    "params": {"file_path": str(out), "text": "hi", "mode": "append"},
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert out.read_text(encoding="utf-8") == "OLD\nhi\n"

def test_engine_write_file_supports_placeholders_in_path(tmp_path: Path) -> None:
    out_tmpl = tmp_path / "{author}-{platform}.txt"
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "write_file", "params": {"file_path": str(out_tmpl), "text": "hi\\n"}}],
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
    out = tmp_path / "alice-twitch.txt"
    assert out.read_text(encoding="utf-8") == "hi\\n"
    assert st == []


def test_engine_runs_multiple_actions_in_parallel(tmp_path: Path) -> None:
    p1 = tmp_path / "a.mp3"
    p2 = tmp_path / "b.mp3"
    p1.write_bytes(b"a")
    p2.write_bytes(b"b")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[
                {"type": "play_sound", "params": {"file_path": str(p1)}},
                {"type": "play_sound", "params": {"file_path": str(p2)}},
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_chat_message(ev))
    # Order is not guaranteed when actions run concurrently.
    assert sorted(sink.mp3_calls) == sorted([b"a", b"b"])


def test_engine_run_program_invokes_interpreter() -> None:
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[
                {
                    "type": "run_program",
                    "params": {"program_path": sys.executable, "arguments": "-c pass"},
                },
            ],
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
    assert st == []


def test_engine_run_exe_legacy_type_and_exe_path_key() -> None:
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[
                {"type": "run_exe", "params": {"exe_path": sys.executable, "arguments": "-c pass"}},
            ],
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
    assert st == []


def test_engine_speak_tts_invokes_callback() -> None:
    sink = FakeSink()
    spoken: list[str] = []

    async def speak(s: str) -> None:
        spoken.append(s)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "speak_tts", "params": {"text": "Привіт"}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, tts_speak=speak)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=timezone.utc),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert spoken == ["Привіт"]


def test_engine_speak_tts_without_callback_reports_status() -> None:
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            event={"type": "chat_keyword", "params": {"keyword": "hello"}},
            actions=[{"type": "speak_tts", "params": {"text": "x"}}],
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
    assert any("not configured" in m for m in st)
