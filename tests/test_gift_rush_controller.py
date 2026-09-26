"""Tests for the ``gift_rush`` per-instance controller.

Covers gift normalization, the global combo window, intensity tiering,
aggregation of rapid low-value gifts, the bounded event list, reduced-mode
flag round-trip, stream reset, and the debounced publish path.
"""

from __future__ import annotations

import asyncio
from collections import Counter
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


# ---------------------------------------------------------------------------
# App-side SFX (played from the app process via the AudioSink, not the page).
# ---------------------------------------------------------------------------


class _SfxSink:
    """Fake ``AudioSink`` recording every parallel-play (data, linear) pair.

    Mirrors ``QtAudioSink.play_mp3_parallel_with_volume``. The recorded
    ``data`` is a deterministic stub (see ``_sfx_bytes`` below) so clip
    payloads never depend on the real ``assets/sounds/*.mp3`` files."""

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, float]] = []

    async def play_mp3_parallel_with_volume(self, data: bytes, linear: float) -> None:
        self.calls.append((data, linear))


def make_sfx_ctl(**overrides: Any):
    """Controller wired for SFX tests.

    A recording sink is installed and ``self._loop`` is a real (unstarted)
    ``asyncio`` loop so the launch clip and the ``call_later`` burst both
    run. ``_sfx_bytes`` is stubbed to deterministic per-name payloads."""
    ctl, pubsub = make_controller(cfg=_make_cfg(**overrides))
    sink = _SfxSink()
    ctl._audio_sink = sink
    ctl._loop = asyncio.new_event_loop()
    ctl._sfx_bytes = lambda name: f"MP3:{name}".encode()
    return ctl, pubsub, sink


def _fire(ctl: GiftRushController, now: float, **gift_kw: Any) -> None:
    """Dispatch one gift at wall-clock ``now`` (controller ``time`` patched)."""
    params: dict[str, Any] = {
        "sender": "A",
        "gift_id": "g",
        "sender_user_key": "uk1",
        "count": 1,
        "tiktok_coin_each": 1,
        "gift_name": "x",
    }
    params.update(gift_kw)
    with mock.patch(_TIME, return_value=now):
        ctl.on_gift(**params)


def _advance(ctl: GiftRushController, seconds: float) -> None:
    """Run the controller loop until ``seconds`` of loop time elapse, so any
    ``loop.call_later`` burst fires. (Real-time cost ~= ``seconds``.)"""

    async def _wait() -> None:
        await asyncio.sleep(seconds)

    ctl._loop.run_until_complete(_wait())


def _names(sink: _SfxSink) -> list[str]:
    return [d.decode() for d, _ in sink.calls]


def _assert_calls(sink: _SfxSink, expected: list[tuple[str, float]]) -> None:
    # Multiset comparison: the burst clips fire as concurrent tasks, so their
    # completion order is not deterministic. Compare (name, volume) as a set.
    got = Counter((d.decode(), round(ln, 6)) for d, ln in sink.calls)
    exp = Counter((n, round(ln, 6)) for n, ln in expected)
    assert got == exp, f"got={dict(got)} expected={dict(exp)}"


def _close(ctl: GiftRushController) -> None:
    try:
        ctl._loop.close()
    except Exception:  # noqa: BLE001
        pass


def test_sfx_silent_when_sound_disabled() -> None:
    """Default config has sound off -> no clip played."""
    ctl, _pub, sink = make_sfx_ctl()  # sound_enabled defaults to False
    _fire(ctl, 1000.0, tiktok_coin_each=25)
    _advance(ctl, 1.0)
    assert sink.calls == []
    _close(ctl)


def test_sfx_silent_when_animations_off() -> None:
    """event_animations=False gates out the whole gift flow, sounds included."""
    ctl, _pub, sink = make_sfx_ctl(sound_enabled=True, event_animations=False)
    _fire(ctl, 1000.0, tiktok_coin_each=25)
    _advance(ctl, 1.0)
    assert sink.calls == []
    _close(ctl)


def test_sfx_does_not_raise_without_audio_sink() -> None:
    """Sound on but no sink wired -> early return, never crashes."""
    ctl, _pub = make_controller(cfg=_make_cfg(sound_enabled=True))
    ctl._loop = asyncio.new_event_loop()
    ctl._sfx_bytes = lambda name: b"x"  # noqa: E731
    _fire(ctl, 1000.0, tiktok_coin_each=25)
    _advance(ctl, 1.0)
    ctl._loop.close()


