from stream_cheremsha.overlays.registry import OverlayRegistry


def test_registry_has_community_world_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("community_world")
    assert t.type == "community_world"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    assert "Community World" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "quests" in st
    assert "buildings" in st
    assert "level" in st
    assert st["level"] == 1


def test_community_world_html_is_safe_on_bad_instance() -> None:
    reg = OverlayRegistry()
    t = reg.get("community_world")
    html = t.render_html({"instance": "</script><script>alert(1)</script>"})
    assert html.lower().count("</script>") == 1


def test_community_world_initial_state_valid_json_embed() -> None:
    reg = OverlayRegistry()
    t = reg.get("community_world")
    html = t.render_html({"instance": "main"})
    # The subscribe payload embedded in JS must be present and well-formed.
    assert '"op": "subscribe"' in html
    assert '"type": "community_world"' in html
    assert '"instance": "main"' in html
    assert 'const subscribeMsg = {"op": "subscribe"' in html


def test_community_world_themes_defined_in_html() -> None:
    reg = OverlayRegistry()
    t = reg.get("community_world")
    html = t.render_html({"instance": "main"})
    for theme in ("theme-ukrainian", "theme-pixel", "theme-fantasy", "theme-cyber"):
        assert theme in html
    for var in ("--sky1", "--sky2", "--ground1", "--ground2", "--cloud"):
        assert var in html
    assert "layout-compact" in html
    assert "layout_mode" in html