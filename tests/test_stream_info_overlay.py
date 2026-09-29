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


def _css_rule(html: str, selector: str) -> str:
    start = html.index(selector)
    return html[start : html.index("}", start)]


def test_stream_info_panel_fills_available_area() -> None:
    overlay = StreamInfoOverlayType()
    html = overlay.render_html({"instance": "main"})
    panel_css = _css_rule(html, ".panel-stats {")
    assert "width: 100%" in panel_css
    assert "height: 100%" in panel_css
    cell_css = _css_rule(html, ".stat-cell {")
    assert "flex-direction: column" in cell_css
    assert "justify-content: center" in cell_css
