from __future__ import annotations

import os
import struct
import sys
import time
from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

from stream_cheremsha.soundpad.hotkeys import (
    FakeHotkeyBackend,
    GlobalHotkeyManager,
    XKeyGrabBackend,
)

_COOKIE = b"\x66\x53\xef\x48"


def _write_xauth(path: Path, *entries) -> None:
    raw = b""
    for fam, addr, num, name, data in entries:
        raw += struct.pack(">H", fam) + struct.pack(">H", len(addr)) + addr
        raw += struct.pack(">H", len(num)) + num
        raw += struct.pack(">H", len(name)) + name
        raw += struct.pack(">H", len(data)) + data
    path.write_bytes(raw)


def _read_xauth(path: Path):
    from Xlib import xauth as _xauth

    return _xauth.Xauthority(str(path)).entries


# NOTE: the `qapp` session fixture lives in tests/conftest.py (exactly one
# QApplication per pytest process). Do NOT define module-scoped duplicates:
# they get garbage-collected mid-session, breaking later suites.


def test_ensure_x_authority_repairs_stale_host_entry(tmp_path, monkeypatch):
    if not sys.platform.startswith("linux"):
        pytest.skip("X11 xauth self-heal is Linux-only")
    import socket

    from stream_cheremsha import x11_auth

    source = tmp_path / "xauth_src"
    _write_xauth(source, (256, b"stale-host", b"0", b"MIT-MAGIC-COOKIE-1", _COOKIE))
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XAUTHORITY", str(source))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    x11_auth.ensure_x_authority()

    target = Path(os.environ["XAUTHORITY"])
    assert target == tmp_path / "cache" / "cheremsha" / "xauth"
    entries = _read_xauth(target)
    host = socket.gethostname().encode()
    assert (256, host, b"0", b"MIT-MAGIC-COOKIE-1", _COOKIE) in entries
    # Original stale entry preserved.
    assert (256, b"stale-host", b"0", b"MIT-MAGIC-COOKIE-1", _COOKIE) in entries
    # Source file untouched.
    assert len(_read_xauth(source)) == 1


def test_ensure_x_authority_noop_when_host_entry_exists(tmp_path, monkeypatch):
    import socket

    from stream_cheremsha import x11_auth

    source = tmp_path / "xauth_src"
    _write_xauth(source, (256, socket.gethostname().encode(), b"0", b"MIT-MAGIC-COOKIE-1", _COOKIE))
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XAUTHORITY", str(source))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    x11_auth.ensure_x_authority()

    assert os.environ["XAUTHORITY"] == str(source)
    assert not (tmp_path / "cache" / "cheremsha").exists()


def test_ensure_x_authority_missing_source_is_noop(tmp_path, monkeypatch):
    from stream_cheremsha import x11_auth

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XAUTHORITY", str(tmp_path / "nope"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    x11_auth.ensure_x_authority()  # must not raise

    assert os.environ["XAUTHORITY"] == str(tmp_path / "nope")


def test_ensure_x_authority_skipped_without_display(tmp_path, monkeypatch):
    from stream_cheremsha import x11_auth

    source = tmp_path / "xauth_src"
    _write_xauth(source, (256, b"stale-host", b"0", b"MIT-MAGIC-COOKIE-1", _COOKIE))
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("XAUTHORITY", str(source))

    x11_auth.ensure_x_authority()

    assert os.environ["XAUTHORITY"] == str(source)


def _pump() -> None:
    """Dispatch queued cross-thread signal deliveries (release timer thread)."""
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
        time.sleep(0.01)
        app.processEvents()


def test_register_and_conflict():
    m = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    assert m.register_hotkey("a", "F2") is True
    conflicts: list[tuple[str, str]] = []
    m.hotkeyConflict.connect(lambda i, e: conflicts.append((i, e)))
    assert m.register_hotkey("b", "F2") is False
    assert conflicts == [("b", "a")]
    assert m.list_hotkeys() == {"a": "F2"}


