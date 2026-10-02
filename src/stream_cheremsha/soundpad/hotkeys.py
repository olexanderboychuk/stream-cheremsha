from __future__ import annotations

import logging
import threading
import time
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from stream_cheremsha.soundpad.models import normalize_hotkey
from stream_cheremsha.x11_auth import ensure_x_authority

logger = logging.getLogger(__name__)


# X11 key auto-repeat emits synthetic release+press pairs for a physically
# held key, and pynput forwards them unfiltered. Without debouncing, every
# synthetic release would stop a hold-to-play loop mid-start (the pipeline
# then restarts from zero each cycle = seconds of perceived latency).
# A release is therefore emitted only if the combo is STILL unsatisfied
# after this window. 50ms dwarfs the repeat pair gap (µs–ms) yet a real
# key-up still stops the loop imperceptibly fast.
_RELEASE_DEBOUNCE_SEC = 0.05

# A press arriving while its combo is still flagged "fired" is normally an
# X11 auto-repeat echo of a held key and is suppressed. But if the flag is
# stale (its key-release was lost: listener restart, grab mid-hold), the
# next real press would be swallowed silently while other combos keep
# working. Re-fire when the last fire is older than this: genuine repeats
# arrive every ~33 ms, so only a stale flag can be this old.
_PRESS_STALE_SEC = 2.0


