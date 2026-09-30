from __future__ import annotations

import time

from PySide6.QtWidgets import QApplication

from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager

# NOTE: the `qapp` session fixture lives in tests/conftest.py (exactly one
# QApplication per pytest process). Do NOT define module-scoped duplicates:
# they get garbage-collected mid-session, breaking later suites.


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