def test_sfx_plays_launch_and_full_burst() -> None:
    """MEDIUM gift (combo=1, all gates on): launch whoosh first, then the
    impact/coins/ding/sparks burst, in order and at configured gains."""
    ctl, _pub, sink = make_sfx_ctl(sound_enabled=True)
    _fire(ctl, 1000.0, tiktok_coin_each=25)  # MEDIUM, combo=1
    _advance(ctl, 1.0)
    _assert_calls(
        sink,
        [
            ("MP3:sfx_gift_launch", 0.8),
            ("MP3:sfx_impact_mid", 1.0),
            ("MP3:sfx_coins", 0.7),
            ("MP3:sfx_score_ding", 0.6),
            ("MP3:sfx_spark_tink", 0.4),
        ],
    )
    _close(ctl)


def test_sfx_impact_matches_intensity_tier() -> None:
    """The burst impact clip follows the tier mapping (LOW / MID / EPIC)."""
    for value, want in [
        (5, "sfx_impact_low"),
        (25, "sfx_impact_mid"),
        (150, "sfx_impact_mid"),
        (250, "sfx_impact_epic"),
    ]:
        ctl, _pub, sink = make_sfx_ctl(sound_enabled=True)
        _fire(ctl, 1000.0, tiktok_coin_each=value)
        _advance(ctl, 1.0)
        assert f"MP3:{want}" in _names(sink)
        _close(ctl)


def test_sfx_respects_effect_gates() -> None:
    """coins / ding / sparks are individually gated by their config flags."""
    ctl, _pub, sink = make_sfx_ctl(
        sound_enabled=True,
        effects_coins=False,
        effects_sparks=False,
    )
    _fire(ctl, 1000.0, tiktok_coin_each=25)
    _advance(ctl, 1.0)
    names = _names(sink)
    assert "MP3:sfx_coins" not in names
    assert "MP3:sfx_spark_tink" not in names
    assert "MP3:sfx_impact_mid" in names
    assert "MP3:sfx_score_ding" in names
    assert "MP3:sfx_gift_launch" in names
    _close(ctl)


def test_sfx_reduced_halves_gain_and_shortens_flight() -> None:
    """reduced_effects: half gain and the burst lands before the full flight.

    Full MEDIUM flight = 650 ms, reduced = int(650 * 0.7) = 455 ms. At 600
    ms the full-mode burst is still pending while the reduced-mode burst has
    already fired."""
    # full mode, 600 ms in -> only the launch, burst pending
    ctl_full, _pub, sink_full = make_sfx_ctl(sound_enabled=True)
    _fire(ctl_full, 1000.0, tiktok_coin_each=25)
    _advance(ctl_full, 0.60)
    assert len(sink_full.calls) == 1
    assert sink_full.calls[0][0].decode() == "MP3:sfx_gift_launch"
    _close(ctl_full)

    # reduced mode, 600 ms in -> full burst fired, at half gain
    ctl_red, _pub2, sink_red = make_sfx_ctl(sound_enabled=True, reduced_effects=True)
    _fire(ctl_red, 1000.0, tiktok_coin_each=25)
    _advance(ctl_red, 0.60)
    _assert_calls(
        sink_red,
        [
            ("MP3:sfx_gift_launch", 0.4),
            ("MP3:sfx_impact_mid", 0.5),
            ("MP3:sfx_coins", 0.35),
            ("MP3:sfx_score_ding", 0.3),
            ("MP3:sfx_spark_tink", 0.2),
        ],
    )
    _close(ctl_red)


def test_sfx_combo_tick_fires_for_combo_gates_on() -> None:
    """A second gift (combo=2) adds the combo tick; the first (combo=1) does
    not. Distinct gift_ids keep both gifts from aggregating."""
    ctl, _pub, sink = make_sfx_ctl(sound_enabled=True)
    _fire(ctl, 1000.0, tiktok_coin_each=1, gift_id="g1", sender_user_key="uk1")
    _fire(
        ctl,
        1000.1,
        tiktok_coin_each=1,
        gift_id="g2",
        sender_user_key="uk2",
    )
    _advance(ctl, 1.0)
    names = _names(sink)
    assert "MP3:sfx_combo_tick" in names
    assert names.count("MP3:sfx_combo_tick") == 1
    _close(ctl)


def test_sfx_no_combo_tick_when_gates_off() -> None:
    """combo tick needs show_combo AND combo_enabled; either off kills it."""
    for off in [dict(show_combo=False), dict(combo_enabled=False)]:
        ctl, _pub, sink = make_sfx_ctl(sound_enabled=True, **off)
        _fire(
            ctl,
            1000.0,
            tiktok_coin_each=1,
            gift_id="g1",
            sender_user_key="uk1",
        )
        _fire(
            ctl,
            1000.1,
            tiktok_coin_each=1,
            gift_id="g2",
            sender_user_key="uk2",
        )
        _advance(ctl, 1.0)
        assert "MP3:sfx_combo_tick" not in _names(sink)
        _close(ctl)
