"""SQLite persistence for the song-request points economy.

Three tables, all in a dedicated DB file (override via
``STREAM_CHEREMSHA_POINTS_DB``):

* ``points_wallet`` — one row per TikTok viewer (keyed by the stable viewer key),
  holding the current balance plus the latest seen ``unique_id`` (TikTok handle)
  used to resolve Telegram links.
* ``points_ledger`` — append-only audit log of every credit/debit, for debugging
  and dispute resolution.
* ``telegram_links`` — maps a Telegram user id to the TikTok ``unique_id`` they
  entered once in the bot. Balance/spend resolve through this handle.

All writes take a process-wide lock and run in a single transaction so concurrent
earn events and spends cannot corrupt a balance or double-spend.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from stream_cheremsha.domain.points import normalize_tiktok_username
from stream_cheremsha.domain.tiktok_link_challenge import (
    DEFAULT_LINK_CHALLENGE_TTL_SEC,
    generate_link_code,
    normalize_link_code,
)

_LOCK = threading.Lock()
_ENV_DB = "STREAM_CHEREMSHA_POINTS_DB"


@dataclass(frozen=True, slots=True)
class WalletSummary:
    """Resolved wallet snapshot for a TikTok handle."""

    stable_key: str
    unique_id: str
    display_name: str
    balance: int


@dataclass(frozen=True, slots=True)
class LinkChallengeResult:
    """Outcome of attempting to complete a TikTok chat link challenge."""

    ok: bool
    telegram_id: int = 0
    unique_id: str = ""
    error: str = ""


def points_db_path() -> Path:
    """Return the points DB path, creating parent dirs when needed."""
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
                return d / "points.sqlite"
    except ImportError:
        pass
    d = Path.home() / ".stream-cheremsha" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / "points.sqlite"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS points_wallet (
            stable_key TEXT PRIMARY KEY,
            unique_id TEXT NOT NULL DEFAULT '',
            display_name TEXT NOT NULL DEFAULT '',
            balance INTEGER NOT NULL DEFAULT 0,
            updated_utc TEXT NOT NULL,
            CHECK (length(trim(stable_key)) > 0),
            CHECK (balance >= 0)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS points_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stable_key TEXT NOT NULL,
            unique_id TEXT NOT NULL DEFAULT '',
            delta INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            ref TEXT NOT NULL DEFAULT '',
            created_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_links (
            telegram_id INTEGER PRIMARY KEY,
            tiktok_unique_id TEXT NOT NULL,
            linked_utc TEXT NOT NULL,
            CHECK (length(trim(tiktok_unique_id)) > 0)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_points_wallet_unique "
        "ON points_wallet(unique_id, updated_utc)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_points_ledger_key ON points_ledger(stable_key, id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_points_ledger_key_reason "
        "ON points_ledger(stable_key, reason, id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telegram_links_unique ON telegram_links(tiktok_unique_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_link_challenges (
            code TEXT PRIMARY KEY,
            telegram_id INTEGER NOT NULL,
            created_utc TEXT NOT NULL,
            expires_utc TEXT NOT NULL,
            CHECK (length(trim(code)) > 0)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telegram_link_challenges_tid "
        "ON telegram_link_challenges(telegram_id)"
    )


def _now_iso(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).isoformat()


def _connect(db_path: Path | None) -> sqlite3.Connection:
    path = db_path if db_path is not None else points_db_path()
    conn = sqlite3.connect(str(path), timeout=60.0)
    _ensure_schema(conn)
    return conn


def add_points(
    *,
    stable_key: str,
    unique_id: str,
    display_name: str,
    delta: int,
    reason: str,
    ref: str = "",
    now: datetime | None = None,
    db_path: Path | None = None,
) -> int:
    """Credit (or debit) ``delta`` points to ``stable_key`` and log the ledger row.

    Returns the new balance. The balance never drops below zero (a debit larger
    than the balance clamps to zero). ``unique_id`` is normalized and stored so a
    later Telegram link can resolve this wallet by handle.
    """
    sk = (stable_key or "").strip()
    if not sk:
        return 0
    try:
        d = int(delta)
    except (TypeError, ValueError):
        d = 0
    if d == 0:
        return get_balance_for_stable_key(sk, db_path=db_path)
    uid = normalize_tiktok_username(unique_id)
    name = (display_name or "").strip()
    iso = _now_iso(now)
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT balance FROM points_wallet WHERE stable_key = ?",
                (sk,),
            ).fetchone()
            current = int(row[0]) if row is not None else 0
            new_balance = max(0, current + d)
            applied = new_balance - current
            conn.execute(
                """
                INSERT INTO points_wallet (
                    stable_key, unique_id, display_name, balance, updated_utc
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(stable_key) DO UPDATE SET
                    balance = excluded.balance,
                    updated_utc = excluded.updated_utc,
                    unique_id = CASE
                        WHEN length(trim(excluded.unique_id)) > 0
                        THEN excluded.unique_id ELSE points_wallet.unique_id END,
                    display_name = CASE
                        WHEN length(trim(excluded.display_name)) > 0
                        THEN excluded.display_name ELSE points_wallet.display_name END
                """,
                (sk, uid, name, new_balance, iso),
            )
            conn.execute(
                """
                INSERT INTO points_ledger (
                    stable_key, unique_id, delta, reason, ref, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sk, uid, applied, (reason or "").strip(), (ref or "").strip(), iso),
            )
            conn.commit()
            return new_balance
        finally:
            conn.close()


