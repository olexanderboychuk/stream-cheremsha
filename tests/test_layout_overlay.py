import json

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


def test_single_layout_payload_is_migrated_to_collection() -> None:
    payload = {
        "id": "tiktok-vertical",
        "name": "TikTok вертикаль",
        "width": 1080,
        "height": 1920,
        "widgets": [{"id": "chat", "type": "chat", "x": 12, "visible": False}],
    }

    layouts = layouts_from_json_text(json.dumps(payload, ensure_ascii=False))

    assert len(layouts) == 1
    assert layouts[0].id == "tiktok-vertical"
    assert layouts[0].name == "TikTok вертикаль"
    assert (layouts[0].width, layouts[0].height) == (1080, 1920)
    assert layouts[0].widgets[0].visible is False


def test_duplicate_layout_ids_are_repaired_during_migration() -> None:
    payload = {
        "layouts": [
            {"id": "same", "name": "A", "widgets": []},
            {"id": "same", "name": "B", "widgets": []},
        ]
    }

    layouts = layouts_from_json_text(json.dumps(payload))

    assert [x.name for x in layouts] == ["A", "B"]
    assert layouts[0].id == "same"
    assert layouts[1].id != layouts[0].id


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
    from PySide6.QtCore import QSettings

    import stream_cheremsha.overlays.widget_instances as wimod

    monkeypatch.setattr(
        wimod, "QSettings", lambda *a, **k: QSettings("t-org-lay-ov", "t-app-lay-ov")
    )
    QSettings("t-org-lay-ov", "t-app-lay-ov").clear()

    lay = default_layout()
    # Bind the first widget so a by-id iframe renders.
    inst = wimod.create_instance("chat", "Bound", None)
    w = lay.widgets[0]
    from dataclasses import replace

    bound = replace(w, widget_instance_id=inst.id)
    monkeypatch.setattr(
        layout_overlay,
        "load_layouts",
        lambda: [replace(lay, widgets=(bound,))],
    )
    html = LayoutOverlayType().render_html({"instance": "main"})
    assert "class=\"canvas\"" in html
    assert f"/overlay/by-id/{inst.id}" in html
    assert "/overlay/chat?instance=" not in html
    assert "position:absolute" in html
