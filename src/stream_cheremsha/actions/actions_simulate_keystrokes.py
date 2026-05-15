"""Simulate keyboard / mouse input for platform Actions (cross-platform).

Sequence syntax:
- Literal text: typed as Unicode, except **on Windows** keys mapped by ``VkKeyScanExW`` for the
  foreground window's keyboard layout use **physical VK + scan codes** so games see real
  key presses (e.g. ``x``).
- Special keys and mouse buttons: ``{NAME}`` (case-insensitive), e.g. ``{ENTER}``, ``{F7}``,
  ``{LCLICK}``.
- Optional global modifiers (Ctrl / Alt / Shift) apply only to ``{...}`` tokens,
  not to literal text.

Backends:
- **Windows + Interception**: if ``use_interception`` is enabled, uses the **Interception**
  kernel driver via ``interception-python`` (no LLKHF_INJECTED flag). Requires the oblitum
  Interception driver. **Literal text** uses ``VkKeyScanExW`` with the **foreground**
  window's keyboard layout, then scan ``KeyStroke`` writes — so worker threads match the
  focused game, not the background app's thread layout. ``interception.press`` for letters would
  follow the library's **import-time** ``VkKeyScanA`` table and often mismatches games under
  non-US layouts. **Named tags** (``{F1}``, arrows, etc.) still use the library's
  ``press`` / ``key_down`` / ``key_up``. Device indices use the **first** keyboard/mouse
  slot that reports a hardware ID (the library's ``auto_capture_devices()`` picks the
  **last** slot, often a virtual device).
- **Windows (default)**: ``SendInput`` with ``VkKeyScanExW`` (foreground layout) for literals;
  ``{TAG}`` scan codes when **game compatibility** is on.
- **macOS / Linux**: `pynput`.
"""

from __future__ import annotations

import ctypes
import os
import re
import sys
import threading
import time
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Any, Final, Literal

_TAG_PATTERN = re.compile(r"\{([^}]*)\}")

_user32_lock = threading.Lock()
_user32_singleton: Any | None = None


def _user32_dll() -> Any:
    """Shared user32 with ctypes prototypes set once (thread-safe).

    ``run_simulate_keystrokes`` can run on ``asyncio.to_thread`` workers; assigning
    ``argtypes`` / ``restype`` on every call races and can crash the process.
    """
    global _user32_singleton
    if _user32_singleton is not None:
        return _user32_singleton
    with _user32_lock:
        if _user32_singleton is not None:
            return _user32_singleton
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.VkKeyScanExW.argtypes = [ctypes.c_uint16, ctypes.c_void_p]
        u.VkKeyScanExW.restype = ctypes.c_short
        u.GetForegroundWindow.argtypes = []
        u.GetForegroundWindow.restype = ctypes.c_void_p
        u.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        u.GetWindowThreadProcessId.restype = ctypes.c_ulong
        u.GetKeyboardLayout.argtypes = [ctypes.c_ulong]
        u.GetKeyboardLayout.restype = ctypes.c_void_p
        u.MapVirtualKeyW.argtypes = [ctypes.c_uint, ctypes.c_uint]
        u.MapVirtualKeyW.restype = ctypes.c_uint
        u.MapVirtualKeyExW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
        u.MapVirtualKeyExW.restype = ctypes.c_uint
        _user32_singleton = u
        return u


