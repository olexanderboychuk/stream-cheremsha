"""Tests for the ``battle`` overlay theme set.

Verifies that all nine themes are accepted by the config validator and that
the rendered HTML contains a ``data-theme`` CSS block for each of them.
"""

from __future__ import annotations

import pytest

from stream_cheremsha.overlays.battle_overlay import BattleOverlayType
from stream_cheremsha.overlays.battle_overlay_config import (
    BATTLE_THEMES,
    battle_overlay_config_from_json_text,
)

EXPECTED_THEMES = frozenset(
    {
        "cheremsha_neon",
        "cyber",
        "arcade",
        "minimal",
        "halloween",
        "anime",
        "glitch",
        "fantasy",
        "newyear",
    }
)


def test_theme_set_matches_expected() -> None:
    assert BATTLE_THEMES == EXPECTED_THEMES


@pytest.mark.parametrize("theme", sorted(EXPECTED_THEMES))
def test_theme_round_trip(theme: str) -> None:
    cfg = battle_overlay_config_from_json_text(f'{{"theme": "{theme}"}}')
    assert cfg.theme == theme


@pytest.mark.parametrize("theme", sorted(EXPECTED_THEMES))
def test_theme_case_insensitive(theme: str) -> None:
    cfg = battle_overlay_config_from_json_text(f'{{"theme": "{theme.upper()}"}}')
    assert cfg.theme == theme


@pytest.mark.parametrize("theme", sorted(EXPECTED_THEMES))
def test_html_contains_data_theme_block(theme: str) -> None:
    html = BattleOverlayType().render_html({"instance": "test"})
    assert f'data-theme="{theme}"' in html
