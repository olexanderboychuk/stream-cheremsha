from __future__ import annotations

import json

from stream_cheremsha.overlays.top_likers_overlay_config import (
    TOP_LIKERS_USERNAME_TEXT_EFFECTS,
    top_likers_overlay_config_defaults,
    top_likers_overlay_config_from_json_text,
    top_likers_overlay_config_to_json_text,
)


def test_text_effect_username_accepts_extended_palette() -> None:
    base = top_likers_overlay_config_defaults()
    extra = TOP_LIKERS_USERNAME_TEXT_EFFECTS - {"none"}
    for fx in extra:
        obj = json.loads(top_likers_overlay_config_to_json_text(base))
        obj["text_effect_username"] = fx
        cfg = top_likers_overlay_config_from_json_text(json.dumps(obj))
        assert cfg.text_effect_username == fx


def test_text_effect_username_unknown_falls_back_to_default() -> None:
    base = top_likers_overlay_config_defaults()
    obj = json.loads(top_likers_overlay_config_to_json_text(base))
    obj["text_effect_username"] = "not_a_real_effect"
    cfg = top_likers_overlay_config_from_json_text(json.dumps(obj))
    assert cfg.text_effect_username == base.text_effect_username


def test_heart_size_px_clamped() -> None:
    base = top_likers_overlay_config_defaults()
    obj = json.loads(top_likers_overlay_config_to_json_text(base))
    obj["heart_size_px"] = 99
    assert top_likers_overlay_config_from_json_text(json.dumps(obj)).heart_size_px == 48
    obj["heart_size_px"] = 1
    assert top_likers_overlay_config_from_json_text(json.dumps(obj)).heart_size_px == 8


def test_heart_animated_roundtrip() -> None:
    base = top_likers_overlay_config_defaults()
    obj = json.loads(top_likers_overlay_config_to_json_text(base))
    obj["heart_animated"] = False
    cfg = top_likers_overlay_config_from_json_text(json.dumps(obj))
    assert cfg.heart_animated is False


def test_list_scroll_interval_sec_clamped() -> None:
    base = top_likers_overlay_config_defaults()
    obj = json.loads(top_likers_overlay_config_to_json_text(base))
    obj["list_scroll_interval_sec"] = 9999
    assert top_likers_overlay_config_from_json_text(json.dumps(obj)).list_scroll_interval_sec == 600
    obj["list_scroll_interval_sec"] = -5
    assert top_likers_overlay_config_from_json_text(json.dumps(obj)).list_scroll_interval_sec == 0


def test_top_count_clamped_to_range_1_10() -> None:
    base = top_likers_overlay_config_defaults()
    obj = json.loads(top_likers_overlay_config_to_json_text(base))
    obj["top_count"] = 99
    cfg_high = top_likers_overlay_config_from_json_text(json.dumps(obj))
    assert cfg_high.top_count == 10
    obj["top_count"] = 0
    cfg_low = top_likers_overlay_config_from_json_text(json.dumps(obj))
    assert cfg_low.top_count == 1
