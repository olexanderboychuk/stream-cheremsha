"""Regression: every WidgetsView settings control must use a live save path.

Catches:
- StyledComboBox settings that only listen to dead C++ onActivated
- VarMapSpinBox syncGroup values that are not wired in loading/persist/pull
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_WIDGETS_VIEW = (
    Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml" / "WidgetsView.qml"
)


@pytest.fixture(scope="module")
def qml_text() -> str:
    return _WIDGETS_VIEW.read_text(encoding="utf-8")


def _extract_brace_block(text: str, start: int) -> str:
    i = text.find("{", start)
    assert i >= 0
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    raise AssertionError("unbalanced brace")


def _styled_combobox_component(text: str) -> str:
    start = text.find("component StyledComboBox: ComboBox {")
    assert start >= 0
    nxt = text.find("\n    component ", start + 1)
    assert nxt > start
    return text[start:nxt]


def test_styled_combobox_emits_user_activated_on_mouse_select(qml_text: str) -> None:
    block = _styled_combobox_component(qml_text)
    assert "signal userActivated(int index)" in block
    assert "onClicked:" in block
    assert "_emitUserActivated" in block


def test_every_settings_styled_combobox_uses_live_selection_signal(qml_text: str) -> None:
    """Combos that persist settings must use onUserActivated or onCurrentIndexChanged.

    Add-only pickers (no save in the combo itself) are excluded by name.
    """
    add_only_ids = {"llAddSource", "llAddScene", "srAddPlatform"}
    bad: list[str] = []
    for m in re.finditer(r"StyledComboBox\s*\{", qml_text):
        block = _extract_brace_block(qml_text, m.start())
        idm = re.search(r"\bid:\s*(\w+)", block)
        cid = idm.group(1) if idm else f"anon@{m.start()}"
        if cid in add_only_ids:
            continue
        # Canvas preset + stream pet preset call helpers; still need a live signal.
        live = ("onUserActivated:" in block) or ("onCurrentIndexChanged:" in block)
        if not live:
            bad.append(cid)
            continue
        # Must not rely solely on dead onActivated without userActivated/currentIndex.
        if (
            "onActivated:" in block
            and "onUserActivated:" not in block
            and "onCurrentIndexChanged:" not in block
        ):
            bad.append(f"{cid}:onActivated-only")
    assert bad == [], f"StyledComboBox settings missing live selection handler: {bad}"


def test_every_varmap_sync_group_is_fully_wired(qml_text: str) -> None:
    """Legacy VarMapSpinBox machinery is gone: no syncGroup usages may remain.

    Number settings are owned by the universal editor (WidgetEditorControl
    "number" type) which persists via settingChanged -> _saveAndApplyCurrentWidget.
    """
    assert "component VarMapSpinBox:" not in qml_text
    assert re.findall(r'syncGroup:\s*"([^"]+)"', qml_text) == []


def test_signal_system_settings_use_backend_config_keys(qml_text: str) -> None:
    """Signal System universal schema must bind to SignalSystemOverlayConfig field names."""
    start = qml_text.find('} else if (typeId === "signal_system")')
    assert start >= 0
    end = qml_text.find('if (typeId === "chat") advanced', start)
    assert end > start
    block = qml_text[start:end]

    # Wrong legacy keys that silently no-op against the Python schema.
    for bad in (
        "perimeter_idle_opacity",
        "perimeter_active_opacity",
        '"min_gift_coins"',
        "cooldown_seconds",
        "enable_milestones",
        "enable_activity_surge",
        "enable_ai_observations",
        "enable_unknown_signals",
    ):
        assert bad not in block, f"signal_system settings still use dead key {bad!r}"

    for good in (
        '"idle_opacity_pct"',
        '"active_opacity_pct"',
        '"min_gift_coins_for_event"',
        '"cooldown_ms"',
        '"scale_percent"',
        '"core_vertical_pct"',
        '"milestones_enabled"',
        '"activity_surge_enabled"',
        '"ai_observations_enabled"',
        '"unknown_signals_enabled"',
    ):
        assert good in block, f"signal_system settings missing live key {good!r}"
