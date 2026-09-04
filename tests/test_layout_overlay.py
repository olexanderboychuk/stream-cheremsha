import stream_cheremsha.overlays.layout_overlay as layout_overlay
from stream_cheremsha.overlays.layout import (
    default_layout,
    layout_from_dict,
    layouts_from_json_text,
    layouts_to_json_text,
)
from stream_cheremsha.overlays.layout_overlay import LayoutOverlayType


def test_layout_round_trip() -> None:
    layout = default_layout()
    restored = layouts_from_json_text(layouts_to_json_text([layout]))[0]
    assert restored == layout


def test_layout_parser_ignores_unknown_widget_types() -> None:
    layout = layout_from_dict(
        {
            "id": "vertical",
            "name": "Vertical",
            "width": 1080,
            "height": 1920,
            "widgets": [
                {"id": "chat", "type": "chat", "x": 1, "y": 2},
                {"id": "bad", "type": "not-an-overlay"},
            ],
        }
    )
    assert layout.id == "vertical"
    assert [x.type for x in layout.widgets] == ["chat"]
    assert layout.widgets[0].width == 320


def test_layout_overlay_renders_absolute_iframes(monkeypatch) -> None:
    monkeypatch.setattr(layout_overlay, "load_layouts", lambda: [default_layout()])
    html = LayoutOverlayType().render_html({"instance": "main"})
    assert "class=\"canvas\"" in html
    assert "/overlay/chat?instance=main" in html
    assert "/overlay/actions?instance=main" in html
    assert "position:absolute" in html
