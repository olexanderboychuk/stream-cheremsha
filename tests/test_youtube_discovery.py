from unittest.mock import MagicMock

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
    service.search.assert_not_called()
    service.videos.assert_not_called()


def test_discover_skips_non_live_broadcast_rows() -> None:
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
    service.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": {"videoId": "dQw4w9WgXcQ"}}],
        "nextPageToken": None,
    }
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC99"}}],
    }
    assert discover_my_live_chat_ids(service) == ["LC99"]
    search_list = service.search.return_value.list
    assert search_list.call_args is not None
    assert search_list.call_args.kwargs["channelId"] == "UCchannel"
    assert search_list.call_args.kwargs["eventType"] == "live"


def test_discover_search_fallback_when_no_broadcast_rows() -> None:
    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }
    service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UCmine"}],
    }
    service.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": {"videoId": "dQw4w9WgXcQ"}}],
        "nextPageToken": None,
    }
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"liveStreamingDetails": {"activeLiveChatId": "LC99"}}],
    }
    assert discover_my_live_chat_ids(service) == ["LC99"]


def test_discover_no_search_without_channel() -> None:
    service = MagicMock()
    service.liveBroadcasts.return_value.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }
    service.channels.return_value.list.return_value.execute.return_value = {"items": []}
    assert discover_my_live_chat_ids(service) == []
    service.search.return_value.list.assert_not_called()
