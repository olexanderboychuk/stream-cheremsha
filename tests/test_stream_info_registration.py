from __future__ import annotations

from stream_cheremsha.overlays import widget_instances
from stream_cheremsha.overlays.layout import SUPPORTED_LAYOUT_WIDGETS
from stream_cheremsha.overlays.registry import OverlayRegistry


def test_stream_info_registered_everywhere() -> None:
    assert "stream_info" in widget_instances.WIDGET_TYPES
    assert "stream_info" in SUPPORTED_LAYOUT_WIDGETS
    assert OverlayRegistry().get("stream_info").type == "stream_info"
