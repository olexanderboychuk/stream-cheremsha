"""Persistent Kick OAuth credentials (keyring) and bundle helpers."""

from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.config import constants, keyring_store

KICK_OAUTH_ACCESS = "access_token"
KICK_OAUTH_REFRESH = "refresh_token"
KICK_OAUTH_SCOPE = "scope"
KICK_OAUTH_EXPIRES_IN = "expires_in"


def save_oauth_bundle(payload: dict[str, Any]) -> None:
    """Persist a Kick OAuth token payload to the OS keyring."""
    keyring_store.set_password(constants.KEY_KICK_OAUTH, json.dumps(payload))


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
    save_oauth_bundle(current)


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
