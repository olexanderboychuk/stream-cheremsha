from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class BattleDecision:
    is_big_moment: bool = False
    is_high_priority: bool = False
    is_highlight_candidate: bool = False
    is_close_battle: bool = False
    is_comeback: bool = False
    should_trigger_special_animation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_big_moment": bool(self.is_big_moment),
            "is_high_priority": bool(self.is_high_priority),
            "is_highlight_candidate": bool(self.is_highlight_candidate),
            "is_close_battle": bool(self.is_close_battle),
            "is_comeback": bool(self.is_comeback),
            "should_trigger_special_animation": bool(self.should_trigger_special_animation),
        }


class NullDecisionLayer:
    kind = "null"

    def decide(self, event: dict[str, Any]) -> BattleDecision:  # noqa: ARG002
        return BattleDecision()


HEURISTIC_KIND = "heuristic_v1"
