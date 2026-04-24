"""QML bridge for the platform Actions editor (rules: Event -> Actions)."""

from __future__ import annotations

import typing
import weakref

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from stream_cheremsha.actions.models import ruleset_from_json_text
from stream_cheremsha.actions.store import load_rules, save_rules

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow


class ActionsQmlApi(QObject):
    refreshUiRequested = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)

    def _win(self) -> MainWindow | None:
        return self._m()

    @Slot(str, str, result=str)
    def loadRulesJson(self, platform: str, accountKey: str) -> str:
        """Return ruleset JSON (wrapper: schema_version + rules list)."""
        rules = load_rules(platform, accountKey)
        # Reuse canonical serializer to keep stable formatting.
        from stream_cheremsha.actions.models import ruleset_to_json_text  # noqa: PLC0415

        return ruleset_to_json_text(rules)

    @Slot(str, str, str)
    def saveRulesJson(self, platform: str, accountKey: str, rulesJson: str) -> None:
        """Validate & persist ruleset JSON. Also refresh in-memory engines."""
        txt = (rulesJson or "").strip()
        if not txt:
            save_rules(platform, accountKey, [])
            w = self._win()
            if w is not None:
                w._actions_reload_scope(platform, accountKey)  # noqa: SLF001
            return

        rules = ruleset_from_json_text(txt)
        save_rules(platform, accountKey, rules)
        w = self._win()
        if w is not None:
            w._actions_reload_scope(platform, accountKey)  # noqa: SLF001

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
