from __future__ import annotations

import re
from typing import Final

import httpx

from stream_cheremsha.updates.constants import HTTP_TIMEOUT_S, LATEST_MANIFEST_URL, USER_AGENT
from stream_cheremsha.updates.models import LatestManifest

_SEMVER_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)\s*$")


def _parse_semver(v: str) -> tuple[int, int, int]:
    m = _SEMVER_RE.match(v)
    if not m:
        raise ValueError(f"Invalid version: {v!r}")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def is_newer_version(latest: str, current: str) -> bool:
    return _parse_semver(latest) > _parse_semver(current)


def fetch_latest_manifest(*, url: str = LATEST_MANIFEST_URL) -> LatestManifest:
    r = httpx.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        timeout=HTTP_TIMEOUT_S,
        follow_redirects=True,
    )
    r.raise_for_status()
    return LatestManifest.from_json(r.text)
