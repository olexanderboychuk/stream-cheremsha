from __future__ import annotations

from typing import Final

LATEST_MANIFEST_URL: Final[str] = (
    "https://github.com/olexanderboychuk/stream-cheremsha/releases/latest/download/latest.json"
)

HTTP_TIMEOUT_S: Final[float] = 5.0
USER_AGENT: Final[str] = "stream-cheremsha-updater/1"

# Sanity check for downloads (avoid writing HTML error pages, etc.).
MIN_DOWNLOAD_SIZE_BYTES: Final[int] = 128 * 1024
