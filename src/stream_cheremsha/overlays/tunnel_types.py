from __future__ import annotations

from enum import StrEnum


class TunnelProvider(StrEnum):
    NONE = "none"
    NGROK = "ngrok"
    CLOUDFLARE = "cloudflare"
    CUSTOM = "custom"
