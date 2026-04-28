"""QML bridge for the platform Actions editor (rules: Event -> Actions)."""

from __future__ import annotations

import asyncio
import typing
import weakref
from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from stream_cheremsha.actions.models import ruleset_from_json_text
from stream_cheremsha.actions.store import load_rules, save_rules
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.config import constants
from stream_cheremsha.domain.models import ChatPlatform

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow


class ActionsQmlApi(QObject):
    refreshUiRequested = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)

    def _win(self) -> MainWindow | None:
        return self._m()

    @staticmethod
    def _store_account_key(platform: str, accountKey: str) -> str:
        p = (platform or "").strip().lower()
        if p == "tiktok":
            return constants.TIKTOK_ACTIONS_ACCOUNT_KEY
        return (accountKey or "").strip()

    @Slot(str, str, result=str)
    def loadRulesJson(self, platform: str, accountKey: str) -> str:
        """Return ruleset JSON (wrapper: schema_version + rules list)."""
        p = (platform or "").strip()
        if not p:
            return '{"schema_version":1,"rules":[]}'
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return '{"schema_version":1,"rules":[]}'
        w0 = self._win()
        if w0 is not None and p == "tiktok" and ak == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            w0._maybe_migrate_tiktok_actions()  # noqa: SLF001
        rules = load_rules(p, ak)
        # Reuse canonical serializer to keep stable formatting.
        from stream_cheremsha.actions.models import ruleset_to_json_text  # noqa: PLC0415

        return ruleset_to_json_text(rules)

    @Slot(str, str, str)
    def saveRulesJson(self, platform: str, accountKey: str, rulesJson: str) -> None:
        """Validate & persist ruleset JSON. Also refresh in-memory engines."""
        p = (platform or "").strip()
        if not p:
            return
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return
        txt = (rulesJson or "").strip()
        if not txt:
            save_rules(p, ak, [])
            w = self._win()
            if w is not None:
                w._actions_reload_scope(p, ak)  # noqa: SLF001
            return

        rules = ruleset_from_json_text(txt)
        save_rules(p, ak, rules)
        w = self._win()
        if w is not None:
            w._actions_reload_scope(p, ak)  # noqa: SLF001

    @Slot(result=str)
    def pickSoundFile(self) -> str:
        """Open file picker for an MP3 clip and return a path or empty string."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select MP3",
            "",
            "MP3 (*.mp3);;All files (*)",
        )
        return str(path or "")

    @Slot(result=str)
    def pickWriteFile(self) -> str:
        """Pick an output text file path for write_file action."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getSaveFileName(
            parent,
            "Select output file",
            "",
            "Text (*.txt);;All files (*)",
        )
        return str(path or "")

    @Slot(result=str)
    def pickProgramFile(self) -> str:
        """Pick a program binary for the launch-program action (any OS)."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select program",
            "",
            "All files (*)",
        )
        return str(path or "")

    @Slot(str, str, result=str)
    def giftOptionsJson(self, platform: str, accountKey: str) -> str:
        """Return JSON array of gift options for this platform scope."""
        w = self._win()
        if w is None:
            return "[]"
        p = (platform or "").strip().lower()
        _ = (accountKey or "").strip()
        if p == "tiktok":
            import json  # noqa: PLC0415

            from stream_cheremsha.actions.tiktok_gifts import TIKTOK_GIFTS  # noqa: PLC0415

            return json.dumps(TIKTOK_GIFTS, ensure_ascii=False)
        return "[]"

    @Slot(str, str, str)
    def previewRule(self, platform: str, accountKey: str, ruleId: str) -> None:
        """Simulate a matching event to preview the rule actions."""
        w = self._win()
        if w is None:
            return
        p = (platform or "").strip().lower()
        ak = self._store_account_key(p, accountKey)
        rid = (ruleId or "").strip()
        if not p or not ak or not rid:
            return

        rules = load_rules(p, ak)
        rule = next((r for r in rules if r.id == rid), None)
        if rule is None or not rule.enabled:
            return

        eng = w._get_actions_engine(p, ak)  # noqa: SLF001
        now = datetime.now(UTC)

        ev_type = (rule.event.get("type") or "").strip()
        if ev_type == "chat_keyword":
            params = rule.event.get("params") or {}
            kw = ""
            if isinstance(params, dict):
                kw = str(params.get("text") or params.get("keyword") or "").strip()
            if not kw:
                kw = "test"
            ev = ChatMessageEvent(
                platform=ChatPlatform.TIKTOK if p == "tiktok" else ChatPlatform.TWITCH,
                author="preview",
                text=f"{kw}",
                received_at=now,
            )
            asyncio.ensure_future(eng.on_chat_message(ev))
            return

        if ev_type == "gift_received":
            params = rule.event.get("params") or {}
            gift_id = ""
            gift_name = ""
            min_count = 1
            if isinstance(params, dict):
                gift_id = str(params.get("gift_id") or "").strip()
                gift_name = str(params.get("gift_name") or "").strip()
                try:
                    min_count = int(params.get("min_count", 1))
                except (TypeError, ValueError):
                    min_count = 1
            if min_count < 1:
                min_count = 1
            ev = GiftReceivedEvent(
                platform=ChatPlatform.TIKTOK if p == "tiktok" else ChatPlatform.TWITCH,
                sender="preview",
                gift_id=gift_id,
                gift_name=gift_name or "Rose",
                count=min_count,
                received_at=now,
            )
            asyncio.ensure_future(eng.on_gift_received(ev))
            return
