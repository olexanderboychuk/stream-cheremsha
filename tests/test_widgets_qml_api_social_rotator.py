from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_widgets_api_social_rotator_url_and_config() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=None)
    assert (
        api.socialRotatorOverlayUrl()
        == "http://127.0.0.1:17171/overlay/social_rotator?instance=main"
    )
    cfg = api.loadSocialRotatorOverlayConfigMap()
    assert cfg["enabled"] is True
    assert isinstance(cfg["platforms"], list)
    assert cfg["transition"] == "glitch_morph"
