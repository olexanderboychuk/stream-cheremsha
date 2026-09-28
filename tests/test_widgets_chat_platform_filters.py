"""Regression: chat widget editor must expose per-platform message filters.

The overlay JS skips messages whose platform flag is disabled in the config,
so the universal schema (and defaults-filling) must bind the same keys or the
setting would be invisible to users.
"""

from __future__ import annotations

import re
from pathlib import Path

_WIDGETS_VIEW = Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha/qml/WidgetsView.qml"

_PLATFORM_KEYS = (
    "platform_twitch_enabled",
    "platform_youtube_enabled",
    "platform_tiktok_enabled",
    "platform_kick_enabled",
)


def _qml_text() -> str:
    return _WIDGETS_VIEW.read_text(encoding="utf-8")


def test_chat_universal_schema_exposes_platform_filters() -> None:
    text = _qml_text()
    start = text.find('if (typeId === "chat") {')
    assert start >= 0, "chat branch of universalSchema not found"
    end = text.find('} else if (typeId === "actions")', start)
    assert end > start
    block = text[start:end]
    for key in _PLATFORM_KEYS:
        pattern = rf'c\("[^"]+", "{key}", "toggle"'
        assert re.search(pattern, block), f"chat schema missing toggle control {key}"


def test_chat_ensure_defaults_fills_platform_filters() -> None:
    text = _qml_text()
    start = text.find("function _ensureDefaults(obj)")
    assert start >= 0, "_ensureDefaults not found"
    end = text.find("function _clamp01", start)
    assert end > start
    block = text[start:end]
    for key in _PLATFORM_KEYS:
        assert f"obj.{key} === undefined" in block, (
            f"_ensureDefaults does not fill default for {key}"
        )
