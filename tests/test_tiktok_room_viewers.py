"""TikTok live viewer counters forwarded from TikTokLive events."""

from __future__ import annotations

import asyncio

import pytest

import stream_cheremsha.chat.tiktok_source as tk_mod
from stream_cheremsha.chat.tiktok_source import TikTokChatSource


class _FakeCoordinator:
    async def enqueue_chat(self, _msg):  # noqa: ANN001
        return None


class _FakeWeb:
    async def fetch_room_info(self):  # noqa: ANN001
        return {}


class _FakeTikTokClient:
    def __init__(self) -> None:
        self.start_called = False
        self._handlers: dict[object, list[object]] = {}
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
        return True

    async def start(self, **_kwargs):  # noqa: ANN001
        self.start_called = True

        async def _emit_room_seq_zero_totals() -> None:
            evt = type("R", (), {"m_total": 0, "total_user": 12345})()
            for fn in self._handlers.get(_RoomSeq, []):
                await fn(evt)

        async def _emit_join_with_count() -> None:
            evt = type(
                "J",
                (),
                {
                    "user": type("U", (), {"nickname": "Alice"})(),
                    "count": 77,
                },
            )()
            for fn in self._handlers.get(_Join, []):
                await fn(evt)

        async def _run() -> None:
            await _emit_room_seq_zero_totals()
            await _emit_join_with_count()

        return asyncio.create_task(_run())

    async def disconnect(self, **_kwargs):  # noqa: ANN001
        return None

    async def close(self) -> None:
        return None


class _Connect:
    pass


class _Disconnect:
    pass


class _LiveEnd:
    pass


class _RoomSeq:
    pass


class _Join:
    pass


@pytest.fixture(autouse=True)
def _patch_tiktok_viewer_events(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid supervisor reconnect spinning duplicate emits during short asyncio.sleep windows.
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 60.0)
    monkeypatch.setattr(tk_mod, "TIKTOK_VIEWERS_POLL_SEC", 3600.0)
    monkeypatch.setattr(tk_mod, "ConnectEvent", _Connect)
    monkeypatch.setattr(tk_mod, "DisconnectEvent", _Disconnect)
    monkeypatch.setattr(tk_mod, "LiveEndEvent", _LiveEnd)
    monkeypatch.setattr(tk_mod, "RoomUserSeqEvent", _RoomSeq)
    monkeypatch.setattr(tk_mod, "JoinEvent", _Join)
    monkeypatch.setattr(tk_mod, "CommentEvent", type("_Comment", (), {}))
    monkeypatch.setattr(tk_mod, "GiftEvent", None)


def test_room_user_seq_total_updates_but_zero_m_total_does_not_clear_online() -> None:
    """Regression: total_user without m_total must not push online to 0."""

    client = _FakeTikTokClient()
    currents: list[int] = []
    totals: list[int] = []

    async def _start_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        evt = type("R", (), {"m_total": 0, "total_user": 900})()
        for fn in client._handlers.get(_RoomSeq, []):
            await fn(evt)

        async def _done() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_done())

    client.start = _start_emit  # type: ignore[method-assign]

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
        on_room_viewers_current=currents.append,
        on_room_viewers_total=totals.append,
    )

    async def _run() -> None:
        await src.start("user")
        await asyncio.sleep(0.05)
        await src.stop()

    asyncio.run(_run())

    assert currents == []
    assert totals == [900]


def test_join_member_count_updates_online_when_room_seq_has_no_current() -> None:
    client = _FakeTikTokClient()
    currents: list[int] = []
    totals: list[int] = []

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
        on_room_viewers_current=currents.append,
        on_room_viewers_total=totals.append,
    )

    async def _run() -> None:
        await src.start("user")
        await asyncio.sleep(0.05)
        await src.stop()

    asyncio.run(_run())

    assert currents == [77]
    assert totals == [12345]


def test_join_viewer_hint_does_not_override_recent_reliable_current_value(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeTikTokClient()
    currents: list[int] = []

    async def _start_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        # Reliable current viewers observed first (e.g. from RoomUserSeq / HTTP poll).
        evt_room = type("R", (), {"m_total": 8, "total_user": 100})()
        for fn in client._handlers.get(_RoomSeq, []):
            await fn(evt_room)

        # Unreliable join hint shows smaller number; must be ignored.
        evt_join = type(
            "J",
            (),
            {
                "user": type("U", (), {"nickname": "Bob"})(),
                "count": 2,
            },
        )()
        for fn in client._handlers.get(_Join, []):
            await fn(evt_join)

        async def _done() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_done())

    client.start = _start_emit  # type: ignore[method-assign]

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
        on_room_viewers_current=currents.append,
    )

    async def _run() -> None:
        await src.start("user")
        await asyncio.sleep(0.05)
        await src.stop()

    asyncio.run(_run())

    assert currents == [8]


