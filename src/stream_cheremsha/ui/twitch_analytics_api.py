"""QML-facing Twitch analytics (session counters + activity feed)."""

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


class TwitchAnalyticsFeedModel(QAbstractListModel):
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


class TwitchAnalyticsApi(QObject):
    """Counters and feed; safe to call enqueue_* from non-Qt threads."""

    statsChanged = Signal()

    _viewers_sig = Signal(int)
    _follow_sig = Signal(str)
    _sub_sig = Signal(str, str, int, str)
    _cheer_sig = Signal(str, int)
    _raid_sig = Signal(str, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._feed = TwitchAnalyticsFeedModel(self)

        self._viewers_current = 0
        self._viewers_peak = 0
        self._follows = 0
        self._subs = 0
        self._bits = 0
        self._raids = 0

        self._viewers_sig.connect(self._apply_viewers, Qt.ConnectionType.QueuedConnection)
        self._follow_sig.connect(self._apply_follow, Qt.ConnectionType.QueuedConnection)
        self._sub_sig.connect(self._apply_sub, Qt.ConnectionType.QueuedConnection)
        self._cheer_sig.connect(self._apply_cheer, Qt.ConnectionType.QueuedConnection)
        self._raid_sig.connect(self._apply_raid, Qt.ConnectionType.QueuedConnection)

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
    def followsSession(self) -> int:  # noqa: N802
        return self._follows

    @Property(int, notify=statsChanged)
    def subsSession(self) -> int:  # noqa: N802
        return self._subs

    @Property(int, notify=statsChanged)
    def bitsSession(self) -> int:  # noqa: N802
        return self._bits

    @Property(int, notify=statsChanged)
    def raidsSession(self) -> int:  # noqa: N802
        return self._raids

    @Property(QObject, constant=True)
    def feedModel(self) -> TwitchAnalyticsFeedModel:  # noqa: N802
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

    @Slot(str)
    def _apply_follow(self, user: str) -> None:
        u = (user or "").strip() or "?"
        self._follows += 1
        self._feed.prepend(
            {
                "kind": "follow",
                "user": u,
                "detail": "",
                "count": 1,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(str, str, int, str)
    def _apply_sub(self, user: str, sub_type: str, months: int, message: str = "") -> None:
        u = (user or "").strip() or "?"
        st = (sub_type or "").strip()
        m = max(0, int(months))
        msg_s = (message or "").strip()
        self._subs += 1
        detail = st if not m else f"{st} · {m}m"
        if st == "resub" and msg_s:
            detail = f"{detail} · {msg_s[:80]}" if detail else msg_s[:120]
        self._feed.prepend(
            {
                "kind": "sub",
                "user": u,
                "detail": detail,
                "count": 1,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(str, int)
    def _apply_cheer(self, user: str, bits: int) -> None:
        u = (user or "").strip() or "?"
        b = max(0, int(bits))
        self._bits += b
        self._feed.prepend(
            {
                "kind": "cheer",
                "user": u,
                "detail": "",
                "count": b,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(str, int)
    def _apply_raid(self, from_channel: str, viewers: int) -> None:
        ch = (from_channel or "").strip() or "?"
        v = max(0, int(viewers))
        self._raids += 1
        self._feed.prepend(
            {
                "kind": "raid",
                "user": ch,
                "detail": "",
                "count": v,
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    # Public enqueue helpers (thread-safe)
    def enqueue_viewers(self, n: int) -> None:
        self._viewers_sig.emit(int(n))

    def enqueue_follow(self, user: str) -> None:
        self._follow_sig.emit(user)

    def enqueue_sub(self, user: str, sub_type: str, months: int, message: str = "") -> None:
        self._sub_sig.emit(user, sub_type, int(months), message or "")

    def enqueue_cheer(self, user: str, bits: int) -> None:
        self._cheer_sig.emit(user, int(bits))

    def enqueue_raid(self, from_channel: str, viewers: int) -> None:
        self._raid_sig.emit(from_channel, int(viewers))

    @Slot()
    def resetSession(self) -> None:  # noqa: N802
        self._viewers_current = 0
        self._viewers_peak = 0
        self._follows = 0
        self._subs = 0
        self._bits = 0
        self._raids = 0
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
    def on_sub(self) -> Callable[..., None]:
        return self.enqueue_sub

    @property
    def on_cheer(self) -> Callable[[str, int], None]:
        return self.enqueue_cheer

    @property
    def on_raid(self) -> Callable[[str, int], None]:
        return self.enqueue_raid
