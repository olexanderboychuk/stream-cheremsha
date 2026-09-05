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
    Path(__file__).resolve().parents[1]
    / "src"
    / "stream_cheremsha"
    / "qml"
    / "WidgetsView.qml"
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
        if "onActivated:" in block and "onUserActivated:" not in block and "onCurrentIndexChanged:" not in block:
            bad.append(f"{cid}:onActivated-only")
    assert bad == [], f"StyledComboBox settings missing live selection handler: {bad}"


def test_every_varmap_sync_group_is_fully_wired(qml_text: str) -> None:
    used = sorted(set(re.findall(r'syncGroup:\s*"([^"]+)"', qml_text)))
    assert used, "expected VarMapSpinBox syncGroups"

    persist_m = re.search(r"function _persist\(\)\s*\{(.*?)\n        \}", qml_text, re.S)
    load_m = re.search(r"function _loadingForGroup\(\)\s*\{(.*?)\n        \}", qml_text, re.S)
    assert persist_m and load_m
    persist_body = persist_m.group(1)
    load_body = load_m.group(1)

    # Connections pull handlers live in the VarMapSpinBox component Connections block.
    missing_load: list[str] = []
    missing_persist: list[str] = []
    missing_pull: list[str] = []
    for g in used:
        if f'syncGroup === "{g}"' not in load_body:
            missing_load.append(g)
        if f'syncGroup === "{g}"' not in persist_body:
            missing_persist.append(g)
        # Epoch and/or Changed pull
        epoch_pat = re.compile(
            rf"function on\w+CfgEpochChanged\(\)\s*\{{[^}}]*syncGroup === \"{re.escape(g)}\"",
            re.S,
        )
        changed_pat = re.compile(
            rf"function on\w+CfgChanged\(\)\s*\{{[^}}]*syncGroup === \"{g}\"",
            re.S,
        )
        # battle/tier/king naming variants
        if not (epoch_pat.search(qml_text) or changed_pat.search(qml_text)):
            # also accept explicit syncGroup check near epoch
            if f'syncGroup === "{g}"' not in qml_text[qml_text.find("Connections {") :]:
                missing_pull.append(g)
            else:
                # Count occurrences in Connections section of VarMapSpinBox
                vsb_start = qml_text.find("component VarMapSpinBox:")
                vsb_end = qml_text.find("\n    property var cfg:", vsb_start)
                vsb = qml_text[vsb_start:vsb_end]
                if vsb.count(f'syncGroup === "{g}"') < 3:
                    # loading + persist are outside Connections; need >=1 pull mention in Connections
                    conn = vsb[vsb.find("Connections {") :]
                    if f'syncGroup === "{g}"' not in conn:
                        missing_pull.append(g)

    assert missing_load == [], f"VarMapSpinBox missing loading wiring: {missing_load}"
    assert missing_persist == [], f"VarMapSpinBox missing persist wiring: {missing_persist}"
    assert missing_pull == [], f"VarMapSpinBox missing pull Connections: {missing_pull}"


def test_signal_system_settings_use_backend_config_keys(qml_text: str) -> None:
    """Signal System UI must bind to SignalSystemOverlayConfig field names."""
    start = qml_text.find("id: signalSystemSettings")
    assert start >= 0
    end = qml_text.find("} // signalSystemSettings", start)
    assert end > start
    block = qml_text[start:end]

    # Wrong legacy keys that silently no-op against the Python schema.
    for bad in (
        'hostKey: "perimeter_idle_opacity"',
        'hostKey: "perimeter_active_opacity"',
        'hostKey: "min_gift_coins"',
        'hostKey: "cooldown_seconds"',
        "enable_milestones",
        "enable_activity_surge",
        "enable_ai_observations",
        "enable_unknown_signals",
    ):
        assert bad not in block, f"signal_system settings still use dead key {bad!r}"

    for good in (
        'hostKey: "idle_opacity_pct"',
        'hostKey: "active_opacity_pct"',
        'hostKey: "min_gift_coins_for_event"',
        'hostKey: "cooldown_ms"',
        'hostKey: "scale_percent"',
        'hostKey: "core_vertical_pct"',
        "milestones_enabled",
        "activity_surge_enabled",
        "ai_observations_enabled",
        "unknown_signals_enabled",
    ):
        assert good in block, f"signal_system settings missing live key {good!r}"
