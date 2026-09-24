"""Tests for the ``battle`` overlay event reaction layer.

Verifies that the rendered HTML contains the new DOM anchors and that the
inline JS contains all required functions and does NOT use forbidden
techniques (requestAnimationFrame, canvas, WebEngine).
"""

from __future__ import annotations

import re

from stream_cheremsha.overlays.battle_overlay import BattleOverlayType


def _render(params=None):
    """Render the battle overlay and return (html, script_body)."""
    o = BattleOverlayType()
    html = o.render_html(params or {"instance": "test"})
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = m.group(1) if m else ""
    return html, script


def test_html_contains_projectile_layer() -> None:
    html, _ = _render()
    assert "btProjectileLayer" in html


def test_html_contains_impact_container() -> None:
    html, _ = _render()
    assert "btImpactLayer" in html


def test_html_contains_lead_badge() -> None:
    html, _ = _render()
    assert "btLeadBadge" in html


def test_html_contains_round_badge() -> None:
    html, _ = _render()
    assert "btRoundBadge" in html


def test_js_contains_spawn_projectile() -> None:
    _, script = _render()
    assert "spawnProjectile" in script


def test_js_contains_max_projectiles_cap() -> None:
    _, script = _render()
    assert "MAX_PROJECTILES" in script


def test_js_max_projectiles_is_eight() -> None:
    _, script = _render()
    assert "const MAX_PROJECTILES = 8" in script


def test_js_contains_get_intensity() -> None:
    _, script = _render()
    assert "getIntensity" in script


def test_js_contains_flash_lead_change() -> None:
    _, script = _render()
    assert "flashLeadChange" in script


def test_js_contains_flash_round() -> None:
    _, script = _render()
    assert "flashRound" in script


def test_js_contains_trigger_comeback_enhance() -> None:
    _, script = _render()
    assert "triggerComebackEnhance" in script


def test_js_contains_trigger_final_push_enhance() -> None:
    _, script = _render()
    assert "triggerFinalPushEnhance" in script


def test_js_contains_show_battle_winner_enhance() -> None:
    _, script = _render()
    assert "showBattleWinnerEnhance" in script


def test_js_no_request_animation_frame() -> None:
    _, script = _render()
    assert "requestAnimationFrame" not in script


def test_js_no_canvas() -> None:
    _, script = _render()
    assert "canvas" not in script


def test_js_no_webengine() -> None:
    _, script = _render()
    assert "WebEngine" not in script


def test_js_contains_offset_path() -> None:
    _, script = _render()
    assert "offset-path" in script