# pynput reports left/right modifier variants per-OS (Key.ctrl_l/ctrl_r on
# Windows, plain Key.ctrl elsewhere). Combos are stored with canonical names
# ("ctrl"/"alt"/"shift"), so normalize here — otherwise modifier combos never
# match on platforms that emit the suffixed variants (Windows hotkeys dead).
def _normalize_key_name(name: str) -> str:
    n = (name or "").lower()
    for suffix in ("_l", "_r"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    if n in ("ctrl", "control"):
        return "ctrl"
    if n in ("alt", "alt_gr"):
        return "alt"
    if n == "shift":
        return "shift"
    return n


def _token_from_vk(vk: int | None) -> str | None:
    """Layout-independent token from a virtual key code.

    While Ctrl/Alt is held, Windows cooks KeyCode chars: digits arrive with
    ``char=None``, letters as C0 control chars (Ctrl+C -> ``'\\x03'``). The
    vk still identifies the physical key, so map the layout-independent
    ranges (digits, US letters, numpad, F-keys) back to combo tokens.
    """
    if vk is None:
        return None
    try:
        vk = int(vk)
    except (TypeError, ValueError):
        return None
    if 48 <= vk <= 57:  # '0'-'9' row
        return chr(vk)
    if 65 <= vk <= 90:  # A-Z (physical position, layout-independent)
        return chr(vk).lower()
    if 96 <= vk <= 105:  # numpad 0-9
        return chr(vk - 48)
    if 112 <= vk <= 135:  # F1-F24
        return f"f{vk - 111}"
    return None


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
    _released = Signal(str)

    def __init__(self, on_fire, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_fire = on_fire
        self._combos: dict[str, frozenset[str]] = {}
        self._pressed: set[str] = set()
        self._fired_combos: set[str] = set()
        self._fired_at: dict[str, float] = {}
        self._pending_release: dict[str, threading.Timer] = {}
        self._listener = None
        self._lock = threading.Lock()
        self._fired.connect(self._on_fire)

    def start(self) -> None:
        return None

    def stop(self) -> None:
        with self._lock:
            lis, self._listener = self._listener, None
            pending = list(self._pending_release.values())
            self._pending_release.clear()
        for timer in pending:
            try:
                timer.cancel()
            except RuntimeError:
                pass
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
        ensure_x_authority()
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
        was_fired = False
        with self._lock:
            was_fired = combo in self._fired_combos
            self._combos.pop(combo, None)
            self._fired_combos.discard(combo)
            self._fired_at.pop(combo, None)
            timer = self._pending_release.pop(combo, None)
            if timer is not None:
                timer.cancel()
        # Ungrabbing a physically-held combo must stop hold-to-play loops.
        if was_fired:
            try:
                self._released.emit(combo)
            except RuntimeError:
                pass

    def _fire_release_later(self, combo: str) -> None:
        timer: threading.Timer | None = None

        def _fire() -> None:
            self._fire_release_if_idle(combo, timer)

        timer = threading.Timer(_RELEASE_DEBOUNCE_SEC, _fire)
        timer.daemon = True
        with self._lock:
            old = self._pending_release.get(combo)
            if old is not None:
                old.cancel()
            self._pending_release[combo] = timer
        timer.start()

    def _fire_release_if_idle(self, combo: str, timer: threading.Timer | None) -> None:
        with self._lock:
            if self._pending_release.get(combo) is not timer:
                return  # superseded by a newer arm; that one decides
            self._pending_release.pop(combo, None)
            tokens = self._combos.get(combo)
            if tokens is not None and tokens <= self._pressed:
                return  # re-pressed inside the window: still held, no release
            self._fired_combos.discard(combo)
        try:
            self._released.emit(combo)
        except RuntimeError:
            pass

    def _ensure_listener_locked(self) -> None:
        if self._listener is not None:
            return
        ensure_x_authority()
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
        suppressed: list[str] = []
        with self._lock:
            now = time.monotonic()
            self._pressed.add(token)
            for combo, tokens in list(self._combos.items()):
                if tokens <= self._pressed:
                    last = self._fired_at.get(combo, 0.0)
                    if combo not in self._fired_combos or (now - last) >= _PRESS_STALE_SEC:
                        self._fired_combos.add(combo)
                        self._fired_at[combo] = now
                        to_fire.append(combo)
                    else:
                        suppressed.append(combo)
        if suppressed:
            logger.debug("hotkey press suppressed (already fired): %s", suppressed)
        for c in to_fire:
            # Logged on the pynput listener thread: compare its timestamp
            # with the manager/api lines to attribute press→handler latency
            # to either X11/pynput delivery or Qt queued-signal dispatch.
            logger.info("hotkey listener fire: %s", c)
            try:
                self._fired.emit(c)
            except RuntimeError:
                pass

    def _on_key_up(self, key, injected: bool = False) -> None:
        token = self._token(key)
        if token is None:
            return
        to_arm: list[str] = []
        with self._lock:
            self._pressed.discard(token)
            # A combo becomes *eligible* for release as soon as ANY of its
            # keys lifts, even if other keys are still held (matters for
            # Ctrl+/Shift+ combos). Discarding from _fired_combos here keeps
            # re-presses responsive; the actual release emission is debounced
            # (X11 auto-repeat storms) by _fire_release_later.
            for combo in list(self._fired_combos):
                tokens = self._combos.get(combo)
                if tokens is None or not (tokens <= self._pressed):
                    self._fired_combos.discard(combo)
                    to_arm.append(combo)
            if not self._pressed:
                self._fired_combos.clear()
        for c in to_arm:
            self._fire_release_later(c)

    @staticmethod
    def _token(key) -> str | None:
        try:
            from pynput.keyboard import Key, KeyCode
        except ImportError:
            return None
        if isinstance(key, Key):
            return _normalize_key_name(key.name.lower())
        if isinstance(key, KeyCode):
            c = key.char or ""
            if len(c) == 1 and c.isprintable():
                return c.lower()
            # Ctrl/Alt held: char is None (digits) or a C0 control char
            # (letters, e.g. Ctrl+C -> '\x03' == 'c'). Fall back to the vk,
            # which still identifies the physical key (see _token_from_vk).
            if len(c) == 1 and 1 <= ord(c) <= 26:
                return chr(ord(c) + 96)
            return _token_from_vk(getattr(key, "vk", None))
        return None


def _xlib_modules():
    """python-xlib pieces, or ``(None, None, None)`` when unavailable.

    Imported lazily so the soundpad stack loads (and degrades to another
    hotkey backend) on machines without X libraries.
    """
    try:
        from Xlib import XK as _XK
        from Xlib import X as _X
        from Xlib import display as _display
    except ImportError:
        return None, None, None
    return _X, _XK, _display


class XKeyGrabBackend(QObject):
    """Global hotkeys via XGrabKey passive grabs (one grab per combo).

    Unlike pynput's XRecord full-stream monitor, the X server delivers only
    the grabbed combos — no per-keystroke Python processing and no record
    context whose delivery can stall by seconds. Same ``_fired``/``_released``
    signal contract, so ``GlobalHotkeyManager`` works unchanged.

    Matching is exact per combo (server-side); NumLock/CapsLock variants are
    grabbed so lock state never blocks a hotkey. X11 auto-repeat echoes of a
    held key arrive as repeat KeyPress events and are suppressed while the
    combo is freshly fired (same staleness bound as the pynput backend, so a
    lost release can never eat the next real press); releases use the same
    50 ms debounce. Combos needing more than one main key cannot be grabbed
    (``grab`` returns False so the manager can fall back to another backend).
    """

    _fired = Signal(str)
    _released = Signal(str)

    # Event-thread poll granularity: bounds press latency (~10 ms) without
    # a blocking read that would stall grab()/stop() from other threads.
    _POLL_SEC = 0.01

    # Modifier keysyms tracked for release detection (keycode -> mask).
    _MOD_KEYSYMS = (
        ("Control_L", "ctrl"),
        ("Control_R", "ctrl"),
        ("Alt_L", "alt"),
        ("Alt_R", "alt"),
        ("Shift_L", "shift"),
        ("Shift_R", "shift"),
    )

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._combos: dict[str, tuple[int, int]] = {}  # combo -> (keycode, modifiers)
        self._mod_keycodes: dict[int, int] = {}  # modifier keycode -> mask
        self._mod_down: dict[int, int] = {}  # held modifier keycode -> mask
        self._fired_combos: set[str] = set()
        self._fired_at: dict[str, float] = {}
        self._pending_release: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._display = None
        self._root = None
        self._worker: threading.Thread | None = None
        self._stop_ev = threading.Event()

    @staticmethod
    def split_tokens(tokens: frozenset[str]) -> tuple[int, str] | None:
        """``(modifier mask, KEYSYM name)`` for single-main combos, else None."""
        X, _, _ = _xlib_modules()
        if X is None:
            return None
        masks = {"ctrl": X.ControlMask, "alt": X.Mod1Mask, "shift": X.ShiftMask}
        mods = 0
        mains: list[str] = []
        for t in tokens:
            if t in masks:
                mods |= masks[t]
            else:
                name = t.upper()
                if not (len(t) == 1 or (name.startswith("F") and name[1:].isdigit())):
                    return None
                mains.append(name)
        if len(mains) != 1:
            return None
        return mods, mains[0]

    @staticmethod
    def _mod_mask() -> int:
        X, _, _ = _xlib_modules()
        if X is None:
            return 0
        return (
            X.ShiftMask
            | X.LockMask
            | X.ControlMask
            | X.Mod1Mask
            | X.Mod2Mask
            | X.Mod3Mask
            | X.Mod4Mask
            | X.Mod5Mask
        )

    @staticmethod
    def _lock_ignored() -> int:
        X, _, _ = _xlib_modules()
        if X is None:
            return 0
        return X.LockMask | X.Mod2Mask

    def start(self) -> None:
        return None

    def stop(self) -> None:
        self._stop_ev.set()
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.join(timeout=2.0)
        with self._lock:
            disp, self._display = self._display, None
            root, self._root = self._root, None
            grabbed = list(self._combos.items())
            self._combos.clear()
            self._mod_keycodes.clear()
            self._mod_down.clear()
            self._fired_combos.clear()
            self._fired_at.clear()
            pending = list(self._pending_release.values())
            self._pending_release.clear()
        for timer in pending:
            try:
                timer.cancel()
            except RuntimeError:
                pass
        X, _, _ = _xlib_modules()
        if disp is not None and grabbed and X is not None and root is not None:
            try:
                for _combo, (keycode, mods) in grabbed:
                    for extra in (0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask):
                        root.ungrab_key(keycode, mods | extra)
                disp.flush()
            except Exception as e:  # noqa: BLE001 - X teardown must not raise
                logger.debug("xgrab ungrab failed: %s", e)
        if disp is not None:
            close = getattr(disp, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - X teardown must not raise
                    pass

    def grab(self, combo: str) -> bool:
        ensure_x_authority()
        X, XK, display_mod = _xlib_modules()
        if X is None or XK is None or display_mod is None:
            logger.warning("python-xlib unavailable, hotkey %r not grabbed", combo)
            return False
        tokens = PynputHotkeyBackend._combo_tokens(combo)
        if tokens is None:
            logger.warning("unparseable hotkey %r", combo)
            return False
        split = self.split_tokens(tokens)
        if split is None:
            logger.warning("hotkey %r needs exactly one main key for xgrab", combo)
            return False
        mods, keysym_name = split
        keysym = XK.string_to_keysym(keysym_name)
        if not keysym:
            logger.warning("unknown keysym for hotkey %r", combo)
            return False
        with self._lock:
            if combo in self._combos:
                return True
            try:
                if self._display is None:
                    self._display = display_mod.Display()
                    self._root = self._display.screen().root
                disp = self._display
                keycode = disp.keysym_to_keycode(keysym)
            except Exception as e:  # noqa: BLE001 - X errors degrade to probe-fail
                logger.warning("xgrab display unavailable for %r: %s", combo, e)
                return False
            if not keycode:
                logger.warning("no keycode for hotkey %r", combo)
                return False
            try:
                for extra in (0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask):
                    self._root.grab_key(
                        keycode, mods | extra, False, X.GrabModeAsync, X.GrabModeAsync
                    )
                disp.flush()
                # Round-trip: surfaces grab errors (e.g. BadAccess on a
                # conflicting grab) here instead of in the event thread.
                self._root.get_attributes()
            except Exception as e:  # noqa: BLE001 - X errors degrade to probe-fail
                logger.warning("xgrab failed for %r: %s", combo, e)
                try:
                    for extra in (0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask):
                        self._root.ungrab_key(keycode, mods | extra)
                    disp.flush()
                except Exception:  # noqa: BLE001 - best-effort cleanup
                    pass
                return False
            self._track_mod_keycodes_locked(X, XK, disp)
            self._combos[combo] = (keycode, mods)
            self._ensure_worker_locked()
            return True

    def _track_mod_keycodes_locked(self, X, XK, disp) -> None:
        """Resolve modifier keycodes once per grab (release detection)."""
        masks = {"ctrl": X.ControlMask, "alt": X.Mod1Mask, "shift": X.ShiftMask}
        for keysym_name, mod in self._MOD_KEYSYMS:
            try:
                kc = disp.keysym_to_keycode(XK.string_to_keysym(keysym_name))
            except Exception:  # noqa: BLE001 - missing keymap entry is fine
                continue
            if kc:
                self._mod_keycodes.setdefault(kc, masks[mod])

    def release(self, combo: str) -> None:
        X, _, _ = _xlib_modules()
        was_fired = False
        spec: tuple[int, int] | None = None
        with self._lock:
            spec = self._combos.pop(combo, None)
            was_fired = combo in self._fired_combos
            self._fired_combos.discard(combo)
            self._fired_at.pop(combo, None)
            timer = self._pending_release.pop(combo, None)
            if timer is not None:
                try:
                    timer.cancel()
                except RuntimeError:
                    pass
            disp = self._display
            root = self._root
        if spec is not None and disp is not None and X is not None and root is not None:
            keycode, mods = spec
            try:
                for extra in (0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask):
                    root.ungrab_key(keycode, mods | extra)
                disp.flush()
            except Exception as e:  # noqa: BLE001 - X teardown must not raise
                logger.debug("xgrab ungrab failed for %r: %s", combo, e)
        # Ungrabbing a physically-held combo must stop hold-to-play loops.
        if was_fired:
            try:
                self._released.emit(combo)
            except RuntimeError:
                pass

    def _ensure_worker_locked(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_ev.clear()
        t = threading.Thread(target=self._event_loop, name="xgrab-keys", daemon=True)
        self._worker = t
        t.start()

    def _event_loop(self) -> None:
        while not self._stop_ev.is_set():
            with self._lock:
                disp = self._display
                if disp is None:
                    pending: list = []
                else:
                    try:
                        n = disp.pending_events()
                        pending = [disp.next_event() for _ in range(n)] if n else []
                    except Exception as e:  # noqa: BLE001 - X teardown races land here
                        logger.debug("xgrab event poll failed: %s", e)
                        pending = []
            for ev in pending:
                self._dispatch(ev)
            if not pending:
                time.sleep(self._POLL_SEC)

    def _dispatch(self, ev) -> None:
        X, _, _ = _xlib_modules()
        if X is None:
            return
        etype = getattr(ev, "type", None)
        keycode = getattr(ev, "detail", 0)
        state = getattr(ev, "state", 0)
        if etype == X.KeyPress:
            self._handle_press(keycode, state)
        elif etype == X.KeyRelease:
            self._handle_release(keycode)

    def _handle_press(self, keycode: int, state: int) -> None:
        want = state & self._mod_mask() & ~self._lock_ignored()
        now = time.monotonic()
        to_fire: list[str] = []
        with self._lock:
            if keycode in self._mod_keycodes:
                self._mod_down[keycode] = self._mod_keycodes[keycode]
            for combo, (kc, mods) in list(self._combos.items()):
                if kc != keycode or mods != want:
                    continue
                # A re-press cancels a pending (debounced) release: the key
                # is down again, so the armed release is stale.
                timer = self._pending_release.pop(combo, None)
                if timer is not None:
                    try:
                        timer.cancel()
                    except RuntimeError:
                        pass
                last = self._fired_at.get(combo, 0.0)
                if combo not in self._fired_combos or (now - last) >= _PRESS_STALE_SEC:
                    self._fired_combos.add(combo)
                    self._fired_at[combo] = now
                    to_fire.append(combo)
        for c in to_fire:
            # Logged on the grab event thread: compare with the manager/api
            # lines to attribute press→handler latency.
            logger.info("hotkey grab fire: %s", c)
            try:
                self._fired.emit(c)
            except RuntimeError:
                pass

    def _handle_release(self, keycode: int) -> None:
        X, _, _ = _xlib_modules()
        if X is None:
            return
        to_arm: list[str] = []
        with self._lock:
            self._mod_down.pop(keycode, None)
            down_masks = set(self._mod_down.values())
            need_bits = (X.ControlMask, X.Mod1Mask, X.ShiftMask)
            for combo, (kc, mods) in list(self._combos.items()):
                if combo not in self._fired_combos:
                    continue
                if kc == keycode:
                    broken = True  # main key lifted: combo definitely broken
                else:
                    need = {b for b in need_bits if mods & b}
                    broken = not need <= down_masks
                if broken:
                    self._fired_combos.discard(combo)
                    to_arm.append(combo)
        for c in to_arm:
            self._fire_release_later(c)

    def _fire_release_later(self, combo: str) -> None:
        timer: threading.Timer | None = None

        def _fire() -> None:
            self._fire_release_if_idle(combo, timer)

        timer = threading.Timer(_RELEASE_DEBOUNCE_SEC, _fire)
        timer.daemon = True
        with self._lock:
            old = self._pending_release.get(combo)
            if old is not None:
                old.cancel()
            self._pending_release[combo] = timer
        timer.start()

    def _fire_release_if_idle(self, combo: str, timer: threading.Timer | None) -> None:
        with self._lock:
            if self._pending_release.get(combo) is not timer:
                return  # superseded by a newer arm; that one decides
            self._pending_release.pop(combo, None)
            self._fired_combos.discard(combo)
        try:
            self._released.emit(combo)
        except RuntimeError:
            pass


class GlobalHotkeyManager(QObject):
    hotkeyPressed = Signal(str)
    hotkeyReleased = Signal(str)
    hotkeyConflict = Signal(str, str)
    registrationFailed = Signal(str, str)

    def __init__(self, backend=None, parent: QObject | None = None, fallback_backend=None) -> None:
        super().__init__(parent)
        self._backend = backend or FakeHotkeyBackend()
        # Per-combo fallback (e.g. xgrab primary, pynput RECORD secondary):
        # tried only when the primary rejects a grab.
        self._fallback = fallback_backend
        self._ids: dict[str, str] = {}
        self._combo_owner: dict[str, str] = {}
        for be in (self._backend, self._fallback):
            start = getattr(be, "start", None)
            if callable(start):
                try:
                    start()
                except (RuntimeError, OSError) as e:
                    logger.warning("hotkey backend start failed: %s", e)
            fired = getattr(be, "_fired", None)
            if fired is not None:
                try:
                    fired.connect(self._on_backend_fire)
                except RuntimeError:
                    pass
            released = getattr(be, "_released", None)
            if released is not None:
                try:
                    released.connect(self._on_backend_release)
                except RuntimeError:
                    pass

    def _on_backend_fire(self, combo: str) -> None:
        owner = self._combo_owner.get(str(combo))
        # GUI thread (queued slot): timestamp vs the listener line above
        # shows whether the delay is Qt dispatch (starved event loop) or
        # happened before pynput saw the key.
        logger.info("hotkey manager dispatch: combo=%s owner=%s", combo, owner)
        if owner:
            self.hotkeyPressed.emit(owner)

    def _on_backend_release(self, combo: str) -> None:
        owner = self._combo_owner.get(str(combo))
        if owner:
            self.hotkeyReleased.emit(owner)

    def _release_combo(self, combo: str) -> None:
        """Best-effort ungrab on both backends (only the owner holds it)."""
        for be in (self._backend, self._fallback):
            rel = getattr(be, "release", None)
            if callable(rel):
                try:
                    rel(combo)
                except (RuntimeError, OSError):
                    pass

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
        if not ok and self._fallback is not None:
            grab = getattr(self._fallback, "grab", None)
            ok = bool(grab(norm)) if callable(grab) else True
        if not ok:
            self.registrationFailed.emit(sound_id, f"backend rejected {norm}")
            return False
        if old and old != norm:
            self._release_combo(old)
            self._combo_owner.pop(old, None)
            # Stop a hold-to-play loop bound to the previous combo.
            self.hotkeyReleased.emit(sound_id)
        self._ids[sound_id] = norm
        self._combo_owner[norm] = sound_id
        return True

    def unregister_hotkey(self, sound_id: str) -> None:
        self.clear_hotkey(sound_id)

    def clear_hotkey(self, sound_id: str) -> None:
        old = self._ids.pop(sound_id, "")
        if old:
            self._combo_owner.pop(old, None)
            self._release_combo(old)
            # Stop a hold-to-play loop bound to the cleared combo.
            self.hotkeyReleased.emit(sound_id)

    def list_hotkeys(self) -> dict[str, str]:
        return dict(self._ids)

    def simulate_press(self, sound_id: str) -> None:
        if sound_id in self._ids:
            self.hotkeyPressed.emit(sound_id)

    def simulate_release(self, sound_id: str) -> None:
        if sound_id in self._ids:
            self.hotkeyReleased.emit(sound_id)

    def shutdown(self) -> None:
        for be in (self._backend, self._fallback):
            stop = getattr(be, "stop", None)
            if callable(stop):
                try:
                    stop()
                except (RuntimeError, OSError):
                    pass
