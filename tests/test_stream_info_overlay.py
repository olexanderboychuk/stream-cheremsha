from __future__ import annotations

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.stream_info_overlay import StreamInfoOverlayType


def test_stream_info_renderer_and_registry() -> None:
    overlay = StreamInfoOverlayType()
    assert overlay.type == "stream_info"
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "panel-stats" in html
    assert "statTime" in html
    assert "statTop" in html
    assert "statOnline" in html
    assert "/ws" in html
    st = overlay.initial_state({"instance": "main"})
    assert "config" in st and "stats" in st
    assert "rotation" not in st
    reg = OverlayRegistry()
    assert reg.get("stream_info").type == "stream_info"
