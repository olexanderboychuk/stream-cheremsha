"""Download and validate the public TLS certificate used by the overlay server."""

from __future__ import annotations

import logging
import os
import ssl
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

CERTS_DIR = Path("certs")
CERT_PATH = CERTS_DIR / "cert.pem"
KEY_PATH = CERTS_DIR / "key.pem"
CERT_URL = "https://ssl.cheremsha.click/cert.pem"
KEY_URL = "https://ssl.cheremsha.click/key.pem"
_REQUEST_TIMEOUT_SECONDS = 20


def is_cert_expiring_soon(cert_path: str, days_threshold: int = 14) -> bool:
    """Return whether a certificate is missing, invalid, or expires soon."""
    path = Path(cert_path)
    try:
        certificate = x509.load_pem_x509_certificate(path.read_bytes(), default_backend())
        expires_at = getattr(certificate, "not_valid_after_utc", None)
        if expires_at is None:
            expires_at = certificate.not_valid_after.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC) + timedelta(
            days=max(0, int(days_threshold))
        )
    except (OSError, ValueError, TypeError):
        return True


def _download(url: str, destination: Path) -> None:
    response = requests.get(url, timeout=_REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    destination.write_bytes(response.content)


def _ssl_pair_is_valid(cert_path: Path, key_path: Path) -> bool:
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    except (OSError, ssl.SSLError):
        return False
    return True


def download_fresh_certs() -> None:
    """Download both certificate files atomically into ``./certs``."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CERTS_DIR) as temp_dir:
        temp = Path(temp_dir)
        cert_tmp = temp / "cert.pem"
        key_tmp = temp / "key.pem"
        _download(CERT_URL, cert_tmp)
        _download(KEY_URL, key_tmp)
        if not _ssl_pair_is_valid(cert_tmp, key_tmp):
            raise ssl.SSLError("downloaded certificate and private key are not a valid pair")
        os.replace(cert_tmp, CERT_PATH)
        os.replace(key_tmp, KEY_PATH)
    KEY_PATH.chmod(0o600)


def ensure_valid_ssl() -> tuple[Path, Path] | None:
    """Refresh certificates when needed, falling back to existing valid files."""
    needs_refresh = (
        is_cert_expiring_soon(str(CERT_PATH))
        or not KEY_PATH.is_file()
        or not _ssl_pair_is_valid(CERT_PATH, KEY_PATH)
    )
    if needs_refresh:
        try:
            download_fresh_certs()
            logger.info("Downloaded fresh overlay TLS certificates")
        except (OSError, requests.RequestException, ssl.SSLError) as error:
            logger.error("Unable to refresh overlay TLS certificates: %s", error)

    if (
        CERT_PATH.is_file()
        and KEY_PATH.is_file()
        and _ssl_pair_is_valid(CERT_PATH, KEY_PATH)
    ):
        return CERT_PATH, KEY_PATH
    logger.error("Overlay TLS certificates are unavailable")
    return None
