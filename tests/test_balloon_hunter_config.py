"""Tests for the ``balloon_hunter`` overlay config schema.

Mirrors ``test_gift_rush_config.py``: defaults, JSON round-trip, clamping,
invalid-JSON fallback, and epic/gold threshold ordering.
"""

from __future__ import annotations

from stream_cheremsha.overlays.balloon_hunter_config import (
    BALLOON_HUNTER_CONFIG_SCHEMA_VERSION,
    balloon_hunter_overlay_config_defaults,
    balloon_hunter_overlay_config_from_json_text,
    balloon_hunter_overlay_config_to_json_text,
)


def test_defaults() -> None:
    cfg = balloon_hunter_overlay_config_defaults()
    assert cfg.schema_version == BALLOON_HUNTER_CONFIG_SCHEMA_VERSION
    assert cfg.balloon_count == 8
    assert cfg.spawn_interval_ms == 1500
    assert cfg.float_speed_percent == 100
    assert cfg.gold_min_coins == 50
    assert cfg.epic_min_coins == 200
    assert cfg.combo_enabled is True
    assert cfg.combo_window_s == 10
    assert cfg.show_sender is True
    assert cfg.show_gift_icon is True
    assert cfg.event_animations is True
    assert cfg.effect_duration_ms == 800
    assert cfg.max_particles == 200
    assert cfg.max_simultaneous_events == 10
    assert cfg.reduced_effects is False
    # SFX are opt-in: default must be silent.
    assert cfg.sound_enabled is False


def test_json_round_trip() -> None:
    cfg = balloon_hunter_overlay_config_defaults()
    cfg = balloon_hunter_overlay_config_from_json_text(
        balloon_hunter_overlay_config_to_json_text(cfg)
    )
    assert balloon_hunter_overlay_config_to_json_text(
        cfg
    ) == balloon_hunter_overlay_config_to_json_text(balloon_hunter_overlay_config_defaults())


def test_clamping() -> None:
    cfg = balloon_hunter_overlay_config_from_json_text(
        '{"balloon_count": 99, "spawn_interval_ms": 1, "max_particles": 9999,'
        ' "combo_window_s": 99, "effect_duration_ms": 1, "float_speed_percent": 1}'
    )
    assert cfg.balloon_count == 20
    assert cfg.spawn_interval_ms == 500
    assert cfg.max_particles == 500
    assert cfg.combo_window_s == 30
    assert cfg.effect_duration_ms == 300
    assert cfg.float_speed_percent == 40


def test_epic_always_above_gold() -> None:
    cfg = balloon_hunter_overlay_config_from_json_text(
        '{"gold_min_coins": 500, "epic_min_coins": 100}'
    )
    assert cfg.epic_min_coins > cfg.gold_min_coins


def test_invalid_json_falls_back_to_defaults() -> None:
    cfg = balloon_hunter_overlay_config_from_json_text("not-json{{{")
    assert cfg == balloon_hunter_overlay_config_defaults()
    cfg = balloon_hunter_overlay_config_from_json_text("")
    assert cfg == balloon_hunter_overlay_config_defaults()
