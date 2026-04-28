from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone

import pytest

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.overlays.chat_overlay import chat_message_to_patch
from stream_cheremsha.overlays.pubsub import OverlayPubSub


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


@pytest.mark.asyncio
async def test_pubsub_topic_for_chat_main() -> None:
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:chat:main")
    await ps.publish(
        "overlay:chat:main",
        {
            "append": {
                "author": "a",
                "text": "t",
                "platform": "twitch",
                "received_at": "x",
            }
        },
    )
    got = await asyncio.wait_for(q.get(), timeout=1.0)
    assert got["append"]["author"] == "a"
