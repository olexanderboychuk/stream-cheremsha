import json

import pytest

from stream_cheremsha.overlays.chat_config import (
    CHAT_CONFIG_SCHEMA_VERSION,
    ChatOverlayConfig,
    chat_config_defaults,
    chat_config_from_json_text,
    chat_config_to_json_text,
)


def test_chat_config_defaults_are_valid() -> None:
    cfg = chat_config_defaults()
    assert isinstance(cfg, ChatOverlayConfig)
    assert cfg.schema_version == CHAT_CONFIG_SCHEMA_VERSION
    assert cfg.max_items >= 1
    assert cfg.font_size_px >= 8
    assert cfg.show_platform in (True, False)
    assert cfg.username_color_mode in ("auto", "platform", "custom")
    assert isinstance(cfg.bubble_radius_px, int) and cfg.bubble_radius_px >= 0
    assert cfg.text_shadow_enabled is False
    assert "rgba" in cfg.text_shadow_rgba
    assert 0 <= cfg.text_shadow_blur_px <= 24


def test_chat_config_json_roundtrip() -> None:
    cfg = chat_config_defaults().replace(
        max_items=7,
        show_platform=False,
        username_color_mode="custom",
        username_color_custom="#ffffff",
        bubble_radius_px=22,
        bubble_bg_rgba="rgba(1,2,3,0.4)",
        show_platform_icon=False,
        text_shadow_enabled=True,
        text_shadow_rgba="rgba(10,20,30,0.5)",
        text_shadow_blur_px=8,
        text_shadow_offset_x_px=2,
        text_shadow_offset_y_px=-1,
    )
    txt = chat_config_to_json_text(cfg)
    obj = json.loads(txt)
    assert obj["schema_version"] == CHAT_CONFIG_SCHEMA_VERSION
    out = chat_config_from_json_text(txt)
    assert out.max_items == 7
    assert out.show_platform is False
    assert out.username_color_mode == "custom"
    assert out.username_color_custom == "#ffffff"
    assert out.bubble_radius_px == 22
    assert out.bubble_bg_rgba == "rgba(1,2,3,0.4)"
    assert out.show_platform_icon is False
    assert out.text_shadow_enabled is True
    assert out.text_shadow_rgba == "rgba(10,20,30,0.5)"
    assert out.text_shadow_blur_px == 8
    assert out.text_shadow_offset_x_px == 2
    assert out.text_shadow_offset_y_px == -1


def test_chat_config_rejects_bad_schema_version() -> None:
    with pytest.raises(ValueError):
        chat_config_from_json_text('{"schema_version":999,"max_items":1}')
