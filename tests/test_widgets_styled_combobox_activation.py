"""StyledComboBox must notify listeners on mouse selection.

Custom delegates do not emit C++ ComboBox.activated; settings that only use
onActivated never save (e.g. Actions username_text_effect).
"""

from __future__ import annotations

from pathlib import Path

_WIDGETS_VIEW = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "stream_cheremsha"
    / "qml"
    / "WidgetsView.qml"
)


def _styled_combobox_block() -> str:
    text = _WIDGETS_VIEW.read_text(encoding="utf-8")
    start = text.find("component StyledComboBox: ComboBox {")
    assert start >= 0, "StyledComboBox component missing"
    nxt = text.find("\n    component ", start + 1)
    assert nxt > start
    return text[start:nxt]


def test_styled_combobox_emits_user_activated_from_delegate_click() -> None:
    block = _styled_combobox_block()
    assert "signal userActivated(int index)" in block
    assert "_emitUserActivated" in block
    assert "onClicked:" in block
    assert "cb._emitUserActivated(index)" in block


def test_actions_username_effect_listens_for_user_activated() -> None:
    text = _WIDGETS_VIEW.read_text(encoding="utf-8")
    idx = text.find("id: actionsUsernameEffect")
    assert idx >= 0
    window = text[idx : idx + 900]
    assert "onUserActivated:" in window
    assert "username_text_effect" in window
    assert "_saveActions" in window
