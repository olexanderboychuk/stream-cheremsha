from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from stream_cheremsha.persistence import points_sqlite as mod


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "points.sqlite"
    monkeypatch.setenv("STREAM_CHEREMSHA_POINTS_DB", str(path))
    return path


def test_add_points_creates_wallet_and_balance(db: Path) -> None:
    bal = mod.add_points(
        stable_key="sk1",
        unique_id="@Alice",
        display_name="Alice",
        delta=30,
        reason="follow",
    )
    assert bal == 30
    assert mod.get_balance_for_stable_key("sk1") == 30
    # Resolved by normalized handle.
    assert mod.get_balance_for_unique_id("alice") == 30
    assert mod.get_balance_for_unique_id("@ALICE") == 30


def test_balance_never_negative(db: Path) -> None:
    mod.add_points(stable_key="sk1", unique_id="a", display_name="A", delta=10, reason="x")
    bal = mod.add_points(stable_key="sk1", unique_id="a", display_name="A", delta=-50, reason="y")
    assert bal == 0


def test_unique_id_preserved_when_later_event_lacks_it(db: Path) -> None:
    mod.add_points(stable_key="sk1", unique_id="alice", display_name="Alice", delta=10, reason="x")
    mod.add_points(stable_key="sk1", unique_id="", display_name="", delta=5, reason="y")
    summary = mod.resolve_wallet_for_unique_id("alice")
    assert summary is not None
    assert summary.balance == 15
    assert summary.display_name == "Alice"


def test_try_spend_success_and_insufficient(db: Path) -> None:
    mod.add_points(stable_key="sk1", unique_id="alice", display_name="Alice", delta=100, reason="g")
    assert mod.try_spend_for_unique_id(unique_id="alice", amount=80, reason="song") is True
    assert mod.get_balance_for_unique_id("alice") == 20
    # Not enough for another 80.
    assert mod.try_spend_for_unique_id(unique_id="alice", amount=80, reason="song") is False
    assert mod.get_balance_for_unique_id("alice") == 20


def test_try_spend_unknown_handle(db: Path) -> None:
    assert mod.try_spend_for_unique_id(unique_id="ghost", amount=10, reason="song") is False


def test_try_spend_zero_is_noop_success(db: Path) -> None:
    assert mod.try_spend_for_unique_id(unique_id="ghost", amount=0, reason="song") is True


def test_refund_restores_balance(db: Path) -> None:
    mod.add_points(stable_key="sk1", unique_id="alice", display_name="Alice", delta=100, reason="g")
    assert mod.try_spend_for_unique_id(unique_id="alice", amount=100, reason="song") is True
    assert mod.get_balance_for_unique_id("alice") == 0
    assert mod.refund_for_unique_id(unique_id="alice", amount=100, reason="refund") is True
    assert mod.get_balance_for_unique_id("alice") == 100


def test_telegram_link_roundtrip(db: Path) -> None:
    assert mod.set_telegram_link(telegram_id=42, tiktok_unique_id="@Alice") is True
    assert mod.get_telegram_link(42) == "alice"
    # Re-link updates the handle.
    assert mod.set_telegram_link(telegram_id=42, tiktok_unique_id="bob") is True
    assert mod.get_telegram_link(42) == "bob"
    assert mod.get_telegram_link(999) is None


def test_get_telegram_id_for_unique_id(db: Path) -> None:
    mod.set_telegram_link(telegram_id=42, tiktok_unique_id="@Alice")
    assert mod.get_telegram_id_for_unique_id("alice") == 42
    assert mod.get_telegram_id_for_unique_id("@ALICE") == 42
    assert mod.get_telegram_id_for_unique_id("ghost") is None
    assert mod.get_telegram_id_for_unique_id("") is None


def test_get_wallet_for_stable_key(db: Path) -> None:
    mod.add_points(
        stable_key="sk1",
        unique_id="alice",
        display_name="Alice",
        delta=15,
        reason="gift",
    )
    wallet = mod.get_wallet_for_stable_key("sk1")
    assert wallet is not None
    assert wallet.unique_id == "alice"
    assert wallet.balance == 15
    assert mod.get_wallet_for_stable_key("missing") is None


