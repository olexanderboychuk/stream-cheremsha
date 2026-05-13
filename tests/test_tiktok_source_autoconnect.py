import asyncio

import pytest

import stream_cheremsha.chat.tiktok_source as tk_mod
from stream_cheremsha.chat.tiktok_source import TikTokChatSource
from stream_cheremsha.pipeline.coordinator import StreamCoordinator


class _FakeCoordinator(StreamCoordinator):
    def __init__(self) -> None:
        # Coordinator is only used for enqueue_chat; keep it minimal.
        # We don't start any workers here.
        super().__init__(
            tts=None,  # type: ignore[arg-type]
            audio_sink=None,  # type: ignore[arg-type]
            on_chat=lambda _msg: None,
            on_status=lambda _msg: None,
        )


class _FakeWeb:
    async def fetch_room_info(self):  # noqa: ANN001
        return {}


class _FakeTikTokClient:
    def __init__(self, unique_id: str) -> None:
        self.unique_id = unique_id
        self.is_live_calls = 0
        self.start_called = False
        self._handlers: dict[object, list[object]] = {}
        self._gate_live: asyncio.Event | None = None
        self._fake_web = _FakeWeb()

    @property
    def web(self) -> _FakeWeb:
        return self._fake_web

    def on(self, event_type: object):  # noqa: ANN001
        def _decorator(fn):  # noqa: ANN001
            gt = getattr(event_type, "get_type", None)
            key = gt() if callable(gt) else event_type
            self._handlers.setdefault(key, []).append(fn)
            return fn

        return _decorator

    async def is_live(self) -> bool:
        self.is_live_calls += 1
        # Allow the test to deterministically pause before "becoming live".
        if self.is_live_calls >= 3:
            if self._gate_live is not None:
                await self._gate_live.wait()
            return True
        return False

    async def start(self, **_kwargs):  # noqa: ANN001
        self.start_called = True

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    async def disconnect(self, **_kwargs):  # noqa: ANN001
        return None

    async def close(self) -> None:
        return None


def test_tiktok_source_polls_is_live_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    # Speed up retries.
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    client = _FakeTikTokClient("user1")

    def _factory(unique_id: str):
        assert unique_id == "user1"
        return client

    statuses: list[str] = []
    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=statuses.append,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=_factory,  # type: ignore[arg-type]
    )

    async def _run() -> None:
        client._gate_live = asyncio.Event()
        await src.start("user1")
        # After two polls (still offline), we should NOT have called start/connect yet.
        await asyncio.wait_for(_wait_until(lambda: client.is_live_calls >= 2), timeout=1.0)
        assert client.start_called is False

        # Eventually is_live becomes True and we connect.
        client._gate_live.set()
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await src.stop()

    asyncio.run(_run())


