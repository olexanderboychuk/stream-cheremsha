"""End-to-end proof that a Battle actually runs: arm -> countdown -> active ->
round switches -> battle finishes -> auto-reset, with every transition
published to ``overlay:battle:{instance}``.

Regression context: the shared 1s ``_battle_tick_timer`` used to be
lifecycle-managed by the legacy ``battle_royale`` singleton only, so on a
fresh boot it never fired and ``BattleController.tick_advance()`` never ran.
The visible symptom was an overlay stuck on ROUND 1 forever: gifts armed the
battle (COUNTDOWN shows round 1) but engine time never advanced. The timer is
now always-on; this test pins the full published lifecycle with an injected
clock (no Qt, no sleeping, no QSettings).
"""

from __future__ import annotations

import time
from pathlib import Path

from stream_cheremsha.overlays.battle_controller import BattleController
from stream_cheremsha.overlays.battle_overlay_config import (
    battle_overlay_config_defaults,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _controller(instance: str, ps: OverlayPubSub, **overrides) -> BattleController:
    cfg = battle_overlay_config_defaults().replace(**overrides)
    return BattleController(
        pubsub=ps,
        get_locale=lambda: "uk",
        instance=instance,
        config_loader=lambda: cfg,
    )


def _last(q):  # drain to the most recent patch
    patch = None
    while q.qsize():
        patch = q.get_nowait()
    assert patch is not None
    return patch


def test_full_lifecycle_rounds_switch_and_publish() -> None:
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:battle:lifecycle")
    ctl = _controller(
        "lifecycle",
        ps,
        auto_start=True,
        auto_threshold_each=1,
        best_of=3,
        countdown_s=5,
        round_duration_s=60,
        victory_display_s=8,
        auto_reset=True,
    )

    t = time.monotonic()  # engine anchors deadlines to the real clock on gifts
    # --- arm: two distinct gifters -> COUNTDOWN round 1 ---
    # (U1 out-gifts U2, so U1 locks the LEFT slot.)
    ctl.on_gift(sender="U1", count=20, sender_user_key="u1", sender_avatar_url="")
    ctl.on_gift(sender="U2", count=9, sender_user_key="u2", sender_avatar_url="")
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["status"] == "countdown"
    assert patch["round"] == 1

    # --- countdown elapses -> ACTIVE round 1 ---
    t += 5.1
    assert ctl.tick_advance(now=t) is True
    ctl._publish_patch_sync()
    assert _last(q)["status"] == "active"

    # --- slot-owner gift scores ---
    ctl.on_gift(sender="U1", count=50, sender_user_key="u1", sender_avatar_url="")
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["teams"][0]["score"] == 50

    # --- round 1 ends: U1 wins -> COUNTDOWN round 2 (the reported bug) ---
    t += 60.1
    assert ctl.tick_advance(now=t) is True
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["status"] == "countdown"
    assert patch["round"] == 2, f"round did not switch: {patch['round']}"
    assert patch["round_wins"] == {"left": 1, "right": 0}

    # --- round 2: U2 wins -> COUNTDOWN round 3 ---
    t += 5.1
    ctl.tick_advance(now=t)
    ctl.on_gift(sender="U2", count=70, sender_user_key="u2", sender_avatar_url="")
    t += 60.1
    ctl.tick_advance(now=t)
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["round"] == 3
    assert patch["round_wins"] == {"left": 1, "right": 1}

    # --- round 3: U1 wins -> FINISHED, overall winner left (2-1) ---
    t += 5.1
    ctl.tick_advance(now=t)
    ctl.on_gift(sender="U1", count=30, sender_user_key="u1", sender_avatar_url="")
    t += 60.1
    ctl.tick_advance(now=t)
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["status"] == "finished"
    assert patch["winner"] is not None
    assert patch["winner"]["team_id"] == "left"

    # --- victory display elapses -> auto-reset to IDLE ---
    t += 8.1
    ctl.tick_advance(now=t)
    ctl._publish_patch_sync()
    patch = _last(q)
    assert patch["status"] == "idle"
    assert patch["round"] == 1
    assert patch["round_wins"] == {"left": 0, "right": 0}


def test_shared_battle_tick_is_always_on() -> None:
    """Guard the root cause: ``_battle_tick_timer`` must be started at boot
    and never stopped (it drives both battle_royale and Battle groups)."""
    src = (
        Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "ui" / "main_window.py"
    ).read_text(encoding="utf-8")
    assert "_battle_tick_timer.stop()" not in src
    assert src.count("_battle_tick_timer.start()") >= 1
