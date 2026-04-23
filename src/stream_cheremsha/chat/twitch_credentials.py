from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from stream_cheremsha.chat import twitch_oauth_device
from stream_cheremsha.config import constants, keyring_store


@dataclass(frozen=True, slots=True)
class TwitchOAuthBundle:
    access_token: str
    refresh_token: str | None
    expires_at: float | None
    authorized_login: str | None = None


def _load_oauth_raw() -> dict[str, Any] | None:
    raw = keyring_store.get_password(constants.KEY_TWITCH_OAUTH)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_oauth_bundle(
    token_response: dict[str, Any],
    *,
    client_id: str,
    authorized_login: str | None = None,
) -> TwitchOAuthBundle:
    """Persist Twitch token response; ``expires_in`` is seconds from now."""
    access = token_response.get("access_token")
    if not isinstance(access, str) or not access:
        raise ValueError("Twitch response missing access_token")
    prior = load_oauth_bundle()
    prior_raw = _load_oauth_raw()
    refresh = token_response.get("refresh_token")
    refresh_s = refresh if isinstance(refresh, str) and refresh else None
    if refresh_s is None and prior is not None:
        refresh_s = prior.refresh_token

    expires_in = token_response.get("expires_in")
    expires_at: float | None = None
    if isinstance(expires_in, (int, float)):
        expires_at = time.time() + float(expires_in)

    login_out: str | None = None
    if authorized_login and authorized_login.strip():
        login_out = authorized_login.strip().lower()
    elif prior_raw and isinstance(prior_raw.get("authorized_login"), str):
        login_out = prior_raw["authorized_login"].strip().lower() or None

    bundle: dict[str, Any] = {
        "access_token": access,
        "refresh_token": refresh_s,
        "expires_at": expires_at,
        "client_id": client_id,
    }
    if login_out:
        bundle["authorized_login"] = login_out

    keyring_store.set_password(constants.KEY_TWITCH_OAUTH, json.dumps(bundle))
    return TwitchOAuthBundle(
        access_token=access,
        refresh_token=refresh_s,
        expires_at=expires_at,
        authorized_login=login_out,
    )


def set_authorized_login(login: str) -> None:
    """Attach Twitch ``login`` from /validate to the stored OAuth blob."""
    raw = _load_oauth_raw()
    if not raw:
        return
    raw["authorized_login"] = login.strip().lower()
    keyring_store.set_password(constants.KEY_TWITCH_OAUTH, json.dumps(raw))


def load_oauth_bundle() -> TwitchOAuthBundle | None:
    data = _load_oauth_raw()
    if not data:
        return None
    access = data.get("access_token")
    if not isinstance(access, str) or not access:
        return None
    refresh = data.get("refresh_token")
    refresh_s = refresh if isinstance(refresh, str) and refresh else None
    exp = data.get("expires_at")
    exp_f = float(exp) if isinstance(exp, (int, float)) else None
    al = data.get("authorized_login")
    al_s = al.strip().lower() if isinstance(al, str) and al.strip() else None
    return TwitchOAuthBundle(
        access_token=access,
        refresh_token=refresh_s,
        expires_at=exp_f,
        authorized_login=al_s,
    )


def clear_twitch_session() -> None:
    """Remove Twitch OAuth and manual token from keyring (not app Client ID/secret)."""
    keyring_store.delete_password(constants.KEY_TWITCH_OAUTH)
    keyring_store.delete_password(constants.KEY_TWITCH_TOKEN)


def twitch_keyring_has_session() -> bool:
    """True if browser OAuth bundle or a saved manual token exists."""
    if load_oauth_bundle() is not None:
        return True
    tok = keyring_store.get_password(constants.KEY_TWITCH_TOKEN)
    return bool(tok and tok.strip())


async def ensure_fresh_access_token(
    client_id: str,
    client_secret: str | None,
    *,
    skew_sec: float = 120.0,
) -> str | None:
    """Return a usable OAuth access token from keyring, refreshing when near expiry."""
    bundle = load_oauth_bundle()
    if bundle is None:
        return None

    cid = client_id.strip()
    if not cid:
        raw = _load_oauth_raw()
        if raw and isinstance(raw.get("client_id"), str):
            cid = raw["client_id"].strip()
    if not cid:
        return None

    now = time.time()
    if bundle.expires_at is None:
        return bundle.access_token

    expired_or_soon = now >= bundle.expires_at - skew_sec
    if not expired_or_soon:
        return bundle.access_token

    if not bundle.refresh_token:
        return None

    refreshed = await twitch_oauth_device.refresh_access_token(
        cid,
        bundle.refresh_token,
        client_secret,
    )
    updated = save_oauth_bundle(refreshed, client_id=cid, authorized_login=bundle.authorized_login)
    return updated.access_token
