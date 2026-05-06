from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

ActivityPlatform = Literal["twitch", "tiktok", "youtube"]
ActivityKind = Literal[
    "follow",
    "sub",
    "resub",
    "gift",
    "join",
    "like",
    "share",
    "superchat",
    "supersticker",
    "member",
]


@dataclass(frozen=True, slots=True)
class ActivityItem:
    platform: ActivityPlatform
    kind: ActivityKind
    user: str
    detail: str
    count: int
    icon_url: str
    time_hms: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "kind": self.kind,
            "user": self.user,
            "detail": self.detail,
            "count": int(self.count),
            "icon_url": self.icon_url,
            "time": self.time_hms,
        }


def now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def activity_append_patch(item: ActivityItem) -> dict[str, Any]:
    return {"append": item.to_dict()}

