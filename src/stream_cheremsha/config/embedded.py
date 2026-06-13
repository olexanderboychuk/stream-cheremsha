"""Build-time defaults for optional compile-time embedding (see cheremsha-build)."""

from __future__ import annotations

CLOUDFLARE_TUNNEL_TOKEN: str = ""
CLOUDFLARE_TUNNEL_HOSTNAME: str = ""

try:
    from stream_cheremsha.config.embedded_local import (  # type: ignore[import-not-found]
        CLOUDFLARE_TUNNEL_HOSTNAME as _EMBEDDED_CLOUDFLARE_TUNNEL_HOSTNAME,
    )
    from stream_cheremsha.config.embedded_local import (
        CLOUDFLARE_TUNNEL_TOKEN as _EMBEDDED_CLOUDFLARE_TUNNEL_TOKEN,
    )
except ImportError:
    pass
else:
    CLOUDFLARE_TUNNEL_TOKEN = _EMBEDDED_CLOUDFLARE_TUNNEL_TOKEN
    CLOUDFLARE_TUNNEL_HOSTNAME = _EMBEDDED_CLOUDFLARE_TUNNEL_HOSTNAME
