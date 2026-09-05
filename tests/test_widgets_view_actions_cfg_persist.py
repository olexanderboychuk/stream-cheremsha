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
    Path(__file__).resolve().parents[1]
    / "src"
    / "stream_cheremsha"
    / "qml"
    / "WidgetsView.qml"
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
    text = _widgets_view_text()
    load_idx = text.find("root.cfg = root._ensureDefaults")
    assert load_idx >= 0
    window = text[load_idx : load_idx + 1500]
    assert "_syncChatCombosFromCfg" in window
    assert "function _syncChatCombosFromCfg" in text
    sync = text[text.find("function _syncChatCombosFromCfg") :]
    assert "usernameColorMode" in sync
    assert "fontFamily" in sync


def test_actions_font_and_effect_combos_resync_after_load() -> None:
    text = _widgets_view_text()
    # After loadActionsConfigMap assignment, combos must be synced (not only onCompleted).
    load_idx = text.find("root.actionsCfg = root._ensureActionsDefaults")
    assert load_idx >= 0
    window = text[load_idx : load_idx + 1200]
    assert "_syncActionsCombosFromCfg" in window
    assert "function _syncActionsCombosFromCfg" in text
    assert "actionsFontFamily" in text[text.find("function _syncActionsCombosFromCfg") :]
    assert "actionsUsernameEffect" in text[text.find("function _syncActionsCombosFromCfg") :]


def test_varmap_spinbox_persists_signal_system_group() -> None:
    text = _widgets_view_text()
    # syncGroup "signal_system" is used in settings; VarMapSpinBox must persist it.
    assert 'syncGroup: "signal_system"' in text
    assert re.search(
        r'if\s*\(\s*vsb\.syncGroup\s*===\s*"signal_system"\s*\)\s*'
        r"return\s+root\._loadingSignalSystemCfg",
        text,
    )
    assert re.search(
        r'else if\s*\(\s*vsb\.syncGroup\s*===\s*"signal_system"\s*\)\s*'
        r"root\._saveSignalSystem\(\)",
        text,
    )
