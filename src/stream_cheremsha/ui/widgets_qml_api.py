from __future__ import annotations

import json

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication

from stream_cheremsha.overlays.chat_config import (
    chat_config_defaults,
    chat_config_from_json_text,
    chat_config_to_json_text,
    load_chat_config,
    save_chat_config,
)


class WidgetsQmlApi(QObject):
    def __init__(self, *, overlay_base_url: str) -> None:
        super().__init__()
        self._base = str(overlay_base_url or "").rstrip("/")

    @Slot(result=str)
    def chatOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/chat?instance=main"

    @Slot()
    def copyChatOverlayUrl(self) -> None:
        url = self.chatOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot(result=str)
    def loadChatConfigJson(self) -> str:
        cfg = load_chat_config()
        return chat_config_to_json_text(cfg)

    @Slot(str)
    def saveChatConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            save_chat_config(chat_config_defaults())
            return
        try:
            cfg = chat_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError):
            save_chat_config(chat_config_defaults())
            return
        save_chat_config(cfg)
