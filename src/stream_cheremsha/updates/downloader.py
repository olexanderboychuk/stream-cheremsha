from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from stream_cheremsha.updates.constants import HTTP_TIMEOUT_S, MIN_DOWNLOAD_SIZE_BYTES, USER_AGENT


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT_S,
        follow_redirects=True,
    ) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for b in r.iter_bytes():
                f.write(b)

    size = dest.stat().st_size
    if size < MIN_DOWNLOAD_SIZE_BYTES:
        raise ValueError(f"Downloaded file too small ({size} bytes)")
