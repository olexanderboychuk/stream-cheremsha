from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_NGROK_DEV_DOMAIN_SUFFIXES = (".ngrok-free.dev", ".ngrok-free.app", ".ngrok-free.pizza")
_NGROK_DOMAIN_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.ngrok-free\.(?:dev|app|pizza))$",
    re.IGNORECASE,
)


def normalize_ngrok_domain(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    for prefix in ("https://", "http://"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
    return raw.split("/", 1)[0].strip()


def is_ngrok_dev_domain(hostname: str) -> bool:
    host = normalize_ngrok_domain(hostname)
    if not host:
        return False
    return any(host.endswith(suffix) for suffix in _NGROK_DEV_DOMAIN_SUFFIXES)


def validate_ngrok_domain(hostname: str) -> str:
    host = normalize_ngrok_domain(hostname)
    if not host:
        raise ValueError("ngrok domain is empty")
    if not _NGROK_DOMAIN_RE.match(host):
        raise ValueError(
            "ngrok domain must look like abc123.ngrok-free.dev (see dashboard.ngrok.com/domains)"
        )
    return host


def fetch_ngrok_dev_domain(authtoken: str) -> str:
    token = str(authtoken or "").strip()
    if not token:
        return ""
    headers = {
        "Authorization": f"Bearer {token}",
        "Ngrok-Version": "2",
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://api.ngrok.com/reserved_domains",
                headers=headers,
                params={"limit": "25"},
            )
    except httpx.HTTPError as e:
        logger.debug("ngrok reserved_domains request failed: %s", e)
        return ""

    if resp.status_code != 200:
        logger.debug("ngrok reserved_domains HTTP %s: %s", resp.status_code, resp.text[:200])
        return ""

    payload = resp.json()
    rows = payload.get("reserved_domains")
    if not isinstance(rows, list):
        return ""

    dev_domains: list[str] = []
    other_domains: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        hostname = normalize_ngrok_domain(str(row.get("domain") or row.get("hostname") or ""))
        if not hostname:
            continue
        if is_ngrok_dev_domain(hostname):
            dev_domains.append(hostname)
        else:
            other_domains.append(hostname)

    if dev_domains:
        return sorted(dev_domains)[0]
    if other_domains:
        return sorted(other_domains)[0]
    return ""