def test_unregister_frees_combo():
    m = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    m.register_hotkey("a", "F2")
    m.unregister_hotkey("a")
    assert m.register_hotkey("b", "F2") is True


def test_fake_press_emits_signal(qtbot=None):
    m = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    seen: list[str] = []
    m.hotkeyPressed.connect(seen.append)
    m.register_hotkey("a", "F3")
    m.simulate_press("a")
    assert seen == ["a"]


def test_clear_hotkey():
    m = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    m.register_hotkey("a", "Ctrl+Alt+1")
    m.clear_hotkey("a")
    assert m.list_hotkeys() == {}


def test_pynput_release_fires_on_key_up(qapp: QApplication):
    from pynput.keyboard import Key

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    fired: list[str] = []
    released: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._released.connect(released.append)
    # Seed directly: no listener thread in unit tests.
    be._combos["F9"] = frozenset({"f9"})
    be._on_key_down(Key.f9)
    assert fired == ["F9"]
    be._on_key_up(Key.f9)
    _pump()
    assert released == []  # debounced: not yet
    time.sleep(0.15)
    _pump()
    assert released == ["F9"]


def test_pynput_release_on_any_modifier_lift(qapp: QApplication):
    from pynput.keyboard import Key

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    fired: list[str] = []
    released: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._released.connect(released.append)
    be._combos["Ctrl+F9"] = frozenset({"ctrl", "f9"})
    be._on_key_down(Key.ctrl)
    assert fired == []
    be._on_key_down(Key.f9)
    assert fired == ["Ctrl+F9"]
    # Lifting Ctrl releases the combo even though F9 is still held.
    be._on_key_up(Key.ctrl)
    time.sleep(0.15)
    _pump()
    assert released == ["Ctrl+F9"]
    be._on_key_up(Key.f9)
    time.sleep(0.15)
    _pump()
    assert released == ["Ctrl+F9"]  # no duplicate
    be.stop()


def test_pynput_token_normalizes_win_left_right_modifiers(qapp: QApplication):
    """Windows reports Ctrl/Alt/Shift as ctrl_l/ctrl_r etc.; combos are
    stored canonical, so the token mapper must strip the side suffix."""
    from pynput.keyboard import Key

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    assert PynputHotkeyBackend._token(Key.ctrl_l) == "ctrl"
    assert PynputHotkeyBackend._token(Key.ctrl_r) == "ctrl"
    assert PynputHotkeyBackend._token(Key.alt_l) == "alt"
    assert PynputHotkeyBackend._token(Key.shift_r) == "shift"

    fired: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._combos["Ctrl+F9"] = frozenset({"ctrl", "f9"})
    be._on_key_down(Key.ctrl_l)
    be._on_key_down(Key.f9)
    assert fired == ["Ctrl+F9"]
    be.stop()


def test_pynput_token_ctrl_held_digits_and_letters(qapp: QApplication):
    """Windows cooks chars while Ctrl is held: digits arrive char=None,
    letters as C0 controls (Ctrl+C -> '\\x03'). The vk fallback must still
    yield the combo token (regression: Ctrl+1 / Ctrl+C never fired)."""
    from pynput.keyboard import Key, KeyCode

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    assert PynputHotkeyBackend._token(KeyCode(vk=49)) == "1"  # digit row, char=None
    assert PynputHotkeyBackend._token(KeyCode(vk=67, char="\x03")) == "c"
    assert PynputHotkeyBackend._token(KeyCode(vk=65, char="\x01")) == "a"
    assert PynputHotkeyBackend._token(KeyCode.from_char("1")) == "1"
    assert PynputHotkeyBackend._token(KeyCode.from_char("z")) == "z"

    fired: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._combos["Ctrl+1"] = frozenset({"ctrl", "1"})
    be._on_key_down(Key.ctrl_l)
    be._on_key_down(KeyCode(vk=49))  # physical '1' with Ctrl held
    assert fired == ["Ctrl+1"]
    be.stop()


