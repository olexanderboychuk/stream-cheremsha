from pathlib import Path

WIDGETS_VIEW = Path(__file__).parents[1] / "src/stream_cheremsha/qml/WidgetsView.qml"


def test_layout_browser_repeater_is_visible():
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    repeater = source[source.index("id: layoutBrowserGrid") : source.index("id: layoutCardMenu")]

    assert "visible: false" not in repeater


def test_spinbox_indicators_use_focused_user_step():
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    spinbox = source[
        source.index("component StyledSpinBox") : source.index("component ResizeHandle")
    ]

    assert "sb.forceActiveFocus()" in spinbox
    # Synchronous assign + emit: no deferred callLater (it raced with
    # focus loss and reset inspector values).
    assert "sb.valueModified()" in spinbox
    assert "Qt.callLater(function() { sb.valueModified(); })" not in spinbox


def test_inspector_spins_sync_explicitly_without_live_binding():
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "_syncInspectorSpins" in source
    inspector = source[source.index("id: layoutXSpin") : source.index("id: layoutHSpin")]
    assert "Binding {" not in inspector


def test_spinbox_editor_keeps_live_text_binding():
    # Direct `text = sb.displayText` freezes the editor: after stepping X and
    # touching W, focus loss re-parsed the stale text and reverted X.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    spinbox = source[
        source.index("component StyledSpinBox") : source.index("component ResizeHandle")
    ]
    assert "text = sb.displayText" not in spinbox
    assert "Qt.binding(function() { return sb.displayText; })" in spinbox


def test_canvas_drag_live_syncs_inspector_spins():
    # Drag/resize mutates delegate-local geometry; layoutDoc commits only on
    # release, so the canvas must mirror values into the spins live.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "_syncInspectorLive" in source
    assert "root._syncInspectorLive(index, rawX, rawY, rawW, rawH)" in source
    assert (
        "root._syncInspectorLive(index, targetX, targetY, layoutWidget.localW, layoutWidget.localH)"
        in source
    )


def test_inspector_spins_register_for_root_scope_sync():
    # The editor UI lives inside `Component { id: gatedUi }`: spin ids are
    # invisible from root functions, so spins must register their refs.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    for key in ("_spinX", "_spinY", "_spinW", "_spinH"):
        assert f"property var {key}: null" in source
    assert "root._spinX = layoutXSpin" in source
    assert "root._spinW = layoutWSpin" in source
    # No bare id references may remain in root sync functions (ReferenceError
    # inside try/catch would silently skip the whole sync).
    sync = source[source.index("function _syncInspectorSpins") : source.index("function updateLayoutItem")]
    assert "typeof layoutXSpin" not in sync
    assert "layoutXSpin.value" not in sync


def test_spinbox_text_kept_between_indicators():
    # The editor must not slide under the -/+ buttons nor steal their clicks.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    spinbox = source[
        source.index("component StyledSpinBox") : source.index("component ResizeHandle")
    ]
    assert "anchors.leftMargin: 37" in spinbox
    assert "anchors.rightMargin: 37" in spinbox


def test_layout_url_binding_tracks_server_base():
    # Slot calls never re-evaluate: the binding must also read the reactive
    # overlayBaseUrl property so the URL appears once the server starts.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "api.overlayBaseUrl" in source
    assert "api.layoutOverlayUrl(root.activeLayoutId" in source


def test_layout_editor_uses_l10n_not_hardcoded_strings():
    # The canvas editor must go through root.loc() (navApi -> l10n.py) so
    # UI locale switching applies. No hardcoded Cyrillic literals allowed
    # in the editor section (single letters X/Y/W/H and symbols excepted).
    import re

    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    editor = source[source.index("id: layoutCanvasViewport") : source.index("// Bottom Panel: Canvas Settings")]
    hardcoded = [
        m for m in re.findall(r'(?:text|placeholderText|toolTipText|title): "([^"]+)"', editor)
        if re.search(r"[А-Яа-яІіЇїЄєҐґ]", m) and m not in ("X", "Y", "W", "H")
    ]
    assert hardcoded == []


