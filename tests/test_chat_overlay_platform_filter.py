from stream_cheremsha.overlays.chat_overlay import ChatOverlayType


def test_chat_overlay_html_filters_messages_by_platform() -> None:
    html = ChatOverlayType().render_html({"instance": "main"})
    # Helper that resolves the per-platform config flag (missing key => allowed).
    assert "function platformAllowed(" in html
    # Append path must skip messages from disabled platforms.
    assert "if (!platformAllowed(it.platform)) return;" in html
    # Config changes and initial state must drop buffered items of disabled platforms.
    assert html.count("items = items.filter(x => platformAllowed(x.platform));") >= 2
