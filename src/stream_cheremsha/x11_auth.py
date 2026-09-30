"""X11 cookie self-heal for python-xlib (pynput) on this desktop.

Some sessions ship an $XAUTHORITY whose entries are keyed by a stale hostname;
python-xlib matches family+address exactly (socket.gethostname()), so pynput's
import-time Display() fails with "Authorization required, but no authorization
protocol specified". Qt/libxcb tolerates the same file (wildcard fallback),
which is why only pynput-based features break.

Call :func:`ensure_x_authority` before importing pynput; it is idempotent and
a no-op when DISPLAY is unset or the file already matches this host.
"""

from __future__ import annotations

import logging
import os
import socket
import struct
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _xauth_entries(raw: bytes) -> list[tuple[int, bytes, bytes, bytes, bytes]]:
    """Parse xauthority entries as (family, addr, num, name, data)."""
    out: list[tuple[int, bytes, bytes, bytes, bytes]] = []
    n = 0
    try:
        while n < len(raw):
            family = struct.unpack(">H", raw[n : n + 2])[0]
            n += 2
            parts: list[bytes] = []
            for _ in range(4):
                length = struct.unpack(">H", raw[n : n + 2])[0]
                parts.append(raw[n + 2 : n + 2 + length])
                n += 2 + length
            out.append((family, *parts))
    except (struct.error, IndexError):
        pass
    return out


def ensure_x_authority() -> None:
    """Point XAUTHORITY at a cookie file python-xlib can actually match.

    If no entry for the current host exists in $XAUTHORITY (or ~/.Xauthority),
    copy that file into ``$XDG_CACHE_HOME/cheremsha/xauth`` (default
    ``~/.cache/cheremsha/xauth``), append one entry for this host reusing an
    existing MIT-MAGIC-COOKIE-1, and point XAUTHORITY at the copy. The source
    file is never modified; the copy is rewritten from scratch on each repair
    (bounded size) with 0600 permissions.
    """
    if sys.platform != "linux" or not os.environ.get("DISPLAY"):
        return
    source = Path(os.environ.get("XAUTHORITY") or str(Path.home() / ".Xauthority"))
    try:
        raw = source.read_bytes()
    except OSError:
        return

    host = socket.gethostname().encode()
    dispno = os.environ["DISPLAY"].rsplit(":", 1)[-1].encode()
    entries = _xauth_entries(raw)
    if any(
        fam == 256 and addr == host and num in (b"", dispno) for fam, addr, num, _, _ in entries
    ):
        return
    cookie = next((data for _, _, _, name, data in entries if name == b"MIT-MAGIC-COOKIE-1"), None)
    if cookie is None:
        return

    cache = Path(os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")) / "cheremsha"
    entry = (
        struct.pack(">H", 256)
        + struct.pack(">H", len(host))
        + host
        + struct.pack(">H", len(dispno))
        + dispno
        + struct.pack(">H", len(b"MIT-MAGIC-COOKIE-1"))
        + b"MIT-MAGIC-COOKIE-1"
        + struct.pack(">H", len(cookie))
        + cookie
    )
    try:
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / "xauth"
        tmp = target.parent / (target.name + ".tmp")
        tmp.write_bytes(raw + entry)
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
    except OSError as e:
        logger.debug("xauth fixup failed: %s", e)
        return
    os.environ["XAUTHORITY"] = str(target)
