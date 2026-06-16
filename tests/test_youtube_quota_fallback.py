import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

import stream_cheremsha.chat.youtube_source as yt_mod
from stream_cheremsha.chat.youtube_chat_downloader import (
    ChatDownloaderMessage,
    pump_messages_to_queue,
)
from stream_cheremsha.chat.youtube_source import YouTubeActionSignal, YouTubeChatSource
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform


def test_chat_downloader_adapter_pushes_messages_into_async_queue() -> None:
    async def _run() -> None:
        loop = asyncio.get_running_loop()
        q: asyncio.Queue[ChatDownloaderMessage] = asyncio.Queue()

        def _iter() -> Iterator[dict[str, str]]:
            yield {"author": "a", "message": "hi"}

        pump_messages_to_queue(_iter(), q, loop)
        m = await asyncio.wait_for(q.get(), timeout=1.0)
        assert m.author == "a"
        assert m.text == "hi"

    asyncio.run(_run())


class _Coord:
    def __init__(self) -> None:
        self.messages: list[ChatMessage] = []

    async def enqueue_chat(self, msg: ChatMessage) -> None:
        self.messages.append(msg)


def _make_source(on_action_event: object = None) -> YouTubeChatSource:
    return YouTubeChatSource(
        coordinator=_Coord(),  # type: ignore[arg-type]
        on_status=lambda _s: None,
        on_analytics_event=None,
        get_locale=lambda: "uk",
        on_action_event=on_action_event,  # type: ignore[arg-type]
    )


def test_ingest_emits_superchat_action_signal_with_amount() -> None:
    signals: list[YouTubeActionSignal] = []
    src = _make_source(signals.append)
    snippet = {
        "type": "superChatEvent",
        "superChatDetails": {
            "amountMicros": "5000000",
            "currency": "USD",
            "amountDisplayString": "$5.00",
        },
    }
    src._ingest_analytics_item(
        author="Alice",
        snippet=snippet,
        text="great stream",
        profile_image_url="https://yt3.ggpht.com/alice.png",
    )
    assert len(signals) == 1
    s = signals[0]
    assert s.kind == "superchat"
    assert s.user == "Alice"
    assert s.amount_micros == 5_000_000
    assert s.currency == "USD"
    assert s.amount_display == "$5.00"
    assert s.message == "great stream"
    assert s.profile_image_url == "https://yt3.ggpht.com/alice.png"


def test_ingest_emits_member_milestone_signal_with_months() -> None:
    signals: list[YouTubeActionSignal] = []
    src = _make_source(signals.append)
    snippet = {
        "type": "memberMilestoneChatEvent",
        "memberMilestoneChatDetails": {"memberLevelName": "Gold", "memberMonth": 6},
    }
    src._ingest_analytics_item(author="Bob", snippet=snippet, text="")
    assert len(signals) == 1
    s = signals[0]
    assert s.kind == "member"
    assert s.user == "Bob"
    assert s.months == 6
    assert s.level == "Gold"


def test_ingest_plain_chat_emits_no_action_signal() -> None:
    signals: list[YouTubeActionSignal] = []
    src = _make_source(signals.append)
    src._ingest_analytics_item(
        author="Carol",
        snippet={"type": "textMessageEvent"},
        text="hello",
    )
    assert signals == []


def _quota_http_error() -> HttpError:
    resp = MagicMock()
    resp.status = 403
    return HttpError(
        resp=resp,
        content=b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}',
    )


def _access_not_configured_http_error() -> HttpError:
    resp = MagicMock()
    resp.status = 403
    return HttpError(
        resp=resp,
        content=b'{"error":{"errors":[{"reason":"accessNotConfigured"}]}}',
    )


def test_youtube_switches_to_fallback_on_quota_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    quota = _quota_http_error()
    service = MagicMock()
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC1"}}],
    }
    service.liveChatMessages.return_value.list.return_value.execute.side_effect = quota

    monkeypatch.setattr(yt_mod, "build", lambda *a, **k: service)
    creds = MagicMock()
    creds.expired = False
    monkeypatch.setattr(yt_mod, "_load_credentials", lambda: creds)

    coord = _Coord()
    statuses: list[str] = []
    src = YouTubeChatSource(
        coordinator=coord,  # type: ignore[arg-type]
        on_status=statuses.append,
        on_analytics_event=None,
        get_locale=lambda: "uk",
    )

    async def _fake_fallback_watch(_self: YouTubeChatSource, _url: str) -> None:
        await coord.enqueue_chat(
            ChatMessage(
                author="a",
                text="hi",
                platform=ChatPlatform.YOUTUBE,
                received_at=datetime.now(UTC),
            ),
        )

    monkeypatch.setattr(YouTubeChatSource, "_run_fallback_for_watch_url", _fake_fallback_watch)

    async def _run() -> None:
        await src.start("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert src._task is not None
        deadline = asyncio.get_running_loop().time() + 2.0
        while asyncio.get_running_loop().time() < deadline and not coord.messages:
            await asyncio.sleep(0.02)
        await src.stop()

    asyncio.run(_run())
    assert any("фоллбек" in s.lower() for s in statuses)
    assert coord.messages and coord.messages[0].text == "hi"


def test_youtube_switches_to_fallback_when_api_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    err = _access_not_configured_http_error()
    service = MagicMock()
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC1"}}],
    }
    service.liveChatMessages.return_value.list.return_value.execute.side_effect = err

    monkeypatch.setattr(yt_mod, "build", lambda *a, **k: service)
    creds = MagicMock()
    creds.expired = False
    monkeypatch.setattr(yt_mod, "_load_credentials", lambda: creds)

    coord = _Coord()
    statuses: list[str] = []
    src = YouTubeChatSource(
        coordinator=coord,  # type: ignore[arg-type]
        on_status=statuses.append,
        on_analytics_event=None,
        get_locale=lambda: "uk",
    )

    async def _fake_fallback_watch(_self: YouTubeChatSource, _url: str) -> None:
        await coord.enqueue_chat(
            ChatMessage(
                author="a",
                text="hi",
                platform=ChatPlatform.YOUTUBE,
                received_at=datetime.now(UTC),
            ),
        )

    monkeypatch.setattr(YouTubeChatSource, "_run_fallback_for_watch_url", _fake_fallback_watch)

    async def _run() -> None:
        await src.start("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert src._task is not None
        deadline = asyncio.get_running_loop().time() + 2.0
        while asyncio.get_running_loop().time() < deadline and not coord.messages:
            await asyncio.sleep(0.02)
        await src.stop()

    asyncio.run(_run())
    assert any("фоллбек" in s.lower() for s in statuses)
    assert coord.messages and coord.messages[0].text == "hi"
