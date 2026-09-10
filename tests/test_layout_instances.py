from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays import layout as L
from stream_cheremsha.overlays import widget_instances as wi


def _fresh() -> QSettings:
    s = QSettings("stream-cheremsha-test", "layout-instances-test")
    s.clear()
    s.sync()
    return s


def test_legacy_single_layout_is_persisted_as_collection() -> None:
    s = _fresh()
    s.setValue(
        L.LAYOUTS_QSETTINGS_KEY,
        json.dumps(
            {
                "id": "tiktok-vertical",
                "name": "TikTok вертикаль",
                "width": 1080,
                "height": 1920,
                "widgets": [],
            },
            ensure_ascii=False,
        ),
    )
    s.sync()

    layouts = L.load_layouts(s)
    stored = json.loads(str(s.value(L.LAYOUTS_QSETTINGS_KEY, "", str)))

    assert len(layouts) == 1
    assert layouts[0].id == "tiktok-vertical"
    assert stored["layouts"][0]["name"] == "TikTok вертикаль"
    assert L.get_active_layout_id(s) == "tiktok-vertical"


def test_legacy_default_layout_survives() -> None:
    s = _fresh()
    layouts = L.ensure_layouts(s)
    assert len(layouts) == 1
    assert layouts[0].id == "default"
    assert layouts[0].name == L.layout_default_name()
    # idempotent: second call does not duplicate
    assert len(L.ensure_layouts(s)) == 1


def test_create_rename_duplicate_delete() -> None:
    s = _fresh()
    L.ensure_layouts(s)
    a = L.create_layout("TikTok вертикаль", width=1080, height=1920, settings=s)
    assert a.id != "default"
    assert (a.width, a.height) == (1080, 1920)
    assert len(L.load_layouts(s)) == 2

    renamed = L.rename_layout(a.id, "Нова назва", settings=s)
    assert renamed is not None and renamed.name == "Нова назва"

    dup = L.duplicate_layout(a.id, settings=s)
    assert dup is not None and dup.id != a.id
    assert dup.widgets == a.widgets and dup.name == "Нова назва" + L.layout_copy_suffix()

    assert L.delete_layout(dup.id, settings=s) is True
    assert L.get_layout(dup.id, s) is None
    assert L.get_layout(a.id, s) is not None


def test_delete_last_layout_refused() -> None:
    s = _fresh()
    L.ensure_layouts(s)
    assert L.delete_layout("default", settings=s) is False
    assert len(L.load_layouts(s)) == 1


def test_active_layout_persists() -> None:
    s = _fresh()
    L.ensure_layouts(s)
    a = L.create_layout("Друга", settings=s)
    L.set_active_layout_id(a.id, s)
    assert L.get_active_layout_id(s) == a.id
    assert L.resolve_active_layout(s).id == a.id


def test_upsert_preserves_siblings() -> None:
    s = _fresh()
    L.ensure_layouts(s)
    a = L.create_layout("A", settings=s)
    b = L.create_layout("B", settings=s)
    renamed_b = L.StreamLayout(
        id=b.id, name="B2", width=b.width, height=b.height, widgets=b.widgets
    )
    L.upsert_layout(renamed_b, s)
    assert L.get_layout(a.id, s).name == "A"
    assert L.get_layout(b.id, s).name == "B2"


def test_widget_instance_binding_roundtrip() -> None:
    s = _fresh()
    L.ensure_layouts(s)
    a = L.create_layout("Bound", settings=s)
    w = L.LayoutWidget("w1", "chat", "main", 0, 0, 100, 100, widget_instance_id="abc123")
    L.upsert_layout(
        L.StreamLayout(id=a.id, name=a.name, width=a.width, height=a.height, widgets=(w,)), s
    )
    text = L.layouts_to_json_text(L.load_layouts(s))
    restored = L.layouts_from_json_text(text)
    bound = next(x for x in restored if x.id == a.id).widgets[0]
    assert bound.widget_instance_id == "abc123"
    assert bound.instance == "main"  # legacy token preserved


def test_layout_overlay_renders_by_id_when_bound(monkeypatch) -> None:
    import stream_cheremsha.overlays.layout as lmod
    import stream_cheremsha.overlays.widget_instances as wimod
    from stream_cheremsha.overlays.layout_overlay import LayoutOverlayType

    monkeypatch.setattr(lmod, "QSettings", lambda *a, **k: QSettings("t-org-lay", "t-app-lay"))
    monkeypatch.setattr(wimod, "QSettings", lambda *a, **k: QSettings("t-org-lay", "t-app-lay"))
    QSettings("t-org-lay", "t-app-lay").clear()

    inst = wi.create_instance("chat", "Bound Chat", None)
    legacy_w = L.LayoutWidget("w1", "chat", "main", 0, 0, 100, 100)
    bound_w = L.LayoutWidget("w2", "chat", "main", 0, 0, 100, 100, widget_instance_id=inst.id)
    lay = L.StreamLayout(
        id="default", name="X", width=1920, height=1080, widgets=(legacy_w, bound_w)
    )
    L.save_layouts([lay])

    html = LayoutOverlayType().render_html({"instance": "main", "layout": "default"})
    assert "/overlay/chat?instance=main" in html  # legacy URL intact
    assert f"/overlay/by-id/{inst.id}" in html  # bound instance URL

    # unknown instance id falls back to legacy URL, never breaks render
    ghost = L.LayoutWidget("w3", "chat", "main", 0, 0, 100, 100, widget_instance_id="nope")
    lay2 = L.StreamLayout(id="default", name="X", width=1920, height=1080, widgets=(ghost,))
    L.save_layouts([lay2])
    html2 = LayoutOverlayType().render_html({"instance": "main", "layout": "default"})
    assert "/overlay/chat?instance=main" in html2
