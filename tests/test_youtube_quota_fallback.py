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
from stream_cheremsha.chat.youtube_source import YouTubeChatSource
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
        await asyncio.wait_for(src._task, timeout=2.0)

    asyncio.run(_run())
    assert any("фоллбек" in s.lower() for s in statuses)
    assert [m.text for m in coord.messages] == ["hi"]


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
        await asyncio.wait_for(src._task, timeout=2.0)

    asyncio.run(_run())
    assert any("фоллбек" in s.lower() for s in statuses)
    assert [m.text for m in coord.messages] == ["hi"]
