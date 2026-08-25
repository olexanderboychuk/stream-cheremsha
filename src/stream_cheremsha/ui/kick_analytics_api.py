"""QML-facing Kick analytics (session counters + activity feed)."""

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

_MAX_FEED_ROWS = 150


class KickAnalyticsFeedModel(QAbstractListModel):
    """Newest-first list for QML ListView."""

    _KIND = Qt.ItemDataRole.UserRole + 1
    _USER = Qt.ItemDataRole.UserRole + 2
    _DETAIL = Qt.ItemDataRole.UserRole + 3
    _COUNT = Qt.ItemDataRole.UserRole + 4
    _TIME = Qt.ItemDataRole.UserRole + 5

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
            self._COUNT: b"countValue",
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


class KickAnalyticsApi(QObject):
    """Counters and feed; safe to call enqueue_* from non-Qt threads."""

    statsChanged = Signal()

    _viewers_sig = Signal(int)
    _messages_sig = Signal(int)
    _follow_sig = Signal(str)
    _sub_sig = Signal(str, int)
    _gift_sub_sig = Signal(str, int)
    _kick_gift_sig = Signal(str, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._feed = KickAnalyticsFeedModel(self)

        self._viewers_current = 0
        self._viewers_peak = 0
        self._messages = 0
        self._follows = 0
        self._subscriptions = 0
        self._gift_subs = 0
        self._kicks = 0

        self._viewers_sig.connect(self._apply_viewers, Qt.ConnectionType.QueuedConnection)
        self._messages_sig.connect(self._apply_messages, Qt.ConnectionType.QueuedConnection)
        self._follow_sig.connect(self._apply_follow, Qt.ConnectionType.QueuedConnection)
        self._sub_sig.connect(self._apply_sub, Qt.ConnectionType.QueuedConnection)
        self._gift_sub_sig.connect(self._apply_gift_sub, Qt.ConnectionType.QueuedConnection)
        self._kick_gift_sig.connect(self._apply_kick_gift, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @Property(int, notify=statsChanged)
    def viewersCurrent(self) -> int:  # noqa: N802
        return self._viewers_current

    @Property(int, notify=statsChanged)
    def viewersPeak(self) -> int:  # noqa: N802
        return self._viewers_peak

    @Property(int, notify=statsChanged)
    def messagesSession(self) -> int:  # noqa: N802
        return self._messages

    @Property(int, notify=statsChanged)
    def followsSession(self) -> int:  # noqa: N802
        return self._follows

    @Property(int, notify=statsChanged)
    def subscriptionsSession(self) -> int:  # noqa: N802
        return self._subscriptions

    @Property(int, notify=statsChanged)
    def giftSubsSession(self) -> int:  # noqa: N802
        return self._gift_subs

    @Property(int, notify=statsChanged)
    def kicksSession(self) -> int:  # noqa: N802
        return self._kicks

    @Property(QObject, constant=True)
    def feedModel(self) -> KickAnalyticsFeedModel:  # noqa: N802
        return self._feed

    def _emit_stats(self) -> None:
        self.statsChanged.emit()

    @Slot(int)
    def _apply_viewers(self, n: int) -> None:
        v = max(0, int(n))
        if v == self._viewers_current and v <= self._viewers_peak:
            return
        self._viewers_current = v
        if v > self._viewers_peak:
            self._viewers_peak = v
        self._emit_stats()

    @Slot(int)
    def _apply_messages(self, n: int) -> None:
        self._messages += max(1, int(n))
        self._emit_stats()

    @Slot(str)
    def _apply_follow(self, user: str) -> None:
        u = (user or "").strip() or "?"
        self._follows += 1
        self._feed.prepend(
            {"kind": "follow", "user": u, "detail": "", "count": 1, "time": self._now_hms()}
        )
        self._emit_stats()

    @Slot(str, int)
    def _apply_sub(self, user: str, months: int) -> None:
        u = (user or "").strip() or "?"
        m = max(0, int(months))
        self._subscriptions += 1
        self._feed.prepend(
            {
                "kind": "subscription",
                "user": u,
                "detail": f"{m}m" if m else "",
                "count": 1,
                "time": self._now_hms(),
            }
        )
        self._emit_stats()

    @Slot(str, int)
    def _apply_gift_sub(self, user: str, count: int) -> None:
        u = (user or "").strip() or "?"
        c = max(1, int(count))
        self._gift_subs += c
        self._feed.prepend(
            {"kind": "gift", "user": u, "detail": "gift sub", "count": c, "time": self._now_hms()}
        )
        self._emit_stats()

    @Slot(str, int)
    def _apply_kick_gift(self, user: str, amount: int) -> None:
        u = (user or "").strip() or "?"
        a = max(1, int(amount))
        self._kicks += a
        self._feed.prepend(
            {"kind": "kick_gift", "user": u, "detail": "", "count": a, "time": self._now_hms()}
        )
        self._emit_stats()

    # Public enqueue helpers (thread-safe)
    def enqueue_viewers(self, n: int) -> None:
        self._viewers_sig.emit(int(n))

    def enqueue_messages(self, n: int) -> None:
        self._messages_sig.emit(int(n))

    def enqueue_follow(self, user: str) -> None:
        self._follow_sig.emit(user)

    def enqueue_sub(self, user: str, months: int = 1) -> None:
        self._sub_sig.emit(user, int(months))

    def enqueue_gift_sub(self, user: str, count: int = 1) -> None:
        self._gift_sub_sig.emit(user, int(count))

    def enqueue_kick_gift(self, user: str, amount: int = 1) -> None:
        self._kick_gift_sig.emit(user, int(amount))

    @Slot()
    def resetSession(self) -> None:  # noqa: N802
        self._viewers_current = 0
        self._viewers_peak = 0
        self._messages = 0
        self._follows = 0
        self._subscriptions = 0
        self._gift_subs = 0
        self._kicks = 0
        self._feed.clear()
        self._emit_stats()

    # Callable aliases for external clients
    @property
    def on_viewers(self) -> Callable[[int], None]:
        return self.enqueue_viewers

    @property
    def on_follow(self) -> Callable[[str], None]:
        return self.enqueue_follow

    @property
    def on_sub(self) -> Callable[[str, int], None]:
        return self.enqueue_sub

    @property
    def on_gift_sub(self) -> Callable[[str, int], None]:
        return self.enqueue_gift_sub

    @property
    def on_kick_gift(self) -> Callable[[str, int], None]:
        return self.enqueue_kick_gift
