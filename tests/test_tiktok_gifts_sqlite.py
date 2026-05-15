from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from stream_cheremsha.persistence import tiktok_gifts_sqlite as mod


def _bundle(*, nick: str = "", uniq: str = "", sk: str = "secuid123") -> str:
    return json.dumps(
        {
            "stable_key": sk,
            "display_fallback": "bob",
            "avatar_url": "https://example.com/a.png",
            "fields": {"nickname": nick, "unique_id": uniq},
            "profile": {},
        },
        ensure_ascii=False,
    )


def test_append_gift_writes_row_and_links_user(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "gifts.sqlite"
    monkeypatch.setenv("STREAM_CHEREMSHA_TIKTOK_GIFTS_DB", str(db))
    when = datetime(2026, 5, 15, 12, 34, 56, tzinfo=UTC)
    mod.append_tiktok_gift_event(
        anchor_username="anchor1",
        received_at=when,
        sender_display="bob",
        sender_user_key="secuid123",
        gift_id="99",
        gift_name="Rose",
        gift_count=3,
        diamond_each=5,
        diamonds_total=15,
        gift_icon_url="https://example.com/g.png",
        sender_avatar_url="https://example.com/a.png",
        raw_json='{"x":1}',
        tiktok_user_bundle_json=_bundle(nick="BobN", uniq="bob_u"),
        db_path=db,
    )
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute("SELECT COUNT(*) FROM tiktok_gifts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tiktok_users").fetchone()[0] == 1
        uid = conn.execute(
            "SELECT id FROM tiktok_users WHERE stable_key = ?",
            ("secuid123",),
        ).fetchone()
        assert uid is not None
        fk = conn.execute("SELECT tiktok_user_id FROM tiktok_gifts LIMIT 1").fetchone()
        assert fk is not None and fk[0] == uid[0]
        row = conn.execute(
            "SELECT nickname, unique_id, avatar_url FROM tiktok_users WHERE id = ?",
            (uid[0],),
        ).fetchone()
        assert row == ("BobN", "bob_u", "https://example.com/a.png")
    finally:
        conn.close()
    monkeypatch.delenv("STREAM_CHEREMSHA_TIKTOK_GIFTS_DB", raising=False)


def test_same_stable_key_reuses_user_row(tmp_path: Path) -> None:
    db = tmp_path / "g.sqlite"
    when = datetime(2026, 1, 1, tzinfo=UTC)
    mod.append_tiktok_gift_event(
        anchor_username="a",
        received_at=when,
        sender_display="u",
        sender_user_key="same",
        gift_id="1",
        gift_name="g",
        gift_count=1,
        diamond_each=1,
        diamonds_total=1,
        gift_icon_url="",
        sender_avatar_url="https://a/1.png",
        raw_json="{}",
        tiktok_user_bundle_json=_bundle(sk="same", nick="N1", uniq="h1"),
        db_path=db,
    )
    mod.append_tiktok_gift_event(
        anchor_username="a",
        received_at=when,
        sender_display="u2",
        sender_user_key="same",
        gift_id="2",
        gift_name="g2",
        gift_count=1,
        diamond_each=2,
        diamonds_total=2,
        gift_icon_url="",
        sender_avatar_url="https://a/2.png",
        raw_json="{}",
        tiktok_user_bundle_json=_bundle(sk="same", nick="N2", uniq="h2"),
        db_path=db,
    )
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute("SELECT COUNT(*) FROM tiktok_users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tiktok_gifts").fetchone()[0] == 2
        u = conn.execute(
            "SELECT display_name, nickname, avatar_url FROM tiktok_users WHERE stable_key = ?",
            ("same",),
        ).fetchone()
        assert u is not None
        assert u[0] == "u2"
        assert u[1] == "N2"
        assert u[2] == "https://a/2.png"
    finally:
        conn.close()


def test_fetch_all_time_gifter_totals_orders_by_diamonds(tmp_path: Path) -> None:
    db = tmp_path / "rank.sqlite"
    when = datetime(2026, 3, 1, tzinfo=UTC)
    for sk, total in (("a", 100), ("b", 500), ("c", 200)):
        mod.append_tiktok_gift_event(
            anchor_username="host",
            received_at=when,
            sender_display=sk.upper(),
            sender_user_key=sk,
            gift_id="1",
            gift_name="g",
            gift_count=1,
            diamond_each=total,
            diamonds_total=total,
            gift_icon_url="",
            sender_avatar_url="",
            raw_json="{}",
            tiktok_user_bundle_json="{}",
            db_path=db,
        )
    rows = mod.fetch_all_time_gifter_totals(limit=10, db_path=db)
    assert [r["key"] for r in rows] == ["b", "c", "a"]
    assert rows[0]["diamonds"] == 500
    assert rows[0]["user"] == "B"


def test_empty_stable_key_skips_user_row(tmp_path: Path) -> None:
    db = tmp_path / "anon.sqlite"
    mod.append_tiktok_gift_event(
        anchor_username="",
        received_at=datetime.now(UTC),
        sender_display="ghost",
        sender_user_key="",
        gift_id="1",
        gift_name="g",
        gift_count=1,
        diamond_each=0,
        diamonds_total=0,
        gift_icon_url="",
        sender_avatar_url="https://x/p.png",
        raw_json="{}",
        tiktok_user_bundle_json="{}",
        db_path=db,
    )
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute("SELECT COUNT(*) FROM tiktok_users").fetchone()[0] == 0
        fk = conn.execute("SELECT tiktok_user_id FROM tiktok_gifts LIMIT 1").fetchone()
        assert fk is not None and fk[0] is None
    finally:
        conn.close()


def test_tiktok_gifts_db_path_respects_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "sub" / "x.sqlite"
    monkeypatch.setenv("STREAM_CHEREMSHA_TIKTOK_GIFTS_DB", str(db))
    assert mod.tiktok_gifts_db_path() == db
    assert db.parent.is_dir()
    monkeypatch.delenv("STREAM_CHEREMSHA_TIKTOK_GIFTS_DB", raising=False)


def test_append_truncates_huge_raw_json(tmp_path: Path) -> None:
    db = tmp_path / "g.sqlite"
    huge = "a" * (mod._RAW_JSON_MAX + 5000)
    mod.append_tiktok_gift_event(
        anchor_username="",
        received_at=datetime.now(UTC),
        sender_display="u",
        sender_user_key="",
        gift_id="1",
        gift_name="g",
        gift_count=1,
        diamond_each=0,
        diamonds_total=0,
        gift_icon_url="",
        sender_avatar_url="",
        raw_json=huge,
        db_path=db,
    )
    conn = sqlite3.connect(str(db))
    try:
        raw = conn.execute("SELECT LENGTH(raw_json) FROM tiktok_gifts").fetchone()
        assert raw is not None and raw[0] == mod._RAW_JSON_MAX
    finally:
        conn.close()
