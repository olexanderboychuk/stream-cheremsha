from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.social_rotator_overlay_config import (
    load_social_rotator_overlay_config,
    parse_platforms,
    save_social_rotator_overlay_config,
    social_rotator_overlay_config_defaults,
    social_rotator_overlay_config_from_json_text,
    social_rotator_overlay_config_to_json_text,
)


def test_defaults_have_five_platforms() -> None:
    cfg = social_rotator_overlay_config_defaults()
    plats = parse_platforms(cfg)
    assert [p["platform"] for p in plats] == [
        "twitch",
        "youtube",
        "kick",
        "telegram",
        "tiktok",
    ]
    assert cfg.rotation_interval_ms == 8000
    assert cfg.transition == "glitch_morph"
    assert cfg.theme == "neon_cyber"
    assert cfg.tiktok_coin_to_value_rate == 1.0
    assert cfg.background_opacity_percent == 85


def test_roundtrip_clamps() -> None:
    cfg = social_rotator_overlay_config_defaults().replace(
        rotation_interval_ms=50,
        scale_percent=10,
        transition="nope",
        theme="nope",
        tiktok_coin_to_value_rate=-1,
    )
    cfg2 = social_rotator_overlay_config_from_json_text(
        social_rotator_overlay_config_to_json_text(cfg)
    )
    assert cfg2.rotation_interval_ms == 1000
    assert cfg2.scale_percent == 40
    assert cfg2.transition == "glitch_morph"
    assert cfg2.theme == "neon_cyber"
    assert cfg2.tiktok_coin_to_value_rate == 0.0


def test_drops_unknown_platform_entries() -> None:
    raw = {
        "schema_version": 1,
        "platforms": [
            {
                "id": "1",
                "platform": "twitch",
                "username": "a",
                "enabled": True,
                "order": 0,
            },
            {
                "id": "2",
                "platform": "myspace",
                "username": "x",
                "enabled": True,
                "order": 1,
            },
        ],
    }
    cfg = social_rotator_overlay_config_from_json_text(json.dumps(raw))
    plats = parse_platforms(cfg)
    assert len(plats) == 1
    assert plats[0]["platform"] == "twitch"


def test_qsettings_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ini = str(tmp_path / "sr.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)
    cfg = social_rotator_overlay_config_defaults().replace(
        show_url=False, background_opacity_percent=0
    )
    save_social_rotator_overlay_config(cfg, settings)
    loaded = load_social_rotator_overlay_config(settings)
    assert loaded.show_url is False
    assert loaded.background_opacity_percent == 0


def test_background_opacity_clamped() -> None:
    cfg = social_rotator_overlay_config_from_json_text(
        social_rotator_overlay_config_to_json_text(
            social_rotator_overlay_config_defaults().replace(background_opacity_percent=250)
        )
    )
    assert cfg.background_opacity_percent == 100
    cfg2 = social_rotator_overlay_config_from_json_text(
        social_rotator_overlay_config_to_json_text(
            social_rotator_overlay_config_defaults().replace(background_opacity_percent=-5)
        )
    )
    assert cfg2.background_opacity_percent == 0
