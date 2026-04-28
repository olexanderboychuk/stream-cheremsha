from __future__ import annotations

from datetime import UTC, datetime

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
    assert a["received_at"].endswith("Z")

