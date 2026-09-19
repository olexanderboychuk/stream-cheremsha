"""Keyring-backed storage for the Cheremsha desktop session.

Stores ONLY the desktop's own Cheremsha credentials (access + refresh tokens
plus a user snapshot). Provider OAuth tokens/secrets are never handled here —
they belong exclusively to Cheremsha Cloud API.

Follows the ``chat/twitch_credentials.py`` bundle pattern: one JSON blob in
one keyring key, via ``config/keyring_store.py`` (no direct keychain code).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass

from stream_cheremsha.cloud import constants
from stream_cheremsha.config import keyring_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CheremshaSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    display_name: str
    avatar_url: str | None = None
    saved_at: float = 0.0


def save_session(session: CheremshaSession) -> None:
    payload = asdict(session)
    payload["saved_at"] = time.time()
    try:
        keyring_store.set_password(constants.KEY_CHEREMSHA_SESSION, json.dumps(payload))
    except RuntimeError:
        # No OS keyring: session simply won't survive restarts. The in-memory
        # session keeps working for this run.
        logger.debug("cheremsha session not persisted (no keyring backend)")


def load_session() -> CheremshaSession | None:
    try:
        raw = keyring_store.get_password(constants.KEY_CHEREMSHA_SESSION)
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or not data.get("access_token") or not data.get("user_id"):
        return None
    try:
        return CheremshaSession(
            access_token=str(data["access_token"]),
            refresh_token=str(data.get("refresh_token") or ""),
            user_id=str(data["user_id"]),
            email=str(data.get("email") or ""),
            display_name=str(data.get("display_name") or ""),
            avatar_url=str(data["avatar_url"]) if data.get("avatar_url") else None,
            saved_at=float(data.get("saved_at") or 0.0),
        )
    except (TypeError, ValueError):
        return None


def clear_session() -> None:
    try:
        keyring_store.delete_password(constants.KEY_CHEREMSHA_SESSION)
    except Exception:
        pass
