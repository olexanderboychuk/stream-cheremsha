from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication


class DocksQmlApi(QObject):
    def __init__(self, *, base_url: str = "") -> None:
        super().__init__()
        self._base = str(base_url or "").rstrip("/")

    baseUrlChanged = Signal()

    def set_base_url(self, base_url: str) -> None:
        base = str(base_url or "").rstrip("/")
        if base == self._base:
            return
        self._base = base
        self.baseUrlChanged.emit()

    @Property(str, notify=baseUrlChanged)
    def multichatDockUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.multichatDockUrl()

    @Slot(result=str)
    def multichatDockUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/dock/multichat"

    @Slot()
    def copyMultichatDockUrl(self) -> None:
        url = self.multichatDockUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Property(str, notify=baseUrlChanged)
    def activityDockUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.activityDockUrl()

    @Slot(result=str)
    def activityDockUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/dock/activity"

    @Slot()
    def copyActivityDockUrl(self) -> None:
        url = self.activityDockUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Property(str, notify=baseUrlChanged)
    def onlineDockUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.onlineDockUrl()

    @Slot(result=str)
    def onlineDockUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/dock/online"

    @Slot()
    def copyOnlineDockUrl(self) -> None:
        url = self.onlineDockUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)