def test_tiktok_source_suppresses_backlog_comments_before_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Make reconnect loop fast and deterministic.
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    # Patch the event "types" used as keys in @client.on(...)
    class _Connect:  # noqa: N801
        pass

    class _Comment:  # noqa: N801
        pass

    class _Disconnect:  # noqa: N801
        pass

    class _LiveEnd:  # noqa: N801
        pass

    monkeypatch.setattr(tk_mod, "ConnectEvent", _Connect)
    monkeypatch.setattr(tk_mod, "CommentEvent", _Comment)
    monkeypatch.setattr(tk_mod, "DisconnectEvent", _Disconnect)
    monkeypatch.setattr(tk_mod, "LiveEndEvent", _LiveEnd)

    # Freeze connect "now".
    monkeypatch.setattr(tk_mod.time, "time", lambda: 1000.0)

    client = _FakeTikTokClient("user1")
    client.is_live = lambda: asyncio.sleep(0, result=True)  # type: ignore[method-assign]

    async def _start_and_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        # Emit ConnectEvent (sets cutoff=1000.0).
        for fn in client._handlers.get(_Connect, []):
            await fn(type("E", (), {"unique_id": "user1"})())

        # Emit two comments: one older than cutoff, one newer.
        old = type(
            "C",
            (),
            {"create_time": 999, "user_info": type("U", (), {"nickname": "a"})(), "comment": "old"},
        )()
        new = type(
            "C",
            (),
            {
                "create_time": 1001,
                "user_info": type("U", (), {"nickname": "b"})(),
                "comment": "new",
            },
        )()
        for fn in client._handlers.get(_Comment, []):
            await fn(old)
            await fn(new)

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    client.start = _start_and_emit  # type: ignore[assignment]

    class _Coord:
        def __init__(self) -> None:
            self.messages: list[object] = []

        async def enqueue_chat(self, msg):  # noqa: ANN001
            self.messages.append(msg)

    coord = _Coord()
    statuses: list[str] = []
    src = TikTokChatSource(
        coordinator=coord,  # type: ignore[arg-type]
        on_status=statuses.append,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
    )

    async def _run() -> None:
        await src.start("user1")
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await asyncio.sleep(0.03)
        await src.stop()

    asyncio.run(_run())

    assert [getattr(m, "text", None) for m in coord.messages] == ["new"]


def test_tiktok_source_suppresses_backlog_without_timestamps_right_after_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    class _Connect:  # noqa: N801
        pass

    class _Comment:  # noqa: N801
        pass

    class _Disconnect:  # noqa: N801
        pass

    class _LiveEnd:  # noqa: N801
        pass

    monkeypatch.setattr(tk_mod, "ConnectEvent", _Connect)
    monkeypatch.setattr(tk_mod, "CommentEvent", _Comment)
    monkeypatch.setattr(tk_mod, "DisconnectEvent", _Disconnect)
    monkeypatch.setattr(tk_mod, "LiveEndEvent", _LiveEnd)

    # Freeze epoch time; do NOT patch monotonic (asyncio uses it for scheduling).
    monkeypatch.setattr(tk_mod.time, "time", lambda: 1000.0)

    client = _FakeTikTokClient("user1")
    client.is_live = lambda: asyncio.sleep(0, result=True)  # type: ignore[method-assign]

    async def _start_and_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        for fn in client._handlers.get(_Connect, []):
            await fn(type("E", (), {"unique_id": "user1"})())

        # No timestamps available on these comment events.
        early = type(
            "C", (), {"user_info": type("U", (), {"nickname": "a"})(), "comment": "early"}
        )()
        late = type("C", (), {"user_info": type("U", (), {"nickname": "b"})(), "comment": "late"})()

        for fn in client._handlers.get(_Comment, []):
            await fn(early)
            # Wait past backlog window so the second message is accepted.
            await asyncio.sleep(0.02)
            await fn(late)

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    client.start = _start_and_emit  # type: ignore[assignment]

    class _Coord:
        def __init__(self) -> None:
            self.messages: list[object] = []

        async def enqueue_chat(self, msg):  # noqa: ANN001
            self.messages.append(msg)

    coord = _Coord()
    src = TikTokChatSource(
        coordinator=coord,  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
    )
    src._comment_backlog_window_sec = 0.01

    async def _run() -> None:
        await src.start("user1")
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await asyncio.sleep(0.03)
        await src.stop()

    asyncio.run(_run())

    assert [getattr(m, "text", None) for m in coord.messages] == ["late"]


