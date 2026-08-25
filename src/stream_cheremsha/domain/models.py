from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ChatPlatform(StrEnum):
    TWITCH = "twitch"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    KICK = "kick"


@dataclass(slots=True)
class ChatMessage:
    author: str
    text: str
    platform: ChatPlatform
    received_at: datetime
    author_avatar_url: str = ""
    tiktok_stable_key: str = ""
    tiktok_unique_id: str = ""
