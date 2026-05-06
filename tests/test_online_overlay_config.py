from __future__ import annotations

from stream_cheremsha.overlays.online_overlay_config import (
    online_overlay_config_defaults,
    online_overlay_config_from_json_text,
    online_overlay_config_to_json_text,
)


def test_online_overlay_config_roundtrip() -> None:
    base = online_overlay_config_defaults()
    txt = online_overlay_config_to_json_text(base)
    again = online_overlay_config_from_json_text(txt)
    assert again == base


def test_online_overlay_config_layout_mode_normalized() -> None:
    raw = '{"layout_mode":"COMBINED"}'
    cfg = online_overlay_config_from_json_text(raw)
    assert cfg.layout_mode == "combined"
