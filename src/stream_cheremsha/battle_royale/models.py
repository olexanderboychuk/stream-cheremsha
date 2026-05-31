from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BattlePhase(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    VICTORY = "victory"


@dataclass(slots=True)
class BattleSupportGift:
    gift_id: str
    name: str
    image_url: str
    price: int = 0

    def to_dict(self) -> dict[str, str | int]:
        return {
            "gift_id": str(self.gift_id),
            "name": str(self.name),
            "image_url": str(self.image_url),
            "price": int(self.price),
        }


@dataclass(slots=True)
class BattleFighter:
    user_key: str
    display_name: str
    avatar_url: str
    hp: int
    max_hp: int
    side: str  # left | right | slot0..slot3
    session_donated: int = 0
    support_gifts: list[BattleSupportGift] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_key": self.user_key,
            "user": self.display_name,
            "avatar_url": self.avatar_url,
            "hp": int(self.hp),
            "max_hp": int(self.max_hp),
            "side": self.side,
            "session_donated": int(self.session_donated),
            "support_gifts": [g.to_dict() for g in self.support_gifts],
        }


@dataclass(slots=True)
class BattleHit:
    from_index: int
    to_index: int
    damage: int
    heal: int
    crit: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": int(self.from_index),
            "to": int(self.to_index),
            "damage": int(self.damage),
            "heal": int(self.heal),
            "crit": bool(self.crit),
        }


@dataclass(slots=True)
class BattleState:
    phase: BattlePhase = BattlePhase.IDLE
    session_id: str = ""
    fighters: list[BattleFighter] = field(default_factory=list)
    timer_remaining_s: int = 0
    countdown_remaining_s: int = 0
    winner_key: str = ""
    winner_display: str = ""
    winner_avatar_url: str = ""
    fx_seq: int = 0
    last_hit: BattleHit | None = None
    target_rr_index: int = 0  # round-robin for 3+ fighters
    countdown_deadline: float | None = None
    round_deadline: float | None = None
    victory_deadline: float | None = None

    def fighter_index(self, user_key: str) -> int | None:
        key = (user_key or "").strip()
        if not key:
            return None
        for i, f in enumerate(self.fighters):
            if f.user_key == key:
                return i
        return None
