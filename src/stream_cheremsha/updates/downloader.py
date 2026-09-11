from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx

from stream_cheremsha.updates.constants import HTTP_TIMEOUT_S, MIN_DOWNLOAD_SIZE_BYTES, USER_AGENT


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class DownloadCancelled(Exception):
    """Raised when a caller asks an in-progress download to stop."""


ProgressCallback = Callable[[int, int | None], None]
CancelCallback = Callable[[], bool]


def download_file(
    url: str,
    dest: Path,
    *,
    progress: ProgressCallback | None = None,
    cancelled: CancelCallback | None = None,
) -> None:
    """Download *url* atomically, optionally reporting actual transferred bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(f"{dest.name}.part")
    partial.unlink(missing_ok=True)

    try:
        with httpx.stream(
            "GET",
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT_S,
            follow_redirects=True,
        ) as r:
            r.raise_for_status()
            raw_total = r.headers.get("Content-Length", "").strip()
            total = int(raw_total) if raw_total.isdigit() else None
            downloaded = 0
            if progress is not None:
                progress(downloaded, total)
            with partial.open("wb") as f:
                for chunk in r.iter_bytes():
                    if cancelled is not None and cancelled():
                        raise DownloadCancelled
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(downloaded, total)

        size = partial.stat().st_size
        if size < MIN_DOWNLOAD_SIZE_BYTES:
            raise ValueError(f"Downloaded file too small ({size} bytes)")
        partial.replace(dest)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
