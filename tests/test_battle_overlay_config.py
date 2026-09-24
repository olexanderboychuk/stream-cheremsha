"""Tests for ``stream_cheremsha.overlays.battle_overlay_config``.

Note on QSettings: tests must never touch the production QSettings scope
(`"stream-cheremsha"` / `"cheremsha"`). All tests below pass an isolated
``QSettings("stream-cheremsha-test", ...)``.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.battle_overlay_config import (
    battle_overlay_config_defaults,
    battle_overlay_config_from_json_text,
    battle_overlay_config_to_json_text,
    load_battle_overlay_config,
    save_battle_overlay_config,
)

SETTINGS_KEY = "overlays/battle/main/config_json"
BACKUP_KEY = "overlays/battle/main/config_json_backup"


def _test_settings() -> QSettings:
    s = QSettings("stream-cheremsha-test", "battle-overlay-config")
    # Isolated org/app: clearing is safe (conftest guard allows it) and makes
    # tests order-independent across repeated runs, since QSettings INI files
    # persist on disk between runs.
    s.clear()
    return s


def test_defaults_round_trip() -> None:
    cfg = battle_overlay_config_defaults()
    txt = battle_overlay_config_to_json_text(cfg)
    cfg2 = battle_overlay_config_from_json_text(txt)
    assert cfg2 == cfg
    assert cfg2.battle_name == "BATTLE"
    assert cfg2.best_of == 3
    assert cfg2.round_duration_s == 60
    assert cfg2.theme == "cheremsha_neon"
    assert cfg2.auto_start is True
    assert cfg2.combo_enabled is True
    assert cfg2.hide_when_idle is False


def test_partial_json_merges_with_defaults() -> None:
    # A partial object must be accepted and filled with defaults.
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "best_of": 1}')
    assert cfg.best_of == 1
    # All other fields fall back to defaults.
    assert cfg.round_duration_s == battle_overlay_config_defaults().round_duration_s
    assert cfg.theme == "cheremsha_neon"
    assert cfg.auto_start is True


def test_round_duration_s_clamped_to_30() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "round_duration_s": -5}')
    assert cfg.round_duration_s == 30


def test_round_duration_s_clamped_to_300() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "round_duration_s": 99999}')
    assert cfg.round_duration_s == 300


def test_gift_multiplier_clamped_to_max() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "gift_multiplier": 99}')
    assert cfg.gift_multiplier == 10.0


def test_gift_multiplier_clamped_to_min() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "gift_multiplier": 0.05}')
    assert cfg.gift_multiplier == 0.1


def test_theme_invalid_falls_back_to_cheremsha_neon() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "theme": "nope"}')
    assert cfg.theme == "cheremsha_neon"
    # Valid themes are preserved (case-insensitive).
    assert battle_overlay_config_from_json_text('{"theme": "Cyber"}').theme == "cyber"
    assert battle_overlay_config_from_json_text('{"theme": "arcade"}').theme == "arcade"


def test_scale_percent_clamped_to_250() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "scale_percent": 999}')
    assert cfg.scale_percent == 250


def test_scale_percent_clamped_to_40() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "scale_percent": 5}')
    assert cfg.scale_percent == 40


def test_from_json_text_raises_on_non_json() -> None:
    with pytest.raises(ValueError):
        battle_overlay_config_from_json_text("not json")


def test_from_json_text_raises_on_non_object() -> None:
    # Valid JSON, but not an object.
    with pytest.raises(ValueError):
        battle_overlay_config_from_json_text("[1, 2]")
    with pytest.raises(ValueError):
        battle_overlay_config_from_json_text('"hello"')
    with pytest.raises(ValueError):
        battle_overlay_config_from_json_text("123")


def test_best_of_restricted_to_1_3_5() -> None:
    cfg = battle_overlay_config_from_json_text('{"schema_version": 1, "best_of": 4}')
    assert cfg.best_of == 3
    cfg5 = battle_overlay_config_from_json_text('{"schema_version": 1, "best_of": 5}')
    assert cfg5.best_of == 5


def test_load_battle_overlay_config_no_value_returns_defaults() -> None:
    s = _test_settings()
    cfg = load_battle_overlay_config(s)
    assert cfg == battle_overlay_config_defaults()


def test_load_battle_overlay_config_valid_value() -> None:
    s = _test_settings()
    custom = battle_overlay_config_defaults().replace(theme="cyber", best_of=5)
    save_battle_overlay_config(custom, s)
    loaded = load_battle_overlay_config(s)
    assert loaded.theme == "cyber"
    assert loaded.best_of == 5
    # The stored raw value must be a valid JSON object.
    assert s.value(SETTINGS_KEY, "", str) != ""


def test_load_battle_overlay_config_corrupt_key_falls_back_to_defaults() -> None:
    s = _test_settings()
    s.remove(BACKUP_KEY)
    # Write a corrupt value at the primary key, no backup.
    s.setValue(SETTINGS_KEY, "this-is-not-json")
    cfg = load_battle_overlay_config(s)
    assert cfg == battle_overlay_config_defaults()


def test_load_battle_overlay_config_corrupt_key_uses_backup() -> None:
    s = _test_settings()
    good = battle_overlay_config_defaults().replace(theme="arcade")
    txt = battle_overlay_config_to_json_text(good)
    s.setValue(SETTINGS_KEY, "corrupt!!!")
    s.setValue(BACKUP_KEY, txt)
    loaded = load_battle_overlay_config(s)
    assert loaded.theme == "arcade"
    # On recovery, the primary key is refreshed with the good value.
    assert s.value(SETTINGS_KEY, "", str) == txt


def test_load_battle_overlay_config_both_corrupt_falls_back_to_defaults() -> None:
    s = _test_settings()
    s.setValue(SETTINGS_KEY, "corrupt!!!")
    s.setValue(BACKUP_KEY, "also-corrupt")
    cfg = load_battle_overlay_config(s)
    assert cfg == battle_overlay_config_defaults()


def test_save_then_load_round_trip_via_settings() -> None:
    s = _test_settings()
    custom = battle_overlay_config_defaults().replace(
        theme="minimal", best_of=1, round_duration_s=90
    )
    save_battle_overlay_config(custom, s)
    assert s.value(SETTINGS_KEY, "", str) != ""
    loaded = load_battle_overlay_config(s)
    assert loaded == custom