def test_pynput_autorepeat_storm_emits_single_release(qapp: QApplication):
    """X11 hold sends synthetic release+press pairs; only the final,
    still-idle-after-50ms release may stop a hold loop. Re-presses inside
    the window must keep refiring (responsive machine-gun taps)."""
    import time

    from pynput.keyboard import Key

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    fired: list[str] = []
    released: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._released.connect(released.append)
    be._combos["F9"] = frozenset({"f9"})
    # Physical press, then a synthetic auto-repeat storm.
    be._on_key_down(Key.f9)
    for _ in range(5):
        be._on_key_up(Key.f9)
        be._on_key_down(Key.f9)
    assert fired == ["F9"] * 6
    _pump()
    assert released == []  # storm coalesced: nothing emitted mid-hold
    time.sleep(0.15)
    _pump()
    assert released == []  # last event was a press: still held
    # Real lift: exactly one release.
    be._on_key_up(Key.f9)
    time.sleep(0.15)
    _pump()
    assert released == ["F9"]
    be.stop()


def test_stale_fired_combo_refires():
    """A press suppressed as 'already fired' must re-fire once the flag is
    stale (lost key-release): otherwise one lost release eats the next real
    press silently on that combo only, while other hotkeys keep working."""
    import time

    from pynput.keyboard import Key

    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    fired: list[str] = []
    be = PynputHotkeyBackend(on_fire=fired.append)
    be._combos["F9"] = frozenset({"f9"})
    be._on_key_down(Key.f9)
    assert fired == ["F9"]
    # Immediate re-press (auto-repeat echo): still suppressed.
    be._on_key_down(Key.f9)
    assert fired == ["F9"]
    # Flag gone stale (release lost long ago): next real press fires.
    be._fired_at["F9"] = time.monotonic() - 10.0
    be._on_key_down(Key.f9)
    assert fired == ["F9", "F9"]
    be.stop()


def test_pynput_ungrab_while_held_releases():
    from stream_cheremsha.soundpad.hotkeys import PynputHotkeyBackend

    released: list[str] = []
    be = PynputHotkeyBackend(on_fire=lambda c: None)
    be._released.connect(released.append)
    be._combos["F9"] = frozenset({"f9"})
    be._fired_combos.add("F9")
    be.release("F9")
    assert released == ["F9"]


def test_manager_release_mapping_and_clear():
    m = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    released: list[str] = []
    m.hotkeyReleased.connect(released.append)
    m.register_hotkey("a", "F9")
    m.simulate_release("a")
    assert released == ["a"]
    # Clearing a combo also releases (stops hold loops bound to it).
    released.clear()
    m.clear_hotkey("a")
    assert released == ["a"]
    # Unknown id: silent no-op.
    m.simulate_release("nope")
    assert released == ["a"]


def _xev_factory():
    import types

    import pytest

    pytest.importorskip("Xlib")
    from Xlib import X

    def ev(etype: int, keycode: int, state: int):
        return types.SimpleNamespace(type=etype, detail=keycode, state=state)

    return X, ev


def test_xgrab_split_tokens():
    X, _ev = _xev_factory()
    assert XKeyGrabBackend.split_tokens(frozenset({"ctrl", "3"})) == (X.ControlMask, "3")
    assert XKeyGrabBackend.split_tokens(frozenset({"f9"})) == (0, "F9")
    mods, name = XKeyGrabBackend.split_tokens(frozenset({"ctrl", "shift", "f12"}))
    assert mods == (X.ControlMask | X.ShiftMask) and name == "F12"
    # Modifiers alone or several main keys cannot be grabbed.
    assert XKeyGrabBackend.split_tokens(frozenset({"ctrl"})) is None
    assert XKeyGrabBackend.split_tokens(frozenset({"a", "b"})) is None


def test_xgrab_grab_without_xlib_degrades(monkeypatch):
    monkeypatch.setattr(
        "stream_cheremsha.soundpad.hotkeys._xlib_modules",
        lambda: (None, None, None),
    )
    be = XKeyGrabBackend()
    assert be.grab("F9") is False
    be.stop()  # never-started backend stops cleanly


