"""QML-facing TikTok live analytics (session counters + activity feed)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

_MAX_FEED_ROWS = 100


class TikTokAnalyticsFeedModel(QAbstractListModel):
    """Newest-first list for QML ListView."""

    _KIND = Qt.ItemDataRole.UserRole + 1
    _USER = Qt.ItemDataRole.UserRole + 2
    _DETAIL = Qt.ItemDataRole.UserRole + 3
    _ICON = Qt.ItemDataRole.UserRole + 4
    _COUNT = Qt.ItemDataRole.UserRole + 5
    _TIME = Qt.ItemDataRole.UserRole + 6

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: N802
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == self._KIND:
            return row.get("kind", "")
        if role == self._USER:
            return row.get("user", "")
        if role == self._DETAIL:
            return row.get("detail", "")
        if role == self._ICON:
            return row.get("icon", "")
        if role == self._COUNT:
            return int(row.get("count", 0) or 0)
        if role == self._TIME:
            return row.get("time", "")
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self._KIND: b"eventKind",
            self._USER: b"userName",
            self._DETAIL: b"detailText",
            self._ICON: b"iconUrl",
            self._COUNT: b"giftCount",
            self._TIME: b"timeText",
        }

    def clear(self) -> None:
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def prepend(self, row: dict[str, Any]) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._rows.insert(0, row)
        self.endInsertRows()
        while len(self._rows) > _MAX_FEED_ROWS:
            last = len(self._rows) - 1
            self.beginRemoveRows(QModelIndex(), last, last)
            self._rows.pop()
            self.endRemoveRows()


class TikTokAnalyticsApi(QObject):
    """Counters and feed; safe to call ingest_* from non-Qt threads (signals queue to GUI)."""

    statsChanged = Signal()

    _viewers_current_sig = Signal(int)
    _viewers_total_sig = Signal(int)
    _follow_sig = Signal(str)
    _join_sig = Signal(str)
    _gift_sig = Signal(str, str, str, int, int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._feed = TikTokAnalyticsFeedModel(self)
        self._online_current = 0
        self._online_total = 0
        self._gift_units = 0
        self._diamonds = 0

        self._viewers_current_sig.connect(
            self._apply_viewers_current,
            Qt.ConnectionType.QueuedConnection,
        )
        self._viewers_total_sig.connect(
            self._apply_viewers_total,
            Qt.ConnectionType.QueuedConnection,
        )
        self._follow_sig.connect(self._apply_follow, Qt.ConnectionType.QueuedConnection)
        self._join_sig.connect(self._apply_join, Qt.ConnectionType.QueuedConnection)
        self._gift_sig.connect(self._apply_gift, Qt.ConnectionType.QueuedConnection)

    @Property(int, notify=statsChanged)
    def onlineViewersCurrent(self) -> int:  # noqa: N802
        return self._online_current

    @Property(int, notify=statsChanged)
    def onlineViewersTotal(self) -> int:  # noqa: N802
        return self._online_total

    @Property(int, notify=statsChanged)
    def giftUnitsTotal(self) -> int:  # noqa: N802
        return self._gift_units

    @Property(int, notify=statsChanged)
    def diamondsTotal(self) -> int:  # noqa: N802
        return self._diamonds

    @Property(QObject, constant=True)
    def feedModel(self) -> TikTokAnalyticsFeedModel:  # noqa: N802
        return self._feed

    def _emit_stats(self) -> None:
        self.statsChanged.emit()

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @Slot(int)
    def _apply_viewers_current(self, n: int) -> None:
        v = max(0, int(n))
        if v == self._online_current:
            return
        self._online_current = v
        self._emit_stats()

    @Slot(int)
    def _apply_viewers_total(self, n: int) -> None:
        v = max(0, int(n))
        if v == self._online_total:
            return
        self._online_total = v
        self._emit_stats()

    @Slot(str)
    def _apply_follow(self, user: str) -> None:
        u = (user or "").strip() or "?"
        self._feed.prepend(
            {
                "kind": "follow",
                "user": u,
                "detail": "",
                "icon": "",
                "count": 0,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(str)
    def _apply_join(self, user: str) -> None:
        u = (user or "").strip() or "?"
        self._feed.prepend(
            {
                "kind": "join",
                "user": u,
                "detail": "",
                "icon": "",
                "count": 0,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(str, str, str, int, int, str)
    def _apply_gift(
        self,
        sender: str,
        gift_id: str,
        gift_name: str,
        count: int,
        diamonds: int,
        icon_url: str,
    ) -> None:
        s = (sender or "").strip() or "?"
        name = (gift_name or "").strip() or (gift_id or "").strip() or "gift"
        c = max(1, int(count)) if count else 1
        d = max(0, int(diamonds))
        self._gift_units += c
        self._diamonds += d
        self._feed.prepend(
            {
                "kind": "gift",
                "user": s,
                "detail": name,
                "icon": (icon_url or "").strip(),
                "count": c,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    def enqueue_viewers_current(self, n: int) -> None:
        self._viewers_current_sig.emit(int(n))

    def enqueue_viewers_total(self, n: int) -> None:
        self._viewers_total_sig.emit(int(n))

    def enqueue_follow(self, user: str) -> None:
        self._follow_sig.emit(user)

    def enqueue_join(self, user: str) -> None:
        self._join_sig.emit(user)

    def enqueue_gift(
        self,
        sender: str,
        gift_id: str,
        gift_name: str,
        count: int,
        diamonds: int,
        icon_url: str,
    ) -> None:
        self._gift_sig.emit(sender, gift_id, gift_name, int(count), int(diamonds), icon_url)

    @Slot()
    def resetSession(self) -> None:  # noqa: N802
        self._online_current = 0
        self._online_total = 0
        self._gift_units = 0
        self._diamonds = 0
        self._feed.clear()
        self._emit_stats()

    # Callable aliases for TikTokChatSource (no Qt types in chat layer).
    @property
    def on_room_viewers_current(self) -> Callable[[int], None]:
        return self.enqueue_viewers_current

    @property
    def on_room_viewers_total(self) -> Callable[[int], None]:
        return self.enqueue_viewers_total

    @property
    def on_follow(self) -> Callable[[str], None]:
        return self.enqueue_follow

    @property
    def on_join(self) -> Callable[[str], None]:
        return self.enqueue_join

    @property
    def on_gift_analytics(self) -> Callable[[str, str, str, int, int, str], None]:
        return self.enqueue_gift
