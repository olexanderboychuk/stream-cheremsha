from __future__ import annotations

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.social_rotator_overlay import SocialRotatorOverlayType


def test_overlay_renderer_and_registry() -> None:
    overlay = SocialRotatorOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "Social Rotator" in html or "LIVE SOCIAL" in html
    assert "hud-frame" in html
    assert "hero-icon" in html
    assert "next-box" in html
    assert "secondary" in html
    assert "panel-stats" in html
    assert "orbit-ring" in html
    assert "glitch_morph" in html
    assert "playTransition" in html
    assert "transition_token" in html
    assert "--sr-widget-scale" in html
    assert "Press+Start+2P" in html
    assert "VT323" in html
    assert "transform: scale(var(--sr-widget-scale))" not in html
    st = overlay.initial_state({"instance": "main"})
    assert "config" in st
    assert "rotation" in st
    assert "stats" in st
    reg = OverlayRegistry()
    assert reg.get("social_rotator").type == "social_rotator"


def test_registry_has_social_rotator_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("social_rotator")
    assert t.type == "social_rotator"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