def test_xgrab_press_release_cycle(qapp: QApplication):
    X, ev = _xev_factory()
    kc, mods = 0x14, X.ControlMask
    fired: list[str] = []
    released: list[str] = []
    be = XKeyGrabBackend()
    be._fired.connect(fired.append)
    be._released.connect(released.append)
    be._combos["Ctrl+3"] = (kc, mods)
    be._handle_press(kc, mods)
    assert fired == ["Ctrl+3"]
    # Auto-repeat echo while held: suppressed.
    be._handle_press(kc, mods)
    assert fired == ["Ctrl+3"]
    # Wrong modifiers: no match.
    be._handle_press(kc, 0)
    assert fired == ["Ctrl+3"]
    # Release of the main key: debounced release fires once.
    be._handle_release(kc)
    _pump()
    assert released == []
    time.sleep(0.15)
    _pump()
    assert released == ["Ctrl+3"]
    be.stop()


def test_xgrab_modifier_lift_releases_but_unrelated_tap_does_not(qapp: QApplication):
    X, ev = _xev_factory()
    main_kc, mod_kc, mods = 0x14, 0x25, X.ControlMask
    released: list[str] = []
    be = XKeyGrabBackend()
    be._released.connect(released.append)
    be._combos["Ctrl+3"] = (main_kc, mods)
    be._mod_keycodes[mod_kc] = mods
    # Combo live: Ctrl physically held, main key down.
    be._mod_down[mod_kc] = mods
    be._fired_combos.add("Ctrl+3")
    # Unrelated Shift tap while the combo is held: no release.
    be._mod_keycodes[0x32] = X.ShiftMask
    be._handle_press(0x32, mods | X.ShiftMask)
    be._handle_release(0x32)
    time.sleep(0.15)
    _pump()
    assert released == []
    assert "Ctrl+3" in be._fired_combos
    # Lifting Ctrl while 3 is held: releases.
    be._handle_release(mod_kc)
    time.sleep(0.15)
    _pump()
    assert released == ["Ctrl+3"]
    be.stop()


def test_xgrab_stale_fired_refires():
    _X, _ev = _xev_factory()
    fired: list[str] = []
    be = XKeyGrabBackend()
    be._fired.connect(fired.append)
    be._combos["F9"] = (0x44, 0)
    be._handle_press(0x44, 0)
    assert fired == ["F9"]
    be._handle_press(0x44, 0)
    assert fired == ["F9"]  # fresh echo suppressed
    be._fired_at["F9"] = time.monotonic() - 10.0
    be._handle_press(0x44, 0)
    assert fired == ["F9", "F9"]  # stale flag re-fires
    be.stop()


def test_xgrab_dispatch_routes_and_ignores_unknown():
    X, ev = _xev_factory()
    fired: list[str] = []
    released: list[str] = []
    be = XKeyGrabBackend()
    be._fired.connect(fired.append)
    be._released.connect(released.append)
    be._combos["F9"] = (0x44, 0)
    be._dispatch(ev(X.KeyPress, 0x44, 0))
    assert fired == ["F9"]
    be._dispatch(ev(9999, 0x44, 0))  # unknown event type: ignored
    assert fired == ["F9"] and released == []
    be.stop()


def test_manager_fallback_grab_routing():
    primary = FakeHotkeyBackend()
    primary.fail.add("F9")
    fallback = FakeHotkeyBackend()
    m = GlobalHotkeyManager(backend=primary, fallback_backend=fallback)
    assert m.register_hotkey("a", "F9") is True
    assert "F9" not in primary.grabbed
    assert "F9" in fallback.grabbed
    assert m.list_hotkeys() == {"a": "F9"}
    # Primary success never touches the fallback.
    assert m.register_hotkey("b", "F10") is True
    assert "F10" in primary.grabbed
    assert "F10" not in fallback.grabbed
    m.shutdown()