def _foreground_keyboard_layout_hkl(user32: Any) -> int:
    """Return ``HKL`` for the thread that owns the foreground (focused) window.

    ``VkKeyScanW`` / ``MapVirtualKeyW`` use the **calling thread's** layout; keystroke actions
    often run on ``asyncio.to_thread`` workers, which may not match the game in focus.
    ``VkKeyScanExW`` with this HKL aligns with the window that receives input.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return int(user32.GetKeyboardLayout(0) or 0)
    pid = ctypes.c_ulong(0)
    tid = int(user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)))
    return int(user32.GetKeyboardLayout(tid) or 0)


TagKind = Literal["key", "mouse_left", "mouse_right"]


@dataclass(frozen=True, slots=True)
class _Segment:
    kind: Literal["text", "tag"]
    value: str


def tokenize_keystroke_sequence(sequence: str) -> list[_Segment]:
    """Split ``sequence`` into literal runs and ``{tag}`` markers (tags are uppercased)."""
    if not sequence:
        return []
    out: list[_Segment] = []
    pos = 0
    for m in _TAG_PATTERN.finditer(sequence):
        if m.start() > pos:
            out.append(_Segment("text", sequence[pos : m.start()]))
        inner = (m.group(1) or "").strip()
        if inner:
            norm = inner.upper().replace(" ", "_")
            out.append(_Segment("tag", norm))
        pos = m.end()
    if pos < len(sequence):
        out.append(_Segment("text", sequence[pos:]))
    return out


def _pynput_key_table() -> dict[str, Any]:
    from pynput.keyboard import Key as K

    t: dict[str, Any] = {
        "ENTER": K.enter,
        "RETURN": K.enter,
        "SPACE": K.space,
        "ESC": K.esc,
        "ESCAPE": K.esc,
        "TAB": K.tab,
        "BACKSPACE": K.backspace,
        "BS": K.backspace,
        "BREAK": K.pause,
        "PAUSE": K.pause,
        "CAPSLOCK": K.caps_lock,
        "CAPS_LOCK": K.caps_lock,
        "DELETE": K.delete,
        "DEL": K.delete,
        "INSERT": K.insert,
        "INS": K.insert,
        "HOME": K.home,
        "END": K.end,
        "PAGEUP": K.page_up,
        "PAGE_UP": K.page_up,
        "PGUP": K.page_up,
        "PRIOR": K.page_up,
        "PAGEDOWN": K.page_down,
        "PAGE_DOWN": K.page_down,
        "PGDN": K.page_down,
        "NEXT": K.page_down,
        "UP": K.up,
        "UPARROW": K.up,
        "DOWN": K.down,
        "DOWNARROW": K.down,
        "LEFT": K.left,
        "LEFTARROW": K.left,
        "RIGHT": K.right,
        "RIGHTARROW": K.right,
    }
    for i in range(1, 13):
        t[f"F{i}"] = getattr(K, f"f{i}")
    return t


_key_table_cache: dict[str, Any] | None = None


def _key_table() -> dict[str, Any]:
    global _key_table_cache
    if _key_table_cache is None:
        _key_table_cache = _pynput_key_table()
    return _key_table_cache


def _resolve_tag(tag: str) -> tuple[TagKind, Any] | None:
    if tag in ("LCLICK", "LEFTCLICK", "MOUSELEFT"):
        return ("mouse_left", None)
    if tag in ("RCLICK", "RIGHTCLICK", "MOUSERIGHT"):
        return ("mouse_right", None)
    key = _key_table().get(tag)
    if key is not None:
        return ("key", key)
    return None


def describe_unknown_tags(sequence: str) -> list[str]:
    """Return distinct unknown ``{tag}`` names (uppercased) in order of first appearance."""
    seen: set[str] = set()
    bad: list[str] = []
    for seg in tokenize_keystroke_sequence(sequence):
        if seg.kind != "tag":
            continue
        if _resolve_tag(seg.value) is not None:
            continue
        if seg.value not in seen:
            seen.add(seg.value)
            bad.append(seg.value)
    return bad


def run_simulate_keystrokes(
    sequence: str,
    *,
    hold_ms: int = 0,
    game_mode: bool = False,
    with_ctrl: bool = False,
    with_alt: bool = False,
    with_shift: bool = False,
    use_interception: bool = False,
) -> None:
    """Execute ``sequence`` as system-wide keyboard/mouse input.

    Raises:
        ValueError: empty effective sequence, unknown ``{tag}``, or invalid options.
        OSError: OS rejected input (permissions, no session, etc.).
    """
    seq = (sequence or "").strip()
    if not seq:
        raise ValueError("Keystroke sequence is empty")

    unknown = describe_unknown_tags(seq)
    if unknown:
        raise ValueError(f"Unknown key tags: {', '.join(unknown)}")

    hm = max(0, min(int(hold_ms), 60_000))
    gm = bool(game_mode)
    wc = bool(with_ctrl)
    wa = bool(with_alt)
    ws = bool(with_shift)
    ui = bool(use_interception)

    if ui and sys.platform != "win32":
        raise ValueError("Interception mode is only supported on Windows")

    if sys.platform == "win32" and ui:
        _ensure_interception()
        _interception_send_sequence(
            seq,
            hold_ms=hm,
            with_ctrl=wc,
            with_alt=wa,
            with_shift=ws,
        )
    elif sys.platform == "win32":
        _win_send_sequence(
            seq,
            hold_ms=hm,
            game_mode=gm,
            with_ctrl=wc,
            with_alt=wa,
            with_shift=ws,
        )
    else:
        _pynput_send_sequence(seq, hold_ms=hm, with_ctrl=wc, with_alt=wa, with_shift=ws)


def _pynput_send_sequence(
    seq: str,
    *,
    hold_ms: int,
    with_ctrl: bool,
    with_alt: bool,
    with_shift: bool,
) -> None:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.keyboard import Key
    from pynput.mouse import Button
    from pynput.mouse import Controller as MouseController

    kbd = KeyboardController()
    mouse = MouseController()
    hold_s = hold_ms / 1000.0 if hold_ms else 0.0

    mods: list[Any] = []
    if with_shift:
        mods.append(Key.shift)
    if with_ctrl:
        mods.append(Key.ctrl)
    if with_alt:
        mods.append(Key.alt)

    def _tap_key(key: Any) -> None:
        def stroke() -> None:
            kbd.press(key)
            if hold_s:
                time.sleep(hold_s)
            kbd.release(key)

        if mods:
            with kbd.pressed(*mods):
                stroke()
        else:
            stroke()

    for seg in tokenize_keystroke_sequence(seq):
        if seg.kind == "text":
            if seg.value:
                kbd.type(seg.value)
            time.sleep(0.002)
            continue

        resolved = _resolve_tag(seg.value)
        if resolved is None:
            continue
        kind, payload = resolved
        if kind == "mouse_left":
            mouse.click(Button.left, 1)
            time.sleep(0.002)
            continue
        if kind == "mouse_right":
            mouse.click(Button.right, 1)
            time.sleep(0.002)
            continue

        _tap_key(payload)
        time.sleep(0.002)


_interception_init_lock = threading.Lock()
_interception_devices_loaded = False

# Normalized ``{TAG}`` -> interception-python ``press`` / ``key_down`` names (lowercase).
_IC_TAG: Final[dict[str, str]] = {
    "ENTER": "enter",
    "RETURN": "enter",
    "SPACE": "space",
    "ESC": "escape",
    "ESCAPE": "escape",
    "TAB": "tab",
    "BACKSPACE": "backspace",
    "BS": "backspace",
    "BREAK": "pause",
    "PAUSE": "pause",
    "CAPSLOCK": "capslock",
    "CAPS_LOCK": "capslock",
    "DELETE": "delete",
    "DEL": "delete",
    "INSERT": "insert",
    "INS": "insert",
    "HOME": "home",
    "END": "end",
    "PAGEUP": "pageup",
    "PAGE_UP": "pageup",
    "PGUP": "pageup",
    "PRIOR": "pageup",
    "PAGEDOWN": "pagedown",
    "PAGE_DOWN": "pagedown",
    "PGDN": "pagedown",
    "NEXT": "pagedown",
    "UP": "up",
    "UPARROW": "up",
    "DOWN": "down",
    "DOWNARROW": "down",
    "LEFT": "left",
    "LEFTARROW": "left",
    "RIGHT": "right",
    "RIGHTARROW": "right",
}


def _all_interception_slots_with_hwid(devices: list[Any], lo: int, hi: int) -> list[int]:
    """Return device indices in ``[lo, hi)`` whose ``get_HWID()`` is non-empty (in order)."""
    out: list[int] = []
    for num in range(lo, hi):
        if devices[num].get_HWID():
            out.append(num)
    return out


def _first_interception_slot_with_hwid(devices: list[Any], lo: int, hi: int) -> int | None:
    """First slot in ``[lo, hi)`` with a non-empty HWID, or ``None`` if none."""
    for num in range(lo, hi):
        if devices[num].get_HWID():
            return num
    return None


def _parse_interception_env_index(name: str, lo: int, hi_exclusive: int) -> int | None:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        v = int(raw, 10)
    except ValueError:
        return None
    if lo <= v < hi_exclusive:
        return v
    return None


def _bind_interception_devices() -> None:
    """Bind Interception keyboard/mouse indices.

    ``interception.auto_capture_devices()`` walks 0..19 and assigns the **last** keyboard
    and **last** mouse slot that has an HWID. On many PCs the last keyboard slot is a
    virtual device: writes succeed but nothing appears in games or Notepad.

    We prefer the **first** slot with HWID in 0..9 (keyboard) and 10..19 (mouse), then
    apply optional ``STREAM_CHEREMSHA_INTERCEPTION_*`` overrides.
    """
    import interception.inputs as _ic_inputs
    from interception.exceptions import DriverNotFoundError

    ctx = _ic_inputs._g_context
    if not ctx.valid:
        raise DriverNotFoundError()

    kb_pick = _first_interception_slot_with_hwid(ctx.devices, 0, 10)
    ms_pick = _first_interception_slot_with_hwid(ctx.devices, 10, 20)
    try:
        if kb_pick is not None:
            ctx.keyboard = kb_pick
        if ms_pick is not None:
            ctx.mouse = ms_pick
    except ValueError as e:
        raise ValueError(
            "Interception: could not apply default keyboard/mouse device indices. "
            f"keyboard={kb_pick!r}, mouse={ms_pick!r}: {e}"
        ) from e

    kb_manual = _parse_interception_env_index("STREAM_CHEREMSHA_INTERCEPTION_KEYBOARD", 0, 10)
    ms_manual = _parse_interception_env_index("STREAM_CHEREMSHA_INTERCEPTION_MOUSE", 10, 20)
    try:
        if kb_manual is not None:
            ctx.keyboard = kb_manual
        if ms_manual is not None:
            ctx.mouse = ms_manual
    except ValueError as e:
        raise ValueError(
            "Interception: invalid keyboard/mouse index from environment variables. "
            f"keyboard={kb_manual!r}, mouse={ms_manual!r}: {e}"
        ) from e


def _ensure_interception() -> None:
    global _interception_devices_loaded
    with _interception_init_lock:
        if _interception_devices_loaded:
            return
        try:
            import interception  # noqa: F401 — package PyPI name is interception-python
            from interception.exceptions import DriverNotFoundError

            _bind_interception_devices()
        except ImportError as e:
            raise ValueError(
                "Python package «interception» (PyPI: interception-python) is not installed "
                "in this environment — run «uv sync» or reinstall deps from pyproject.toml. "
                f"Detail: {e}"
            ) from e
        except DriverNotFoundError as e:
            raise ValueError(
                "Interception driver was not found or is not installed. "
                "Install the oblitum Interception driver and reboot."
            ) from e
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                "Interception driver or device setup failed. "
                "Install the oblitum Interception driver and reboot. "
                "Run as Administrator if setup still fails. "
                f"Detail: {e!r}"
            ) from e
        _interception_devices_loaded = True


def _interception_resolve(
    tag: str,
) -> tuple[Literal["mouse_left", "mouse_right", "key"], str] | None:
    if tag in ("LCLICK", "LEFTCLICK", "MOUSELEFT"):
        return ("mouse_left", "")
    if tag in ("RCLICK", "RIGHTCLICK", "MOUSERIGHT"):
        return ("mouse_right", "")
    if len(tag) >= 2 and tag[0] == "F" and tag[1:].isdigit():
        n = int(tag[1:])
        if 1 <= n <= 12:
            return ("key", f"f{n}")
    name = _IC_TAG.get(tag)
    if name is not None:
        return ("key", name)
    return None


@contextmanager
def _ic_hold_modifiers(names: list[str]) -> Generator[None, None, None]:
    import interception

    if not names:
        yield
        return
    with ExitStack() as stack:
        for n in names:
            stack.enter_context(interception.hold_key(n))
        yield


# --- Windows scan-code path (game compatibility) --------------------------------

_VK_BY_TAG: Final[dict[str, int]] = {
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "SPACE": 0x20,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "TAB": 0x09,
    "BACKSPACE": 0x08,
    "BS": 0x08,
    "BREAK": 0x13,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "CAPS_LOCK": 0x14,
    "DELETE": 0x2E,
    "DEL": 0x2E,
    "INSERT": 0x2D,
    "INS": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGE_UP": 0x21,
    "PGUP": 0x21,
    "PRIOR": 0x21,
    "PAGEDOWN": 0x22,
    "PAGE_DOWN": 0x22,
    "PGDN": 0x22,
    "NEXT": 0x22,
    "UP": 0x26,
    "UPARROW": 0x26,
    "DOWN": 0x28,
    "DOWNARROW": 0x28,
    "LEFT": 0x25,
    "LEFTARROW": 0x25,
    "RIGHT": 0x27,
    "RIGHTARROW": 0x27,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}

_EXTENDED_VKS: Final[frozenset[int]] = frozenset(
    {
        0x21,
        0x22,
        0x23,
        0x24,
        0x25,
        0x26,
        0x27,
        0x28,
        0x2D,
        0x2E,
    }
)

_VK_LSHIFT = 0xA0
_VK_LCONTROL = 0xA2
_VK_LMENU = 0xA4

_MAPVK_VK_TO_VSC_EX: Final[int] = 4
# Short hold between make/break so game loops see a real edge (library uses ~25 ms).
_INTERCEPTION_LAYOUT_KEY_HOLD_S: Final[float] = 0.008


def _interception_map_vk_to_scan(user32: Any, vk: int, hkl: int) -> tuple[int, bool]:
    vk_u = vk & 0xFFFF
    if hkl:
        sc_full = (
            int(user32.MapVirtualKeyExW(vk_u, _MAPVK_VK_TO_VSC_EX, ctypes.c_void_p(hkl))) & 0xFFFF
        )
    else:
        sc_full = int(user32.MapVirtualKeyW(vk_u, _MAPVK_VK_TO_VSC_EX)) & 0xFFFF
    scan = sc_full & 0xFF
    extended = bool(((sc_full >> 8) & 0xFF) & 0xE0) or vk_u in _EXTENDED_VKS
    return scan, extended


def _interception_send_scan_keyboard(scan: int, extended: bool, *, key_down: bool) -> None:
    import interception.inputs as _ic_inputs
    from interception.constants import KeyFlag
    from interception.strokes import KeyStroke

    sc = scan & 0xFF
    if sc == 0:
        raise ValueError(
            "Interception: scan code 0 from MapVirtualKeyW — refusing to send. "
            "This character may not exist on the active keyboard layout."
        )
    fk = KeyFlag.KEY_DOWN if key_down else KeyFlag.KEY_UP
    stroke = KeyStroke(sc, int(fk))
    if extended:
        stroke.flags |= KeyFlag.KEY_E0
    ctx = _ic_inputs._g_context
    res = ctx.send(ctx.keyboard, stroke)
    if not res.succeeded:
        err = ctypes.get_last_error()
        raise OSError(err, "Interception keyboard write failed")


def _interception_tap_vk_scan(user32: Any, vk: int, *, hold_s: float, hkl: int) -> None:
    scan, ext = _interception_map_vk_to_scan(user32, vk, hkl)
    hold = hold_s if hold_s > 0 else _INTERCEPTION_LAYOUT_KEY_HOLD_S
    _interception_send_scan_keyboard(scan, ext, key_down=True)
    time.sleep(hold)
    _interception_send_scan_keyboard(scan, ext, key_down=False)


def _interception_type_text_vk_key_scan_w(user32: Any, text: str) -> None:
    """Send literal text: ``VkKeyScanExW`` (foreground layout) → scan ``KeyStroke``.

    ``interception-python`` fills ASCII ``press`` mappings once at import via ``VkKeyScanA``;
    that does not track layout changes. ``VkKeyScanW`` uses the **worker thread's** layout;
    rules run on ``asyncio.to_thread`` and must use the focused window's HKL instead.
    """
    import interception
    from interception.exceptions import UnknownKeyError

    hkl = _foreground_keyboard_layout_hkl(user32)
    hkl_arg = ctypes.c_void_p(hkl)
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            _interception_tap_vk_scan(user32, 0x0D, hold_s=0.0, hkl=hkl)
            time.sleep(0.002)
            continue
        if ch == "\t":
            _interception_tap_vk_scan(user32, 0x09, hold_s=0.0, hkl=hkl)
            time.sleep(0.002)
            continue
        cp = ord(ch)
        if cp == 0 or cp > 0xFFFF:
            continue
        sr = user32.VkKeyScanExW(ctypes.c_uint16(cp & 0xFFFF), hkl_arg)
        if int(sr) == -1:
            try:
                interception.press(ch, presses=1, interval=0)
            except UnknownKeyError as e:
                raise ValueError(
                    f"Interception: cannot type character {ch!r} for the foreground layout. {e}"
                ) from e
            time.sleep(0.002)
            continue
        r_int = int(sr) & 0xFFFF
        low = r_int & 0xFF
        hi = (r_int >> 8) & 0xFF
        if low == 0:
            try:
                interception.press(ch, presses=1, interval=0)
            except UnknownKeyError as e:
                raise ValueError(
                    f"Interception: cannot type character {ch!r} for the foreground layout. {e}"
                ) from e
            time.sleep(0.002)
            continue
        extras: list[int] = []
        if hi & 1:
            extras.append(_VK_LSHIFT)
        if hi & 2:
            extras.append(_VK_LCONTROL)
        if hi & 4:
            extras.append(_VK_LMENU)
        for mv in extras:
            sm, exm = _interception_map_vk_to_scan(user32, mv, hkl)
            _interception_send_scan_keyboard(sm, exm, key_down=True)
        try:
            _interception_tap_vk_scan(user32, low, hold_s=0.0, hkl=hkl)
        finally:
            for mv in reversed(extras):
                sm, exm = _interception_map_vk_to_scan(user32, mv, hkl)
                _interception_send_scan_keyboard(sm, exm, key_down=False)
        time.sleep(0.002)


def _interception_send_sequence(
    seq: str,
    *,
    hold_ms: int,
    with_ctrl: bool,
    with_alt: bool,
    with_shift: bool,
) -> None:
    import interception

    mod_names: list[str] = []
    if with_shift:
        mod_names.append("shift")
    if with_ctrl:
        mod_names.append("ctrl")
    if with_alt:
        mod_names.append("alt")

    hold_s = hold_ms / 1000.0 if hold_ms else 0.0
    user32 = _user32_dll()

    for seg in tokenize_keystroke_sequence(seq):
        if seg.kind == "text":
            _interception_type_text_vk_key_scan_w(user32, seg.value)
            continue

        resolved = _interception_resolve(seg.value)
        if resolved is None:
            raise ValueError(
                f"Interception: unsupported tag {{{seg.value}}} despite validation; "
                "this is an internal bug — please report."
            )
        kind, key_name = resolved
        if kind == "mouse_left":
            with _ic_hold_modifiers(mod_names):
                interception.left_click(clicks=1, interval=0)
            time.sleep(0.002)
            continue
        if kind == "mouse_right":
            with _ic_hold_modifiers(mod_names):
                interception.right_click(clicks=1, interval=0)
            time.sleep(0.002)
            continue

        with _ic_hold_modifiers(mod_names):
            if hold_s:
                interception.key_down(key_name)
                time.sleep(hold_s)
                interception.key_up(key_name)
            else:
                interception.press(key_name, presses=1, interval=0)
        time.sleep(0.002)


def _win_resolve_vk(tag: str) -> tuple[Literal["vk", "mouse_left", "mouse_right"], int] | None:
    if tag in ("LCLICK", "LEFTCLICK", "MOUSELEFT"):
        return ("mouse_left", 0)
    if tag in ("RCLICK", "RIGHTCLICK", "MOUSERIGHT"):
        return ("mouse_right", 0)
    if len(tag) >= 2 and tag[0] == "F" and tag[1:].isdigit():
        n = int(tag[1:])
        if 1 <= n <= 12:
            return ("vk", 0x6F + n)
    vk = _VK_BY_TAG.get(tag)
    if vk is not None:
        return ("vk", vk)
    return None


def _win_send_sequence(
    seq: str,
    *,
    hold_ms: int,
    game_mode: bool,
    with_ctrl: bool,
    with_alt: bool,
    with_shift: bool,
) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = _user32_dll()
    hkl_fg = _foreground_keyboard_layout_hkl(user32)

    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008
    KEYEVENTF_EXTENDEDKEY = 0x0001

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010

    ULONG_PTR = ctypes.c_ulonglong

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        )

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        )

    class INPUT_UNION(ctypes.Union):
        _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT))

    class INPUT(ctypes.Structure):
        _fields_ = (("type", wintypes.DWORD), ("u", INPUT_UNION))

    input_sz = ctypes.sizeof(INPUT)

    def _send_input_checked(n: int, arr: Any, *, what: str) -> None:
        sent = user32.SendInput(n, ctypes.byref(arr), input_sz)
        if sent != n:
            err = ctypes.get_last_error()
            raise OSError(err, f"SendInput {what}: got {sent}, expected {n}")

    def _send_mouse(left: bool) -> None:
        down_f = MOUSEEVENTF_LEFTDOWN if left else MOUSEEVENTF_RIGHTDOWN
        up_f = MOUSEEVENTF_LEFTUP if left else MOUSEEVENTF_RIGHTUP
        extra = ULONG_PTR(0)
        down = INPUT(
            type=INPUT_MOUSE,
            u=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, down_f, 0, extra)),
        )
        up = INPUT(
            type=INPUT_MOUSE,
            u=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, up_f, 0, extra)),
        )
        arr = (INPUT * 2)(down, up)
        _send_input_checked(2, arr, what="mouse click")

    def _map_scan(vk: int) -> int:
        MAPVK_VK_TO_VSC = 0
        vk_u = vk & 0xFFFF
        if hkl_fg:
            sc = (
                int(user32.MapVirtualKeyExW(vk_u, MAPVK_VK_TO_VSC, ctypes.c_void_p(hkl_fg)))
                & 0xFFFF
            )
        else:
            sc = int(user32.MapVirtualKeyW(vk_u, MAPVK_VK_TO_VSC)) & 0xFFFF
        return int(sc)

    def _key_input(vk: int, scan: int, flags: int) -> INPUT:
        return INPUT(
            type=INPUT_KEYBOARD,
            u=INPUT_UNION(
                ki=KEYBDINPUT(
                    vk & 0xFFFF,
                    scan & 0xFFFF,
                    flags,
                    0,
                    ULONG_PTR(0),
                )
            ),
        )

    def _unicode_type(text: str) -> None:
        if not text:
            return
        inputs: list[INPUT] = []
        extra = ULONG_PTR(0)
        for ch in text:
            cp = ord(ch)
            if cp == 0 or cp > 0xFFFF:
                continue
            down = INPUT(
                type=INPUT_KEYBOARD,
                u=INPUT_UNION(
                    ki=KEYBDINPUT(0, cp, KEYEVENTF_UNICODE, 0, extra),
                ),
            )
            up = INPUT(
                type=INPUT_KEYBOARD,
                u=INPUT_UNION(
                    ki=KEYBDINPUT(0, cp, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, extra),
                ),
            )
            inputs.extend((down, up))
        if not inputs:
            return
        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        _send_input_checked(n, arr, what="unicode")

    def _press_scan_phys(vk: int) -> None:
        sc = _map_scan(vk)
        ext = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_VKS else 0
        inp = _key_input(0, sc, KEYEVENTF_SCANCODE | ext)
        arr = (INPUT * 1)(inp)
        _send_input_checked(1, arr, what="key down (scan)")

    def _release_scan_phys(vk: int) -> None:
        sc = _map_scan(vk)
        ext = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_VKS else 0
        inp = _key_input(0, sc, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP | ext)
        arr = (INPUT * 1)(inp)
        _send_input_checked(1, arr, what="key up (scan)")

    def _tap_scan_phys(vk: int) -> None:
        _press_scan_phys(vk)
        if hold_ms:
            time.sleep(hold_ms / 1000.0)
        _release_scan_phys(vk)

    def _type_text_win(text: str) -> None:
        """Prefer physical keys (scan codes) so games receive real key events."""
        hkl_arg = ctypes.c_void_p(hkl_fg)
        for ch in text:
            cp = ord(ch)
            if cp == 0 or cp > 0xFFFF:
                continue
            sr = user32.VkKeyScanExW(ctypes.c_uint16(cp & 0xFFFF), hkl_arg)
            if int(sr) == -1:
                _unicode_type(ch)
                time.sleep(0.002)
                continue
            r_int = int(sr) & 0xFFFF
            low = r_int & 0xFF
            hi = (r_int >> 8) & 0xFF
            if low == 0:
                _unicode_type(ch)
                time.sleep(0.002)
                continue
            extras: list[int] = []
            if hi & 1:
                extras.append(_VK_LSHIFT)
            if hi & 2:
                extras.append(_VK_LCONTROL)
            if hi & 4:
                extras.append(_VK_LMENU)
            for mv in extras:
                _press_scan_phys(mv)
            try:
                _tap_scan_phys(low)
            finally:
                for mv in reversed(extras):
                    _release_scan_phys(mv)
            time.sleep(0.002)

    def _modifier_vks() -> list[int]:
        out: list[int] = []
        if with_shift:
            out.append(_VK_LSHIFT)
        if with_ctrl:
            out.append(_VK_LCONTROL)
        if with_alt:
            out.append(_VK_LMENU)
        return out

    def _press_mods(mods: list[int]) -> None:
        for vk in mods:
            if game_mode:
                sc = _map_scan(vk)
                inp = _key_input(0, sc, KEYEVENTF_SCANCODE)
            else:
                inp = _key_input(vk, 0, 0)
            arr = (INPUT * 1)(inp)
            _send_input_checked(1, arr, what="modifier down")

    def _release_mods(mods: list[int]) -> None:
        for vk in reversed(mods):
            if game_mode:
                sc = _map_scan(vk)
                inp = _key_input(0, sc, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP)
            else:
                inp = _key_input(vk, 0, KEYEVENTF_KEYUP)
            arr = (INPUT * 1)(inp)
            _send_input_checked(1, arr, what="modifier up")

    mods = _modifier_vks()

    for seg in tokenize_keystroke_sequence(seq):
        if seg.kind == "text":
            _type_text_win(seg.value)
            continue

        resolved = _win_resolve_vk(seg.value)
        if resolved is None:
            continue
        kind, vk = resolved
        if kind == "mouse_left":
            _send_mouse(True)
            time.sleep(0.002)
            continue
        if kind == "mouse_right":
            _send_mouse(False)
            time.sleep(0.002)
            continue

        _press_mods(mods)
        try:
            if game_mode:
                sc = _map_scan(vk)
                ext = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_VKS else 0
                down = _key_input(0, sc, KEYEVENTF_SCANCODE | ext)
                arr_d = (INPUT * 1)(down)
                _send_input_checked(1, arr_d, what="tag key down (scan)")
                if hold_ms:
                    time.sleep(hold_ms / 1000.0)
                up = _key_input(0, sc, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP | ext)
                arr_u = (INPUT * 1)(up)
                _send_input_checked(1, arr_u, what="tag key up (scan)")
            else:
                ext = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_VKS else 0
                down = _key_input(vk, 0, ext)
                arr_d = (INPUT * 1)(down)
                _send_input_checked(1, arr_d, what="tag key down (vk)")
                if hold_ms:
                    time.sleep(hold_ms / 1000.0)
                up = _key_input(vk, 0, KEYEVENTF_KEYUP | ext)
                arr_u = (INPUT * 1)(up)
                _send_input_checked(1, arr_u, what="tag key up (vk)")
        finally:
            _release_mods(mods)
        time.sleep(0.002)
