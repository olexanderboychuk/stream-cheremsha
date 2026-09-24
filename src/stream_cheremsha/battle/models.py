from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BattleStatus(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    FINISHED = "finished"


@dataclass(slots=True)
class Participant:
    id: str  # stable user key
    name: str  # display name
    avatar_url: str = ""
    team_id: str = "left"  # left | right | team_<n> (2v2-ready)
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "team_id": self.team_id,
            "score": int(self.score),
        }


@dataclass(slots=True)
class Team:
    id: str
    score: int = 0
    round_wins: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "score": int(self.score), "round_wins": int(self.round_wins)}


@dataclass(slots=True)
class BattleEvent:
    type: str
    team_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    at: float = 0.0  # time.monotonic()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "team_id": self.team_id,
            "payload": dict(self.payload),
            "at": float(self.at),
        }


@dataclass(slots=True)
class ComboState:
    team_id: str | None = None
    count: int = 0
    multiplier: float = 1.0
    window_start: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "count": int(self.count),
            "multiplier": float(self.multiplier),
        }


@dataclass(slots=True)
class BattleState:
    battle_id: str = ""
    status: BattleStatus = BattleStatus.IDLE
    round: int = 1
    best_of: int = 3
    participants: list[Participant] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    combo: ComboState = field(default_factory=ComboState)
    events: list[BattleEvent] = field(default_factory=list)  # ring, max 10
    winner_team_id: str | None = None
    remaining_seconds: int = 0
    countdown_remaining_s: int = 0
    is_close: bool = False
    is_comeback: bool = False
    final_push: bool = False
    countdown_deadline: float | None = None
    round_deadline: float | None = None
    victory_deadline: float | None = None

    def push_event(self, ev: BattleEvent) -> None:
        self.events.append(ev)
        if len(self.events) > 10:
            del self.events[: len(self.events) - 10]

    def team(self, tid: str) -> Team | None:
        for t in self.teams:
            if t.id == tid:
                return t
        return None

    def participant(self, uid: str) -> Participant | None:
        for p in self.participants:
            if p.id == uid:
                return p
        return None
