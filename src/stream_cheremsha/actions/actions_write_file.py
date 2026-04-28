from __future__ import annotations

from pathlib import Path


def write_text_to_file(path: str, text: str, *, mode: str = "overwrite") -> None:
    p = Path((path or "").strip())
    if not p:
        raise ValueError("file_path is required")
    payload = str(text or "")

    # Ensure parent directory exists for nested paths.
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    m = (mode or "").strip().lower()
    if m in ("w", "write", "overwrite", "replace"):
        open_mode = "w"
    elif m in ("a", "append", "add"):
        open_mode = "a"
    else:
        raise ValueError('mode must be "overwrite" or "append"')

    if open_mode == "a":
        # Make append behave as "append a line" by default:
        # - If file doesn't end with newline, start on a new line
        # - If payload doesn't end with newline, terminate the line
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            try:
                with p.open("rb") as rf:
                    rf.seek(-1, 2)
                    last = rf.read(1)
            except OSError:
                last = b""
            if last not in (b"", b"\n") and payload and not payload.startswith("\n"):
                payload = "\n" + payload
        if payload and not payload.endswith("\n"):
            payload = payload + "\n"

    with p.open(open_mode, encoding="utf-8", newline="") as f:
        f.write(payload)


def append_text_to_file(path: str, text: str) -> None:
    # Back-compat wrapper (legacy name). Historically this overwrote the file.
    write_text_to_file(path, text, mode="overwrite")