def test_layout_editor_loc_keys_exist_in_l10n():
    import re

    from stream_cheremsha import l10n

    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    keys = set(re.findall(r'root\.loc\("(widgets\.layouts\.editor\.[a-z_]+)"\)', source))
    assert keys, "expected editor loc keys"
    for key in sorted(keys):
        row = l10n._TABLE.get(key)
        assert row is not None, f"missing l10n key: {key}"
        assert row.get("uk") and row.get("en"), f"key needs uk+en: {key}"


def test_layer_moves_keep_z_index_in_sync_with_array_order():
    # OBS export sorts by z_index while the canvas stacks by array index:
    # every array mutation must renumber z_index to the position.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "function _renumberLayoutZ(items)" in source
    for fn in ("function moveWidgetLayer", "function addLayoutWidget", "function removeSelectedLayoutWidget"):
        body = source[source.index(fn): source.index(fn) + 2500]
        assert "_renumberLayoutZ" in body, fn


def test_layers_list_shows_front_layer_on_top():
    # Array order is back-to-front, so the visible list must be reversed
    # and row actions must address the real array index.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert ".slice().reverse()" in source
    assert "property int realIndex" in source
    # "Move up" brings forward (toward array end = higher z).
    assert "root.moveWidgetLayer(realIndex, realIndex + 1)" in source
    assert "root.moveWidgetLayer(realIndex, realIndex - 1)" in source


def test_layout_preview_uses_explicit_z_index_check():
    # `z_index || index` silently drops a stored 0; must distinguish missing.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "modelData.z_index !== undefined ? Number(modelData.z_index) : index" in source
    assert "Number(modelData.z_index || index)" not in source


def test_fit_to_content_changes_viewport_only():
    # Fit must adjust zoom + camera pan, never widget geometry.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    fit = source[source.index("function fitToContent") : source.index("// Snapping calculation for moving")]
    assert "setLayoutCanvasZoom" in fit
    assert "layoutCanvasPanX" in fit
    assert "layoutCanvasPanY" in fit
    for forbidden in ("item.x =", "item.y =", "item.width =", "commitWidgetGeometry"):
        assert forbidden not in fit
    # Empty canvas: no division by zero, reset to default view.
    assert "setLayoutCanvasZoom(1.0)" in fit


def test_grid_config_is_centralized():
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "property int layoutGridSize: 16" in source
    assert "property bool layoutGridSnapEnabled" in source
    assert "function snapCanvasToGrid" in source
    assert "function gridSnapActive" in source


def test_grid_snap_uses_canvas_coordinates():
    # Snap must round in canvas space; screen scale only affects rendering.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    snap = source[source.index("function snapCanvasToGrid") : source.index("function gridSnapActive")]
    assert "layoutGridSize" in snap
    assert "editorScale" not in snap
    # Applied to both move and resize paths.
    assert source.count("snapCanvasToGrid") >= 5


def test_resize_grid_snap_preserves_minimums():
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "function snapGridSize(value, minimum)" in source
    assert "snapGridSize(nextW, 32)" in source
    assert "snapGridSize(nextH, 24)" in source


def test_grid_is_editor_only_layer():
    # Grid Canvas lives inside layoutCanvas (moves/scales with it) and is
    # never referenced by save/export paths.
    source = WIDGETS_VIEW.read_text(encoding="utf-8")
    assert "id: editorGridCanvas" in source
    grid = source[source.index("id: editorGridCanvas") : source.index("// Canvas background click")]
    # Both minor and major paths must actually be stroked; a beginPath
    # without stroke() renders nothing.
    assert grid.count("ctx.stroke()") >= 2
    save = source[source.index("function saveLayoutEditor") : source.index("function updateLayoutItemStr")]
    assert "editorGridCanvas" not in save
    assert "layoutCanvasGridVisible" not in save
