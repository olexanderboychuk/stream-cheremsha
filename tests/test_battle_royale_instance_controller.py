"""Tests for ``stream_cheremsha.overlays.battle_royale_controller``.

The instance controller is a thin GUI adapter over the pure
``BattleRoyaleController`` engine + ``OverlayPubSub``. These tests pin down
the per-instance contract that ``overlay:battle_royale:{instance}`` OBS
sources depend on (mirrors ``test_battle_controller.py``):

* each instance publishes only to its own topic (no cross-instance leakage),
* unknown-price TikTok gifts (``tiktok_coin_each=0``) fall back to gift
  count so they still qualify for auto-arm,
* ``tick_advance`` drives countdown/active transitions and publishes,
* ``start_manual`` / ``stop_battle`` / ``reset_for_new_stream`` behave.

All tests use in-memory configs via ``config_loader``; no QSettings or disk
state is involved.
"""

from __future__ import annotations

import time

from stream_cheremsha.overlays.battle_royale_controller import (
    BattleRoyaleInstanceController,
)
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    BattleRoyaleOverlayConfig,
    battle_royale_overlay_config_defaults,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _cfg(**overrides: object) -> BattleRoyaleOverlayConfig:
    return battle_royale_overlay_config_defaults().replace(**overrides)  # type: ignore[arg-type]


def _controller(
    instance: str, ps: OverlayPubSub, **overrides: object
) -> BattleRoyaleInstanceController:
    return BattleRoyaleInstanceController(
        pubsub=ps,
        get_locale=lambda: "uk",
        instance=instance,
        config_loader=lambda: _cfg(**overrides),
    )


def _gift(
    ctl: BattleRoyaleInstanceController,
    sender: str,
    key: str,
    count: int = 1,
    each: int = 0,
) -> None:
    ctl.on_gift(
        sender=sender,
        count=count,
        tiktok_coin_each=each,
        gift_id="g1",
        gift_name="Rose",
        sender_avatar_url="",
        sender_user_key=key,
    )


def test_instance_topics_are_isolated() -> None:
    """Arming instance ``a`` must never leak a patch to instance ``b``."""
    ps = OverlayPubSub()
    q_a = ps.subscribe("overlay:battle_royale:a")
    q_b = ps.subscribe("overlay:battle_royale:b")

    ctl_a = _controller("a", ps, auto_arm_enabled=True, auto_threshold_each=1)

    _gift(ctl_a, "U1", "u1")
    _gift(ctl_a, "U2", "u2")
    # The arming gift already published synchronously; nothing else queued.

    assert q_a.qsize() == 1
    assert q_b.qsize() == 0  # no leakage to another instance's topic
    patch_a = q_a.get_nowait()
    assert patch_a["phase"] == "countdown"
    assert len(patch_a["fighters"]) == 2

    # Reverse direction: arming "b" must not touch "a"'s topic either.
    ctl_b = _controller("b", ps, auto_arm_enabled=True, auto_threshold_each=1)
    ctl_b.on_gift(sender="U3", count=10, sender_user_key="u3", sender_avatar_url="")
    ctl_b.on_gift(sender="U4", count=20, sender_user_key="u4", sender_avatar_url="")

    assert q_a.qsize() == 0  # still only "a"'s own patch
    assert q_b.qsize() == 1  # and now only "b"'s own patch
    patch_b = q_b.get_nowait()
    assert patch_b["phase"] == "countdown"


def test_zero_price_gifts_fall_back_to_count() -> None:
    """Gifts with unknown TikTok price still auto-arm at threshold 1."""
    ps = OverlayPubSub()
    ctl = _controller("main", ps, auto_arm_enabled=True, auto_threshold_each=1, auto_window_s=120)

    _gift(ctl, "Alice", "a", count=1, each=0)
    assert ctl.phase_value() == "idle"
    _gift(ctl, "Bob", "b", count=1, each=0)
    assert ctl.phase_value() == "countdown"


def test_distinct_thresholds_per_instance() -> None:
    """Same gifts arm a threshold-1 instance but not a threshold-100 one."""
    ps = OverlayPubSub()
    low = _controller("low", ps, auto_arm_enabled=True, auto_threshold_each=1)
    high = _controller("high", ps, auto_arm_enabled=True, auto_threshold_each=100)

    for ctl in (low, high):
        _gift(ctl, "Alice", "a", count=1, each=0)
        _gift(ctl, "Bob", "b", count=1, each=0)

    assert low.phase_value() == "countdown"
    assert high.phase_value() == "idle"


def test_tick_advances_countdown_to_active() -> None:
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:battle_royale:main")
    ctl = _controller("main", ps, countdown_s=5, round_duration_s=60)

    assert ctl.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ]
    )
    assert ctl.phase_value() == "countdown"

    t0 = time.monotonic()
    ctl._engine.state().countdown_deadline = t0 + 0.05
    assert ctl.tick_advance(now=t0 + 0.1) is True
    assert ctl.phase_value() == "active"

    ctl._publish_patch_sync()
    last = None
    while not q.empty():
        last = q.get_nowait()
    assert last is not None and last["phase"] == "active"


def test_manual_start_stop_reset() -> None:
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:battle_royale:main")
    ctl = _controller("main", ps)

    assert ctl.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ]
    )
    assert ctl.phase_value() == "countdown"

    ctl.stop_battle()
    assert ctl.phase_value() == "idle"

    ctl.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ]
    )
    ctl.reset_for_new_stream()
    assert ctl.phase_value() == "idle"

    # reset publishes an idle snapshot synchronously (drain any patches).
    phases = set()
    while not q.empty():
        phases.add(q.get_nowait()["phase"])
    assert "idle" in phases


def test_battle_ended_callback_receives_instance() -> None:
    ps = OverlayPubSub()
    seen: list[tuple[str, object]] = []
    ctl = BattleRoyaleInstanceController(
        pubsub=ps,
        get_locale=lambda: "uk",
        instance="x1",
        config_loader=lambda: _cfg(countdown_s=0, round_duration_s=60),
        on_battle_ended=lambda winner, iid: seen.append((iid, winner)),
    )
    ctl.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ]
    )
    st = ctl._engine.state()
    st.phase = st.phase.__class__.ACTIVE
    st.fighters[1].hp = 1
    ctl._engine._end_battle(st.fighters[0], ctl.config())

    assert len(seen) == 1
    assert seen[0][0] == "x1"
    assert getattr(seen[0][1], "user_key", None) == "a"
