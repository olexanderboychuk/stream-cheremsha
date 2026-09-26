"""Tests for the ``gift_rush`` overlay config schema.

Mirrors the structural tests used for ``battle_overlay_config``: defaults,
JSON round-trip, clamping, invalid-JSON fallback, and theme normalization.
"""

from __future__ import annotations

from stream_cheremsha.overlays.gift_rush_config import (
    GIFT_OVERLAY_CONFIG_SCHEMA_VERSION,
    gift_rush_overlay_config_defaults,
    gift_rush_overlay_config_from_json_text,
    gift_rush_overlay_config_to_json_text,
    load_gift_rush_overlay_config,
)


def test_defaults() -> None:
    cfg = gift_rush_overlay_config_defaults()
    assert cfg.schema_version == GIFT_OVERLAY_CONFIG_SCHEMA_VERSION
    assert cfg.theme == "cheremsha"
    assert cfg.target_mode == "center"
    assert cfg.scale_percent == 100
    assert cfg.intensity_percent == 100
    assert cfg.event_animations is True
    assert cfg.show_gift_image is True
    assert cfg.show_value is True
    assert cfg.show_sender is True
    assert cfg.show_combo is True
    assert cfg.show_intensity_badge is True
    assert cfg.effects_coins is True
    assert cfg.effects_sparks is True
    assert cfg.effects_impact_ring is True
    assert cfg.camera_impact is True
    assert cfg.combo_enabled is True
    assert cfg.combo_window_s == 10
    assert cfg.combo_escalation is True
    assert cfg.max_simultaneous_events == 10
    assert cfg.reduced_effects is False
    # SFX are opt-in: default must be silent.
    assert cfg.sound_enabled is False


def test_json_round_trip() -> None:
    cfg = gift_rush_overlay_config_defaults()
    cfg = gift_rush_overlay_config_from_json_text(gift_rush_overlay_config_to_json_text(cfg))
    assert gift_rush_overlay_config_to_json_text(cfg) == gift_rush_overlay_config_to_json_text(
        gift_rush_overlay_config_defaults()
    )


def test_custom_values_round_trip() -> None:
    cfg = gift_rush_overlay_config_defaults()
    src = gift_rush_overlay_config_to_json_text(cfg)
    cfg = gift_rush_overlay_config_from_json_text(src)
    assert cfg.theme == "cheremsha"
    assert cfg.target_mode == "center"
    assert cfg.scale_percent == 100
    assert cfg.intensity_percent == 100
    assert cfg.combo_window_s == 10
    assert cfg.max_simultaneous_events == 10
    assert cfg.reduced_effects is False
    assert cfg.show_sender is True


def test_clamping() -> None:
    raw = {
        "theme": "arcade",
        "target_mode": "left",
        "scale_percent": 999,
        "intensity_percent": 999,
        "combo_window_s": 999,
        "max_simultaneous_events": 999,
        "reduced_effects": True,
        "event_animations": False,
        "sound_enabled": "yes",
    }
    cfg = gift_rush_overlay_config_from_json_text(__import__("json").dumps(raw))
    # scale_percent clamps to [40, 250]
    assert cfg.scale_percent == 250
    # intensity_percent clamps to [25, 200]
    assert cfg.intensity_percent == 200
    # combo_window_s clamps to [3, 30]
    assert cfg.combo_window_s == 30
    # max_simultaneous_events clamps to [4, 12]
    assert cfg.max_simultaneous_events == 12
    assert cfg.theme == "arcade"
    assert cfg.target_mode == "left"
    assert cfg.reduced_effects is True
    assert cfg.event_animations is False
    # truthy junk clamps to a plain bool, like the other toggles
    assert cfg.sound_enabled is True


def test_clamping_low_bound() -> None:
    raw = {
        "scale_percent": 0,
        "intensity_percent": 0,
        "combo_window_s": 0,
        "max_simultaneous_events": 0,
    }
    cfg = gift_rush_overlay_config_from_json_text(__import__("json").dumps(raw))
    assert cfg.scale_percent == 40
    assert cfg.intensity_percent == 25
    assert cfg.combo_window_s == 3
    assert cfg.max_simultaneous_events == 4


def test_invalid_json_falls_back_to_defaults() -> None:
    cfg = gift_rush_overlay_config_from_json_text("not valid json {")
    assert cfg == gift_rush_overlay_config_defaults()


def test_empty_string_falls_back_to_defaults() -> None:
    cfg = gift_rush_overlay_config_from_json_text("")
    assert cfg == gift_rush_overlay_config_defaults()


def test_unknown_theme_normalized() -> None:
    raw = {"theme": "NO_SUCH_THEME", "target_mode": "UPPER"}
    cfg = gift_rush_overlay_config_from_json_text(__import__("json").dumps(raw))
    assert cfg.theme == "cheremsha"
    assert cfg.target_mode == "center"


def test_unknown_target_mode_normalized() -> None:
    raw = {"target_mode": "nope"}
    cfg = gift_rush_overlay_config_from_json_text(__import__("json").dumps(raw))
    assert cfg.target_mode == "center"


def test_missing_fields_fill_defaults() -> None:
    cfg = gift_rush_overlay_config_from_json_text('{"theme": "celebration"}')
    assert cfg.theme == "celebration"
    assert cfg.scale_percent == 100
    assert cfg.intensity_percent == 100
    assert cfg.combo_window_s == 10
    assert cfg.max_simultaneous_events == 10
    assert cfg.sound_enabled is False


def test_load_default_settings() -> None:
    # A fresh QSettings-based load must return the clamped defaults.
    cfg = load_gift_rush_overlay_config()
    assert cfg == gift_rush_overlay_config_defaults()
