"""Tests for the ``balloon_hunter`` per-instance controller.

Covers gift normalization, value-based tiers (NORMAL / GOLD / EPIC),
combo escalation, the bounded pop-event list, stream reset, and publish.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest import mock

from stream_cheremsha.overlays.balloon_hunter_config import (
    balloon_hunter_overlay_config_defaults,
)
from stream_cheremsha.overlays.balloon_hunter_controller import BalloonHunterController

_TIME = "stream_cheremsha.overlays.balloon_hunter_controller.time.time"


class _PubSub:
    """Minimal pubsub stub recording every sync publish."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish_sync(self, topic: str, patch: dict) -> None:
        self.published.append((topic, patch))


def make_controller(cfg: Any = None):
    pubsub = _PubSub()
    ctl = BalloonHunterController(
        pubsub=pubsub,
        get_locale=lambda: "uk",
        instance="test",
        config_loader=lambda: cfg if cfg is not None else balloon_hunter_overlay_config_defaults(),
    )
    return ctl, pubsub


def _gift_at(ctl, now: float, **kw: Any) -> None:
    params: dict[str, Any] = {
        "sender": "Alice",
        "gift_id": "g",
        "sender_user_key": "uk1",
        "count": 1,
        "tiktok_coin_each": 1,
        "gift_name": "Rose",
    }
    params.update(kw)
    with mock.patch(_TIME, return_value=now):
        ctl.on_gift(**params)


def test_on_gift_emits_pop_event() -> None:
    ctl, _ = make_controller()
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_name="Rose",
            gift_id="g1",
            count=1,
            tiktok_coin_each=5,
            sender_user_key="uk1",
        )
    assert len(ctl._events) == 1
    ev = ctl._events[0]
    assert ev["type"] == "pop"
    assert ev["payload"]["intensity"] == "NORMAL"
    assert ev["payload"]["target_balloon_kind"] == "NORMAL"
    assert ev["payload"]["value"] == 5


def test_value_tiers_gold_and_epic() -> None:
    ctl, _ = make_controller()
    _gift_at(ctl, 1000.0, tiktok_coin_each=60, gift_id="gold")
    assert ctl._events[-1]["payload"]["intensity"] == "GOLD"
    _gift_at(ctl, 1100.0, tiktok_coin_each=300, gift_id="epic")
    assert ctl._events[-1]["payload"]["intensity"] == "EPIC"


def test_combo_escalates_tier() -> None:
    ctl, _ = make_controller()
    for i in range(5):
        _gift_at(ctl, 1000.0 + i, tiktok_coin_each=1, gift_id=f"g{i}")
    assert ctl._events[-1]["payload"]["combo"] == 5
    assert ctl._events[-1]["payload"]["intensity"] == "GOLD"


def test_combo_disabled_ignores_streak() -> None:
    cfg = replace(balloon_hunter_overlay_config_defaults(), combo_enabled=False)
    ctl, _ = make_controller(cfg)
    for i in range(12):
        _gift_at(ctl, 1000.0 + i, tiktok_coin_each=1, gift_id=f"g{i}")
    assert ctl._events[-1]["payload"]["intensity"] == "NORMAL"


def test_events_bounded() -> None:
    ctl, _ = make_controller()
    for i in range(50):
        _gift_at(ctl, 1000.0 + i * 100, tiktok_coin_each=1, gift_id=f"g{i}")
    assert len(ctl._events) == 32


def test_reset_for_new_stream() -> None:
    ctl, pubsub = make_controller()
    _gift_at(ctl, 1000.0)
    assert ctl._events
    ctl.reset_for_new_stream()
    assert ctl._events == []
    assert ctl._gift_timestamps == []
    assert pubsub.published  # idle state published


def test_initial_state_shape() -> None:
    ctl, _ = make_controller()
    state = ctl.initial_state()
    assert set(state) == {"config", "locale", "events"}
    assert state["locale"] == "uk"
    assert state["config"]["balloon_count"] == 8


def test_publish_topic() -> None:
    ctl, pubsub = make_controller()
    ctl._publish_patch_sync()
    assert pubsub.published
    topic, _ = pubsub.published[-1]
    assert topic == "overlay:balloon_hunter:test"


def test_animations_off_emits_nothing() -> None:
    cfg = replace(balloon_hunter_overlay_config_defaults(), event_animations=False)
    ctl, _ = make_controller(cfg)
    _gift_at(ctl, 1000.0)
    assert ctl._events == []


def test_pop_sfx_names_per_tier() -> None:
    from stream_cheremsha.overlays.balloon_hunter_controller import pop_sfx_names

    assert pop_sfx_names("NORMAL") == ("sfx_balloon_pop", "sfx_impact_low")
    assert pop_sfx_names("GOLD") == ("sfx_balloon_pop_gold", "sfx_impact_low")
    assert pop_sfx_names("EPIC") == ("sfx_balloon_pop_epic", "sfx_impact_epic")
    # Unknown/empty intensity degrades to the NORMAL pair, never raises.
    assert pop_sfx_names("") == ("sfx_balloon_pop", "sfx_impact_low")
    assert pop_sfx_names("bogus") == ("sfx_balloon_pop", "sfx_impact_low")


def test_pop_sfx_fallback_files_exist() -> None:
    """Legacy impacts must exist so pops stay audible before dedicated files land."""
    from stream_cheremsha.overlays.balloon_hunter_controller import pop_sfx_names

    ctl, _ = make_controller()
    for intensity in ("NORMAL", "GOLD", "EPIC"):
        _, fallback = pop_sfx_names(intensity)
        assert ctl._sfx_bytes(fallback)
