"""Tests for the ``gift_rush`` per-instance controller.

Covers gift normalization, the global combo window, intensity tiering,
aggregation of rapid low-value gifts, the bounded event list, reduced-mode
flag round-trip, stream reset, and the debounced publish path.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from unittest import mock

from stream_cheremsha.overlays.gift_rush_config import (
    GiftRushOverlayConfig,
    gift_rush_overlay_config_defaults,
    gift_rush_overlay_config_from_json_text,
    gift_rush_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.gift_rush_controller import GiftRushController

_TIME = "stream_cheremsha.overlays.gift_rush_controller.time.time"


class _PubSub:
    """Minimal pubsub stub recording every sync publish."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish_sync(self, topic: str, patch: dict) -> None:
        self.published.append((topic, patch))


def _make_cfg(**overrides: Any) -> GiftRushOverlayConfig:
    """Cloned defaults with targeted field overrides."""
    return replace(gift_rush_overlay_config_defaults(), **overrides)


def make_controller(cfg: Any = None):
    pubsub = _PubSub()
    ctl = GiftRushController(
        pubsub=pubsub,
        get_locale=lambda: "uk",
        instance="test",
        config_loader=lambda: cfg if cfg is not None else gift_rush_overlay_config_defaults(),
    )
    return ctl, pubsub


def _gift_at(ctl, now: float, **kw: Any) -> None:
    """Dispatch one gift at a deterministic wall-clock ``now``.

    ``kw`` may override any parameter; unprovided parameters take the helper
    defaults so callers can vary just ``sender_user_key`` etc.
    """
    params: dict[str, Any] = {
        "sender": "Alice",
        "gift_id": "g",
        "sender_user_key": "uk1",
        "count": 1,
        "tiktok_coin_each": 20,
        "gift_name": "Rose",
    }
    params.update(kw)
    with mock.patch(_TIME, return_value=now):
        ctl.on_gift(**params)


def test_on_gift_emits_event() -> None:
    ctl, _ = make_controller()
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_name="Rose",
            gift_id="g1",
            count=2,
            tiktok_coin_each=3,
            icon_url="https://x/g.png",
            sender_avatar_url="https://x/a.png",
            sender_user_key="uk1",
            platform="tiktok",
        )
    assert len(ctl._events) == 1
    e = ctl._events[0]
    assert e["type"] == "gift"
    p = e["payload"]
    assert p["sender"] == "Alice"
    assert p["gift_name"] == "Rose"
    assert p["gift_id"] == "g1"
    assert p["count"] == 2
    assert p["value"] == 6  # each * count = 3 * 2
    assert p["icon_url"] == "https://x/g.png"
    assert p["sender_avatar_url"] == "https://x/a.png"
    assert p["platform"] == "tiktok"
    assert p["combo"] == 1
    assert p["intensity"] == "LOW"
    assert p["target"] == "center"


def test_at_increases() -> None:
    ctl, _ = make_controller()
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="A1",
            gift_id="g",
            sender_user_key="uk1",
            count=1,
            tiktok_coin_each=20,
            gift_name="x",
        )
    with mock.patch(_TIME, return_value=1001.0):
        ctl.on_gift(
            sender="A2",
            gift_id="g",
            sender_user_key="uk1",
            count=1,
            tiktok_coin_each=20,
            gift_name="x",
        )
    a1 = ctl._events[0]["at"]
    a2 = ctl._events[1]["at"]
    assert a1 == 1000.0
    assert a2 == 1001.0
    assert a2 > a1


def test_intensity_tiers() -> None:
    # (value, combo, expected) — combo is realised by pre-seeding ``combo - 1``
    # identical-time, distinct-key gifts, then sending the target gift.
    for value, combo, want in [
        (5, 1, "LOW"),
        (6, 2, "LOW"),
        (25, 1, "MEDIUM"),
        (6, 3, "MEDIUM"),
        (25, 5, "HIGH"),
        (100, 2, "HIGH"),
        (100, 1, "HIGH"),
        (5, 5, "HIGH"),
        (5, 10, "EPIC"),
        (250, 1, "EPIC"),
    ]:
        ctl, _ = make_controller()
        with mock.patch(_TIME, return_value=1000.0):
            for i in range(combo - 1):
                ctl.on_gift(
                    sender=f"p{i}",
                    gift_id=f"g{i}",
                    sender_user_key=f"pk{i}",
                    count=1,
                    tiktok_coin_each=1,
                    gift_name="x",
                )
            ctl.on_gift(
                sender="x",
                gift_id="target",
                sender_user_key="target_pk",
                count=1,
                tiktok_coin_each=value,
                gift_name="x",
            )
        assert len(ctl._events) == combo
        p = ctl._events[-1]["payload"]
        assert p["intensity"] == want, f"value={value} -> {p['intensity']!r}, expected {want!r}"


