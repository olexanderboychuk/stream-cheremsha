from __future__ import annotations

import os

from stream_cheremsha.config import constants, embedded, keyring_store


def resolve_cloudflare_tunnel_token() -> str:
    keyring = (keyring_store.get_password(constants.KEY_CLOUDFLARE_TUNNEL_TOKEN) or "").strip()
    if keyring:
        return keyring
    env = (os.environ.get(constants.ENV_CLOUDFLARE_TUNNEL_TOKEN) or "").strip()
    if env:
        return env
    return (embedded.CLOUDFLARE_TUNNEL_TOKEN or "").strip()


def resolve_cloudflare_tunnel_hostname(*, settings_value: str = "") -> str:
    configured = (settings_value or "").strip()
    if configured:
        return configured
    env = (os.environ.get(constants.ENV_CLOUDFLARE_TUNNEL_HOSTNAME) or "").strip()
    if env:
        return env
    return (embedded.CLOUDFLARE_TUNNEL_HOSTNAME or "").strip()


def cloudflare_tunnel_token_configured() -> bool:
    return bool(resolve_cloudflare_tunnel_token())
