from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_actions_overlay_url_empty_when_base_missing() -> None:
    api = WidgetsQmlApi(overlay_base_url="")
    assert api.actionsOverlayUrl() == ""


def test_actions_overlay_url_value() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171")
    assert api.actionsOverlayUrl() == "http://127.0.0.1:17171/overlay/actions?instance=main"