def test_engagement_cooldown_remaining(db: Path) -> None:
    when = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    mod.add_points(
        stable_key="sk1",
        unique_id="alice",
        display_name="Alice",
        delta=25,
        reason="follow",
        now=when,
    )
    rem = mod.engagement_cooldown_remaining_sec(
        stable_key="sk1",
        reason="follow",
        cooldown_sec=3600,
        now=when + timedelta(minutes=30),
    )
    assert 1799 <= rem <= 1801
    assert (
        mod.engagement_cooldown_remaining_sec(
            stable_key="sk1",
            reason="follow",
            cooldown_sec=3600,
            now=when + timedelta(hours=2),
        )
        == 0.0
    )
    assert (
        mod.engagement_cooldown_remaining_sec(
            stable_key="sk1",
            reason="share",
            cooldown_sec=300,
            now=when,
        )
        == 0.0
    )
    assert (
        mod.engagement_cooldown_remaining_sec(
            stable_key="sk1",
            reason="follow",
            cooldown_sec=0,
        )
        == 0.0
    )


def test_set_link_rejects_empty_handle(db: Path) -> None:
    assert mod.set_telegram_link(telegram_id=1, tiktok_unique_id="  @  ") is False
    assert mod.get_telegram_link(1) is None


def test_end_to_end_earn_link_spend(db: Path) -> None:
    # Viewer earns via TikTok activity (keyed by stable_key, handle captured).
    mod.add_points(stable_key="sk", unique_id="alice", display_name="A", delta=60, reason="gift")
    mod.add_points(stable_key="sk", unique_id="alice", display_name="A", delta=40, reason="like")
    code = mod.create_telegram_link_challenge(telegram_id=7)
    result = mod.try_complete_telegram_link_challenge(
        code=code,
        stable_key="sk",
        unique_id="alice",
    )
    assert result.ok is True
    assert result.telegram_id == 7
    assert result.unique_id == "alice"
    handle = mod.get_telegram_link(7)
    assert handle == "alice"
    # Order a song costing 100.
    assert mod.get_balance_for_unique_id(handle) == 100
    assert mod.try_spend_for_unique_id(unique_id=handle, amount=100, reason="song_order") is True
    assert mod.get_balance_for_unique_id(handle) == 0


def test_link_challenge_rejects_wrong_sender_without_handle(db: Path) -> None:
    code = mod.create_telegram_link_challenge(telegram_id=3)
    result = mod.try_complete_telegram_link_challenge(
        code=code,
        stable_key="sk-unknown",
        unique_id="",
    )
    assert result.ok is False
    assert result.error == "missing_unique_id"
    assert mod.get_telegram_link(3) is None


def test_link_challenge_rejects_expired_code(db: Path) -> None:
    when = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    code = mod.create_telegram_link_challenge(
        telegram_id=5,
        ttl_sec=60,
        now=when,
    )
    result = mod.try_complete_telegram_link_challenge(
        code=code,
        stable_key="sk1",
        unique_id="alice",
        now=when + timedelta(minutes=2),
    )
    assert result.ok is False
    assert result.error == "expired"


def test_link_challenge_rejects_handle_linked_to_other_telegram(db: Path) -> None:
    mod.set_telegram_link(telegram_id=1, tiktok_unique_id="alice")
    code = mod.create_telegram_link_challenge(telegram_id=2)
    result = mod.try_complete_telegram_link_challenge(
        code=code,
        stable_key="sk1",
        unique_id="alice",
    )
    assert result.ok is False
    assert result.error == "handle_taken"


def test_cancel_link_challenge(db: Path) -> None:
    code = mod.create_telegram_link_challenge(telegram_id=9)
    mod.cancel_telegram_link_challenge(telegram_id=9)
    result = mod.try_complete_telegram_link_challenge(
        code=code,
        stable_key="sk1",
        unique_id="bob",
    )
    assert result.ok is False
    assert result.error == "unknown_code"
