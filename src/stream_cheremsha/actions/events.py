from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from stream_cheremsha.domain.models import ChatPlatform


@dataclass(frozen=True, slots=True)
class ChatMessageEvent:
    platform: ChatPlatform
    author: str
    text: str
    received_at: datetime


@dataclass(frozen=True, slots=True)
class GiftReceivedEvent:
    platform: ChatPlatform
    sender: str
    gift_id: str
    gift_name: str
    count: int
    received_at: datetime
