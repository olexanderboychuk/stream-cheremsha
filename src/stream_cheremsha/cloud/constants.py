"""Cheremsha Cloud API configuration (desktop side).

The desktop is a PUBLIC client: it holds no provider client secrets and never
sees provider OAuth tokens. All values here are public configuration; the only
secrets the desktop ever stores are its own Cheremsha session credentials,
kept in the OS keyring (see ``session_store``).
"""

from __future__ import annotations

import os

# Default Cloud API base: local backend. CI/release builds override this via
# the Nuitka-baked ``embedded.CHEREMSHA_CLOUD_API_URL`` (from the
# ``STREAM_CHEREMSHA_CLOUD_API_URL`` secret). Resolution order at runtime:
# QSettings > runtime env > embedded value > this default.
#   PowerShell: $env:STREAM_CHEREMSHA_CLOUD_API_URL="http://localhost:8000"
#   bash:       export STREAM_CHEREMSHA_CLOUD_API_URL="http://localhost:8000"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
ENV_API_BASE_URL = "STREAM_CHEREMSHA_CLOUD_API_URL"
SETTINGS_API_BASE_URL = "cloud/api_base_url"

ENV_DASHBOARD_URL = "STREAM_CHEREMSHA_CLOUD_DASHBOARD_URL"
DEFAULT_DASHBOARD_URL = "https://account.cheremsha.app/dashboard"

HTTP_TIMEOUT_S = 15.0
AVATAR_TIMEOUT_S = 10.0

# Loopback callback for the desktop login flow. Must match the Cloud API
# ``DESKTOP_CALLBACK_URL`` (default ``http://127.0.0.1:8471/callback``).
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8471
CALLBACK_PATH = "/callback"

# How long we wait for the user to finish in the system browser.
LOGIN_WAIT_TIMEOUT_S = 600.0

# Keyring keys for the Cheremsha session bundle (own credentials only —
# never provider tokens).
KEY_CHEREMSHA_SESSION = "cheremsha_session_json"

LOGIN_PROVIDERS: tuple[str, ...] = ("google", "twitch", "tiktok", "kick")
CLOUD_PLATFORMS: tuple[str, ...] = ("twitch", "tiktok", "kick", "youtube")


def api_base_url(settings_get: object = None) -> str:
    """Resolve the Cloud API base URL: QSettings > runtime env > embedded > default."""
    if settings_get is not None:
        try:
            value = settings_get(SETTINGS_API_BASE_URL, "", str)  # type: ignore[operator]
            if isinstance(value, str) and value.strip():
                return value.strip().rstrip("/")
        except Exception:
            pass
    env_value = (os.environ.get(ENV_API_BASE_URL) or "").strip()
    if env_value:
        return env_value.rstrip("/")
    embedded_value = ""
    try:
        from stream_cheremsha.config import embedded as _embedded

        embedded_value = (_embedded.CHEREMSHA_CLOUD_API_URL or "").strip()
    except Exception:
        embedded_value = ""
    if embedded_value:
        return embedded_value.rstrip("/")
    return DEFAULT_API_BASE_URL


def dashboard_url() -> str:
    env_value = (os.environ.get(ENV_DASHBOARD_URL) or "").strip()
    if env_value:
        return env_value
    return DEFAULT_DASHBOARD_URL
