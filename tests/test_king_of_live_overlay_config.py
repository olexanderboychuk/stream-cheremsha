from __future__ import annotations

import json

import pytest

from stream_cheremsha.overlays.king_of_live_overlay_config import (
    king_of_live_overlay_config_defaults,
    king_of_live_overlay_config_from_json_text,
    king_of_live_overlay_config_to_json_text,
)


def test_king_defaults_roundtrip_json() -> None:
    cfg = king_of_live_overlay_config_defaults()
    txt = king_of_live_overlay_config_to_json_text(cfg)
    back = king_of_live_overlay_config_from_json_text(txt)
    assert back == cfg


def test_king_from_json_clamps_threshold_and_avatar() -> None:
    raw = json.dumps(
        {
            "schema_version": 1,
            "preset": "cyber_king",
            "title_text": "X",
            "show_gap_strip": False,
            "danger_threshold_pct": 40,
            "avatar_size_px": 400,
            "font_family": "Arial",
        },
    )
    cfg = king_of_live_overlay_config_from_json_text(raw)
    assert cfg.preset == "cyber_king"
    assert cfg.danger_threshold_pct == 50
    assert cfg.avatar_size_px == 220
    assert cfg.anim_crown_float is True
    assert cfg.anim_rays_spin is True
    assert cfg.backdrop_blur_px == 0
    assert cfg.backdrop_bubble_blur_px == 0
    assert cfg.rays_intensity_pct == 130
    assert cfg.text_scale_pct == 100
    assert cfg.anim_intensity_pct == 100


def test_king_from_json_clamps_backdrop_blur() -> None:
    hi = json.dumps(
        {"schema_version": 1, "preset": "minimalist", "title_text": "T", "backdrop_blur_px": 120}
    )
    assert king_of_live_overlay_config_from_json_text(hi).backdrop_blur_px == 48
    lo = json.dumps(
        {"schema_version": 1, "preset": "minimalist", "title_text": "T", "backdrop_blur_px": -5}
    )
    assert king_of_live_overlay_config_from_json_text(lo).backdrop_blur_px == 0


def test_king_from_json_clamps_bubble_text_anim_rays() -> None:
    raw = json.dumps(
        {
            "schema_version": 1,
            "preset": "minimalist",
            "title_text": "T",
            "backdrop_bubble_blur_px": 80,
            "rays_intensity_pct": 3,
            "text_scale_pct": 500,
            "anim_intensity_pct": 1,
        },
    )
    c = king_of_live_overlay_config_from_json_text(raw)
    assert c.backdrop_bubble_blur_px == 48
    assert c.rays_intensity_pct == 40
    assert c.text_scale_pct == 160
    assert c.anim_intensity_pct == 25


def test_king_from_json_disables_animation_flags() -> None:
    raw = json.dumps(
        {
            "schema_version": 1,
            "preset": "minimalist",
            "title_text": "T",
            "show_gap_strip": True,
            "danger_threshold_pct": 90,
            "avatar_size_px": 120,
            "font_family": "Segoe UI",
            "anim_avatar_motion": False,
            "anim_crown_float": False,
            "anim_rays_spin": False,
            "anim_coins_fall": False,
            "anim_gem_pulse": False,
            "anim_title_shimmer": False,
            "anim_fireworks_on_presence": False,
        },
    )
    cfg = king_of_live_overlay_config_from_json_text(raw)
    assert cfg.anim_avatar_motion is False
    assert cfg.anim_fireworks_on_presence is False


def test_king_invalid_preset_falls_back() -> None:
    raw = '{"schema_version":1,"preset":"nope","title_text":"T","show_gap_strip":true,'
    raw += '"danger_threshold_pct":90,"avatar_size_px":120,"font_family":"Segoe UI"}'
    cfg = king_of_live_overlay_config_from_json_text(raw)
    assert cfg.preset == "imperial_gold"


def test_king_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        king_of_live_overlay_config_from_json_text("[]")
