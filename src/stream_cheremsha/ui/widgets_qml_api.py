from __future__ import annotations

import asyncio
import json
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from stream_cheremsha.overlays.actions_config import (
    actions_config_from_json_text,
    actions_config_to_json_text,
    load_actions_config,
    save_actions_config,
)
from stream_cheremsha.overlays.chat_config import (
    chat_config_from_json_text,
    chat_config_to_json_text,
    load_chat_config,
    save_chat_config,
)
from stream_cheremsha.overlays.online_overlay_config import (
    load_online_overlay_config,
    online_overlay_config_from_json_text,
    online_overlay_config_to_json_text,
    save_online_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _sorted_system_font_families() -> list[str]:
    db = QFontDatabase()
    names = [str(x).strip() for x in db.families() if str(x).strip()]
    return sorted(set(names), key=str.casefold)


_FONT_FALLBACK_NO_GUI_APP = sorted(
    {"Segoe UI", "Arial", "Tahoma", "Consolas", "Verdana"},
    key=str.casefold,
)


class WidgetsQmlApi(QObject):
    def __init__(
        self,
        *,
        overlay_base_url: str = "",
        pubsub: OverlayPubSub | None = None,
        actions_instance: str = "main",
        online_instance: str = "main",
    ) -> None:
        super().__init__()
        self._base = str(overlay_base_url or "").rstrip("/")
        self._pubsub = pubsub
        self._actions_instance = str(actions_instance or "main").strip() or "main"
        self._online_instance = str(online_instance or "main").strip() or "main"
        self._system_font_families: list[str] | None = None

    @Slot(result="QStringList")
    def systemFontFamilies(self) -> list[str]:
        """Font families Qt reads from the OS (picker for overlay widgets).

        Requires a running ``QGuiApplication``; headless/unit-test callers get a tiny fallback list.
        """
        if QGuiApplication.instance() is None:
            return list(_FONT_FALLBACK_NO_GUI_APP)
        if self._system_font_families is None:
            families = _sorted_system_font_families()
            # Some headless/test environments still create a QGuiApplication but expose no fonts.
            # Keep the picker usable (and tests stable) by falling back in that case too.
            self._system_font_families = families if families else list(_FONT_FALLBACK_NO_GUI_APP)
        return list(self._system_font_families)

    chatOverlayUrlChanged = Signal()

    def set_overlay_base_url(self, base_url: str) -> None:
        base = str(base_url or "").rstrip("/")
        if base == self._base:
            return
        self._base = base
        self.chatOverlayUrlChanged.emit()
        self.actionsOverlayUrlChanged.emit()
        self.onlineOverlayUrlChanged.emit()

    @Property(str, notify=chatOverlayUrlChanged)
    def chatOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.chatOverlayUrl()

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

    # Music overlay was removed (local playback via yt-dlp instead of BrowserSource).

    actionsOverlayUrlChanged = Signal()

    @Property(str, notify=actionsOverlayUrlChanged)
    def actionsOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.actionsOverlayUrl()

    @Slot(result=str)
    def actionsOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/actions?instance=main"

    @Slot()
    def copyActionsOverlayUrl(self) -> None:
        url = self.actionsOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    onlineOverlayUrlChanged = Signal()

    @Property(str, notify=onlineOverlayUrlChanged)
    def onlineOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.onlineOverlayUrl()

    @Slot(result=str)
    def onlineOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/online?instance={self._online_instance}"

    @Slot()
    def copyOnlineOverlayUrl(self) -> None:
        url = self.onlineOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    def _publish_patch(self, *, topic: str, patch: dict[str, Any]) -> None:
        ps = self._pubsub
        if ps is None:
            return

        async def _run() -> None:
            await ps.publish(topic, patch)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_run())
            return
        loop.create_task(_run())

    @Slot()
    def previewActionsOverlay(self) -> None:
        topic = f"overlay:actions:{self._actions_instance}"
        patch = {
            "append": {
                "username": "username",
                "text": "action triggered",
                "profile_picture_url": "",
                "gift_picture_url": "",
                "platform": "tiktok",
                # Lets ▶ preview show the asset row without persisting show_action_platform_icon on.
                "preview_force_platform_icon": True,
            }
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot(result="QVariantMap")
    def loadChatConfigMap(self) -> dict[str, Any]:
        """Plain dict for QML (avoids JSON.parse failures wiping UI → disk)."""
        cfg = load_chat_config()
        return json.loads(chat_config_to_json_text(cfg))

    @Slot(result="QVariantMap")
    def loadActionsConfigMap(self) -> dict[str, Any]:
        cfg = load_actions_config()
        return json.loads(actions_config_to_json_text(cfg))

    @Slot(result=str)
    def loadChatConfigJson(self) -> str:
        cfg = load_chat_config()
        return chat_config_to_json_text(cfg)

    @Slot(str)
    def saveChatConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            # Do not overwrite existing settings on empty payloads (transient UI states).
            return
        try:
            cfg = chat_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError):
            # Ignore invalid payloads to avoid resetting user settings to defaults.
            return
        if chat_config_to_json_text(cfg) == chat_config_to_json_text(load_chat_config()):
            return
        save_chat_config(cfg)

    @Slot(result=str)
    def loadActionsConfigJson(self) -> str:
        cfg = load_actions_config()
        return actions_config_to_json_text(cfg)

    @Slot(str)
    def saveActionsConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            # Do not overwrite existing settings on empty payloads (transient UI states).
            return
        try:
            cfg = actions_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError):
            # Ignore invalid payloads to avoid resetting user settings to defaults.
            return
        if actions_config_to_json_text(cfg) == actions_config_to_json_text(load_actions_config()):
            return
        save_actions_config(cfg)
        if self._pubsub is not None:
            topic = f"overlay:actions:{self._actions_instance}"
            patch = {"config": json.loads(actions_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(result="QVariantMap")
    def loadOnlineOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_online_overlay_config()
        return json.loads(online_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadOnlineOverlayConfigJson(self) -> str:
        cfg = load_online_overlay_config()
        return online_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveOnlineOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = online_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError):
            return
        if online_overlay_config_to_json_text(cfg) == online_overlay_config_to_json_text(
            load_online_overlay_config()
        ):
            return
        save_online_overlay_config(cfg)
        if self._pubsub is not None:
            topic = f"overlay:online:{self._online_instance}"
            patch = {"config": json.loads(online_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)


class WidgetsWindowQmlApi(QObject):
    def __init__(self, *, view: QQuickView) -> None:
        super().__init__()
        self._view = view

    @Slot()
    def close(self) -> None:
        self._view.close()

    @Slot()
    def minimize(self) -> None:
        self._view.showMinimized()

    @Slot()
    def toggleMaximize(self) -> None:
        if self._view.visibility() == QQuickView.Visibility.Maximized:
            self._view.showNormal()
        else:
            self._view.showMaximized()

    @Slot(result=bool)
    def isMaximized(self) -> bool:
        return self._view.visibility() == QQuickView.Visibility.Maximized

    @Slot()
    def startMove(self) -> None:
        # Best effort: on supported platforms this enables native window dragging.
        try:
            self._view.startSystemMove()
        except (AttributeError, RuntimeError):
            return

    @Slot(int)
    def startResize(self, edges: int) -> None:
        # edges: Qt.Edge bitmask (Qt.LeftEdge | Qt.TopEdge | ...)
        try:
            self._view.startSystemResize(Qt.Edges(edges))
        except (AttributeError, RuntimeError, TypeError):
            return
