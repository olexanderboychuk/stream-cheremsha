from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from stream_cheremsha.domain.models import ChatMessage


class _ChatAppendPatch(TypedDict):
    author: str
    text: str
    platform: str
    received_at: str


class ChatPatch(TypedDict):
    append: _ChatAppendPatch


def _iso_utc_z(dt: datetime) -> str:
    # Defensive: treat naive datetimes as UTC rather than crashing on astimezone().
    if dt.tzinfo is None or dt.utcoffset() is None:
        dtu = dt.replace(tzinfo=UTC)
    else:
        dtu = dt.astimezone(UTC)
    return dtu.isoformat(timespec="seconds").replace("+00:00", "Z")


def chat_message_to_patch(msg: ChatMessage) -> ChatPatch:
    return {
        "append": {
            "author": str(msg.author),
            "text": str(msg.text),
            "platform": str(msg.platform.value),
            "received_at": _iso_utc_z(msg.received_at),
        }
    }
