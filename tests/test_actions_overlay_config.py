from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.actions_config import (
    ACTIONS_CONFIG_SCHEMA_VERSION,
    actions_config_defaults,
    actions_config_from_json_text,
    actions_config_to_json_text,
    load_actions_config,
    save_actions_config,
)
from stream_cheremsha.overlays.actions_overlay import _platform_icons_data_uris


@pytest.fixture()
def ini_settings(tmp_path: Path) -> QSettings:
    # Ensure tests do not touch Windows registry (NativeFormat).
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    org = f"test-org-{uuid.uuid4()}"
    app = f"test-app-{uuid.uuid4()}"
    s = QSettings(QSettings.IniFormat, QSettings.UserScope, org, app)
    s.clear()
    s.sync()
    return s


def test_defaults_schema_version() -> None:
    cfg = actions_config_defaults()
    assert cfg.schema_version == ACTIONS_CONFIG_SCHEMA_VERSION


def test_actions_overlay_embeds_platform_svgs_as_data_uris() -> None:
    m = _platform_icons_data_uris()
    assert {"tiktok", "twitch", "youtube"}.issubset(m.keys())
    for k in ("tiktok", "twitch", "youtube"):
        assert m[k].startswith("data:image/svg+xml;base64,")


def test_to_json_roundtrip() -> None:
    cfg = actions_config_defaults()
    txt = actions_config_to_json_text(cfg)
    obj = json.loads(txt)
    assert obj["schema_version"] == ACTIONS_CONFIG_SCHEMA_VERSION
    cfg2 = actions_config_from_json_text(txt)
    assert cfg2 == cfg


def test_from_json_accepts_future_schema_version_uses_defaults_for_missing_fields() -> None:
    cfg = actions_config_from_json_text(json.dumps({"schema_version": 999}))
    assert cfg == actions_config_defaults()


def test_from_json_accepts_future_schema_version_preserves_known_fields() -> None:
    base = actions_config_defaults().replace(font_family="CustomFont", platform_icon_size_px=72)
    obj = json.loads(actions_config_to_json_text(base))
    obj["schema_version"] = 424242
    cfg = actions_config_from_json_text(json.dumps(obj))
    assert cfg.font_family == "CustomFont"
    assert cfg.platform_icon_size_px == 72


def test_from_json_accepts_missing_schema_version_for_backcompat() -> None:
    obj = json.loads(actions_config_to_json_text(actions_config_defaults()))
    obj.pop("schema_version", None)
    cfg = actions_config_from_json_text(json.dumps(obj))
    assert cfg.schema_version == ACTIONS_CONFIG_SCHEMA_VERSION


def test_username_text_effect_unknown_falls_back_to_none() -> None:
    base = json.loads(actions_config_to_json_text(actions_config_defaults()))
    base["username_text_effect"] = "unknown"
    cfg = actions_config_from_json_text(json.dumps(base))
    assert cfg.username_text_effect == "none"


def test_auto_hide_seconds_defaults_and_roundtrip() -> None:
    cfg = actions_config_defaults()
    assert cfg.auto_hide_seconds == 0.0
    txt = actions_config_to_json_text(cfg)
    cfg2 = actions_config_from_json_text(txt)
    assert cfg2.auto_hide_seconds == 0.0


def test_auto_hide_seconds_clamped_non_negative() -> None:
    base = json.loads(actions_config_to_json_text(actions_config_defaults()))
    base["auto_hide_seconds"] = -5
    cfg = actions_config_from_json_text(json.dumps(base))
    assert cfg.auto_hide_seconds == 0.0


def test_bubble_settings_roundtrip() -> None:
    base = actions_config_defaults().replace(
        bubble_bg_enabled=False,
        bubble_bg_alpha=0.25,
        bubble_radius_px=33,
    )
    txt = actions_config_to_json_text(base)
    cfg2 = actions_config_from_json_text(txt)
    assert cfg2.bubble_bg_enabled is False
    assert cfg2.bubble_bg_alpha == 0.25
    assert cfg2.bubble_radius_px == 33


def test_bubble_alpha_clamped_0_1() -> None:
    obj = json.loads(actions_config_to_json_text(actions_config_defaults()))
    obj["bubble_bg_alpha"] = 5
    cfg = actions_config_from_json_text(json.dumps(obj))
    assert cfg.bubble_bg_alpha == 1.0


def test_text_color_roundtrip() -> None:
    cfg = actions_config_defaults().replace(text_color="#ff00aa")
    txt = actions_config_to_json_text(cfg)
    cfg2 = actions_config_from_json_text(txt)
    assert cfg2.text_color == "#ff00aa"


def test_parallel_popups_enabled_roundtrip() -> None:
    cfg = actions_config_defaults().replace(parallel_popups_enabled=True)
    cfg2 = actions_config_from_json_text(actions_config_to_json_text(cfg))
    assert cfg2.parallel_popups_enabled is True
    obj = json.loads(actions_config_to_json_text(actions_config_defaults()))
    assert obj["parallel_popups_enabled"] is False


def test_name_text_gap_roundtrip_and_clamp() -> None:
    cfg = actions_config_defaults().replace(name_text_gap_px=22)
    txt = actions_config_to_json_text(cfg)
    cfg2 = actions_config_from_json_text(txt)
    assert cfg2.name_text_gap_px == 22

    obj = json.loads(actions_config_to_json_text(actions_config_defaults()))
    obj["name_text_gap_px"] = 999
    cfg3 = actions_config_from_json_text(json.dumps(obj))
    assert cfg3.name_text_gap_px == 80


def test_load_returns_defaults_when_missing(ini_settings: QSettings) -> None:
    cfg = load_actions_config(settings=ini_settings)
    assert cfg == actions_config_defaults()


def test_save_then_load(ini_settings: QSettings) -> None:
    cfg = actions_config_defaults().replace(font_family="Roboto", font_size_px=50)
    save_actions_config(cfg, settings=ini_settings)
    out = load_actions_config(settings=ini_settings)
    assert out.font_family == "Roboto"
    assert out.font_size_px == 50


def test_load_uses_backup_when_primary_is_invalid(ini_settings: QSettings) -> None:
    cfg = actions_config_defaults().replace(font_family="Inter", name_text_gap_px=12)
    save_actions_config(cfg, settings=ini_settings)
    # Corrupt primary value.
    ini_settings.setValue("overlays/actions/main/config_json", "{")
    ini_settings.sync()
    out = load_actions_config(settings=ini_settings)
    assert out.font_family == "Inter"
    assert out.name_text_gap_px == 12
