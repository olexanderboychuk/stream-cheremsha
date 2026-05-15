from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_top_likers_overlay_url_empty_when_base_missing() -> None:
    api = WidgetsQmlApi(overlay_base_url="")
    assert api.topLikersOverlayUrl() == ""


def test_top_likers_overlay_url_value() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171")
    assert api.topLikersOverlayUrl() == "http://127.0.0.1:17171/overlay/top_likers?instance=main"
