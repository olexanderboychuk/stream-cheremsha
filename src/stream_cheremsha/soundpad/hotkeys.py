from __future__ import annotations

import logging
import threading
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from stream_cheremsha.soundpad.models import normalize_hotkey

logger = logging.getLogger(__name__)


class HotkeyBackend(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def grab(self, combo: str) -> bool: ...

    def release(self, combo: str) -> None: ...


class FakeHotkeyBackend:
    def __init__(self) -> None:
        self.grabbed: set[str] = set()
        self.fail: set[str] = set()

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def grab(self, combo: str) -> bool:
        if combo in self.fail:
            return False
        self.grabbed.add(combo)
        return True

    def release(self, combo: str) -> None:
        self.grabbed.discard(combo)


class PynputHotkeyBackend(QObject):
    """Global hotkeys via pynput (X11). Listener runs in its own daemon thread;
    key events are matched by token and the Qt signal is emitted cross-thread."""

    _fired = Signal(str)

    def __init__(self, on_fire, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_fire = on_fire
        self._combos: dict[str, frozenset[str]] = {}
        self._pressed: set[str] = set()
        self._fired_combos: set[str] = set()
        self._listener = None
        self._lock = threading.Lock()
        self._fired.connect(self._on_fire)

    def start(self) -> None:
        return None

    def stop(self) -> None:
        with self._lock:
            lis, self._listener = self._listener, None
        if lis is not None:
            try:
                lis.stop()
            except (RuntimeError, OSError) as e:
                logger.debug("hotkey listener stop: %s", e)

    @staticmethod
    def _combo_tokens(combo: str) -> frozenset[str] | None:
        tokens: set[str] = set()
        for p in str(combo or "").split("+"):
            t = p.strip().lower()
            if not t:
                continue
            if t in ("ctrl", "control"):
                tokens.add("ctrl")
            elif t == "alt":
                tokens.add("alt")
            elif t == "shift":
                tokens.add("shift")
            elif len(t) == 1:
                tokens.add(t)
            elif t.startswith("f") and t[1:].isdigit():
                tokens.add(t)
            else:
                return None
        if not tokens or tokens <= {"ctrl", "alt", "shift"}:
            return None
        return frozenset(tokens)

    def grab(self, combo: str) -> bool:
        try:
            from pynput import keyboard as _kb  # noqa: F401 (validates X availability)
        except ImportError as e:
            logger.warning("pynput unavailable, hotkey %r not grabbed: %s", combo, e)
            return False
        tokens = self._combo_tokens(combo)
        if tokens is None:
            logger.warning("unparseable hotkey %r", combo)
            return False
        with self._lock:
            if combo in self._combos:
                return True
            self._combos[combo] = tokens
            self._ensure_listener_locked()
            return True

    def release(self, combo: str) -> None:
        with self._lock:
            self._combos.pop(combo, None)
            self._fired_combos.discard(combo)

    def _ensure_listener_locked(self) -> None:
        if self._listener is not None:
            return
        try:
            from pynput import keyboard as _kb
        except ImportError:
            return
        try:
            lis = _kb.Listener(
                on_press=self._on_key_down, on_release=self._on_key_up, suppress=False
            )
            lis.daemon = True
            lis.start()
            self._listener = lis
        except (RuntimeError, OSError) as e:
            logger.warning("hotkey listener start failed: %s", e)

    def _on_key_down(self, key, injected: bool = False) -> None:
        token = self._token(key)
        if token is None:
            return
        to_fire: list[str] = []
        with self._lock:
            self._pressed.add(token)
            for combo, tokens in list(self._combos.items()):
                if tokens <= self._pressed and combo not in self._fired_combos:
                    self._fired_combos.add(combo)
                    to_fire.append(combo)
        for c in to_fire:
            try:
                self._fired.emit(c)
            except RuntimeError:
                pass

    def _on_key_up(self, key, injected: bool = False) -> None:
        token = self._token(key)
        if token is None:
            return
        with self._lock:
            self._pressed.discard(token)
            if not self._pressed:
                self._fired_combos.clear()

    @staticmethod
    def _token(key) -> str | None:
        try:
            from pynput.keyboard import Key, KeyCode
        except ImportError:
            return None
        if isinstance(key, Key):
            return key.name.lower()
        if isinstance(key, KeyCode):
            c = (key.char or "").lower()
            return c if len(c) == 1 else None
        return None


class GlobalHotkeyManager(QObject):
    hotkeyPressed = Signal(str)
    hotkeyConflict = Signal(str, str)
    registrationFailed = Signal(str, str)

    def __init__(self, backend=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend or FakeHotkeyBackend()
        self._ids: dict[str, str] = {}
        self._combo_owner: dict[str, str] = {}
        start = getattr(self._backend, "start", None)
        if callable(start):
            try:
                start()
            except (RuntimeError, OSError) as e:
                logger.warning("hotkey backend start failed: %s", e)
        fired = getattr(self._backend, "_fired", None)
        if fired is not None:
            try:
                fired.connect(self._on_backend_fire)
            except RuntimeError:
                pass

    def _on_backend_fire(self, combo: str) -> None:
        owner = self._combo_owner.get(str(combo))
        if owner:
            self.hotkeyPressed.emit(owner)

    def register_hotkey(self, sound_id: str, combo: str) -> bool:
        norm = normalize_hotkey(combo)
        if not norm:
            self.registrationFailed.emit(sound_id, "empty hotkey")
            return False
        owner = self._combo_owner.get(norm)
        if owner is not None and owner != sound_id:
            self.hotkeyConflict.emit(sound_id, owner)
            return False
        old = self._ids.get(sound_id)
        if old == norm:
            return True
        grab = getattr(self._backend, "grab", None)
        ok = bool(grab(norm)) if callable(grab) else True
        if not ok:
            self.registrationFailed.emit(sound_id, f"backend rejected {norm}")
            return False
        if old and old != norm:
            rel = getattr(self._backend, "release", None)
            if callable(rel):
                try:
                    rel(old)
                except (RuntimeError, OSError):
                    pass
            self._combo_owner.pop(old, None)
        self._ids[sound_id] = norm
        self._combo_owner[norm] = sound_id
        return True

    def unregister_hotkey(self, sound_id: str) -> None:
        self.clear_hotkey(sound_id)

    def clear_hotkey(self, sound_id: str) -> None:
        old = self._ids.pop(sound_id, "")
        if old:
            self._combo_owner.pop(old, None)
            rel = getattr(self._backend, "release", None)
            if callable(rel):
                try:
                    rel(old)
                except (RuntimeError, OSError):
                    pass

    def list_hotkeys(self) -> dict[str, str]:
        return dict(self._ids)

    def simulate_press(self, sound_id: str) -> None:
        if sound_id in self._ids:
            self.hotkeyPressed.emit(sound_id)

    def shutdown(self) -> None:
        stop = getattr(self._backend, "stop", None)
        if callable(stop):
            try:
                stop()
            except (RuntimeError, OSError):
                pass
