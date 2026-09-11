"""Layout overlay URL must appear once the overlay server is up.

Regression: the Layout URL field stayed empty when the Layouts page loaded
before the overlay server started, because `layoutOverlayUrl()` is a Slot
and the QML binding had no reactive dependency. `overlayBaseUrl` (with
notify) gives the binding something to subscribe to.
"""

from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_layout_url_empty_before_server_start() -> None:
    api = WidgetsQmlApi()
    assert api.overlayBaseUrl == ""
    assert api.layoutOverlayUrl("test") == ""


def test_layout_url_available_after_base_applied() -> None:
    api = WidgetsQmlApi()
    api.set_overlay_base_url("http://127.0.0.1:17171")
    assert api.overlayBaseUrl == "http://127.0.0.1:17171"
    assert (
        api.layoutOverlayUrl("test")
        == "http://127.0.0.1:17171/overlay/layout?instance=main&layout=test"
    )


def test_base_change_emits_notify_for_qml_rebind() -> None:
    api = WidgetsQmlApi()
    seen: list[str] = []
    api.overlayBaseUrlChanged.connect(lambda: seen.append(api.overlayBaseUrl))
    api.set_overlay_base_url("http://127.0.0.1:17171")
    assert seen == ["http://127.0.0.1:17171"]
    # Same value must not spam the signal.
    api.set_overlay_base_url("http://127.0.0.1:17171/")
    assert seen == ["http://127.0.0.1:17171"]