def _install_event_class_stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, type]:
    """Patch TikTokLive event classes referenced by the source module with bare stand-ins.

    Returns a mapping name -> stub class so individual tests can register handlers on
    the fake client and emit synthetic events.
    """

    class _Connect:  # noqa: N801
        pass

    class _Comment:  # noqa: N801
        pass

    class _Disconnect:  # noqa: N801
        pass

    class _LiveEnd:  # noqa: N801
        pass

    class _Gift:  # noqa: N801
        pass

    class _Follow:  # noqa: N801
        pass

    class _Share:  # noqa: N801
        pass

    class _Join:  # noqa: N801
        pass

    class _Like:  # noqa: N801
        pass

    class _Subscribe:  # noqa: N801
        pass

    monkeypatch.setattr(tk_mod, "ConnectEvent", _Connect)
    monkeypatch.setattr(tk_mod, "CommentEvent", _Comment)
    monkeypatch.setattr(tk_mod, "DisconnectEvent", _Disconnect)
    monkeypatch.setattr(tk_mod, "LiveEndEvent", _LiveEnd)
    monkeypatch.setattr(tk_mod, "GiftEvent", _Gift)
    monkeypatch.setattr(tk_mod, "FollowEvent", _Follow)
    monkeypatch.setattr(tk_mod, "ShareEvent", _Share)
    monkeypatch.setattr(tk_mod, "JoinEvent", _Join)
    monkeypatch.setattr(tk_mod, "LikeEvent", _Like)
    monkeypatch.setattr(tk_mod, "SubscribeEvent", _Subscribe)

    return {
        "Connect": _Connect,
        "Comment": _Comment,
        "Disconnect": _Disconnect,
        "LiveEnd": _LiveEnd,
        "Gift": _Gift,
        "Follow": _Follow,
        "Share": _Share,
        "Join": _Join,
        "Like": _Like,
        "Subscribe": _Subscribe,
    }


def test_tiktok_source_suppresses_pre_connect_gifts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gifts whose timestamp predates the ConnectEvent must not fire callbacks."""
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)
    stubs = _install_event_class_stubs(monkeypatch)
    # Freeze "now" so the connect cutoff is deterministic.
    monkeypatch.setattr(tk_mod.time, "time", lambda: 1000.0)

    client = _FakeTikTokClient("user1")
    client.is_live = lambda: asyncio.sleep(0, result=True)  # type: ignore[method-assign]

    async def _start_and_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        for fn in client._handlers.get(stubs["Connect"], []):
            await fn(type("E", (), {"unique_id": "user1"})())

        old_gift = type(
            "G",
            (),
            {
                "create_time": 999,
                "user": type("U", (), {"nickname": "alice"})(),
                "gift": type("Gift", (), {"id": "1", "name": "rose"})(),
                "repeat_count": 1,
                "repeat_end": True,
            },
        )()
        fresh_gift = type(
            "G",
            (),
            {
                "create_time": 1001,
                "user": type("U", (), {"nickname": "bob"})(),
                "gift": type("Gift", (), {"id": "2", "name": "lion"})(),
                "repeat_count": 1,
                "repeat_end": True,
            },
        )()
        for fn in client._handlers.get(stubs["Gift"], []):
            await fn(old_gift)
            await fn(fresh_gift)

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    client.start = _start_and_emit  # type: ignore[assignment]

    gifts: list[tuple[str, str, str, int]] = []

    def _on_gift(  # noqa: ANN001
        sender,
        gift_id,
        gift_name,
        count,
        _icon_url,
        _sender_avatar,
        _diamonds_each,
    ):
        gifts.append((sender, gift_id, gift_name, count))

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=lambda _s: None,
        on_gift=_on_gift,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
    )

    async def _run() -> None:
        await src.start("user1")
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await asyncio.sleep(0.03)
        await src.stop()

    asyncio.run(_run())

    assert gifts == [("bob", "2", "lion", 1)]


def test_tiktok_source_suppresses_post_connect_burst_for_actions_without_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Action events lacking timestamps are suppressed inside the post-connect window."""
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)
    stubs = _install_event_class_stubs(monkeypatch)
    monkeypatch.setattr(tk_mod.time, "time", lambda: 1000.0)

    client = _FakeTikTokClient("user1")
    client.is_live = lambda: asyncio.sleep(0, result=True)  # type: ignore[method-assign]

    follows: list[str] = []
    shares: list[tuple[str, int]] = []
    paid_subs: list[str] = []

    async def _start_and_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        for fn in client._handlers.get(stubs["Connect"], []):
            await fn(type("E", (), {"unique_id": "user1"})())

        burst_follow = type("F", (), {"user": type("U", (), {"nickname": "f1"})()})()
        burst_share = type(
            "S",
            (),
            {"user": type("U", (), {"nickname": "s1"})(), "count": 1},
        )()
        burst_sub = type("P", (), {"user": type("U", (), {"nickname": "p1"})()})()
        for fn in client._handlers.get(stubs["Follow"], []):
            await fn(burst_follow)
        for fn in client._handlers.get(stubs["Share"], []):
            await fn(burst_share)
        for fn in client._handlers.get(stubs["Subscribe"], []):
            await fn(burst_sub)

        await asyncio.sleep(0.02)

        live_follow = type("F", (), {"user": type("U", (), {"nickname": "f2"})()})()
        live_share = type(
            "S",
            (),
            {"user": type("U", (), {"nickname": "s2"})(), "count": 1},
        )()
        live_sub = type("P", (), {"user": type("U", (), {"nickname": "p2"})()})()
        for fn in client._handlers.get(stubs["Follow"], []):
            await fn(live_follow)
        for fn in client._handlers.get(stubs["Share"], []):
            await fn(live_share)
        for fn in client._handlers.get(stubs["Subscribe"], []):
            await fn(live_sub)

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    client.start = _start_and_emit  # type: ignore[assignment]

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=lambda _s: None,
        on_gift=None,
        on_follow=follows.append,
        on_share=lambda user, n: shares.append((user, n)),
        on_paid_sub=paid_subs.append,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
    )
    src._action_backlog_window_sec = 0.01

    async def _run() -> None:
        await src.start("user1")
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await asyncio.sleep(0.05)
        await src.stop()

    asyncio.run(_run())

    assert follows == ["f2"]
    assert shares == [("s2", 1)]
    assert paid_subs == ["p2"]


