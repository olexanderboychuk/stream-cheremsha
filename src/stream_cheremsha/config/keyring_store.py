from __future__ import annotations

import keyring
from keyring import errors

from stream_cheremsha.config import constants


def get_password(key: str) -> str | None:
    try:
        return keyring.get_password(constants.KEYRING_SERVICE, key)
    except errors.NoKeyringError:
        return None


def set_password(key: str, value: str) -> None:
    try:
        keyring.set_password(constants.KEYRING_SERVICE, key, value)
    except errors.NoKeyringError:
        raise RuntimeError(
            "No OS keyring backend (install SecretService/KWallet or `pip install keyrings.alt`)"
        ) from None


def delete_password(key: str) -> None:
    try:
        keyring.delete_password(constants.KEYRING_SERVICE, key)
    except (errors.NoKeyringError, errors.PasswordDeleteError):
        pass
