from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication

from stream_cheremsha import l10n

_DOCKSVIEW_KEYS = (
    "header_title",
    "header_subtitle",
    "header_hint",
    "public_access",
    "public_hint",
    "enabled",
    "disabled",
    "copy_url",
    "open",
    "available_title",
    "available_hint",
    "web_dock_badge",
    "multichat_desc",
    "activity_desc",
    "online_desc",
    "how_title",
    "how_hint",
    "step1_title",
    "step1_hint",
    "step2_title",
    "step2_hint",
    "step3_title",
    "step3_hint",
    "not_available",
    "preview_sub",
    "preview_donation",
    "preview_gift",
    "preview_raid",
    "preview_online",
    "preview_viewers",
    "preview_followers",
)


def docksview_strings(locale: str) -> dict[str, str]:
    lc = l10n.normalize_locale(locale)
    out: dict[str, str] = {}
    for short in _DOCKSVIEW_KEYS:
        out[short] = l10n.tr(lc, f"docksview.{short}")
    return out


class DocksQmlApi(QObject):
    def __init__(self, *, base_url: str = "", locale: str = l10n.DEFAULT_LOCALE) -> None:
        super().__init__()
        self._base = str(base_url or "").rstrip("/")
        self._locale = l10n.normalize_locale(locale)

    baseUrlChanged = Signal()
    stringsChanged = Signal()

    def set_locale(self, locale: str) -> None:
        nl = l10n.normalize_locale(locale)
        if nl == self._locale:
            return
        self._locale = nl
        self.stringsChanged.emit()

    @Property("QVariantMap", notify=stringsChanged)
    def strings(self) -> dict[str, str]:  # noqa: ANN201 - PySide pattern
        return docksview_strings(self._locale)

    @Slot(result="QVariantMap")
    def stringsMap(self) -> dict[str, str]:
        return docksview_strings(self._locale)

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        short = str(key or "").strip()
        if not short:
            return ""
        if short.startswith("docksview."):
            short = short.removeprefix("docksview.")
        if short == "count":
            return l10n.tr(self._locale, "docksview.count", n=3)
        if short in _DOCKSVIEW_KEYS:
            return l10n.tr(self._locale, f"docksview.{short}")
        # Fall back to any global l10n key (e.g. "dock.activity.title").
        try:
            return l10n.tr(self._locale, short)
        except KeyError:
            return short

    @Slot(int, result=str)
    def countText(self, n: int) -> str:
        return l10n.tr(self._locale, "docksview.count", n=int(n))

    @Slot()
    def refreshUi(self) -> None:
        self.stringsChanged.emit()
        self.baseUrlChanged.emit()

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

    @Slot(str)
    def copyText(self, text: str) -> None:
        value = str(text or "")
        if not value:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(value)

    @Slot()
    def copyOnlineDockUrl(self) -> None:
        url = self.onlineDockUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @staticmethod
    def _open_url(url: str) -> None:
        value = str(url or "").strip()
        if not value:
            return
        QDesktopServices.openUrl(QUrl(value))

    @Slot()
    def openMultichatDockUrl(self) -> None:
        self._open_url(self.multichatDockUrl())

    @Slot()
    def openActivityDockUrl(self) -> None:
        self._open_url(self.activityDockUrl())

    @Slot()
    def openOnlineDockUrl(self) -> None:
        self._open_url(self.onlineDockUrl())
