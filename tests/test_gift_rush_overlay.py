"""Tests for the ``gift_rush`` overlay type.

Verifies that the rendered HTML contains the VFX layer anchors and that the
inline JS contains all required functions/identifiers and does NOT use forbidden
techniques (requestAnimationFrame, canvas, WebEngine, per-frame timers).

Mirrors the structural pattern of ``test_battle_overlay_event_reactions.py``.
"""

from __future__ import annotations

import re

from stream_cheremsha.overlays.gift_rush_overlay import GiftRushOverlayType


def _render(params=None):
    """Render the gift-rush overlay and return (html, script_body)."""
    o = GiftRushOverlayType()
    html = o.render_html(params or {"instance": "test"})
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = m.group(1) if m else ""
    return html, script


def test_html_transparent_root() -> None:
    html, _ = _render()
    assert "background: transparent" in html
    # The root must be transparent — the stream must show through.
    assert "transparent" in html


def test_html_starts_with_doctype() -> None:
    html, _ = _render()
    assert html.strip().startswith("<!doctype")
    assert "</html>" in html


def test_html_contains_root_layer() -> None:
    html, _ = _render()
    assert 'id="grRoot"' in html


def test_html_contains_camera_layer() -> None:
    html, _ = _render()
    assert 'id="grCam"' in html


def test_html_contains_burst_layer() -> None:
    html, _ = _render()
    assert 'id="grLayer"' in html
    assert 'id="grBurst"' in html


def test_html_contains_popup_layer() -> None:
    html, _ = _render()
    assert 'id="grPopup"' in html


def test_js_no_request_animation_frame() -> None:
    _, script = _render()
    assert "requestAnimationFrame" not in script


def test_js_no_canvas() -> None:
    _, script = _render()
    assert "canvas" not in script


def test_js_no_webengine() -> None:
    _, script = _render()
    assert "WebEngine" not in script


def test_js_no_setinterval() -> None:
    """No per-frame JS loops; cleanup is via animationend + bounded timeouts."""
    _, script = _render()
    assert "setInterval" not in script


def test_js_contains_offset_path() -> None:
    _, script = _render()
    assert "offset-path" in script
    assert "offset-distance" in script


def test_js_contains_process_events() -> None:
    _, script = _render()
    assert "processEvents" in script


def test_js_contains_spawn_gift() -> None:
    _, script = _render()
    assert "spawnGift" in script


def test_js_contains_spawn_projectile() -> None:
    _, script = _render()
    assert "spawnProjectile" in script


def test_js_pool_caps_present() -> None:
    _, script = _render()
    assert "MAX_PROJECTILES" in script
    assert "MAX_COINS" in script
    assert "MAX_SPARKS" in script
    assert "MAX_RIBBONS" in script


def test_js_pool_caps_values() -> None:
    _, script = _render()
    assert "const MAX_PROJECTILES = 12" in script
    assert "const MAX_COINS = 24" in script
    assert "const MAX_SPARKS = 24" in script
    assert "const MAX_RIBBONS = 8" in script


def test_js_pool_onscreen_caps() -> None:
    _, script = _render()
    assert "MAX_COINS_ON_SCREEN" in script
    assert "MAX_SPARKS_ON_SCREEN" in script
    assert "MAX_RIBBONS_ON_SCREEN" in script


def test_js_active_event_cap_read_from_config() -> None:
    """The active-event ceiling must come from the config's
    max_simultaneous_events, clamped, not a hardcoded constant."""
    _, script = _render()
    assert "max_simultaneous_events" in script
    # clamped to the documented [4, 12] range
    assert "4, 12" in script


def test_js_last_seen_at_dedup() -> None:
    """JS mirrors battle: a lastSeenAt pointer dedupes by event `at`."""
    _, script = _render()
    assert "lastSeenAt" in script
    assert "0.0001" in script


def test_js_theme_classes_applied() -> None:
    _, script = _render()
    assert "gr-theme-cheremsha" in script
    assert "gr-theme-celebration" in script
    assert "gr-theme-arcade" in script


def test_css_theme_variable_blocks() -> None:
    """All three themes define their own --gr-* custom properties."""
    html, _ = _render()
    assert ".gr-theme-cheremsha" in html
    assert ".gr-theme-celebration" in html
    assert ".gr-theme-arcade" in html
    # each theme block defines the accent variables
    for token in ("--gr-acc1", "--gr-coin", "--gr-glow", "--gr-ribbon"):
        assert token in html


def test_css_theme_colors_distinct() -> None:
    """The three themes use different palette values."""
    html, _ = _render()
    assert "#22d3ee" in html  # cheremsha
    assert "#fde68a" in html  # celebration
    assert "#4ade80" in html  # arcade


def test_js_subscribe_message() -> None:
    _, script = _render()
    assert "subscribe" in script
    assert "gift_rush" in script


def test_js_embeds_instance() -> None:
    html, script = _render({"instance": "abc123"})
    assert "abc123" in script


def test_js_contains_impact_and_popups() -> None:
    _, script = _render()
    assert "spawnImpactRing" in script
    assert "spawnGlowFlash" in script
    assert "spawnCoins" in script
    assert "spawnRibbons" in script
    assert "spawnSparks" in script
    assert "spawnScorePopup" in script
    assert "spawnComboCounter" in script
    assert "spawnIntensityBadge" in script
    assert "flashCameraImpact" in script


def test_js_cleanup_on_animationend() -> None:
    _, script = _render()
    assert "animationend" in script
    assert "parentNode.removeChild" in script


def test_integrity_no_unbalanced_script_tags() -> None:
    html, _ = _render()
    # exactly one <script>...</script> block
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1


def test_rendered_html_has_single_braces_only() -> None:
    """Regression: template uses doubled braces but render must collapse them.

    A plain (non-f) string template shipped `{{`/`}}` verbatim, which is
    invalid CSS (rules dropped) and invalid JS (`return {{ x...}}` ->
    SyntaxError, whole page dead). Preview and by-id pages showed nothing.
    """
    html, _ = _render()
    assert "{{" not in html
    assert "}}" not in html


def test_svg_colors_use_style_not_presentation_attributes() -> None:
    """Regression: var() in fill=""/stroke="" attributes never resolves.

    Presentation attributes don't support var(), so the gift/coin/spark SVGs
    rendered black/invisible. Colors must go through style="...".
    """
    html, _ = _render()
    assert 'fill="var(' not in html
    assert 'stroke="var(' not in html


def test_projectile_anchored_at_origin_for_absolute_motion_path() -> None:
    """Regression: left/top at the start point double-offset the projectile.

    The offset-path already carries absolute coordinates, so anchoring the
    element at (sx, sy) pushed it up to 2x off-screen (hidden by overflow) —
    the fly-in icon was never seen while bursts/popups (absolute) worked.
    """
    _, script = _render()
    assert "el.style.left = '0px'" in script
    assert "el.style.top = '0px'" in script


def test_popup_stack_does_not_overlap() -> None:
    """Regression: score/sender/combo/badge shared one x with offsets smaller
    than their line heights, so every popup overlapped its neighbours (worse
    on EPIC sizes). Stack must be ordered badge < combo < value above the
    impact point with line-height clearance, sender below it."""
    _, script = _render()
    assert "(y - 52)" in script  # value
    assert "(y + 40)" in script  # sender, below impact
    assert "(y - 116)" in script  # combo
    assert "(y - 165)" in script  # badge


def test_sender_line_clamped_to_single_line() -> None:
    """Long nicknames must not wrap into the value popup above."""
    html, _ = _render()
    assert "text-overflow: ellipsis" in html
