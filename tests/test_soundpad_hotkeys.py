from __future__ import annotations

from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager


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
