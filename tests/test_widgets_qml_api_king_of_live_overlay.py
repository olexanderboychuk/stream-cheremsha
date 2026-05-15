from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_king_of_live_overlay_url_empty_when_base_missing() -> None:
    api = WidgetsQmlApi(overlay_base_url="", pubsub=OverlayPubSub())
    assert api.kingOfLiveOverlayUrl() == ""


def test_king_of_live_overlay_url_value() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=OverlayPubSub())
    assert api.kingOfLiveOverlayUrl() == "http://127.0.0.1:17171/overlay/king_of_live?instance=main"
