from __future__ import annotations

from stream_cheremsha.overlays import widget_instances
from stream_cheremsha.overlays.layout import SUPPORTED_LAYOUT_WIDGETS
from stream_cheremsha.overlays.registry import OverlayRegistry


def test_stream_info_registered_everywhere() -> None:
    assert "stream_info" in widget_instances.WIDGET_TYPES
    assert "stream_info" in SUPPORTED_LAYOUT_WIDGETS
    assert OverlayRegistry().get("stream_info").type == "stream_info"


def test_legacy_social_rotator_config_still_parses() -> None:
    from stream_cheremsha.overlays.social_rotator_overlay_config import (
        social_rotator_overlay_config_from_json_text,
    )

    legacy = (
        '{"enabled": true, "show_top_donator": true, '
        '"show_stream_time": true, "platforms": []}'
    )
    cfg = social_rotator_overlay_config_from_json_text(legacy)
    assert cfg.enabled is True


def test_legacy_layout_with_social_rotator_survives() -> None:
    from stream_cheremsha.overlays.layout import layout_from_dict

    raw = {
        "id": "x",
        "name": "x",
        "width": 1920,
        "height": 1080,
        "widgets": [
            {
                "id": "a",
                "type": "social_rotator",
                "instance": "main",
                "x": 0,
                "y": 0,
                "width": 360,
                "height": 120,
            }
        ],
    }
    layout = layout_from_dict(raw)
    assert layout.widgets[0].type == "social_rotator"
