from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import httpx

from stream_cheremsha.actions.action_placeholders import apply_action_placeholders
from stream_cheremsha.config.constants import MAX_MESSAGE_CHARS
from stream_cheremsha.actions.actions_play_sound import play_sound_from_file
from stream_cheremsha.actions.actions_launch_program import launch_program
from stream_cheremsha.actions.actions_write_file import write_text_to_file
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.actions.registry import match_chat_keyword
from stream_cheremsha.domain.protocols import AudioSink

import logging

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]
TtsSpeakCallback = Callable[[str], Awaitable[None]]


class PlatformActionsEngine:
    def __init__(
        self,
        sink: AudioSink,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
        tts_speak: TtsSpeakCallback | None = None,
    ) -> None:
        self._sink = sink
        self._rules: list[RuleV1] = list(rules or [])
        self._status_callback: StatusCallback = status_callback or (lambda _msg: None)
        self._tts_speak: TtsSpeakCallback | None = tts_speak
        self._dispatch_lock = asyncio.Lock()

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
        logger.info(
            "Actions gift_received: platform=%s sender=%s gift_id=%s gift_name=%s count=%s rules=%s",
            getattr(ev.platform, "value", ev.platform),
            ev.sender,
            ev.gift_id,
            ev.gift_name,
            ev.count,
            len(self._rules),
        )
        matched_any = False
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
                matched_any = True
                logger.info("Actions gift_received matched rule=%s", rule.id)
                await self._dispatch_actions(rule, ev)
        if not matched_any:
            logger.info("Actions gift_received no matching rule")

    async def _dispatch_actions(self, rule: RuleV1, ev: object) -> None:
        if not rule.actions:
            self._status_callback(f"Rule {rule.id}: no actions configured")
            return

        async with self._dispatch_lock:
            coros: list[Coroutine[Any, Any, None]] = []
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

                    async def _play(fp: str = file_path) -> None:
                        try:
                            await play_sound_from_file(fp, sink=self._sink)
                        except FileNotFoundError:
                            self._status_callback(f"Rule {rule.id}: sound file not found: {fp}")
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: play_sound failed: {e}")

                    coros.append(_play())
                    continue

                if t == "write_file":
                    file_path = params.get("file_path")
                    if not isinstance(file_path, str) or not file_path.strip():
                        self._status_callback(f"Rule {rule.id}: actions[{i}].file_path is required")
                        continue
                    text = params.get("text", "")
                    if not isinstance(text, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text must be a string")
                        continue
                    mode = params.get("mode", "overwrite")
                    if not isinstance(mode, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].mode must be a string")
                        continue
                    file_path = apply_action_placeholders(file_path, ev).strip()
                    if not file_path:
                        self._status_callback(
                            f"Rule {rule.id}: actions[{i}].file_path is empty after placeholders"
                        )
                        continue
                    text = apply_action_placeholders(text, ev)

                    async def _write(fp: str = file_path, tx: str = text, m: str = mode) -> None:
                        try:
                            write_text_to_file(fp, tx, mode=m)
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: write_file failed: {e}")

                    coros.append(_write())
                    continue

                if t in ("run_program", "run_exe"):
                    program_path = params.get("program_path") or params.get("exe_path")
                    if not isinstance(program_path, str) or not program_path.strip():
                        self._status_callback(
                            f"Rule {rule.id}: actions[{i}].program_path (or legacy exe_path) is required"
                        )
                        continue
                    args_raw = params.get("arguments", "")
                    if not isinstance(args_raw, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].arguments must be a string")
                        continue
                    args_raw = apply_action_placeholders(args_raw, ev)

                    async def _run(prog: str = program_path, ar: str = args_raw) -> None:
                        try:
                            await launch_program(prog, ar)
                        except FileNotFoundError:
                            self._status_callback(f"Rule {rule.id}: program not found: {prog}")
                        except PermissionError as e:
                            self._status_callback(f"Rule {rule.id}: launch_program failed: {e}")
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: launch_program failed: {e}")

                    coros.append(_run())
                    continue

                if t == "speak_tts":
                    raw = params.get("text", "")
                    if not isinstance(raw, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text must be a string")
                        continue
                    resolved = apply_action_placeholders(raw, ev).strip()
                    if not resolved:
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text is empty after placeholders")
                        continue
                    if self._tts_speak is None:
                        self._status_callback(f"Rule {rule.id}: speak_tts requires TTS (not configured)")
                        continue
                    if len(resolved) > MAX_MESSAGE_CHARS:
                        resolved = resolved[:MAX_MESSAGE_CHARS]

                    async def _tts_line(s: str = resolved) -> None:
                        try:
                            await self._tts_speak(s)
                        except (OSError, ValueError, httpx.HTTPError) as e:
                            self._status_callback(f"Rule {rule.id}: speak_tts failed: {e}")

                    coros.append(_tts_line())
                    continue

                # Unknown action types are ignored in v1 (future extensibility).
                self._status_callback(f"Rule {rule.id}: unknown action type: {t}")

            if not coros:
                return
            await asyncio.gather(*coros)
