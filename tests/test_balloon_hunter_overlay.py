"""Tests for the ``balloon_hunter`` overlay type.

Verifies transparent Canvas rendering, balloon/particle pool identifiers,
pop-event handling keyed by ``target_balloon_kind``, and registry wiring.
"""

from __future__ import annotations

import re

from stream_cheremsha.overlays.balloon_hunter_overlay import BalloonHunterOverlayType


def _render(params=None):
    o = BalloonHunterOverlayType()
    html = o.render_html(params or {"instance": "test"})
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = m.group(1) if m else ""
    return html, script


def test_type_id() -> None:
    assert BalloonHunterOverlayType.type == "balloon_hunter"


def test_html_transparent() -> None:
    html, _ = _render()
    assert html.strip().startswith("<!doctype")
    assert "background: transparent" in html
    assert "</html>" in html


def test_html_has_canvas() -> None:
    html, _ = _render()
    assert 'id="bhCanvas"' in html
    assert "<canvas" in html


def test_js_uses_canvas_pool_and_raf() -> None:
    _, script = _render()
    # Ambient motion is a local rAF Canvas loop (no WS polling).
    assert "requestAnimationFrame" in script
    assert "balloons" in script
    assert "particles" in script
    assert "maxParticles" in script


def test_js_matches_balloon_kind() -> None:
    _, script = _render()
    assert "target_balloon_kind" in script
    assert "findBalloon" in script
    assert "EPIC" in script
    assert "GOLD" in script
    assert "NORMAL" in script


def test_js_matches_exact_gift_first() -> None:
    _, script = _render()
    # Strict matching only: the balloon showing the gifted item pops,
    # otherwise nothing happens — no fallbacks of any kind.
    assert "findBalloonByGift" in script
    assert "morphBalloonToGift" not in script
    assert "|| findBalloon(" not in script
    assert "giftKey" in script


def test_js_backfills_prespawned_balloons() -> None:
    _, script = _render()
    # Boot balloons spawn before the catalog arrives; they must be dressed
    # once it lands instead of staying generic forever.
    assert "backfillBalloonGifts" in script
    assert "dressBalloon" in script


def test_js_homing_projectile_delivers_pop() -> None:
    _, script = _render()
    # The pop is delivered by a homing projectile, not an instant burst.
    assert "fireProjectile" in script
    assert "stepProjectiles" in script
    assert "drawProjectile" in script
    assert "popBalloon" in script
    assert "PROJECTILE_FLIGHT_MS" in script


def test_js_exiting_locked_target_detonates_at_edge() -> None:
    _, script = _render()
    # A reserved balloon that floats off-screen mid-flight must detonate at
    # the visible edge (gift not lost); plain off-screen balloons just respawn.
    assert "detonateExitingTarget" in script


def test_js_balloons_carry_catalog_gifts() -> None:
    _, script = _render()
    assert "pickGift" in script
    assert "recentGifts" in script
    assert "learnGift" in script
    assert "kindForPrice" in script


def test_js_spawn_rarity_tiers() -> None:
    _, script = _render()
    # Five price tiers with fixed weights: cheap spawns often, legendary rarely.
    assert "TIER_WEIGHTS" in script
    assert "45, 25, 17, 9, 4" in script
    assert "tierBounds" in script
    assert "tierIndexForPrice" in script
    assert "LEGENDARY!" in script
    assert "legendary" in script


def test_js_applies_catalog_once() -> None:
    _, script = _render()
    assert "state.catalog" in script


def test_js_draws_gift_icon_inside_balloon() -> None:
    _, script = _render()
    assert "prefetchIcon" in script
    assert "drawImage" in script
    assert "clip()" in script


def test_js_subscribes_correct_topic() -> None:
    _, script = _render()
    assert "balloon_hunter" in script
    assert "/ws" in script


def test_instance_injected_safely() -> None:
    html, _ = _render({"instance": "my-id"})
    assert '"my-id"' in html
    assert "__BH_INSTANCE__" not in html


def test_initial_state_shape() -> None:
    o = BalloonHunterOverlayType()
    state = o.initial_state({"instance": "test"})
    assert set(state) == {"config", "locale", "events", "catalog"}
    assert state["events"] == []
    assert state["config"]["balloon_count"] == 8


def test_initial_state_catalog_has_gift_icons() -> None:
    o = BalloonHunterOverlayType()
    state = o.initial_state({"instance": "test"})
    catalog = state["catalog"]
    assert len(catalog) > 100
    sample = catalog[0]
    assert set(sample) == {"id", "n", "p", "u"}
    assert sample["n"]
    assert sample["u"].startswith("https://")
    assert all(g["u"].startswith("https://") for g in catalog)


def test_catalog_spans_all_spawn_tiers() -> None:
    """Every rarity tier pool must be non-empty with default thresholds."""
    o = BalloonHunterOverlayType()
    catalog = o.initial_state({"instance": "test"})["catalog"]
    prices = [g["p"] for g in catalog]
    assert any(p < 10 for p in prices)  # common
    assert any(10 <= p < 50 for p in prices)  # uncommon
    assert any(50 <= p < 200 for p in prices)  # rare / GOLD
    assert any(200 <= p < 1000 for p in prices)  # epic
    assert any(p >= 1000 for p in prices)  # legendary


def test_registered_in_registry() -> None:
    from stream_cheremsha.overlays.registry import OverlayRegistry

    reg = OverlayRegistry()
    assert "balloon_hunter" in reg.registered_types()
    assert reg.get("balloon_hunter").type == "balloon_hunter"


def test_whitelisted_for_layouts_and_instances() -> None:
    from stream_cheremsha.overlays.layout import SUPPORTED_LAYOUT_WIDGETS
    from stream_cheremsha.overlays.widget_instances import (
        WIDGET_TYPES,
        default_settings_for,
    )

    assert "balloon_hunter" in SUPPORTED_LAYOUT_WIDGETS
    assert "balloon_hunter" in WIDGET_TYPES
    defaults = default_settings_for("balloon_hunter")
    assert defaults.get("balloon_count") == 8
