"""QML-facing YouTube analytics (session counters + activity feed)."""

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

_MAX_FEED_ROWS = 200


class YouTubeAnalyticsFeedModel(QAbstractListModel):
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


class YouTubeAnalyticsApi(QObject):
    """Counters and feed; safe to call enqueue_* from non-Qt threads."""

    statsChanged = Signal()

    _event_sig = Signal(str, str, str, int)
    _viewers_sig = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._feed = YouTubeAnalyticsFeedModel(self)

        self._messages = 0
        self._superchats = 0
        self._memberships = 0
        self._unique_chatters: set[str] = set()
        self._viewers_current = 0
        self._viewers_peak = 0

        self._event_sig.connect(self._apply_event, Qt.ConnectionType.QueuedConnection)
        self._viewers_sig.connect(self._apply_viewers, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @Property(int, notify=statsChanged)
    def messagesSession(self) -> int:  # noqa: N802
        return self._messages

    @Property(int, notify=statsChanged)
    def uniqueChattersSession(self) -> int:  # noqa: N802
        return len(self._unique_chatters)

    @Property(int, notify=statsChanged)
    def superChatsSession(self) -> int:  # noqa: N802
        return self._superchats

    @Property(int, notify=statsChanged)
    def membershipsSession(self) -> int:  # noqa: N802
        return self._memberships

    @Property(int, notify=statsChanged)
    def viewersCurrent(self) -> int:  # noqa: N802
        return self._viewers_current

    @Property(int, notify=statsChanged)
    def viewersPeak(self) -> int:  # noqa: N802
        return self._viewers_peak

    @Property(QObject, constant=True)
    def feedModel(self) -> YouTubeAnalyticsFeedModel:  # noqa: N802
        return self._feed

    def _emit_stats(self) -> None:
        self.statsChanged.emit()

    @Slot(str, str, str, int)
    def _apply_event(self, kind: str, user: str, detail: str, count: int) -> None:
        k = (kind or "").strip() or "chat"
        u = (user or "").strip() or "?"
        d = (detail or "").strip()
        c = max(0, int(count))

        self._unique_chatters.add(u)
        if k == "chat":
            self._messages += max(1, c or 1)
        elif k in ("superchat", "supersticker"):
            self._superchats += max(1, c or 1)
        elif k in ("member", "membership"):
            self._memberships += max(1, c or 1)

        self._feed.prepend(
            {
                "kind": k,
                "user": u,
                "detail": d,
                "count": max(1, c or 1),
                "time": self._now_hms(),
            },
        )
        self._emit_stats()

    @Slot(int)
    def _apply_viewers(self, n: int) -> None:
        v = max(0, int(n))
        if v == self._viewers_current and v <= self._viewers_peak:
            return
        self._viewers_current = v
        if v > self._viewers_peak:
            self._viewers_peak = v
        self._emit_stats()

    # Public enqueue helpers (thread-safe)
    def enqueue_event(self, kind: str, user: str, detail: str, count: int = 1) -> None:
        self._event_sig.emit(kind, user, detail, int(count))

    def enqueue_viewers(self, n: int) -> None:
        self._viewers_sig.emit(int(n))

    def enqueue_chat(self, user: str, text: str) -> None:
        self.enqueue_event("chat", user, text, 1)

    def enqueue_superchat(self, user: str, amount: str, text: str) -> None:
        detail = amount.strip() if amount.strip() else ""
        if text.strip():
            detail = f"{detail} · {text.strip()}" if detail else text.strip()
        self.enqueue_event("superchat", user, detail, 1)

    def enqueue_membership(self, user: str, detail: str = "") -> None:
        self.enqueue_event("member", user, detail, 1)

    @Slot()
    def resetSession(self) -> None:  # noqa: N802
        self._messages = 0
        self._superchats = 0
        self._memberships = 0
        self._viewers_current = 0
        self._viewers_peak = 0
        self._unique_chatters.clear()
        self._feed.clear()
        self._emit_stats()

    # Callable aliases for external clients
    @property
    def on_event(self) -> Callable[[str, str, str, int], None]:
        return self.enqueue_event

    @property
    def on_viewers(self) -> Callable[[int], None]:
        return self.enqueue_viewers

    @property
    def on_chat(self) -> Callable[[str, str], None]:
        return self.enqueue_chat

    @property
    def on_superchat(self) -> Callable[[str, str, str], None]:
        return self.enqueue_superchat

    @property
    def on_membership(self) -> Callable[[str, str], None]:
        return lambda user, detail: self.enqueue_membership(user, detail)
