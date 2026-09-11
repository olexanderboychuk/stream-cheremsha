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
