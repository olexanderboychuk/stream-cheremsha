"""SQLite persistence for TikTok Live gifts and viewer profiles."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_ENV_DB = "STREAM_CHEREMSHA_TIKTOK_GIFTS_DB"
_RAW_JSON_MAX = 262_144
_USER_JSON_MAX = 65_536


def tiktok_gifts_db_path() -> Path:
    """Return path to the gifts database file, creating parent dirs when needed."""
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
                return d / "tiktok_gifts.sqlite"
    except ImportError:
        pass
    d = Path.home() / ".stream-cheremsha" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / "tiktok_gifts.sqlite"


def _nick_unique_from_bundle(bundle: str) -> tuple[str, str]:
    if not (bundle or "").strip():
        return "", ""
    try:
        data = json.loads(bundle)
    except (json.JSONDecodeError, TypeError, UnicodeError):
        return "", ""
    if not isinstance(data, dict):
        return "", ""
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return "", ""
    nick = str(fields.get("nickname") or fields.get("nick_name") or "").strip()
    uniq = str(fields.get("unique_id") or fields.get("uniqueId") or "").strip()
    return nick, uniq


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stable_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            nickname TEXT NOT NULL DEFAULT '',
            unique_id TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            profile_json TEXT NOT NULL DEFAULT '',
            first_seen_utc TEXT NOT NULL,
            last_seen_utc TEXT NOT NULL,
            UNIQUE (stable_key),
            CHECK (length(trim(stable_key)) > 0)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at_utc TEXT NOT NULL,
            -- Normalized TikTok unique_id of the live host (same as TikTokChatSource.start()).
            anchor_username TEXT NOT NULL,
            sender_display TEXT NOT NULL,
            sender_user_key TEXT NOT NULL,
            gift_id TEXT NOT NULL,
            gift_name TEXT NOT NULL,
            gift_count INTEGER NOT NULL,
            diamond_each INTEGER NOT NULL,
            diamonds_total INTEGER NOT NULL,
            gift_icon_url TEXT NOT NULL,
            sender_avatar_url TEXT NOT NULL,
            raw_json TEXT NOT NULL
        )
        """
    )
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(tiktok_gifts)")}
    if "tiktok_user_id" not in cols:
        conn.execute(
            "ALTER TABLE tiktok_gifts ADD COLUMN tiktok_user_id INTEGER "
            "REFERENCES tiktok_users (id)"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tiktok_users_last_seen ON tiktok_users(last_seen_utc)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tiktok_gifts_received ON tiktok_gifts(received_at_utc)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tiktok_gifts_sender_key "
        "ON tiktok_gifts(sender_user_key, received_at_utc)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tiktok_gifts_anchor_time "
        "ON tiktok_gifts(anchor_username, received_at_utc)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_gifts_user ON tiktok_gifts(tiktok_user_id)")


