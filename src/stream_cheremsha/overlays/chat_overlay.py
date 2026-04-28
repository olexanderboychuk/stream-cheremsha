from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from stream_cheremsha.domain.models import ChatMessage


def _iso_utc_z(dt: datetime) -> str:
    dtu = dt.astimezone(UTC)
    return dtu.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def chat_message_to_patch(msg: ChatMessage) -> dict[str, Any]:
    return {
        "append": {
            "author": str(msg.author),
            "text": str(msg.text),
            "platform": str(msg.platform.value),
            "received_at": _iso_utc_z(msg.received_at),
        }
    }