def get_balance_for_stable_key(stable_key: str, *, db_path: Path | None = None) -> int:
    sk = (stable_key or "").strip()
    if not sk:
        return 0
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT balance FROM points_wallet WHERE stable_key = ?",
                (sk,),
            ).fetchone()
            return int(row[0]) if row is not None else 0
        finally:
            conn.close()


def get_wallet_for_stable_key(
    stable_key: str,
    *,
    db_path: Path | None = None,
) -> WalletSummary | None:
    """Return the wallet row for ``stable_key``, or ``None`` when missing."""
    sk = (stable_key or "").strip()
    if not sk:
        return None
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT stable_key, unique_id, display_name, balance
                FROM points_wallet
                WHERE stable_key = ?
                LIMIT 1
                """,
                (sk,),
            ).fetchone()
            if row is None:
                return None
            return WalletSummary(
                stable_key=str(row[0]),
                unique_id=str(row[1] or ""),
                display_name=str(row[2] or ""),
                balance=int(row[3] or 0),
            )
        finally:
            conn.close()


def _resolve_wallet(conn: sqlite3.Connection, unique_id: str) -> WalletSummary | None:
    uid = normalize_tiktok_username(unique_id)
    if not uid:
        return None
    row = conn.execute(
        """
        SELECT stable_key, unique_id, display_name, balance
        FROM points_wallet
        WHERE LOWER(TRIM(unique_id)) = ?
        ORDER BY updated_utc DESC, balance DESC
        LIMIT 1
        """,
        (uid,),
    ).fetchone()
    if row is None:
        return None
    return WalletSummary(
        stable_key=str(row[0]),
        unique_id=str(row[1] or ""),
        display_name=str(row[2] or ""),
        balance=int(row[3] or 0),
    )


def engagement_cooldown_remaining_sec(
    *,
    stable_key: str,
    reason: str,
    cooldown_sec: int,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> float:
    """Seconds until another earn of ``reason`` is allowed for ``stable_key``.

    Returns ``0`` when an award is allowed now (including when there is no prior
    ledger row). A non-positive ``cooldown_sec`` always returns ``0``.
    """
    try:
        cd = int(cooldown_sec)
    except (TypeError, ValueError):
        cd = 0
    if cd <= 0:
        return 0.0
    sk = (stable_key or "").strip()
    r = (reason or "").strip()
    if not sk or not r:
        return 0.0
    now_dt = now if now is not None else datetime.now(UTC)
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT created_utc FROM points_ledger
                WHERE stable_key = ? AND reason = ? AND delta > 0
                ORDER BY id DESC
                LIMIT 1
                """,
                (sk, r),
            ).fetchone()
            if row is None:
                return 0.0
            raw = str(row[0] or "").strip()
            if not raw:
                return 0.0
            try:
                last = datetime.fromisoformat(raw)
            except ValueError:
                return 0.0
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            elapsed = (now_dt - last).total_seconds()
            return max(0.0, float(cd) - elapsed)
        finally:
            conn.close()


def resolve_wallet_for_unique_id(
    unique_id: str,
    *,
    db_path: Path | None = None,
) -> WalletSummary | None:
    """Return the wallet for a TikTok handle, or ``None`` if it has no wallet yet."""
    with _LOCK:
        conn = _connect(db_path)
        try:
            return _resolve_wallet(conn, unique_id)
        finally:
            conn.close()


