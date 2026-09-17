"""Build-time defaults for optional compile-time embedding (see cheremsha-build)."""

from __future__ import annotations

CLOUDFLARE_TUNNEL_TOKEN: str = ""
CLOUDFLARE_TUNNEL_HOSTNAME: str = ""
KICK_CLIENT_ID: str = ""
KICK_CLIENT_SECRET: str = ""
OVERLAY_CERTIFICATE: str = ""
OVERLAY_PRIVATE_KEY: str = ""
OVERLAY_PUBLIC_HOSTNAME: str = "app.cheremsha.click"
# Cheremsha Cloud API base URL. Compiled into the Nuitka build from
# STREAM_CHEREMSHA_CLOUD_API_URL (CI secret) or defaults to localhost for
# dev builds. See ``stream_cheremsha.cloud.constants.api_base_url`` which
# resolves: QSettings > runtime env > this embedded value > default.
CHEREMSHA_CLOUD_API_URL: str = ""

try:
    from stream_cheremsha.config.embedded_local import (
        CHEREMSHA_CLOUD_API_URL as _EMBEDDED_CHEREMSHA_CLOUD_API_URL,
    )
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
    from stream_cheremsha.config.embedded_local import (
        OVERLAY_CERTIFICATE as _EMBEDDED_OVERLAY_CERTIFICATE,
    )
    from stream_cheremsha.config.embedded_local import (
        OVERLAY_PRIVATE_KEY as _EMBEDDED_OVERLAY_PRIVATE_KEY,
    )
    from stream_cheremsha.config.embedded_local import (
        OVERLAY_PUBLIC_HOSTNAME as _EMBEDDED_OVERLAY_PUBLIC_HOSTNAME,
    )
except ImportError:
    pass
else:
    CLOUDFLARE_TUNNEL_TOKEN = _EMBEDDED_CLOUDFLARE_TUNNEL_TOKEN
    CLOUDFLARE_TUNNEL_HOSTNAME = _EMBEDDED_CLOUDFLARE_TUNNEL_HOSTNAME
    KICK_CLIENT_ID = _EMBEDDED_KICK_CLIENT_ID
    KICK_CLIENT_SECRET = _EMBEDDED_KICK_CLIENT_SECRET
    OVERLAY_CERTIFICATE = _EMBEDDED_OVERLAY_CERTIFICATE
    OVERLAY_PRIVATE_KEY = _EMBEDDED_OVERLAY_PRIVATE_KEY
    OVERLAY_PUBLIC_HOSTNAME = _EMBEDDED_OVERLAY_PUBLIC_HOSTNAME
    CHEREMSHA_CLOUD_API_URL = _EMBEDDED_CHEREMSHA_CLOUD_API_URL