def test_tiktok_source_seeds_like_baseline_silently_on_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first like event after connect carries a cumulative total — don't fire actions."""
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)
    stubs = _install_event_class_stubs(monkeypatch)
    monkeypatch.setattr(tk_mod.time, "time", lambda: 1000.0)

    client = _FakeTikTokClient("user1")
    client.is_live = lambda: asyncio.sleep(0, result=True)  # type: ignore[method-assign]

    likes: list[tuple[str, int]] = []

    async def _start_and_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        for fn in client._handlers.get(stubs["Connect"], []):
            await fn(type("E", (), {"unique_id": "user1"})())

        first_like = type(
            "L",
            (),
            {
                "user": type("U", (), {"nickname": "viewer"})(),
                "likeCount": 50000,
                "create_time": 1001,
            },
        )()
        for fn in client._handlers.get(stubs["Like"], []):
            await fn(first_like)

        second_like = type(
            "L",
            (),
            {
                "user": type("U", (), {"nickname": "viewer"})(),
                "likeCount": 50003,
                "create_time": 1002,
            },
        )()
        for fn in client._handlers.get(stubs["Like"], []):
            await fn(second_like)

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    client.start = _start_and_emit  # type: ignore[assignment]

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=lambda _s: None,
        on_gift=None,
        on_like=lambda user, n, _avatar="": likes.append((user, n)),
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
    )

    async def _run() -> None:
        await src.start("user1")
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await asyncio.sleep(0.03)
        await src.stop()

    asyncio.run(_run())

    assert likes == [("viewer", 3)]


async def _wait_until(pred, timeout_sec: float = 1.0) -> None:  # noqa: ANN001
    start = asyncio.get_running_loop().time()
    while True:
        if pred():
            return
        if (asyncio.get_running_loop().time() - start) > timeout_sec:
            raise TimeoutError("predicate not satisfied")
        await asyncio.sleep(0.005)
