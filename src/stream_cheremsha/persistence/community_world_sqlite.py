"""SQLite persistence for Community World all-time badges and village elders."""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_ENV_DB = "STREAM_CHEREMSHA_COMMUNITY_WORLD_DB"
_MAX_ELDERS = 8


def community_world_db_path() -> Path:
    env = (os.environ.get(_ENV_DB) or "").strip()
    if env:
        p = Path(env).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        if QCoreApplication.instance() is not None:
            loc = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
            if loc:
                d = Path(loc) / "stream-cheremsha"
                d.mkdir(parents=True, exist_ok=True)
                return d / "community_world.sqlite"
    except ImportError:
        pass
    d = Path.home() / ".stream-cheremsha" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / "community_world.sqlite"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS community_world_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            avatar_url TEXT NOT NULL DEFAULT '',
            badge TEXT NOT NULL,
            awarded_at_utc TEXT NOT NULL,
            UNIQUE (user_key, badge)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cw_badges_user ON community_world_badges(user_key)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cw_badges_badge ON community_world_badges(badge)"
    )


def award_community_badge(
    *,
    user_key: str,
    display_name: str,
    badge: str,
    avatar_url: str = "",
    awarded_at: datetime | None = None,
    db_path: Path | None = None,
) -> None:
    key = (user_key or "").strip()
    badge_id = (badge or "").strip()
    if not key or not badge_id:
        return
    name = (display_name or "").strip() or "?"
    av = (avatar_url or "").strip()
    ts = (awarded_at or datetime.now(UTC)).isoformat()
    path = db_path if db_path is not None else community_world_db_path()
    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=60.0)
        try:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT OR IGNORE INTO community_world_badges (
                    user_key, display_name, avatar_url, badge, awarded_at_utc
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (key, name, av, badge_id, ts),
            )
            conn.commit()
        finally:
            conn.close()


def fetch_community_badges_for_user(
    user_key: str,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    key = (user_key or "").strip()
    if not key:
        return []
    path = db_path if db_path is not None else community_world_db_path()
    if not path.is_file():
        return []
    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=60.0)
        try:
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT badge, awarded_at_utc
                FROM community_world_badges
                WHERE user_key = ?
                ORDER BY awarded_at_utc ASC
                """,
                (key,),
            ).fetchall()
        finally:
            conn.close()
    return [{"badge": str(b), "awarded_at": str(a)} for b, a in rows]


def fetch_village_elders(
    *,
    limit: int = _MAX_ELDERS,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Top community members by number of all-time badges."""
    lim = max(1, min(_MAX_ELDERS, int(limit)))
    path = db_path if db_path is not None else community_world_db_path()
    if not path.is_file():
        return []
    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=60.0)
        try:
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT user_key,
                       (SELECT display_name FROM community_world_badges b2
                         WHERE b2.user_key = b.user_key ORDER BY b2.awarded_at_utc DESC LIMIT 1),
                       COUNT(*) AS badge_count,
                       (SELECT avatar_url FROM community_world_badges b3
                         WHERE b3.user_key = b.user_key ORDER BY b3.awarded_at_utc DESC LIMIT 1)
                FROM community_world_badges b
                GROUP BY user_key
                ORDER BY badge_count DESC, user_key ASC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        finally:
            conn.close()
    out: list[dict[str, Any]] = []
    for user_key, display_name, badge_count, avatar_url in rows:
        out.append(
            {
                "user_key": str(user_key or ""),
                "user": str(display_name or "?"),
                "badge_count": int(badge_count or 0),
                "avatar_url": str(avatar_url or ""),
            }
        )
    return out
