"""
TikTok proxy failover — temporary hotfix.

ProxyManager fetches a free HTTP proxy list from ProxyScrape, caches it in-memory
for POOL_TTL_SEC, and provides a simple health-tracked pool with per-proxy cooldowns.

IMPORTANT: This is an emergency failover layer.  It is NOT a rotation mechanism.
- Direct connection is always tried first.
- Proxies are only used when direct fails with a retryable network error.
- A successful proxy is held for the rest of the session.
- No background polling; the pool is fetched lazily on first need.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

PROXYSCRAPE_URL = (
    "https://api.proxyscrape.com/v4/free-proxy-list/get"
    "?request=display_proxies&proxy_format=protocolipport&format=json"
)

POOL_TTL_SEC: float = 300.0          # refresh pool after 5 minutes
PROXYSCRAPE_FETCH_TIMEOUT_SEC: float = 8.0
MAX_PROXY_ATTEMPTS: int = 5          # max proxies tried per connection attempt
PROXY_FAILURE_COOLDOWN_SEC: float = 120.0  # cooldown after 3 consecutive failures
PROXY_MAX_FAILURES_BEFORE_COOLDOWN: int = 3

# Supported proxy schemes for httpx.Proxy native support.
# SOCKS proxy entries from ProxyScrape are currently skipped (can be added later
# via python_socks / WebcastProxy union type without changing this interface).
_SUPPORTED_SCHEMES = frozenset({"http", "https"})


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class ProxyEntry:
    """Runtime health state for a single proxy endpoint."""

    scheme: str      # "http" or "https"
    host: str
    port: int
    failures: int = 0
    successes: int = 0
    last_failure: float = field(default=0.0)
    cooldown_until: float = field(default=0.0)

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"

    def is_in_cooldown(self) -> bool:
        return self.cooldown_until > time.monotonic()

    def make_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class ProxyManager:
    """
    Lazy, cached, health-tracked proxy pool for TikTok failover.

    Thread/task safety: designed for single-async-task use inside
    TikTokChatSource._supervisor().  All state mutations happen from the
    event loop; no locking is needed.
    """

    def __init__(self) -> None:
        self._pool: list[ProxyEntry] = []
        self._pool_loaded_at: float = 0.0   # monotonic; 0 = never loaded
        self._fetch_lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_proxy_pool(self) -> list[ProxyEntry]:
        """
        Return the cached proxy pool, fetching it lazily if needed.

        Never raises — if ProxyScrape is unavailable the returned list is
        empty and the caller should fall back to direct connection.
        """
        now = time.monotonic()
        if self._pool and (now - self._pool_loaded_at) < POOL_TTL_SEC:
            return self._pool
        return await self.refresh_proxy_pool()

    async def refresh_proxy_pool(self) -> list[ProxyEntry]:
        """Force-refresh the proxy pool from ProxyScrape."""
        async with self._fetch_lock:
            # Double-check after acquiring the lock (another coroutine may
            # have already refreshed while we were waiting).
            now = time.monotonic()
            if self._pool and (now - self._pool_loaded_at) < POOL_TTL_SEC:
                return self._pool

            try:
                entries = await self._fetch_and_parse()
            except Exception as exc:  # noqa: BLE001
                # Proxy subsystem must NEVER crash TikTokService.
                logger.warning("TikTok proxy pool fetch failed: %s", exc)
                return self._pool  # return stale pool rather than crashing

            # Merge: preserve health counters for proxies already in the pool.
            existing: dict[str, ProxyEntry] = {e.key: e for e in self._pool}
            merged: list[ProxyEntry] = []
            seen: set[str] = set()
            for entry in entries:
                k = entry.key
                if k in seen:
                    continue
                seen.add(k)
                if k in existing:
                    # Preserve runtime health state from current session.
                    old = existing[k]
                    old.scheme = entry.scheme  # update scheme if changed
                    merged.append(old)
                else:
                    merged.append(entry)

            self._pool = merged
            self._pool_loaded_at = time.monotonic()
            logger.info("TikTok proxy pool loaded: %d proxies", len(self._pool))
            return self._pool

    def get_next_proxy(self, skip: set[str]) -> ProxyEntry | None:
        """
        Return the next available proxy, skipping entries in *skip* and those
        on cooldown.  Returns None when the pool is exhausted.

        *skip* should contain proxy keys (``host:port``) already attempted
        in the current failover sequence.
        """
        for entry in self._pool:
            if entry.key in skip:
                continue
            if entry.is_in_cooldown():
                logger.debug(
                    "TikTok proxy skipped (cooldown): %s", entry.key
                )
                continue
            return entry
        return None

    def report_success(self, proxy: ProxyEntry) -> None:
        """Mark a proxy as having succeeded; resets failure counter."""
        proxy.successes += 1
        proxy.failures = 0
        proxy.cooldown_until = 0.0
        logger.debug("TikTok proxy success: %s", proxy.key)

    def report_failure(self, proxy: ProxyEntry) -> None:
        """Mark a proxy as having failed; applies cooldown after threshold."""
        proxy.failures += 1
        proxy.last_failure = time.monotonic()
        if proxy.failures >= PROXY_MAX_FAILURES_BEFORE_COOLDOWN:
            proxy.cooldown_until = time.monotonic() + PROXY_FAILURE_COOLDOWN_SEC
            logger.debug(
                "TikTok proxy %s in cooldown for %.0fs (failures=%d)",
                proxy.key,
                PROXY_FAILURE_COOLDOWN_SEC,
                proxy.failures,
            )

    def make_httpx_proxy(self, entry: ProxyEntry) -> httpx.Proxy:
        """Build an ``httpx.Proxy`` object from a *ProxyEntry*."""
        return httpx.Proxy(entry.make_url())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _fetch_and_parse(self) -> list[ProxyEntry]:
        """
        Fetch the ProxyScrape proxy list and parse it into ProxyEntry objects.

        Malformed/unsupported/duplicate entries are silently skipped.
        Returns an empty list on network error or JSON parse failure.
        """
        logger.info("TikTok proxy pool: fetching from ProxyScrape…")
        try:
            async with httpx.AsyncClient(timeout=PROXYSCRAPE_FETCH_TIMEOUT_SEC) as client:
                resp = await client.get(PROXYSCRAPE_URL)
                resp.raise_for_status()
                raw = resp.text
        except Exception as exc:
            logger.warning("TikTok ProxyScrape HTTP fetch failed: %s", exc)
            return []

        return _parse_proxyscrape_response(raw)


# ---------------------------------------------------------------------------
# Parsing (pure function — easy to unit-test in isolation)
# ---------------------------------------------------------------------------


def _parse_proxyscrape_response(raw: str) -> list[ProxyEntry]:
    """
    Parse the ProxyScrape v4 JSON response.

    Expected shape::

        {
            "proxies": [
                {"protocol": "http", "ip": "1.2.3.4", "port": 8080, ...},
                ...
            ]
        }

    Invalid / unsupported entries are silently dropped.
    Returned list is deduplicated by (host, port).
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("TikTok ProxyScrape JSON parse error: %s", exc)
        return []

    if not isinstance(data, dict):
        logger.warning("TikTok ProxyScrape: unexpected top-level type %s", type(data).__name__)
        return []

    proxies_raw = data.get("proxies")
    if not isinstance(proxies_raw, list):
        logger.warning("TikTok ProxyScrape: 'proxies' field missing or not a list")
        return []

    entries: list[ProxyEntry] = []
    seen: set[str] = set()

    for item in proxies_raw:
        entry = _parse_proxy_item(item)
        if entry is None:
            continue
        k = entry.key
        if k in seen:
            continue
        seen.add(k)
        entries.append(entry)

    return entries


def _parse_proxy_item(item: object) -> ProxyEntry | None:
    """
    Parse a single proxy dict from the ProxyScrape list.

    Returns None for any malformed / unsupported entry.
    """
    if not isinstance(item, dict):
        return None

    # Protocol / scheme
    protocol = item.get("protocol") or item.get("scheme") or ""
    if not isinstance(protocol, str):
        return None
    scheme = protocol.strip().lower()
    if scheme not in _SUPPORTED_SCHEMES:
        return None  # skip SOCKS entries (http/https only for this hotfix)

    # IP / host
    host = item.get("ip") or item.get("host") or ""
    if not isinstance(host, str) or not host.strip():
        return None
    host = host.strip()

    # Port
    raw_port = item.get("port")
    if raw_port is None:
        return None
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        return None
    if not (1 <= port <= 65535):
        return None

    return ProxyEntry(scheme=scheme, host=host, port=port)
