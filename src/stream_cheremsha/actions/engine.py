from __future__ import annotations

from collections.abc import Callable
from typing import Any

from stream_cheremsha.actions.actions_play_sound import play_sound_from_file
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.actions.registry import match_chat_keyword
from stream_cheremsha.domain.protocols import AudioSink


StatusCallback = Callable[[str], None]


class PlatformActionsEngine:
    def __init__(
        self,
        sink: AudioSink,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
    ) -> None:
        self._sink = sink
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

            params: Any = rule.event.get("params")
            if not isinstance(params, dict):
                self._status_callback(f"Rule {rule.id}: event.params must be an object")
                continue

            # Preferred schema keys (spec): text + match + case_sensitive.
            # Back-compat with early drafts/tests: keyword + mode.
            keyword = params.get("text", params.get("keyword"))
            if not isinstance(keyword, str) or not keyword.strip():
                self._status_callback(f"Rule {rule.id}: chat keyword is required")
                continue
            keyword = keyword.strip()

            mode = params.get("match", params.get("mode", "contains"))
            case_sensitive = bool(params.get("case_sensitive", False))

            try:
                matched = match_chat_keyword(
                    ev.text,
                    keyword,
                    mode=mode,  # type: ignore[arg-type]
                    case_sensitive=case_sensitive,
                )
            except ValueError as e:
                self._status_callback(f"Rule {rule.id}: invalid chat_keyword params: {e}")
                continue

            if matched:
                await self._dispatch_actions(rule, ev)

    async def on_gift_received(self, ev: GiftReceivedEvent) -> None:
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.event["type"] != "gift_received":
                continue

            params: Any = rule.event.get("params")
            if not isinstance(params, dict):
                self._status_callback(f"Rule {rule.id}: event.params must be an object")
                continue

            min_count_raw = params.get("min_count", 1)
            try:
                min_count = int(min_count_raw)
            except (TypeError, ValueError):
                self._status_callback(f"Rule {rule.id}: min_count must be an integer")
                continue
            if min_count < 1:
                min_count = 1

            gift_id = params.get("gift_id")
            gift_name = params.get("gift_name")
            match_ok = False
            if isinstance(gift_id, str) and gift_id.strip():
                match_ok = ev.gift_id.strip() == gift_id.strip()
            elif isinstance(gift_name, str) and gift_name.strip():
                match_ok = ev.gift_name.strip().casefold() == gift_name.strip().casefold()
            else:
                self._status_callback(f"Rule {rule.id}: gift_id or gift_name is required")
                continue

            if match_ok and int(ev.count) >= min_count:
                await self._dispatch_actions(rule, ev)

    async def _dispatch_actions(self, rule: RuleV1, ev: object) -> None:
        _ = ev
        for i, action in enumerate(rule.actions):
            if not isinstance(action, dict):
                self._status_callback(f"Rule {rule.id}: actions[{i}] must be an object")
                continue
            t = action.get("type")
            if not isinstance(t, str) or not t.strip():
                self._status_callback(f"Rule {rule.id}: actions[{i}].type is required")
                continue
            params = action.get("params")
            if not isinstance(params, dict):
                self._status_callback(f"Rule {rule.id}: actions[{i}].params must be an object")
                continue

            if t == "play_sound":
                file_path = params.get("file_path")
                if not isinstance(file_path, str) or not file_path.strip():
                    self._status_callback(f"Rule {rule.id}: actions[{i}].file_path is required")
                    continue
                try:
                    await play_sound_from_file(file_path, sink=self._sink)
                except FileNotFoundError:
                    self._status_callback(f"Rule {rule.id}: sound file not found: {file_path}")
                except (OSError, ValueError) as e:
                    self._status_callback(f"Rule {rule.id}: play_sound failed: {e}")
                continue

            # Unknown action types are ignored in v1 (future extensibility).
            self._status_callback(f"Rule {rule.id}: unknown action type: {t}")
