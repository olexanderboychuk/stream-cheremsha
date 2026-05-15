import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.domain.models import ChatPlatform
from stream_cheremsha.overlays.pubsub import OverlayPubSub


class FakeSink:
    def __init__(self) -> None:
        self.mp3_calls: list[bytes] = []
        self._sound_dedupe_lock = asyncio.Lock()
        self._sound_dedupe_keys: set[str] = set()

    async def play_mp3(self, data: bytes) -> None:
        self.mp3_calls.append(bytes(data))

    async def play_mp3_with_volume_deduped(
        self, data: bytes, linear: float, *, dedupe_key: str
    ) -> bool:
        _ = linear
        k = (dedupe_key or "").strip()
        if not k:
            await self.play_mp3(data)
            return True
        async with self._sound_dedupe_lock:
            if k in self._sound_dedupe_keys:
                return False
            self._sound_dedupe_keys.add(k)
        try:
            await self.play_mp3(data)
            return True
        finally:
            async with self._sound_dedupe_lock:
                self._sound_dedupe_keys.discard(k)


class BlockingOnceSink(FakeSink):
    """First play_mp3 waits until ``release`` is set (for overlap / dedupe tests)."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def play_mp3(self, data: bytes) -> None:
        self.entered.set()
        await self.release.wait()
        self.mp3_calls.append(bytes(data))


class CapturingEngine(PlatformActionsEngine):
    def __init__(self, rules: list[RuleV1]) -> None:
        super().__init__(FakeSink(), rules, status_callback=lambda _msg: None)
        self.dispatched: list[str] = []

    async def _dispatch_actions(self, rule: RuleV1, ev: ChatMessageEvent) -> None:
        _ = ev
        self.dispatched.append(rule.id)


def test_engine_chat_or_two_triggers_dispatches_once() -> None:
    rules = [
        RuleV1(
            id="r_or",
            enabled=True,
            events=(
                {"type": "chat_keyword", "params": {"keyword": "hello"}},
                {"type": "chat_keyword", "params": {"keyword": "bye"}},
            ),
            actions=[{"type": "noop", "params": {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="goodbye world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert engine.dispatched == ["r_or"]


def test_engine_matches_chat_keyword_and_dispatches() -> None:
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "noop", "params": {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )

    asyncio.run(engine.on_chat_message(ev))

    assert engine.dispatched == ["r1"]


def test_engine_chat_respects_trigger_platform_tiktok_only() -> None:
    rules = [
        RuleV1(
            id="r_tk",
            enabled=True,
            events=(
                {
                    "type": "chat_keyword",
                    "platform": "tiktok",
                    "params": {"text": "hello", "match": "contains", "case_sensitive": False},
                },
            ),
            actions=[{"type": "noop", "params": {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert engine.dispatched == []


def test_engine_does_not_dispatch_when_not_matched() -> None:
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "bye"}},),
            actions=[{"type": "noop", "params": {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert sink.mp3_calls == [b"mp3-bytes"]


def test_engine_executes_play_random_myinstants_ua_action(monkeypatch) -> None:
    sink = FakeSink()
    calls: list[dict[str, object]] = []

    async def stub(
        *,
        sink,
        volume_percent: int,
        skip_queue_if_same: bool,
        play_immediately: bool,
        max_duration_seconds: float,
        max_page: int,
        skip_words: object,
        status,
    ) -> None:
        _ = status
        calls.append(
            {
                "sink": sink,
                "volume_percent": int(volume_percent),
                "skip_queue_if_same": bool(skip_queue_if_same),
                "play_immediately": bool(play_immediately),
                "max_duration_seconds": float(max_duration_seconds),
                "max_page": int(max_page),
                "skip_words": str(skip_words),
            }
        )

    monkeypatch.setattr("stream_cheremsha.actions.engine.play_random_myinstants_ua", stub)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {
                    "type": "play_random_myinstants_ua",
                    "params": {
                        "volume_percent": 999,
                        "skip_if_same_playing": True,
                        "max_duration_seconds": 5,
                        "max_page": 3,
                        "skip_words": "siren, loud",
                    },
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))

    assert calls == [
        {
            "sink": sink,
            "volume_percent": 100,
            "skip_queue_if_same": True,
            "play_immediately": False,
            "max_duration_seconds": 5.0,
            "max_page": 3,
            "skip_words": "siren, loud",
        },
    ]


def test_engine_play_sound_respects_gift_combo_count(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = FakeSink()
    calls: list[dict[str, object]] = []

    async def fake_play_sound_from_file(
        path: str,
        *,
        sink: object,
        volume_percent: int = 100,
        skip_queue_if_same: bool = False,
        play_immediately: bool = False,
    ) -> None:
        calls.append(
            {
                "path": path,
                "volume_percent": int(volume_percent),
                "skip_queue_if_same": bool(skip_queue_if_same),
                "play_immediately": bool(play_immediately),
            }
        )

    import stream_cheremsha.actions.engine as eng_mod

    monkeypatch.setattr(eng_mod, "play_sound_from_file", fake_play_sound_from_file)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "gift_received", "params": {"gift_name": "Rose"}},),
            actions=[
                {
                    "type": "play_sound",
                    "params": {
                        "file_path": str(p),
                        "volume_percent": 35,
                        "respect_gift_combo": True,
                    },
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="Rose",
        count=3,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev))
    assert len(calls) == 3


def test_engine_play_sound_two_same_file_without_skip_plays_twice(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {"type": "play_sound", "params": {"file_path": str(p)}},
                {"type": "play_sound", "params": {"file_path": str(p)}},
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert sink.mp3_calls == [b"mp3-bytes", b"mp3-bytes"]


def test_engine_play_sound_skip_if_same_playing_skips_overlapping_same_file(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = BlockingOnceSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {
                    "type": "play_sound",
                    "params": {"file_path": str(p), "skip_if_same_playing": True},
                },
                {
                    "type": "play_sound",
                    "params": {"file_path": str(p), "skip_if_same_playing": True},
                },
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )

    async def run() -> None:
        task = asyncio.create_task(engine.on_chat_message(ev))
        await asyncio.wait_for(sink.entered.wait(), timeout=3.0)
        assert sink.mp3_calls == []
        sink.release.set()
        await task
        assert sink.mp3_calls == [b"mp3-bytes"]

    asyncio.run(run())


def test_engine_play_sound_skip_if_same_playing_across_two_overlapping_dispatches(
    tmp_path: Path,
) -> None:
    """Second chat event must be able to dispatch while the first sound is still playing."""
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = BlockingOnceSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {
                    "type": "play_sound",
                    "params": {"file_path": str(p), "skip_if_same_playing": True},
                },
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )

    async def run() -> None:
        t1 = asyncio.create_task(engine.on_chat_message(ev))
        await asyncio.wait_for(sink.entered.wait(), timeout=3.0)
        t2 = asyncio.create_task(engine.on_chat_message(ev))
        await asyncio.sleep(0)
        assert sink.mp3_calls == []
        sink.release.set()
        await asyncio.gather(t1, t2)
        assert sink.mp3_calls == [b"mp3-bytes"]

    asyncio.run(run())


def test_two_action_engines_share_one_sink_skip_duplicate_sound(tmp_path: Path) -> None:
    """Regression: dedupe must live on the sink.

    Each (platform, account) engine used to have its own set.
    """
    p = tmp_path / "a.mp3"
    p.write_bytes(b"mp3-bytes")
    sink = BlockingOnceSink()
    rule = RuleV1(
        id="r1",
        enabled=True,
        events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
        actions=[
            {"type": "play_sound", "params": {"file_path": str(p), "skip_if_same_playing": True}},
        ],
    )
    eng_a = PlatformActionsEngine(sink, [rule])
    eng_b = PlatformActionsEngine(sink, [rule])
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )

    async def run() -> None:
        t1 = asyncio.create_task(eng_a.on_chat_message(ev))
        await asyncio.wait_for(sink.entered.wait(), timeout=3.0)
        t2 = asyncio.create_task(eng_b.on_chat_message(ev))
        await asyncio.sleep(0)
        assert sink.mp3_calls == []
        sink.release.set()
        await asyncio.gather(t1, t2)
        assert sink.mp3_calls == [b"mp3-bytes"]

    asyncio.run(run())


def test_engine_play_sound_skip_if_same_playing_allows_different_files(tmp_path: Path) -> None:
    p1 = tmp_path / "a.mp3"
    p2 = tmp_path / "b.mp3"
    p1.write_bytes(b"aa")
    p2.write_bytes(b"bb")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {
                    "type": "play_sound",
                    "params": {"file_path": str(p1), "skip_if_same_playing": True},
                },
                {
                    "type": "play_sound",
                    "params": {"file_path": str(p2), "skip_if_same_playing": True},
                },
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert sink.mp3_calls == [b"aa", b"bb"]


def test_engine_obs_scene_calls_obs_execute() -> None:
    payloads: list[dict[str, object]] = []

    async def capture(p: dict[str, object]) -> None:
        payloads.append(dict(p))

    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_obs",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "obs"}},),
            actions=[
                {
                    "type": "obs_scene",
                    "params": {"mode": "program_scene", "scene_name": "Alerts"},
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(
        sink, rules, status_callback=lambda _m: None, obs_execute=capture
    )
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="bob",
        text="obs trigger",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert payloads == [
        {
            "mode": "program_scene",
            "scene_name": "Alerts",
            "source_name": "",
            "visible": True,
            "canvas_uuid": "",
        }
    ]


def test_engine_obs_source_visible_revert_schedules_second_call() -> None:
    calls: list[dict[str, object]] = []

    async def capture(p: dict[str, object]) -> None:
        calls.append(dict(p))

    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_obs_rev",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "rev"}},),
            actions=[
                {
                    "type": "obs_scene",
                    "params": {
                        "mode": "source_visible",
                        "scene_name": "Main",
                        "source_name": "Cam",
                        "visible": True,
                        "revert_previous_state": True,
                        "revert_delay_seconds": 0.05,
                    },
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(
        sink, rules, status_callback=lambda _m: None, obs_execute=capture
    )
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="u",
        text="rev",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert len(calls) == 2
    assert calls[0]["visible"] is True
    assert calls[1]["visible"] is False
    assert calls[0]["scene_name"] == calls[1]["scene_name"] == "Main"


def test_engine_obs_revert_skipped_when_delay_zero() -> None:
    calls: list[dict[str, object]] = []

    async def capture(p: dict[str, object]) -> None:
        calls.append(dict(p))

    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_obs_norev",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "x"}},),
            actions=[
                {
                    "type": "obs_scene",
                    "params": {
                        "mode": "source_visible",
                        "scene_name": "Main",
                        "source_name": "Cam",
                        "visible": False,
                        "revert_previous_state": True,
                        "revert_delay_seconds": 0,
                    },
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(
        sink, rules, status_callback=lambda _m: None, obs_execute=capture
    )
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="u",
        text="x",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert len(calls) == 1
    assert calls[0]["visible"] is False


def test_engine_obs_scene_source_visible_false_in_payload() -> None:
    payloads: list[dict[str, object]] = []

    async def capture(p: dict[str, object]) -> None:
        payloads.append(dict(p))

    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_obs2",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hide"}},),
            actions=[
                {
                    "type": "obs_scene",
                    "params": {
                        "mode": "source_visible",
                        "scene_name": "Main",
                        "source_name": "Cam",
                        "visible": False,
                    },
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(
        sink, rules, status_callback=lambda _m: None, obs_execute=capture
    )
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="u",
        text="hide it",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert len(payloads) == 1
    assert payloads[0]["visible"] is False
    assert payloads[0]["mode"] == "source_visible"


def test_engine_missing_sound_file_reports_status(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp3"
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(missing)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "gift_received", "params": {"gift_name": "Rose", "min_count": 2}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="rose",
        count=2,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"gift-mp3"]


def test_engine_gift_respects_trigger_platform_twitch_only() -> None:
    rules = [
        RuleV1(
            id="r_tw_gift",
            enabled=True,
            events=(
                {
                    "type": "gift_received",
                    "platform": "twitch",
                    "params": {"gift_name": "Rose", "min_count": 1},
                },
            ),
            actions=[{"type": "noop", "params": {}}],
        ),
    ]
    engine = CapturingEngine(rules)
    ev_tk = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="a",
        gift_id="",
        gift_name="Rose",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev_tk))
    assert engine.dispatched == []
    ev_tw = GiftReceivedEvent(
        platform=ChatPlatform.TWITCH,
        sender="a",
        gift_id="",
        gift_name="Rose",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev_tw))
    assert engine.dispatched == ["r_tw_gift"]


def test_engine_executes_write_file_action(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    out.write_text("OLD\n", encoding="utf-8")
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "write_file", "params": {"file_path": str(out), "text": "hi\\n"}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
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
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
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
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {"type": "write_file", "params": {"file_path": str(out_tmpl), "text": "hi\\n"}}
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
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
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
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
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert st == []


def test_engine_simulate_keystrokes_invokes_backend() -> None:
    sink = FakeSink()
    captured: list[tuple[str, dict[str, object]]] = []

    def _fake_run(seq: str, **kw: object) -> None:
        captured.append((seq, dict(kw)))

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[
                {
                    "type": "simulate_keystrokes",
                    "params": {
                        "sequence": "{ENTER}{username}",
                        "hold_ms": 50,
                        "game_compatibility": True,
                        "modifier_ctrl": True,
                        "modifier_alt": False,
                        "modifier_shift": True,
                    },
                },
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    with patch("stream_cheremsha.actions.engine.run_simulate_keystrokes", side_effect=_fake_run):
        asyncio.run(engine.on_chat_message(ev))
    assert len(captured) == 1
    seq, kw = captured[0]
    assert seq == "{ENTER}alice"
    assert kw["hold_ms"] == 50
    assert kw["game_mode"] is True
    assert kw["with_ctrl"] is True
    assert kw["with_alt"] is False
    assert kw["with_shift"] is True


def test_engine_simulate_keystrokes_value_error_surfaces_in_status() -> None:
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "simulate_keystrokes", "params": {"sequence": "{BAD}"}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )

    def _boom(_seq: str, **_kw: object) -> None:
        raise ValueError("unit test")

    with patch("stream_cheremsha.actions.engine.run_simulate_keystrokes", side_effect=_boom):
        asyncio.run(engine.on_chat_message(ev))
    assert any("simulate_keystrokes" in m and "unit test" in m for m in st)


def test_engine_run_exe_legacy_type_and_exe_path_key() -> None:
    sink = FakeSink()
    st: list[str] = []
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
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
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert st == []


def test_engine_speak_tts_invokes_callback() -> None:
    sink = FakeSink()
    spoken: list[str] = []

    async def speak(s: str, _author: str | None = None) -> None:
        spoken.append(s)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "speak_tts", "params": {"text": "Привіт"}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, tts_speak=speak)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
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
            events=({"type": "chat_keyword", "params": {"keyword": "hello"}},),
            actions=[{"type": "speak_tts", "params": {"text": "x"}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=st.append)
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="alice",
        text="hello world",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_chat_message(ev))
    assert any("not configured" in m for m in st)


def test_engine_tiktok_likes_all_users_crossing(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 10, "scope": "all_users"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("a", 4, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_likes_received("b", 6, now))
    assert sink.mp3_calls == [b"x"]
    asyncio.run(engine.on_tiktok_likes_received("c", 1, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_user_stream(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 5, "scope": "user_stream"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("Bob", 4, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_likes_received("alice", 5, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_user_combo_any_viewer_when_user_blank(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 3, "scope": "user_combo", "user": ""},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("anyone", 3, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_user_every_n_single_milestone(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 250, "scope": "user_every_n"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("Fan", 240, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_likes_received("Fan", 11, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_user_every_n_two_milestones_one_batch(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 250, "scope": "user_every_n"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("Fan", 240, now))
    asyncio.run(engine.on_tiktok_likes_received("Fan", 270, now))
    assert sink.mp3_calls == [b"x", b"x"]


def test_engine_tiktok_likes_user_every_n_named_viewer_filter(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 10, "scope": "user_every_n", "user": "bob"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("alice", 10, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_likes_received("Bob", 10, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_user_combo(tmp_path: Path) -> None:
    p = tmp_path / "likes.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "tiktok_likes_received",
                    "params": {"min_count": 3, "scope": "user_combo", "user": "x"},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("X", 2, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_likes_received("x", 3, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_likes_placeholder_in_write_file(tmp_path: Path) -> None:
    out = tmp_path / "o.txt"
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {"type": "tiktok_likes_received", "params": {"min_count": 1, "scope": "all_users"}},
            ),
            actions=[
                {"type": "write_file", "params": {"file_path": str(out), "text": "{liketotal}"}}
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_likes_received("u", 7, now))
    assert out.read_text(encoding="utf-8") == "7"


def test_tiktok_likes_preview_batch() -> None:
    sink = FakeSink()
    engine = PlatformActionsEngine(sink, [])
    assert engine.tiktok_likes_preview_batch(scope="all_users", min_count=5, user="") == (
        5,
        "preview",
    )
    asyncio.run(engine.on_tiktok_likes_received("a", 3, datetime.now(tz=UTC)))
    assert engine.tiktok_likes_preview_batch(scope="all_users", min_count=5, user="") == (
        2,
        "preview",
    )
    asyncio.run(engine.on_tiktok_likes_received("b", 2, datetime.now(tz=UTC)))
    assert engine.tiktok_likes_preview_batch(scope="all_users", min_count=5, user="") is None


def test_tiktok_likes_preview_batch_user_every_n() -> None:
    sink = FakeSink()
    engine = PlatformActionsEngine(sink, [])
    assert engine.tiktok_likes_preview_batch(scope="user_every_n", min_count=250, user="") == (
        250,
        "preview",
    )
    asyncio.run(engine.on_tiktok_likes_received("u", 240, datetime.now(tz=UTC)))
    assert engine.tiktok_likes_preview_batch(scope="user_every_n", min_count=250, user="u") == (
        10,
        "u",
    )


def test_engine_tiktok_joined_matches_user_filter(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_joined", "params": {"user": "Bob"}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_joined("alice", now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_joined("bob", now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_followed_matches_user_filter(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_followed", "params": {"user": "Bob"}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_followed("alice", now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_followed("bob", now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_shared_min_count(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_shared", "params": {"min_count": 3}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_shared("bob", 2, now))
    assert sink.mp3_calls == []
    asyncio.run(engine.on_tiktok_shared("bob", 3, now))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_first_activity_fires_once_per_user_per_session(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_first_activity", "params": {}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_joined("bob", now))
    asyncio.run(engine.on_tiktok_followed("alice", now))
    assert sink.mp3_calls == [b"x", b"x"]
    engine.reset_tiktok_like_totals()
    asyncio.run(engine.on_tiktok_followed("alice", now))
    assert sink.mp3_calls == [b"x", b"x", b"x"]


def test_engine_tiktok_any_gift_received_matches_min_price(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 20}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="Perfume",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_any_gift_received_does_not_match_unknown_price(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 1}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="Some Unknown Gift",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
        tiktok_coin_each=0,
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == []


def test_engine_speak_tts_strips_unresolved_placeholders(tmp_path: Path) -> None:
    # When placeholders cannot be resolved (no context), they must not be read aloud.
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    spoken: list[str] = []

    async def speak(s: str, _author: str | None = None) -> None:
        spoken.append(s)

    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_joined", "params": {}},),
            actions=[
                {
                    "type": "speak_tts",
                    "params": {"text": "hello {sender} {unknown} world"},
                }
            ],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, tts_speak=speak)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_tiktok_joined("", now))
    # Sender empty -> removed; unknown -> removed; keep the rest.
    assert spoken == ["hello   world"]


def test_engine_tiktok_any_gift_received_matches_unknown_catalog_via_live_coin_each(
    tmp_path: Path,
) -> None:
    """Stream exposes diamond_count even when our bundled catalog lacks the gift."""
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 1}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="Some Unknown Gift",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
        tiktok_coin_each=5,
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_any_gift_only_highest_min_price_tier(tmp_path: Path) -> None:
    """Among tiktok_any_gift_received rules, only the largest satisfied min_price runs."""
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_low",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 1}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
        RuleV1(
            id="r_mid",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 100}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
        RuleV1(
            id="r_high",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 500}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="UnknownTierGift",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
        tiktok_coin_each=1000,
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"x"]


def test_engine_tiktok_specific_gift_still_fires_alongside_any_gift_tier(tmp_path: Path) -> None:
    """gift_received (specific gift) is independent of any-gift tier selection."""
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_specific",
            enabled=True,
            events=(
                {
                    "type": "gift_received",
                    "params": {"gift_name": "UnknownTierGiftX", "min_count": 1},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
        RuleV1(
            id="r_tier_low",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 1}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
        RuleV1(
            id="r_tier_high",
            enabled=True,
            events=({"type": "tiktok_any_gift_received", "params": {"min_price": 500}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="UnknownTierGiftX",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
        tiktok_coin_each=1000,
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"x", b"x"]


def test_engine_show_overlay_action_publishes_append_with_placeholders_and_gift_icon() -> None:
    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:actions:main")
        rules = [
            RuleV1(
                id="r1",
                enabled=True,
                events=(
                    {"type": "gift_received", "params": {"gift_name": "Rose", "min_count": 1}},
                ),
                actions=[
                    {
                        "type": "show_overlay",
                        "params": {
                            "text": "{sender} подарував {giftname} x{giftcount}",
                            "seconds": 7,
                        },
                    }
                ],
            )
        ]
        engine = PlatformActionsEngine(FakeSink(), rules, pubsub=ps)
        ev = GiftReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            sender="Zerody",
            gift_id="123",
            gift_name="Rose",
            count=2,
            gift_icon_url="https://example.com/gift.png",
            received_at=datetime.now(tz=UTC),
        )
        await engine.on_gift_received(ev)
        return await asyncio.wait_for(q.get(), timeout=1.0)

    patch = asyncio.run(_run())
    app = patch.get("append", {})
    assert app["username"] == "Zerody"
    assert "Rose" in app["text"]
    assert app["gift_picture_url"] == "https://example.com/gift.png"
    assert app["platform"] == "tiktok"
    assert app["show_seconds"] == 7


def test_engine_show_overlay_gift_picture_falls_back_to_catalog_when_live_icon_empty(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "stream_cheremsha.actions.tiktok_gifts.TIKTOK_GIFTS",
        [
            {
                "id": "123",
                "name": "Rose",
                "price": 1,
                "image_url": "https://catalog.example/from-db.png",
            }
        ],
    )

    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:actions:main")
        rules = [
            RuleV1(
                id="r1",
                enabled=True,
                events=({"type": "gift_received", "params": {"gift_id": "123", "min_count": 1}},),
                actions=[{"type": "show_overlay", "params": {"text": "{giftname}", "seconds": 3}}],
            )
        ]
        engine = PlatformActionsEngine(FakeSink(), rules, pubsub=ps)
        ev = GiftReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            sender="u",
            gift_id="123",
            gift_name="Rose",
            count=1,
            gift_icon_url="",
            received_at=datetime.now(tz=UTC),
        )
        await engine.on_gift_received(ev)
        return await asyncio.wait_for(q.get(), timeout=1.0)

    patch = asyncio.run(_run())
    assert patch.get("append", {}).get("gift_picture_url") == "https://catalog.example/from-db.png"
    assert patch.get("append", {}).get("platform") == "tiktok"


def test_engine_gift_received_falls_back_to_name_when_event_missing_id(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r1",
            enabled=True,
            events=(
                {
                    "type": "gift_received",
                    "params": {"gift_id": "123", "gift_name": "Go Popular", "min_count": 1},
                },
            ),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules, status_callback=lambda _m: None)
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="bob",
        gift_id="",
        gift_name="Go Popular",
        count=1,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    asyncio.run(engine.on_gift_received(ev))
    assert sink.mp3_calls == [b"x"]


def test_engine_twitch_follow_and_cheer(tmp_path: Path) -> None:
    p = tmp_path / "a.mp3"
    p.write_bytes(b"x")
    sink = FakeSink()
    rules = [
        RuleV1(
            id="r_tw_f",
            enabled=True,
            events=({"type": "twitch_follow", "params": {"user": ""}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
        RuleV1(
            id="r_tw_bits",
            enabled=True,
            events=({"type": "twitch_cheer", "params": {"min_bits": 50, "user": ""}},),
            actions=[{"type": "play_sound", "params": {"file_path": str(p)}}],
        ),
    ]
    engine = PlatformActionsEngine(sink, rules)
    now = datetime.now(tz=UTC)
    asyncio.run(engine.on_twitch_follow("alice", now))
    assert sink.mp3_calls == [b"x"]
    asyncio.run(engine.on_twitch_cheer("bob", 10, now))
    assert sink.mp3_calls == [b"x"]
    asyncio.run(engine.on_twitch_cheer("bob", 100, now))
    assert sink.mp3_calls == [b"x", b"x"]
