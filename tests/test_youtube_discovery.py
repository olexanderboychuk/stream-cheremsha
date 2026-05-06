from unittest.mock import MagicMock

import pytest

from stream_cheremsha.chat.youtube_source import (
    _dedupe_strs,
    _live_broadcast_row_is_on_air,
    discover_my_live_chat_ids,
)


def test_dedupe_strs_order() -> None:
    assert _dedupe_strs(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_discover_prefers_live_broadcasts_live_chat_id() -> None:
    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [
            {"snippet": {"liveChatId": "LC1"}, "status": {"lifeCycleStatus": "live"}},
            {"snippet": {"liveChatId": "LC2"}, "status": {"lifeCycleStatus": "testing"}},
        ],
        "nextPageToken": None,
    }
    assert discover_my_live_chat_ids(service) == ["LC1", "LC2"]
    service.channels.return_value.list.assert_not_called()
    service.search.return_value.list.assert_not_called()
    service.videos.assert_not_called()


def test_discover_skips_non_live_broadcast_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _live_broadcast_row_is_on_air({"status": {"lifeCycleStatus": "ready"}}) is False
    assert _live_broadcast_row_is_on_air({"status": {"lifeCycleStatus": "live"}}) is True
    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [
            {"snippet": {"liveChatId": "X"}, "status": {"lifeCycleStatus": "ready"}},
        ],
        "nextPageToken": None,
    }
    service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UCchannel"}],
    }
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC99"}}],
    }

    def fake_rss(cid: str) -> list[str]:
        assert cid == "UCchannel"
        return ["dQw4w9WgXcQ"]

    monkeypatch.setattr(
        "stream_cheremsha.chat.youtube_source.fetch_channel_video_ids_from_rss",
        fake_rss,
    )

    assert discover_my_live_chat_ids(service) == ["LC99"]
    service.search.return_value.list.assert_not_called()
    videos_list = service.videos.return_value.list
    assert videos_list.call_args is not None
    assert videos_list.call_args.kwargs["part"] == "liveStreamingDetails"
    assert videos_list.call_args.kwargs["id"] == "dQw4w9WgXcQ"


def test_discover_rss_fallback_when_no_broadcast_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }
    service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UCmine"}],
    }
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC99"}}],
    }

    monkeypatch.setattr(
        "stream_cheremsha.chat.youtube_source.fetch_channel_video_ids_from_rss",
        lambda _cid: ["dQw4w9WgXcQ"],
    )

    assert discover_my_live_chat_ids(service) == ["LC99"]
    service.search.return_value.list.assert_not_called()


def test_discover_no_rss_without_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def spy_rss(cid: str) -> list[str]:
        called.append(cid)
        return []

    monkeypatch.setattr(
        "stream_cheremsha.chat.youtube_source.fetch_channel_video_ids_from_rss",
        spy_rss,
    )

    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }
    service.channels.return_value.list.return_value.execute.return_value = {"items": []}
    assert discover_my_live_chat_ids(service) == []
    service.search.return_value.list.assert_not_called()
    assert called == []