def get_balance_for_unique_id(unique_id: str, *, db_path: Path | None = None) -> int:
    """Return the balance for a TikTok handle (0 if no wallet exists yet)."""
    summary = resolve_wallet_for_unique_id(unique_id, db_path=db_path)
    return summary.balance if summary is not None else 0


def try_spend_for_unique_id(
    *,
    unique_id: str,
    amount: int,
    reason: str,
    ref: str = "",
    now: datetime | None = None,
    db_path: Path | None = None,
) -> bool:
    """Atomically debit ``amount`` from the wallet behind ``unique_id``.

    Returns ``True`` when the balance covered the cost (and was debited), ``False``
    when the handle has no wallet or insufficient balance. ``amount <= 0`` always
    succeeds without touching the wallet.
    """
    try:
        amt = int(amount)
    except (TypeError, ValueError):
        return False
    if amt <= 0:
        return True
    iso = _now_iso(now)
    with _LOCK:
        conn = _connect(db_path)
        try:
            wallet = _resolve_wallet(conn, unique_id)
            if wallet is None or wallet.balance < amt:
                return False
            new_balance = wallet.balance - amt
            conn.execute(
                "UPDATE points_wallet SET balance = ?, updated_utc = ? WHERE stable_key = ?",
                (new_balance, iso, wallet.stable_key),
            )
            conn.execute(
                """
                INSERT INTO points_ledger (
                    stable_key, unique_id, delta, reason, ref, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    wallet.stable_key,
                    wallet.unique_id,
                    -amt,
                    (reason or "").strip(),
                    (ref or "").strip(),
                    iso,
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()


def refund_for_unique_id(
    *,
    unique_id: str,
    amount: int,
    reason: str,
    ref: str = "",
    now: datetime | None = None,
    db_path: Path | None = None,
) -> bool:
    """Credit ``amount`` back to the wallet behind ``unique_id`` (reverse a spend)."""
    try:
        amt = int(amount)
    except (TypeError, ValueError):
        return False
    if amt <= 0:
        return True
    iso = _now_iso(now)
    with _LOCK:
        conn = _connect(db_path)
        try:
            wallet = _resolve_wallet(conn, unique_id)
            if wallet is None:
                return False
            new_balance = wallet.balance + amt
            conn.execute(
                "UPDATE points_wallet SET balance = ?, updated_utc = ? WHERE stable_key = ?",
                (new_balance, iso, wallet.stable_key),
            )
            conn.execute(
                """
                INSERT INTO points_ledger (
                    stable_key, unique_id, delta, reason, ref, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    wallet.stable_key,
                    wallet.unique_id,
                    amt,
                    (reason or "").strip(),
                    (ref or "").strip(),
                    iso,
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()


def set_telegram_link(
    *,
    telegram_id: int,
    tiktok_unique_id: str,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> bool:
    """Link a Telegram user to a TikTok handle (idempotent upsert).

    Returns ``False`` when the handle normalizes to empty.
    """
    uid = normalize_tiktok_username(tiktok_unique_id)
    if not uid:
        return False
    iso = _now_iso(now)
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO telegram_links (telegram_id, tiktok_unique_id, linked_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    tiktok_unique_id = excluded.tiktok_unique_id,
                    linked_utc = excluded.linked_utc
                """,
                (int(telegram_id), uid, iso),
            )
            conn.commit()
            return True
        finally:
            conn.close()


def get_telegram_link(telegram_id: int, *, db_path: Path | None = None) -> str | None:
    """Return the linked TikTok handle for a Telegram user, or ``None``."""
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT tiktok_unique_id FROM telegram_links WHERE telegram_id = ?",
                (int(telegram_id),),
            ).fetchone()
            if row is None:
                return None
            uid = str(row[0] or "").strip()
            return uid or None
        finally:
            conn.close()


def get_telegram_id_for_unique_id(
    unique_id: str,
    *,
    db_path: Path | None = None,
) -> int | None:
    """Return the Telegram user id linked to a TikTok handle, or ``None``."""
    uid = normalize_tiktok_username(unique_id)
    if not uid:
        return None
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT telegram_id FROM telegram_links
                WHERE LOWER(TRIM(tiktok_unique_id)) = ?
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
            if row is None:
                return None
            return int(row[0])
        finally:
            conn.close()


def _purge_expired_link_challenges(conn: sqlite3.Connection, now: datetime) -> None:
    iso = _now_iso(now)
    conn.execute("DELETE FROM telegram_link_challenges WHERE expires_utc <= ?", (iso,))


def create_telegram_link_challenge(
    *,
    telegram_id: int,
    ttl_sec: int = DEFAULT_LINK_CHALLENGE_TTL_SEC,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> str:
    """Create a one-time code for ``telegram_id`` to post in TikTok live chat.

    Replaces any prior pending challenge for the same Telegram user.
    """
    now_dt = now if now is not None else datetime.now(UTC)
    try:
        ttl = int(ttl_sec)
    except (TypeError, ValueError):
        ttl = DEFAULT_LINK_CHALLENGE_TTL_SEC
    ttl = max(60, ttl)
    created = _now_iso(now_dt)
    expires = _now_iso(now_dt + timedelta(seconds=ttl))
    tid = int(telegram_id)
    with _LOCK:
        conn = _connect(db_path)
        try:
            _purge_expired_link_challenges(conn, now_dt)
            conn.execute(
                "DELETE FROM telegram_link_challenges WHERE telegram_id = ?",
                (tid,),
            )
            for _ in range(8):
                code = generate_link_code()
                try:
                    conn.execute(
                        """
                        INSERT INTO telegram_link_challenges (
                            code, telegram_id, created_utc, expires_utc
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (code, tid, created, expires),
                    )
                    conn.commit()
                    return code
                except sqlite3.IntegrityError:
                    continue
            raise RuntimeError("failed to allocate unique link challenge code")
        finally:
            conn.close()


def cancel_telegram_link_challenge(
    *,
    telegram_id: int,
    db_path: Path | None = None,
) -> None:
    """Drop any pending link challenge for ``telegram_id``."""
    tid = int(telegram_id)
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute(
                "DELETE FROM telegram_link_challenges WHERE telegram_id = ?",
                (tid,),
            )
            conn.commit()
        finally:
            conn.close()


def try_complete_telegram_link_challenge(
    *,
    code: str,
    stable_key: str,
    unique_id: str,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> LinkChallengeResult:
    """Verify a chat comment code and link the sender's TikTok to Telegram."""
    normalized_code = normalize_link_code(code)
    sk = (stable_key or "").strip()
    if not normalized_code:
        return LinkChallengeResult(ok=False, error="invalid_code")
    if not sk:
        return LinkChallengeResult(ok=False, error="missing_stable_key")
    uid = normalize_tiktok_username(unique_id)
    if not uid:
        wallet = get_wallet_for_stable_key(sk, db_path=db_path)
        if wallet is not None and wallet.unique_id:
            uid = normalize_tiktok_username(wallet.unique_id)
    if not uid:
        return LinkChallengeResult(ok=False, error="missing_unique_id")
    now_dt = now if now is not None else datetime.now(UTC)
    now_iso = _now_iso(now_dt)
    linked_iso = _now_iso(now_dt)
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT telegram_id, expires_utc FROM telegram_link_challenges
                WHERE code = ?
                LIMIT 1
                """,
                (normalized_code,),
            ).fetchone()
            if row is None:
                return LinkChallengeResult(ok=False, error="unknown_code")
            expires_raw = str(row[1] or "").strip()
            if expires_raw and expires_raw <= now_iso:
                conn.execute(
                    "DELETE FROM telegram_link_challenges WHERE code = ?",
                    (normalized_code,),
                )
                conn.commit()
                return LinkChallengeResult(ok=False, error="expired")
            telegram_id = int(row[0])
            taken = conn.execute(
                """
                SELECT telegram_id FROM telegram_links
                WHERE LOWER(TRIM(tiktok_unique_id)) = ?
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
            if taken is not None and int(taken[0]) != telegram_id:
                return LinkChallengeResult(ok=False, error="handle_taken")
            conn.execute(
                """
                INSERT INTO telegram_links (telegram_id, tiktok_unique_id, linked_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    tiktok_unique_id = excluded.tiktok_unique_id,
                    linked_utc = excluded.linked_utc
                """,
                (telegram_id, uid, linked_iso),
            )
            conn.execute(
                "DELETE FROM telegram_link_challenges WHERE code = ?",
                (normalized_code,),
            )
            conn.commit()
            return LinkChallengeResult(ok=True, telegram_id=telegram_id, unique_id=uid)
        finally:
            conn.close()