def test_combo_window() -> None:
    ctl, _ = make_controller(cfg=_make_cfg(combo_window_s=10))
    _gift_at(ctl, 1000.0)
    assert ctl._events[0]["payload"]["combo"] == 1
    _gift_at(ctl, 1001.0)  # 1 s later, within 10 s window
    assert ctl._events[1]["payload"]["combo"] == 2
    _gift_at(ctl, 1030.0)  # 30 s after start -> older entries trimmed
    assert ctl._events[2]["payload"]["combo"] == 1


def test_aggregation() -> None:
    ctl, _ = make_controller()
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=5,
            tiktok_coin_each=1,
            gift_name="Rose",
        )
    assert len(ctl._events) == 1
    assert ctl._events[0]["payload"]["aggregated_count"] == 1
    assert ctl._events[0]["payload"]["intensity"] == "LOW"
    # second rapid LOW gift, same id+sender, within 2 s -> merges
    with mock.patch(_TIME, return_value=1000.5):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=5,
            tiktok_coin_each=1,
            gift_name="Rose",
        )
    assert len(ctl._events) == 1
    p = ctl._events[0]["payload"]
    assert p["aggregated_count"] == 2
    assert p["value"] == 10  # 5 + 5 accumulated
    assert p["sender"] == "Alice"
    assert p["gift_name"] == "Rose"


def test_aggregation_same_sender_different_gift_id_no_merge() -> None:
    ctl, _ = make_controller()
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=5,
            tiktok_coin_each=1,
            gift_name="Rose",
        )
    with mock.patch(_TIME, return_value=1000.5):
        ctl.on_gift(
            sender="Alice",
            gift_id="g2",
            sender_user_key="uk1",
            count=5,
            tiktok_coin_each=1,
            gift_name="Lily",
        )
    assert len(ctl._events) == 2  # different gift_id -> no merge


def test_aggregation_high_intensity_not_merged() -> None:
    ctl, _ = make_controller()
    # value=150 -> HIGH even at combo=1; HIGH gifts do not aggregate
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=1,
            tiktok_coin_each=150,
            gift_name="Rose",
        )
    with mock.patch(_TIME, return_value=1000.5):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=1,
            tiktok_coin_each=150,
            gift_name="Rose",
        )
    assert len(ctl._events) == 2


def test_event_cap() -> None:
    ctl, _ = make_controller()
    now = 1000.0
    for i in range(40):
        _gift_at(ctl, now + i * 0.1, sender_user_key=f"uk{i}")
    assert len(ctl._events) == 32
    assert len(ctl._events) <= 32


def test_reduced_effects_flag_roundtrip() -> None:
    cfg = _make_cfg(reduced_effects=True)
    src = gift_rush_overlay_config_to_json_text(cfg)
    assert '"reduced_effects":true' in src
    cfg2 = gift_rush_overlay_config_from_json_text(src)
    assert cfg2.reduced_effects is True
    assert gift_rush_overlay_config_defaults().reduced_effects is False


def test_event_animations_disabled_emits_nothing() -> None:
    ctl, pubsub = make_controller(cfg=_make_cfg(event_animations=False))
    with mock.patch(_TIME, return_value=1000.0):
        ctl.on_gift(
            sender="Alice",
            gift_id="g1",
            sender_user_key="uk1",
            count=1,
            tiktok_coin_each=20,
            gift_name="Rose",
        )
    assert len(ctl._events) == 0
    assert pubsub.published == []


def test_reset_clears_events_and_combo() -> None:
    ctl, pubsub = make_controller()
    _gift_at(ctl, 1000.0)
    assert len(ctl._events) == 1
    assert len(ctl._gift_timestamps) == 1
    ctl.reset_for_new_stream()
    assert len(ctl._events) == 0
    assert len(ctl._gift_timestamps) == 0
    assert pubsub.published
    topic, patch = pubsub.published[-1]
    assert topic == "overlay:gift_rush:test"
    assert patch["events"] == []


def test_publish_debounce() -> None:
    ctl, pubsub = make_controller()
    loop = asyncio.new_event_loop()
    ctl.set_event_loop(loop)

    def _gift_now() -> None:
        with mock.patch(_TIME, side_effect=lambda: loop.time()):
            ctl.on_gift(
                sender="A",
                gift_id="g",
                sender_user_key="uk",
                count=1,
                tiktok_coin_each=20,
                gift_name="x",
            )

    async def _run() -> None:
        for _ in range(5):
            _gift_now()
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.35)  # past the 200 ms debounce

    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()
    # 5 rapid gifts -> a single debounced publish
    assert len(pubsub.published) == 1
    topic, patch = pubsub.published[0]
    assert topic == "overlay:gift_rush:test"
    assert len(patch["events"]) == 5
