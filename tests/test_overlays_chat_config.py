import json

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
    assert cfg.widget_bg_enabled is False
    assert "rgba" in cfg.widget_bg_rgba
    assert 0 <= cfg.widget_bg_radius_px <= 60
    assert 0 <= cfg.widget_bg_padding_px <= 48
    assert cfg.bubble_bg_enabled is True


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
        widget_bg_enabled=True,
        widget_bg_rgba="rgba(5,6,7,0.33)",
        widget_bg_radius_px=18,
        widget_bg_padding_px=12,
        bubble_bg_enabled=False,
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
    assert out.widget_bg_enabled is True
    assert out.widget_bg_rgba == "rgba(5,6,7,0.33)"
    assert out.widget_bg_radius_px == 18
    assert out.widget_bg_padding_px == 12
    assert out.bubble_bg_enabled is False


def test_chat_config_future_schema_preserves_known_fields() -> None:
    cfg = chat_config_defaults().replace(max_items=3, show_platform_icon=False)
    obj = json.loads(chat_config_to_json_text(cfg))
    obj["schema_version"] = 999
    out = chat_config_from_json_text(json.dumps(obj))
    assert out.max_items == 3
    assert out.show_platform_icon is False
