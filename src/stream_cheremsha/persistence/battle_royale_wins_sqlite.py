"""SQLite persistence for Battle Royale hall-of-fame wins."""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_ENV_DB = "STREAM_CHEREMSHA_BATTLE_WINS_DB"
_MAX_HALL = 8


def battle_wins_db_path() -> Path:
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
                return d / "battle_royale_wins.sqlite"
    except ImportError:
        pass
    d = Path.home() / ".stream-cheremsha" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / "battle_royale_wins.sqlite"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS battle_royale_wins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            avatar_url TEXT NOT NULL DEFAULT '',
            won_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_battle_wins_at ON battle_royale_wins(won_at_utc DESC)"
    )


def record_battle_win(
    *,
    user_key: str,
    display_name: str,
    avatar_url: str = "",
    won_at: datetime | None = None,
) -> None:
    key = (user_key or "").strip()
    if not key:
        return
    name = (display_name or "").strip() or "?"
    av = (avatar_url or "").strip()
    ts = (won_at or datetime.now(UTC)).isoformat()
    path = battle_wins_db_path()
    with _LOCK:
        conn = sqlite3.connect(path)
        try:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO battle_royale_wins (user_key, display_name, avatar_url, won_at_utc)
                VALUES (?, ?, ?, ?)
                """,
                (key, name, av, ts),
            )
            conn.commit()
        finally:
            conn.close()


def fetch_hall_of_fame(*, limit: int = _MAX_HALL) -> list[dict[str, Any]]:
    lim = max(1, min(_MAX_HALL, int(limit)))
    path = battle_wins_db_path()
    if not path.is_file():
        return []
    with _LOCK:
        conn = sqlite3.connect(path)
        try:
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT user_key, display_name, avatar_url, won_at_utc
                FROM battle_royale_wins
                ORDER BY won_at_utc DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        finally:
            conn.close()
    out: list[dict[str, Any]] = []
    for user_key, display_name, avatar_url, won_at in rows:
        out.append(
            {
                "user_key": str(user_key or ""),
                "user": str(display_name or "?"),
                "avatar_url": str(avatar_url or ""),
                "won_at": str(won_at or ""),
            }
        )
    return out


def fetch_battle_stats_for_users(user_keys: list[str]) -> dict[str, dict[str, int]]:
    """Return per-user win totals and global rank (1 = most wins)."""
    keys = [str(k or "").strip() for k in user_keys if str(k or "").strip()]
    if not keys:
        return {}
    path = battle_wins_db_path()
    if not path.is_file():
        return {k: {"wins": 0, "rank": 0} for k in keys}
    with _LOCK:
        conn = sqlite3.connect(path)
        try:
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT user_key, COUNT(*) AS wins
                FROM battle_royale_wins
                GROUP BY user_key
                ORDER BY wins DESC, user_key ASC
                """
            ).fetchall()
        finally:
            conn.close()
    rank_by_key: dict[str, int] = {}
    for i, (user_key, _wins) in enumerate(rows, start=1):
        rank_by_key[str(user_key or "")] = i
    wins_by_key = {str(user_key or ""): int(_wins) for user_key, _wins in rows}
    out: dict[str, dict[str, int]] = {}
    for k in keys:
        out[k] = {
            "wins": int(wins_by_key.get(k, 0)),
            "rank": int(rank_by_key.get(k, 0)),
        }
    return out
