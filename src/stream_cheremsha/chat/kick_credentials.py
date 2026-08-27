"""Persistent Kick OAuth credentials (keyring) and bundle helpers."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from stream_cheremsha.chat.kick_api import KickOAuthConfig, refresh_access_token
from stream_cheremsha.config import constants, keyring_store

logger = logging.getLogger(__name__)

KICK_OAUTH_ACCESS = "access_token"
KICK_OAUTH_REFRESH = "refresh_token"
KICK_OAUTH_SCOPE = "scope"
KICK_OAUTH_EXPIRES_IN = "expires_in"
KICK_OAUTH_ISSUED_AT = "issued_at"


def save_oauth_bundle(payload: dict[str, Any]) -> None:
    """Persist a Kick OAuth token payload to the OS keyring."""
    stored = dict(payload)
    stored[KICK_OAUTH_ISSUED_AT] = time.time()
    keyring_store.set_password(constants.KEY_KICK_OAUTH, json.dumps(stored))


def load_oauth_bundle() -> dict[str, Any]:
    raw = keyring_store.get_password(constants.KEY_KICK_OAUTH) or ""
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def clear_oauth_bundle() -> None:
    keyring_store.delete_password(constants.KEY_KICK_OAUTH)


def has_session() -> bool:
    return bool(load_oauth_bundle().get(KICK_OAUTH_ACCESS))


def access_token() -> str:
    return str(load_oauth_bundle().get(KICK_OAUTH_ACCESS) or "")


def refresh_token() -> str:
    return str(load_oauth_bundle().get(KICK_OAUTH_REFRESH) or "")


def merge_token_payload(payload: dict[str, Any]) -> None:
    """Merge a refreshed token payload into the stored bundle (keeps old fields)."""
    current = load_oauth_bundle()
    current.update(payload)
    if payload.get(KICK_OAUTH_ACCESS):
        current[KICK_OAUTH_ISSUED_AT] = time.time()
    save_oauth_bundle(current)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


async def ensure_valid_access_token() -> str:
    """Return a still-valid Kick access token, refreshing via OAuth if needed.

    Returns ``""`` when there is no usable session. Kick rotates refresh tokens
    on use, so the refreshed payload is merged back into the keyring bundle.
    """
    bundle = load_oauth_bundle()
    access = str(bundle.get(KICK_OAUTH_ACCESS) or "").strip()
    if not access:
        return ""
    refresh = str(bundle.get(KICK_OAUTH_REFRESH) or "").strip()
    cfg = KickOAuthConfig.from_env()
    if not refresh or cfg is None:
        return access
    issued_at = _as_float(bundle.get(KICK_OAUTH_ISSUED_AT))
    expires_in = _as_float(bundle.get(KICK_OAUTH_EXPIRES_IN))
    if issued_at and expires_in and time.time() - issued_at < expires_in - 60:
        return access
    try:
        payload = await refresh_access_token(cfg, refresh)
    except (ValueError, httpx.HTTPError, OSError, RuntimeError):
        logger.warning("Kick token refresh failed; keeping stored token", exc_info=True)
        return access
    new_access = str(payload.get(KICK_OAUTH_ACCESS) or "").strip()
    if not new_access:
        return access
    merge_token_payload(payload)
    return new_access


def set_authorized_channel(slug: str) -> None:
    """Persist the authorized channel slug to keyring."""
    s = (slug or "").strip().lstrip("@").strip()
    if s:
        keyring_store.set_password(constants.KEY_KICK_CHANNEL, s)
    else:
        keyring_store.delete_password(constants.KEY_KICK_CHANNEL)


def authorized_channel() -> str:
    return str(keyring_store.get_password(constants.KEY_KICK_CHANNEL) or "").strip()


def clear_channel() -> None:
    keyring_store.delete_password(constants.KEY_KICK_CHANNEL)


def set_chatroom_id(cid: int) -> None:
    if int(cid) > 0:
        keyring_store.set_password(constants.KEY_KICK_CHATROOM_ID, str(int(cid)))
    else:
        keyring_store.delete_password(constants.KEY_KICK_CHATROOM_ID)


def chatroom_id() -> int:
    raw = keyring_store.get_password(constants.KEY_KICK_CHATROOM_ID) or ""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0
