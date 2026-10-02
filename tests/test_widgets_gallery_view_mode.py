"""Regression: widgets gallery grid/list density toggle.

Catches:
- gallery defaulting to grid instead of list
- toggle persisting the choice (QSettings roundtrip, bogus rejected)
- restore running before the persist guard flips (no startup overwrite)
- list delegate diverging from the card's action wiring
"""

from __future__ import annotations

from pathlib import Path

_QML = Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml"


def _view() -> str:
    return (_QML / "WidgetsView.qml").read_text(encoding="utf-8")


def test_qmldir_registers_widget_row() -> None:
    src = (_QML / "components" / "qmldir").read_text(encoding="utf-8")
    assert "CheremshaWidgetRow 1.0 CheremshaWidgetRow.qml" in src


def test_gallery_defaults_to_list_with_restore_guard() -> None:
    src = _view()
    assert 'property string galleryViewMode: "list"' in src
    assert "property bool _galleryViewReady: false" in src
    assert "onGalleryViewModeChanged:" in src
    assert "if (!root._galleryViewReady) return;" in src


def test_toggle_sets_and_persists_both_modes() -> None:
    src = _view()
    assert 'root.loc("widgets.gallery.view_grid")' in src
    assert 'root.loc("widgets.gallery.view_list")' in src
    assert "onClicked: root.galleryViewMode = " in src
    assert src.count('root.galleryViewMode = "grid"') >= 1
    assert src.count('root.galleryViewMode = "list"') >= 1
    assert "api.setGalleryViewMode(root.galleryViewMode)" in src


def test_grid_gated_and_list_reuses_model() -> None:
    src = _view()
    assert "visible: root.galleryViewMode " in src
    assert "id: galleryListRepeater" in src
    assert "model: root.galleryFilteredTypes()" in src
    assert "delegate: CheremshaWidgetRow {" in src


def test_list_delegate_mirrors_card_actions() -> None:
    src = _view()
    start = src.find("delegate: CheremshaWidgetRow {")
    assert start >= 0
    # Same action surface as the grid card delegate (copy/open/toggle/menu/edit).
    for token in (
        "api.copyWidgetInstanceUrl",
        "api.openWidgetInstanceUrl",
        "api.setWidgetInstanceEnabled",
        "api.duplicateWidgetInstance",
        "api.deleteWidgetInstance",
        "grow.openEditor()",
        "grow.ensureInstId()",
        "toggleTipText",
        "platformBadgeText",
        "id: rowMenu",
        "pageRoot.refreshWidgetInstances()",
    ):
        assert token in src[start:], token


def test_restore_reads_api_before_ready() -> None:
    src = _view()
    assert "api.galleryViewMode()" in src
    assert "root._galleryViewReady = true;" in src
    # Restore precedes the guard flip so startup never persists a default.
    assert src.find("api.galleryViewMode()") < src.find("root._galleryViewReady = true;")


def test_l10n_has_view_keys() -> None:
    from stream_cheremsha import l10n

    assert l10n.tr("uk", "widgets.gallery.view_grid") == "Сітка"
    assert l10n.tr("en", "widgets.gallery.view_grid") == "Grid"
    assert l10n.tr("uk", "widgets.gallery.view_list") == "Список"
    assert l10n.tr("en", "widgets.gallery.view_list") == "List"


def test_api_view_mode_roundtrip_isolated_settings(monkeypatch) -> None:
    """Default list; grid persists; bogus values rejected — isolated QSettings."""
    from PySide6.QtCore import QSettings

    import stream_cheremsha.ui.widgets_qml_api as wqa
    from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi

    monkeypatch.setattr(
        wqa, "QSettings", lambda *a, **k: QSettings("test-cheremsha-view", "gallery")
    )
    api = WidgetsQmlApi()
    assert api.galleryViewMode() == "list"
    api.setGalleryViewMode("grid")
    assert api.galleryViewMode() == "grid"
    api.setGalleryViewMode("bogus")
    assert api.galleryViewMode() == "grid"
    api.setGalleryViewMode("list")
    assert api.galleryViewMode() == "list"


def test_widget_row_qml_compiles(qapp) -> None:
    """CheremshaWidgetRow instantiates standalone (no api dependency)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    engine.addImportPath(str(_QML))
    url = QUrl.fromLocalFile(str(_QML / "components" / "CheremshaWidgetRow.qml"))
    comp = QQmlComponent(engine, url)
    item = None if comp.isError() else comp.create()
    errs = [str(e.errorString()) for e in comp.errors()]
    assert item is not None, "; ".join(errs)