def test_room_seq_anonymous_does_not_override_room_info_value() -> None:
    currents: list[int] = []
    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: _FakeTikTokClient(),  # type: ignore[arg-type]
        on_room_viewers_current=currents.append,
    )

    # Pretend room/info poll already set a higher value.
    src._push_room_viewers_current(6, reliable=True, source="room_info")  # noqa: SLF001

    # RoomUserSeq arrives with only `anonymous` populated (common but misleading).
    evt = type("E", (), {"m_total": None, "total_user": 159, "anonymous": 2, "m_popularity": None})()
    cur, metric = tk_mod._room_viewers_current_metric(evt)
    assert (cur, metric) == (2, "anonymous")
    src._push_room_viewers_current(cur, reliable=False, source="room_user_seq:anonymous")  # noqa: SLF001

    assert currents == [6]


def test_room_viewers_current_prefers_m_total_then_bounded_popularity() -> None:
    assert (
        tk_mod._room_viewers_current(
            type("E", (), {"m_total": 5, "total_user": 100, "m_popularity": 99})(),
        )
        == 5
    )
    assert (
        tk_mod._room_viewers_current(
            type("E", (), {"m_total": 0, "total_user": 1000, "m_popularity": 42})(),
        )
        == 42
    )
    # Likely "heat" rather than concurrent viewers — ignore when >> cumulative viewers.
    assert (
        tk_mod._room_viewers_current(
            type("E", (), {"m_total": 0, "total_user": 100, "m_popularity": 999999})(),
        )
        == 0
    )


def test_room_viewers_multi_live_popularity_when_m_total_missing() -> None:
    """Fused-room concurrent may exceed cumulative total_user while m_total stays 0."""
    assert (
        tk_mod._room_viewers_current(
            type("E", (), {"m_total": 0, "total_user": 8000, "m_popularity": 42000})(),
        )
        == 42000
    )


def test_extract_live_viewers_from_nested_room_payload() -> None:
    assert tk_mod._extract_live_viewers_from_room_payload({"owner": {"user_count": 333}}) == 333
    assert tk_mod._extract_live_viewers_from_room_payload({"viewer_count": 12}) == 12
    assert tk_mod._extract_live_viewers_from_room_payload({"stats": {"live_watch_cnt": 44}}) == 44
    assert tk_mod._extract_live_viewers_from_room_payload({"multi_live_room_stats": {"viewer_count": 55}}) == 55


def test_extract_live_viewers_prefers_max_candidate_when_multiple_present() -> None:
    payload = {
        # Often present but can be unrelated/too small in some room/info shapes.
        "user_count": 2,
        # Real concurrent viewers field (example).
        "stats": {"viewer_count": 8},
    }
    assert tk_mod._extract_live_viewers_from_room_payload(payload) == 8


def test_room_seq_anonymous_used_when_other_counters_missing() -> None:
    evt = type(
        "E",
        (),
        {"m_total": 0, "total_user": 100, "m_popularity": 999999, "anonymous": 12},
    )()
    assert tk_mod._room_viewers_current(evt) == 12


def test_cold_start_event_updates_online_and_total() -> None:
    client = _FakeTikTokClient()
    currents: list[int] = []
    totals: list[int] = []

    async def _start_emit(**_kwargs):  # noqa: ANN001
        client.start_called = True
        evt = type("CS", (), {"viewer_count": 51, "total_count": 888})()
        for fn in client._handlers.get(tk_mod.ColdStartEvent.get_type(), []):
            await fn(evt)

        async def _done() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_done())

    client.start = _start_emit  # type: ignore[method-assign]

    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=lambda _uid: client,  # type: ignore[arg-type]
        on_room_viewers_current=currents.append,
        on_room_viewers_total=totals.append,
    )

    async def _run() -> None:
        await src.start("user")
        await asyncio.sleep(0.05)
        await src.stop()

    asyncio.run(_run())

    assert currents == [51]
    assert totals == [888]

