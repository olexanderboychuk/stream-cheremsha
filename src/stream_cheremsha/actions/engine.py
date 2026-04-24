from __future__ import annotations

from collections.abc import Callable
from typing import Any

from stream_cheremsha.actions.events import ChatMessageEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.actions.registry import match_chat_keyword


StatusCallback = Callable[[str], None]


class PlatformActionsEngine:
    def __init__(
        self,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
    ) -> None:
        self._rules: list[RuleV1] = list(rules or [])
        self._status_callback: StatusCallback = status_callback or (lambda _msg: None)

    def set_rules(self, rules: list[RuleV1]) -> None:
        self._rules = list(rules)

    async def on_chat_message(self, ev: ChatMessageEvent) -> None:
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.event["type"] != "chat_keyword":
                continue

            params: Any = rule.event.get("params", {})
            if not isinstance(params, dict):
                continue

            keyword = params.get("keyword")
            if not isinstance(keyword, str) or not keyword:
                continue

            mode = params.get("mode", "contains")
            case_sensitive = bool(params.get("case_sensitive", False))

            try:
                matched = match_chat_keyword(
                    ev.text,
                    keyword,
                    mode=mode,  # type: ignore[arg-type]
                    case_sensitive=case_sensitive,
                )
            except ValueError as e:
                self._status_callback(f"Rule {rule.id} has invalid chat_keyword params: {e}")
                continue

            if matched:
                await self._dispatch_actions(rule, ev)

    async def _dispatch_actions(self, rule: RuleV1, ev: ChatMessageEvent) -> None:
        """Placeholder hook; implemented in Task 5."""

        _ = (rule, ev)
        self._status_callback(
            f"Matched rule {rule.id} but action execution is not implemented yet"
        )
