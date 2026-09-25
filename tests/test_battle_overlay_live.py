"""Tests for the locked battle composition + live event layer.

Verifies the static corrections (single round label, symmetric score labels)
and the live visualization system (CTA rotation, score floats, intensity
tiers, winner/loser states) in the rendered HTML/JS.
"""

from __future__ import annotations

import re

from stream_cheremsha.overlays.battle_overlay import BattleOverlayType


def _render(params=None):
    o = BattleOverlayType()
    html = o.render_html(params or {"instance": "test"})
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    return html, (m.group(1) if m else "")


def _info_order(html: str, side: str) -> list[str]:
    m = re.search(
        r'<div class="bt-side bt-side--' + side + r'".*?'
        r'<div class="bt-participant-info">(.*?)</div>\s*</div>',
        html,
        re.DOTALL,
    )
    assert m, f"participant info missing for {side}"
    block = m.group(1)
    order = []
    for cls in re.findall(r'<div class="([a-z-]+)', block):
        if cls in ("bt-name", "bt-score-label", "bt-score", "bt-score-float", "bt-combo"):
            order.append(cls)
    return order


def test_single_round_label_no_title_sub() -> None:
    html, _ = _render()
    assert "btTitleSub" not in html
    assert 'id="btTitle"' in html
    assert 'id="btRound"' in html


def test_score_labels_symmetric() -> None:
    html, _ = _render()
    left = _info_order(html, "left")
    right = _info_order(html, "right")
    assert left == right
    assert left == ["bt-name", "bt-score-label", "bt-score", "bt-score-float", "bt-combo"]


def test_score_floats_present() -> None:
    html, script = _render()
    assert 'id="btFloatL"' in html
    assert 'id="btFloatR"' in html
    assert "spawnScoreFloat" in script
    assert "bt-score-float" in html


def test_cta_rotation_present() -> None:
    _, script = _render()
    assert "rotateCTA" in script
    assert "ctaPool" in script
    assert "holdCTA" in script
    assert "ctaRotateTimer" in script
    assert "setTimeout(rotateCTA, 5000)" in script


def test_cta_pools_localized() -> None:
    html, _ = _render()
    assert "Підтримай свою сторону" in html
    assert "Support your side" in html
    assert "Надішли подарунок — підніми рахунок" in html
    assert "Send a gift to boost your score" in html
    assert "ФІНАЛЬНИЙ РИВОК — ПІДТРИМАЙ СВОЇХ" in html
    assert "ВЕЛИКИЙ ПОДАРУНОК!" in html
    assert "BIG GIFT!" in html


def test_intensity_tiers() -> None:
    _, script = _render()
    assert "is-high" in script
    assert "is-big" in script
    assert "is-epic" in script
    assert "hitFill" in script
    assert "is-hit" in script


def test_winner_loser_states() -> None:
    html, script = _render()
    assert "is-winner" in script
    assert "is-loser" in script
    assert "is-winner" in html and "is-loser" in html


def test_bar_smooth_transition() -> None:
    html, _ = _render()
    assert "transition:width" in html


def test_scale_and_font_size_applied_live() -> None:
    """Scale/font-size must follow the live config like stream_goal's
    applyScale (editor changes arrive as config patches, not page reloads)."""
    html, script = _render()
    assert "--bt-font-k" in html
    assert "'--bt-u'" in script
    assert "'--bt-font-k'" in script
    assert "scale_percent" in script
    assert "base_font_size_px" in script


def test_js_no_forbidden_techniques() -> None:
    _, script = _render()
    assert "requestAnimationFrame" not in script
    assert "canvas" not in script.lower()
    assert "WebEngine" not in script


def test_round_dots_neutral_in_idle() -> None:
    """Current-round dots highlight only mid-battle; in idle all dots stay
    neutral so the widget doesn't look like rounds were already won."""
    _, script = _render()
    assert "inBattle" in script
