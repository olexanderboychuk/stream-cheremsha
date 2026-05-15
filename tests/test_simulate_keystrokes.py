from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from stream_cheremsha.actions.actions_simulate_keystrokes import (
    _all_interception_slots_with_hwid,
    _first_interception_slot_with_hwid,
    describe_unknown_tags,
    run_simulate_keystrokes,
    tokenize_keystroke_sequence,
)


def test_tokenize_mixed_text_and_tags() -> None:
    segs = tokenize_keystroke_sequence("a{F1}bc{END}")
    kinds = [(s.kind, s.value) for s in segs]
    assert kinds == [
        ("text", "a"),
        ("tag", "F1"),
        ("text", "bc"),
        ("tag", "END"),
    ]


def test_tokenize_normalizes_spaces_in_tag() -> None:
    segs = tokenize_keystroke_sequence("{page up}")
    assert len(segs) == 1
    assert segs[0].kind == "tag"
    assert segs[0].value == "PAGE_UP"


def test_describe_unknown_tags_order() -> None:
    assert describe_unknown_tags("{FOO}{BAR}{FOO}") == ["FOO", "BAR"]


def test_all_interception_slots_collects_ordered() -> None:
    devices = [MagicMock() for _ in range(20)]
    for d in devices:
        d.get_HWID.return_value = None
    devices[0].get_HWID.return_value = "HID\\KBD0"
    devices[2].get_HWID.return_value = "HID\\KBD2"
    devices[10].get_HWID.return_value = "HID\\MOUSE10"
    devices[15].get_HWID.return_value = "HID\\MOUSE15"
    assert _all_interception_slots_with_hwid(devices, 0, 10) == [0, 2]
    assert _all_interception_slots_with_hwid(devices, 10, 20) == [10, 15]


def test_all_interception_slots_empty() -> None:
    devices = [MagicMock() for _ in range(5)]
    for d in devices:
        d.get_HWID.return_value = None
    assert _all_interception_slots_with_hwid(devices, 0, 5) == []


def test_first_interception_slot_with_hwid_picks_lowest() -> None:
    devices = [MagicMock() for _ in range(20)]
    for d in devices:
        d.get_HWID.return_value = None
    devices[3].get_HWID.return_value = "HID\\KBD3"
    devices[8].get_HWID.return_value = "HID\\KBD8"
    devices[12].get_HWID.return_value = "HID\\MOUSE12"
    devices[18].get_HWID.return_value = "HID\\MOUSE18"
    assert _first_interception_slot_with_hwid(devices, 0, 10) == 3
    assert _first_interception_slot_with_hwid(devices, 10, 20) == 12


def test_first_interception_slot_with_hwid_none_when_missing() -> None:
    devices = [MagicMock() for _ in range(10)]
    for d in devices:
        d.get_HWID.return_value = None
    assert _first_interception_slot_with_hwid(devices, 0, 10) is None


def test_run_simulate_keystrokes_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        run_simulate_keystrokes("   ")


def test_run_simulate_dispatches_to_platform_backend() -> None:
    target = (
        "stream_cheremsha.actions.actions_simulate_keystrokes._win_send_sequence"
        if sys.platform == "win32"
        else "stream_cheremsha.actions.actions_simulate_keystrokes._pynput_send_sequence"
    )
    with patch(target) as fn:
        run_simulate_keystrokes("{ENTER}", hold_ms=10, game_mode=False)
    fn.assert_called_once()
    args, kw = fn.call_args
    assert args[0] == "{ENTER}"
    assert kw["hold_ms"] == 10
    assert kw["with_ctrl"] is False
    if sys.platform == "win32":
        assert kw["game_mode"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows SendInput path")
def test_run_simulate_keystrokes_game_mode_passed_on_windows() -> None:
    with patch("stream_cheremsha.actions.actions_simulate_keystrokes._win_send_sequence") as win:
        run_simulate_keystrokes("{F1}", game_mode=True, with_ctrl=True)
    win.assert_called_once()
    _args, kw = win.call_args
    assert kw["game_mode"] is True
    assert kw["with_ctrl"] is True


def test_run_simulate_non_windows_uses_pynput() -> None:
    if sys.platform == "win32":
        pytest.skip("non-Windows only")
    with patch("stream_cheremsha.actions.actions_simulate_keystrokes._pynput_send_sequence") as pyn:
        run_simulate_keystrokes("{TAB}", game_mode=True)
    pyn.assert_called_once()


@pytest.mark.skipif(sys.platform == "win32", reason="Interception is Windows-only")
def test_run_simulate_interception_rejected_off_windows() -> None:
    with pytest.raises(ValueError, match="Interception mode"):
        run_simulate_keystrokes("x", use_interception=True)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Interception path")
def test_run_simulate_interception_calls_backend() -> None:
    with (
        patch("stream_cheremsha.actions.actions_simulate_keystrokes._ensure_interception") as ens,
        patch(
            "stream_cheremsha.actions.actions_simulate_keystrokes._interception_send_sequence"
        ) as ic,
    ):
        run_simulate_keystrokes("x", use_interception=True, hold_ms=5)
    ens.assert_called_once()
    ic.assert_called_once()
    _args, kw = ic.call_args
    assert _args[0] == "x"
    assert kw["hold_ms"] == 5
