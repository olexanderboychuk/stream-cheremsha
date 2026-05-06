from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_online_overlay_url_empty_when_base_missing() -> None:
    api = WidgetsQmlApi(overlay_base_url="")
    assert api.onlineOverlayUrl() == ""


def test_online_overlay_url_value() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171")
    assert api.onlineOverlayUrl() == "http://127.0.0.1:17171/overlay/online?instance=main"


def test_system_font_families_from_os() -> None:
    api = WidgetsQmlApi()
    families = api.systemFontFamilies()
    assert isinstance(families, list)
    assert len(families) >= 4
    assert all(isinstance(x, str) and x.strip() for x in families)
