"""Guardrails: Actions overlay settings must detach QVariantMap and re-sync UI after load.

QML load*ConfigMap() returns engine-owned QVariantMaps. Mutating keys that were missing
from the saved blob (filled in by _ensure*Defaults) often does not round-trip through
save*ConfigMap(toVariant()). Newer overlays clone via JSON.parse(JSON.stringify(...));
Actions must do the same. ComboBoxes that only sync in Component.onCompleted miss values
loaded asynchronously afterward.
"""

from __future__ import annotations

import re
from pathlib import Path

_WIDGETS_VIEW = (
    Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml" / "WidgetsView.qml"
)


def _widgets_view_text() -> str:
    return _WIDGETS_VIEW.read_text(encoding="utf-8")


def test_actions_cfg_load_detaches_variant_map() -> None:
    text = _widgets_view_text()
    # Must clone before/while assigning actionsCfg (not assign raw load map).
    assert re.search(
        r"root\.actionsCfg\s*=\s*root\._ensureActionsDefaults\(\s*"
        r"(?:root\._detach(?:TierOverlay)?CfgMap|JSON\.parse\(\s*JSON\.stringify)",
        text,
    ), "actionsCfg must be detached from QVariantMap before use"


def test_chat_cfg_load_detaches_variant_map() -> None:
    text = _widgets_view_text()
    assert re.search(
        r"root\.cfg\s*=\s*root\._ensureDefaults\(\s*"
        r"(?:root\._detach(?:TierOverlay)?CfgMap|JSON\.parse\(\s*JSON\.stringify)",
        text,
    ), "chat cfg must be detached from QVariantMap before use"


def test_online_cfg_load_detaches_variant_map() -> None:
    text = _widgets_view_text()
    assert re.search(
        r"root\.onlineCfg\s*=\s*root\._ensureOnlineDefaults\(\s*"
        r"(?:root\._detach(?:TierOverlay)?CfgMap|JSON\.parse\(\s*JSON\.stringify)",
        text,
    ), "onlineCfg must be detached from QVariantMap before use"


def test_chat_combos_resync_after_load() -> None:
    """Chat combos live in the universal editor now: schema must expose them."""
    text = _widgets_view_text()
    start = text.find('if (typeId === "chat")')
    assert start >= 0
    end = text.find('} else if (typeId === "actions")', start)
    block = text[start:end]
    for key in ('"username_color_mode"', '"font_family"', '"show_platform_icon"'):
        assert key in block, f"chat universal schema missing {key}"


def test_actions_font_and_effect_combos_resync_after_load() -> None:
    """Actions font/effect selects live in the universal editor now."""
    text = _widgets_view_text()
    start = text.find('} else if (typeId === "actions")')
    assert start >= 0
    end = text.find('} else if (typeId === "online")', start)
    block = text[start:end]
    for key in ('"font_family"', '"username_text_effect"', '"platform_icon_size_px"'):
        assert key in block, f"actions universal schema missing {key}"


def test_varmap_spinbox_persists_signal_system_group() -> None:
    """Number settings persist via the universal editor save path (no VarMapSpinBox)."""
    text = _widgets_view_text()
    assert "component VarMapSpinBox:" not in text
    assert "syncGroup:" not in text
    assert "function onSettingChanged(field, value) { root.applyUniversalSetting(field, value) }" in text
    assert "universalPreviewSaveDebounce" in text
