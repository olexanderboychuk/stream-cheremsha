"""Tests for ``stream_cheremsha.overlays.battle_controller``.

The controller is a thin GUI adapter over ``BattleEngine`` + ``OverlayPubSub``.
These tests pin down the pubsub routing contract that per-instance
``overlay:battle:{instance}`` OBS sources depend on:

* each instance publishes only to its own topic (no cross-instance leakage),
* the sync publish path (``_publish_patch_sync``) lands in subscriber queues
  immediately and is callable without a running event loop
  (GUI-thread safe; OBS sources must not wait on a deferred publish),
* ``reset_for_new_stream`` resets the engine and pushes an idle snapshot.

All tests use in-memory ``BattleOverlayConfig`` objects via ``config_loader``;
no QSettings or disk state is involved.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from stream_cheremsha.overlays.battle_controller import BattleController
from stream_cheremsha.overlays.battle_overlay_config import (
    BattleOverlayConfig,
    battle_overlay_config_defaults,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _cfg(**overrides) -> BattleOverlayConfig:
    return battle_overlay_config_defaults().replace(**overrides)


def _controller(instance: str, ps: OverlayPubSub, **overrides) -> BattleController:
    return BattleController(
        pubsub=ps,
        get_locale=lambda: "uk",
        instance=instance,
        config_loader=lambda: _cfg(**overrides),  # type: ignore[assignment]
    )


def test_instance_topics_are_isolated() -> None:
    """A gift on instance ``a`` must never leak to instance ``b``'s topic."""
    ps = OverlayPubSub()
    q_a = ps.subscribe("overlay:battle:a")
    q_b = ps.subscribe("overlay:battle:b")

    ctl_a = _controller("a", ps, auto_start=True, auto_threshold_each=1)
    ctl_b = _controller("b", ps, auto_start=True, auto_threshold_each=1)

    # Two qualifying gifts auto-arm the battle on "a" only.
    ctl_a.on_gift(sender="U1", count=10, sender_user_key="u1", sender_avatar_url="")
    ctl_a.on_gift(sender="U2", count=20, sender_user_key="u2", sender_avatar_url="")
    ctl_a._publish_patch_sync()

    assert q_a.qsize() == 1
    assert q_b.qsize() == 0  # no leakage to another instance's topic

    # Reverse direction: arming "b" must not touch "a"'s topic either.
    ctl_b.on_gift(sender="U3", count=10, sender_user_key="u3", sender_avatar_url="")
    ctl_b.on_gift(sender="U4", count=20, sender_user_key="u4", sender_avatar_url="")
    ctl_b._publish_patch_sync()

    assert q_a.qsize() == 1  # still only "a"'s own patch
    assert q_b.qsize() == 1  # and now only "b"'s own patch
    patch_a = q_a.get_nowait()
    b_patch = q_b.get_nowait()
    assert patch_a["status"] == "countdown"
    assert len(patch_a["participants"]) == 2
    assert b_patch["status"] == "countdown"
    assert len(b_patch["participants"]) == 2


def test_exact_topic_delivery_sync_no_loop() -> None:
    """publish_sync lands on the exact instance topic immediately, with no event loop."""
    instance = "battle-42"
    ps = OverlayPubSub()
    q_exact = ps.subscribe(f"overlay:battle:{instance}")
    q_wrong = ps.subscribe(f"overlay:battle:{instance}-other")

    ctl = _controller(instance, ps, auto_start=True, auto_threshold_each=1)

    ctl.on_gift(sender="U1", count=5, sender_user_key="u1", sender_avatar_url="")
    ctl.on_gift(sender="U2", count=9, sender_user_key="u2", sender_avatar_url="")
    ctl._publish_patch_sync()

    patch = q_exact.get_nowait()
    assert patch["status"] == "countdown"
    assert patch["locale"] == "uk"
    assert patch["config"]["best_of"] == 3
    assert len(patch["participants"]) == 2
    assert {p["team_id"] for p in patch["participants"]} == {"left", "right"}

    with pytest.raises(asyncio.QueueEmpty):
        q_wrong.get_nowait()


def test_reset_for_new_stream_publishes_idle_snapshot() -> None:
    """Resetting a running battle pushes a fresh idle snapshot to the instance topic."""
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:battle:reset")

    ctl = _controller("reset", ps, auto_start=True, auto_threshold_each=1)

    ctl.on_gift(sender="U1", count=5, sender_user_key="u1", sender_avatar_url="")
    ctl.on_gift(sender="U2", count=9, sender_user_key="u2", sender_avatar_url="")

    state = ctl.initial_state()
    assert state["status"] == "countdown"
    assert len(state["participants"]) == 2

    ctl.reset_for_new_stream()

    patch = q.get_nowait()
    assert q.qsize() == 0
    assert patch["status"] == "idle"
    assert patch["participants"] == []
    assert patch["winner"] is None
    assert patch["best_of"] == 3
    assert patch["round"] == 1
    assert patch["round_wins"] == {"left": 0, "right": 0}


@pytest.mark.asyncio
async def test_burst_of_rapid_gifts_is_debounced() -> None:
    """A burst of 50 rapid gifts to an active battle must coalesce into a
    small number of published patches (debounce proof) and the engine's
    event ring buffer must stay bounded (<= 10).

    The 50 gifts are fired synchronously (no event-loop turns between them),
    so only the controller's ``call_later`` debounce can emit patches. A
    working debounce coalesces them to one pending publish; a broken one
    would flood the topic with a publish per gift.
    """
    ps = OverlayPubSub()
    q = ps.subscribe("overlay:battle:burst")
    loop = asyncio.get_running_loop()

    ctl = _controller(
        "burst",
        ps,
        auto_start=True,
        auto_threshold_each=1,
        decision_layer_enabled=False,
    )
    ctl.set_event_loop(loop)
    ctl.set_pubsub(ps)

    # Arm the battle (two qualifying gifts -> COUNTDOWN), then advance the
    # injected clock past the countdown so the engine becomes ACTIVE.
    ctl.on_gift(sender="L", count=10, sender_user_key="l", sender_avatar_url="")
    ctl.on_gift(sender="R", count=20, sender_user_key="r", sender_avatar_url="")
    assert ctl.initial_state()["status"] == "countdown"
    ctl.tick_advance(now=time.monotonic() + 10.0)
    assert ctl.initial_state()["status"] == "active"

    # Flush any patch queued by the arming/tick setup so that only the burst's
    # own output is measured below.
    while q.qsize():
        q.get_nowait()

    # Burst: 50 rapid gifts alternating between the two locked participants.
    for i in range(50):
        key = "l" if i % 2 == 0 else "r"
        ctl.on_gift(
            sender=f"{key.upper()}_{i}",
            count=5,
            sender_user_key=key,
            sender_avatar_url="",
        )

    # Any immediate patch emitted during the synchronous burst (round/battle
    # finish) — expected to be 0 since the round timer does not elapse here.
    immediate = 0
    while q.qsize():
        immediate += 1
        q.get_nowait()

    # Let the coalesced debounced publish fire.
    await asyncio.sleep(0.35)

    debounced = 0
    while q.qsize():
        debounced += 1
        q.get_nowait()

    total = immediate + debounced
    assert 1 <= total <= 6, f"burst published {total} patches (budget 6)"
    # The engine event ring is capped at 10 entries regardless of burst size.
    assert len(ctl.initial_state()["events"]) <= 10
