from __future__ import annotations

import threading

import keyring
from keyring import errors

from stream_cheremsha.config import constants

# In-process read cache: every get_password() is a D-Bus SecretService
# round-trip (~7ms + DH handshake overhead), and startup performs dozens of
# them (measured ~0.41s across 63 calls). Secrets only change through our own
# set_password()/delete_password(), which keep the cache coherent.
_cache_lock = threading.Lock()
_cache: dict[str, str | None] = {}


def get_password(key: str) -> str | None:
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    try:
        value = keyring.get_password(constants.KEYRING_SERVICE, key)
    except errors.NoKeyringError:
        return None
    with _cache_lock:
        _cache[key] = value
    return value


def set_password(key: str, value: str) -> None:
    try:
        keyring.set_password(constants.KEYRING_SERVICE, key, value)
    except errors.NoKeyringError:
        raise RuntimeError(
            "No OS keyring backend (install SecretService/KWallet or `pip install keyrings.alt`)"
        ) from None
    with _cache_lock:
        _cache[key] = value


def delete_password(key: str) -> None:
    try:
        keyring.delete_password(constants.KEYRING_SERVICE, key)
    except (errors.NoKeyringError, errors.PasswordDeleteError):
        pass
    with _cache_lock:
        _cache.pop(key, None)