def _upsert_tiktok_user(
    conn: sqlite3.Connection,
    *,
    stable_key: str,
    display_name: str,
    nickname: str,
    unique_id: str,
    avatar_url: str,
    profile_json: str,
    now_iso: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO tiktok_users (
            stable_key,
            display_name,
            nickname,
            unique_id,
            avatar_url,
            profile_json,
            first_seen_utc,
            last_seen_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stable_key) DO UPDATE SET
            display_name = excluded.display_name,
            nickname = excluded.nickname,
            unique_id = excluded.unique_id,
            avatar_url = excluded.avatar_url,
            profile_json = excluded.profile_json,
            last_seen_utc = excluded.last_seen_utc
        RETURNING id
        """,
        (
            stable_key,
            display_name,
            nickname,
            unique_id,
            avatar_url,
            profile_json,
            now_iso,
            now_iso,
        ),
    )
    row = cur.fetchone()
    if row is not None:
        return int(row[0])
    got = conn.execute(
        "SELECT id FROM tiktok_users WHERE stable_key = ? LIMIT 1",
        (stable_key,),
    ).fetchone()
    if got is None:
        raise sqlite3.IntegrityError("tiktok_users upsert returned no id")
    return int(got[0])


def append_tiktok_gift_event(
    *,
    anchor_username: str,
    received_at: datetime,
    sender_display: str,
    sender_user_key: str,
    gift_id: str,
    gift_name: str,
    gift_count: int,
    diamond_each: int,
    diamonds_total: int,
    gift_icon_url: str,
    sender_avatar_url: str,
    raw_json: str,
    tiktok_user_bundle_json: str = "",
    db_path: Path | None = None,
) -> None:
    """Insert one gift row; upserts ``tiktok_users`` when ``sender_user_key`` is non-empty.

    ``anchor_username`` must be the normalized TikTok **stream host** handle (the same
    ``unique_id`` passed to ``TikTokChatSource.start()``), not the gifter.
    """
    path = db_path if db_path is not None else tiktok_gifts_db_path()
    raw = raw_json if len(raw_json) <= _RAW_JSON_MAX else raw_json[:_RAW_JSON_MAX]
    bundle = (
        tiktok_user_bundle_json
        if len(tiktok_user_bundle_json) <= _USER_JSON_MAX
        else tiktok_user_bundle_json[:_USER_JSON_MAX]
    )
    iso = received_at.isoformat()
    anchor = (anchor_username or "").strip()
    sk = (sender_user_key or "").strip()
    nick, uniq = _nick_unique_from_bundle(bundle)
    display = (sender_display or "").strip() or "?"
    avatar = (sender_avatar_url or "").strip()

    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=60.0)
        try:
            _ensure_schema(conn)
            user_row_id: int | None
            if sk:
                user_row_id = _upsert_tiktok_user(
                    conn,
                    stable_key=sk,
                    display_name=display,
                    nickname=nick,
                    unique_id=uniq,
                    avatar_url=avatar,
                    profile_json=bundle or "{}",
                    now_iso=iso,
                )
            else:
                user_row_id = None
            conn.execute(
                """
                INSERT INTO tiktok_gifts (
                    received_at_utc,
                    anchor_username,
                    sender_display,
                    sender_user_key,
                    gift_id,
                    gift_name,
                    gift_count,
                    diamond_each,
                    diamonds_total,
                    gift_icon_url,
                    sender_avatar_url,
                    raw_json,
                    tiktok_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iso,
                    anchor,
                    display,
                    sk,
                    (gift_id or "").strip(),
                    (gift_name or "").strip(),
                    int(gift_count),
                    int(diamond_each),
                    int(diamonds_total),
                    (gift_icon_url or "").strip(),
                    avatar,
                    raw,
                    user_row_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def fetch_all_time_gifter_totals(
    *,
    limit: int = 10,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return top gifters by sum of ``diamonds_total`` across all stored streams.

    Rows are ordered by total diamonds descending. Only rows with a non-empty
    ``sender_user_key`` participate (same key used for session overlays).
    """
    lim = max(1, min(50, int(limit)))
    path = db_path if db_path is not None else tiktok_gifts_db_path()
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=60.0)
        try:
            _ensure_schema(conn)
            cur = conn.execute(
                """
                SELECT
                    TRIM(g.sender_user_key) AS sender_user_key,
                    SUM(g.diamonds_total) AS diamonds,
                    MAX(
                        COALESCE(
                            NULLIF(TRIM(u.display_name), ''),
                            NULLIF(TRIM(g.sender_display), ''),
                            '?'
                        )
                    ) AS display_name,
                    MAX(
                        COALESCE(
                            NULLIF(TRIM(u.avatar_url), ''),
                            NULLIF(TRIM(g.sender_avatar_url), ''),
                            ''
                        )
                    ) AS avatar_url
                FROM tiktok_gifts g
                LEFT JOIN tiktok_users u ON u.stable_key = g.sender_user_key
                WHERE LENGTH(TRIM(COALESCE(g.sender_user_key, ''))) > 0
                GROUP BY TRIM(g.sender_user_key)
                HAVING SUM(g.diamonds_total) > 0
                ORDER BY diamonds DESC, display_name COLLATE NOCASE ASC
                LIMIT ?
                """,
                (lim,),
            )
            for row in cur.fetchall():
                key_s = str(row[0] or "").strip()
                if not key_s:
                    continue
                try:
                    d = int(row[1] or 0)
                except (TypeError, ValueError):
                    d = 0
                out.append(
                    {
                        "key": key_s,
                        "user": str(row[2] or "").strip() or "?",
                        "avatar_url": str(row[3] or "").strip(),
                        "diamonds": d,
                    }
                )
        finally:
            conn.close()
    return out
