from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_stream_info_qml_api_roundtrip() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=None)
    assert hasattr(WidgetsQmlApi, "loadStreamInfoOverlayConfigMap")
    assert hasattr(WidgetsQmlApi, "saveStreamInfoOverlayConfigJson")
    assert hasattr(WidgetsQmlApi, "previewStreamInfoOverlay")
    assert hasattr(WidgetsQmlApi, "streamInfoOverlayUrl")
    assert (
        api.streamInfoOverlayUrl()
        == "http://127.0.0.1:17171/overlay/stream_info?instance=main"
    )
    cfg = api.loadStreamInfoOverlayConfigMap()
    assert cfg["enabled"] is True
    assert cfg["theme"] == "neon_cyber"
