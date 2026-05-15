from __future__ import annotations

from stream_cheremsha.overlays.top_gifters_overlay_config import (
    top_gifters_overlay_config_defaults,
    top_gifters_overlay_config_from_json_text,
    top_gifters_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.top_likers_overlay_config import (
    top_likers_overlay_config_from_json_text,
    top_likers_overlay_config_to_json_text,
)


def test_top_gifters_json_helpers_match_likers_schema_roundtrip() -> None:
    d = top_gifters_overlay_config_defaults()
    txt_g = top_gifters_overlay_config_to_json_text(d)
    txt_l = top_likers_overlay_config_to_json_text(d)
    assert txt_g == txt_l
    assert top_gifters_overlay_config_from_json_text(
        txt_g
    ) == top_likers_overlay_config_from_json_text(txt_l)
