from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.overlays.chat_overlay import chat_message_to_patch


def test_chat_message_to_patch_shape() -> None:
    msg = ChatMessage(
        author="alice",
        text="hello",
        platform=ChatPlatform.TWITCH,
        received_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )
    p = chat_message_to_patch(msg)
    assert set(p.keys()) == {"append"}
    a = p["append"]
    assert a["author"] == "alice"
    assert a["text"] == "hello"
    assert a["platform"] == "twitch"
    assert a["received_at"] == "2026-01-02T03:04:05Z"


def test_chat_message_to_patch_time_seconds_precision() -> None:
    msg = ChatMessage(
        author="alice",
        text="hello",
        platform=ChatPlatform.TWITCH,
        received_at=datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC),
    )
    p = chat_message_to_patch(msg)
    assert p["append"]["received_at"] == "2026-01-02T03:04:05Z"


def test_chat_message_to_patch_time_converts_to_utc() -> None:
    # +02:00 should convert to Z with correct hour.
    received_at = datetime(
        2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2))
    )
    msg = ChatMessage(
        author="alice",
        text="hello",
        platform=ChatPlatform.TWITCH,
        received_at=received_at,
    )
    p = chat_message_to_patch(msg)
    assert p["append"]["received_at"] == "2026-01-02T01:04:05Z"

