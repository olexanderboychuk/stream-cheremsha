"""Build-time defaults for optional compile-time embedding (see cheremsha-build)."""

from __future__ import annotations

CLOUDFLARE_TUNNEL_TOKEN: str = ""
CLOUDFLARE_TUNNEL_HOSTNAME: str = ""
KICK_CLIENT_ID: str = ""
KICK_CLIENT_SECRET: str = ""

try:
    from stream_cheremsha.config.embedded_local import (  # type: ignore[import-not-found]
        CLOUDFLARE_TUNNEL_HOSTNAME as _EMBEDDED_CLOUDFLARE_TUNNEL_HOSTNAME,
    )
    from stream_cheremsha.config.embedded_local import (
        CLOUDFLARE_TUNNEL_TOKEN as _EMBEDDED_CLOUDFLARE_TUNNEL_TOKEN,
    )
    from stream_cheremsha.config.embedded_local import (
        KICK_CLIENT_ID as _EMBEDDED_KICK_CLIENT_ID,
    )
    from stream_cheremsha.config.embedded_local import (
        KICK_CLIENT_SECRET as _EMBEDDED_KICK_CLIENT_SECRET,
    )
except ImportError:
    pass
else:
    CLOUDFLARE_TUNNEL_TOKEN = _EMBEDDED_CLOUDFLARE_TUNNEL_TOKEN
    CLOUDFLARE_TUNNEL_HOSTNAME = _EMBEDDED_CLOUDFLARE_TUNNEL_HOSTNAME
    KICK_CLIENT_ID = _EMBEDDED_KICK_CLIENT_ID
    KICK_CLIENT_SECRET = _EMBEDDED_KICK_CLIENT_SECRET
