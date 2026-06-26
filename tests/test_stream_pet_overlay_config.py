import json

from stream_cheremsha.overlays.stream_pet_overlay_config import (
    apply_stream_pet_preset,
    load_stream_pet_overlay_config,
    save_stream_pet_overlay_config,
    stream_pet_overlay_config_defaults,
    stream_pet_overlay_config_from_json_text,
    stream_pet_overlay_config_to_json_text,
    stream_pet_overlay_config_to_public_dict,
)


def test_stream_pet_overlay_config_defaults() -> None:
    cfg = stream_pet_overlay_config_defaults()
    assert cfg.enabled is True
    assert cfg.large_gift_threshold_coins == 99
    assert cfg.sleep_idle_sec == 900
    assert cfg.preset == "classic_gold"
    assert cfg.collar_enabled is True
    assert cfg.pet_body_color == "#fbbf24"
    assert cfg.bubble_font_size_px == 20
    assert cfg.evolution_enabled is True
    assert cfg.bubble_max_chars == 110


def test_stream_pet_overlay_config_persist_roundtrip(tmp_path) -> None:
    from PySide6.QtCore import QSettings

    ini = tmp_path / "settings.ini"
    s = QSettings(str(ini), QSettings.Format.IniFormat)
    cfg = stream_pet_overlay_config_defaults().replace(decay_per_2min=2.5)
    save_stream_pet_overlay_config(cfg, settings=s)
    loaded = load_stream_pet_overlay_config(settings=s)
    assert loaded.decay_per_2min == 2.5


def test_stream_pet_overlay_config_json_roundtrip() -> None:
    cfg = stream_pet_overlay_config_defaults()
    got = stream_pet_overlay_config_from_json_text(stream_pet_overlay_config_to_json_text(cfg))
    assert got.bubble_font_family == cfg.bubble_font_family
    assert got.preset == cfg.preset


def test_stream_pet_overlay_config_bubble_font_size_clamped() -> None:
    cfg = stream_pet_overlay_config_defaults()
    raw = stream_pet_overlay_config_to_json_text(cfg)
    data = json.loads(raw)
    data["bubble_font_size_px"] = 8
    got = stream_pet_overlay_config_from_json_text(json.dumps(data))
    assert got.bubble_font_size_px == 12

    data["bubble_font_size_px"] = 64
    got = stream_pet_overlay_config_from_json_text(json.dumps(data))
    assert got.bubble_font_size_px == 48


def test_stream_pet_overlay_config_public_dict_includes_appearance() -> None:
    cfg = stream_pet_overlay_config_defaults()
    pub = stream_pet_overlay_config_to_public_dict(cfg)
    assert "appearance" in pub
    assert pub["appearance"]["body"] == "#fbbf24"
    assert pub["appearance"]["collar_enabled"] is True


def test_apply_stream_pet_preset_cyber_purple() -> None:
    cfg = stream_pet_overlay_config_defaults()
    updated = apply_stream_pet_preset(cfg, "cyber_purple")
    assert updated.preset == "cyber_purple"
    assert updated.pet_body_color == "#a78bfa"
    assert updated.blush_enabled is False
    pub = stream_pet_overlay_config_to_public_dict(updated)
    assert pub["appearance"]["body"] == "#a78bfa"
