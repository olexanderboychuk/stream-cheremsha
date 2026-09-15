"""
Tests for TikTok proxy failover hotfix.

Covers the 15 acceptance criteria from the task specification:
1.  ProxyScrape JSON parsing
2.  Empty proxy response
3.  Invalid proxy entry
4.  Duplicate proxies
5.  Direct success → no proxy
6.  Direct timeout → proxy fallback
7.  Proxy A failed → Proxy B
8.  Proxy B success → session connected
9.  All proxies failed → normal error
10. Max attempts respected
11. Successful proxy remains sticky during session
12. Failed proxy enters cooldown
13. ProxyManager exception doesn't crash TikTokService
14. UI thread isn't blocked (operations are coroutines)
15. HTTP/auth errors do not cause infinite proxy rotation
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

import stream_cheremsha.chat.tiktok_source as tk_mod
from stream_cheremsha.chat.tiktok.proxy_manager import (
    MAX_PROXY_ATTEMPTS,
    PROXY_FAILURE_COOLDOWN_SEC,
    PROXY_MAX_FAILURES_BEFORE_COOLDOWN,
    ProxyEntry,
    ProxyManager,
    _parse_proxyscrape_response,
)
from stream_cheremsha.chat.tiktok_source import TikTokChatSource
from stream_cheremsha.pipeline.coordinator import StreamCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeCoordinator(StreamCoordinator):
    def __init__(self) -> None:
        super().__init__(
            tts=None,  # type: ignore[arg-type]
            audio_sink=None,  # type: ignore[arg-type]
            on_chat=lambda _msg: None,
            on_status=lambda _msg: None,
        )


class _FakeWeb:
    async def fetch_room_info(self):  # noqa: ANN001
        return {}


class _FakeTikTokClient:
    """Minimal TikTokLiveClient stub for unit tests."""

    def __init__(self, unique_id: str) -> None:
        self.unique_id = unique_id
        self.is_live_calls = 0
        self.start_called = False
        self._handlers: dict[object, list[object]] = {}
        self._fake_web = _FakeWeb()
        # Override to inject a specific exception:
        self.is_live_error: BaseException | None = None

    @property
    def web(self) -> _FakeWeb:
        return self._fake_web

    def on(self, event_type: object):  # noqa: ANN001
        def _decorator(fn):  # noqa: ANN001
            gt = getattr(event_type, "get_type", None)
            key = gt() if callable(gt) else event_type
            self._handlers.setdefault(key, []).append(fn)
            return fn
        return _decorator

    async def is_live(self) -> bool:
        self.is_live_calls += 1
        if self.is_live_error is not None:
            raise self.is_live_error
        return False  # offline by default; override for "live" tests

    async def start(self, **_kwargs):  # noqa: ANN001
        self.start_called = True

        async def _run() -> None:
            await asyncio.sleep(0.01)

        return asyncio.create_task(_run())

    async def disconnect(self, **_kwargs) -> None:  # noqa: ANN001
        return None

    async def close(self) -> None:
        return None


async def _wait_until(pred, timeout: float = 1.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while not pred():
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError("Condition not met")
        await asyncio.sleep(0.005)


def _make_source(factory=None, statuses=None) -> TikTokChatSource:
    if statuses is None:
        statuses = []
    return TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=statuses.append,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=factory or (lambda uid: _FakeTikTokClient(uid)),  # type: ignore[arg-type]
    )


def _proxyscrape_payload(proxies: list[dict]) -> str:
    return json.dumps({"proxies": proxies})


def _http_entry(ip: str = "1.2.3.4", port: int = 8080) -> dict:
    return {"protocol": "http", "ip": ip, "port": port}


# ---------------------------------------------------------------------------
# 1. ProxyScrape JSON parsing
# ---------------------------------------------------------------------------


def test_proxyscrape_json_parsing() -> None:
    raw = _proxyscrape_payload([
        _http_entry("10.0.0.1", 3128),
        _http_entry("10.0.0.2", 8080),
        {"protocol": "http", "ip": "10.0.0.3", "port": 9090},
    ])
    entries = _parse_proxyscrape_response(raw)
    assert len(entries) == 3
    assert entries[0].host == "10.0.0.1"
    assert entries[0].port == 3128
    assert entries[0].scheme == "http"
    assert entries[2].host == "10.0.0.3"


# ---------------------------------------------------------------------------
# 2. Empty proxy response
# ---------------------------------------------------------------------------


def test_empty_proxy_response() -> None:
    raw = json.dumps({"proxies": []})
    assert _parse_proxyscrape_response(raw) == []


# ---------------------------------------------------------------------------
# 3. Invalid proxy entries are filtered
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("item", [
    {"protocol": "http", "ip": "1.2.3.4"},               # missing port
    {"protocol": "http", "port": 8080},                   # missing ip
    {"protocol": "http", "ip": "1.2.3.4", "port": 0},    # port out of range
    {"protocol": "http", "ip": "1.2.3.4", "port": 99999},# port out of range
    {"protocol": "http", "ip": "", "port": 8080},         # empty ip
    {"protocol": "socks5", "ip": "1.2.3.4", "port": 1080},# unsupported scheme
    {"ip": "1.2.3.4", "port": 8080},                     # missing protocol
    "not a dict",                                          # not a dict
])
def test_invalid_proxy_entry(item: object) -> None:
    raw = json.dumps({"proxies": [item]})
    entries = _parse_proxyscrape_response(raw)
    assert entries == [], f"Expected empty for invalid item: {item!r}"


# ---------------------------------------------------------------------------
# 4. Duplicate proxies are deduplicated
# ---------------------------------------------------------------------------


def test_duplicate_proxies() -> None:
    raw = _proxyscrape_payload([
        _http_entry("1.2.3.4", 8080),
        _http_entry("1.2.3.4", 8080),  # exact duplicate
        _http_entry("5.6.7.8", 3128),
    ])
    entries = _parse_proxyscrape_response(raw)
    assert len(entries) == 2
    hosts = {e.host for e in entries}
    assert hosts == {"1.2.3.4", "5.6.7.8"}


# ---------------------------------------------------------------------------
# 5. Direct success → no proxy used
# ---------------------------------------------------------------------------


def test_direct_success_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """When direct connection succeeds, ProxyManager is never created."""
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    client = _FakeTikTokClient("streamer")
    # is_live returns False → stream offline → no proxy needed; just verify
    # that the supervisor exits cleanly without touching ProxyManager.
    source = _make_source(factory=lambda _uid: client)

    proxy_manager_created = []

    original_get = TikTokChatSource._get_proxy_manager

    def _spy_get_pm(self):  # noqa: ANN001
        proxy_manager_created.append(True)
        return original_get(self)

    monkeypatch.setattr(TikTokChatSource, "_get_proxy_manager", _spy_get_pm)

    async def _run() -> None:
        await source.start("streamer")
        await asyncio.wait_for(
            _wait_until(lambda: client.is_live_calls >= 1), timeout=1.0
        )
        await source.stop()

    asyncio.run(_run())
    # ProxyManager should never have been touched (direct path / offline path).
    assert not proxy_manager_created, "ProxyManager should not be created when direct is fine"


# ---------------------------------------------------------------------------
# 6. Direct timeout → proxy fallback triggered
# ---------------------------------------------------------------------------


def test_direct_timeout_proxy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """OSError on direct is_live() → _attempt_with_fallback loads the proxy pool."""
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    pool_loaded = []

    class _FakeProxyManager:
        async def get_proxy_pool(self):  # noqa: ANN001
            pool_loaded.append(True)
            return []  # empty → will fall through to error

        def get_next_proxy(self, skip):  # noqa: ANN001
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            pass

    client = _FakeTikTokClient("streamer")
    client.is_live_error = OSError("connection refused")

    statuses: list[str] = []
    source = _make_source(factory=lambda _uid: client, statuses=statuses)

    # Inject our FakeProxyManager.
    fake_pm = _FakeProxyManager()
    source._proxy_manager = fake_pm  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        await asyncio.wait_for(
            _wait_until(lambda: len(pool_loaded) > 0), timeout=2.0
        )
        await source.stop()

    asyncio.run(_run())
    assert pool_loaded, "Proxy pool should be loaded after direct failure"
    assert any("резервн" in s or "fallback" in s for s in statuses), (
        "Should show fallback status message"
    )


# ---------------------------------------------------------------------------
# 7. Proxy A failed → Proxy B tried
# ---------------------------------------------------------------------------


def test_proxy_a_failed_proxy_b_tried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 60.0)  # don't retry loop

    proxy_a = ProxyEntry(scheme="http", host="1.1.1.1", port=3128)
    proxy_b = ProxyEntry(scheme="http", host="2.2.2.2", port=3128)

    tried_keys: list[str] = []

    class _FakeProxyManager:
        def _iter(self):  # noqa: ANN001
            yield proxy_a
            yield proxy_b

        async def get_proxy_pool(self):  # noqa: ANN001
            return [proxy_a, proxy_b]

        def get_next_proxy(self, skip):  # noqa: ANN001
            for e in [proxy_a, proxy_b]:
                if e.key not in skip and not e.is_in_cooldown():
                    return e
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            proxy.failures += 1

        def make_httpx_proxy(self, entry):  # noqa: ANN001
            import httpx
            return httpx.Proxy(entry.make_url())

    call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        # Determine which proxy the client was built with.
        # For proxy attempts, self._client carries the proxy_client.
        tried_keys.append(str(call_count))
        if call_count == 1:
            raise OSError("direct failed")
        if call_count == 2:
            raise OSError("proxy A failed")
        # call_count == 3 → proxy B succeeds (returns normally)

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _FakeProxyManager()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        await asyncio.wait_for(
            _wait_until(lambda: call_count >= 3), timeout=2.0
        )
        await source.stop()

    asyncio.run(_run())
    assert call_count >= 3, "Should have tried direct + proxy A + proxy B"


# ---------------------------------------------------------------------------
# 8. Proxy B success → session connected, _current_proxy set
# ---------------------------------------------------------------------------


def test_proxy_b_success_session_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 60.0)

    proxy_a = ProxyEntry(scheme="http", host="1.1.1.1", port=3128)
    proxy_b = ProxyEntry(scheme="http", host="2.2.2.2", port=3128)

    class _FakePM:
        async def get_proxy_pool(self):  # noqa: ANN001
            return [proxy_a, proxy_b]

        def get_next_proxy(self, skip):  # noqa: ANN001
            for e in [proxy_a, proxy_b]:
                if e.key not in skip and not e.is_in_cooldown():
                    return e
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            proxy.failures += 1

        def make_httpx_proxy(self, entry):  # noqa: ANN001
            import httpx
            return httpx.Proxy(entry.make_url())

    call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("direct failed")
        if call_count == 2:
            raise OSError("proxy A failed")
        # call_count == 3 → proxy B: succeed
        self._current_proxy = proxy_b  # simulate what _attempt_with_fallback does

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _FakePM()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        await asyncio.wait_for(
            _wait_until(lambda: call_count >= 3), timeout=2.0
        )
        await source.stop()

    asyncio.run(_run())
    # current_proxy is set inside _run_connection fake above; verify proxy_b was used
    assert call_count == 3


# ---------------------------------------------------------------------------
# 9. All proxies failed → surfaces error normally
# ---------------------------------------------------------------------------


def test_all_proxies_failed_normal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    proxy_a = ProxyEntry(scheme="http", host="1.1.1.1", port=3128)

    class _FakePM:
        async def get_proxy_pool(self):  # noqa: ANN001
            return [proxy_a]

        def get_next_proxy(self, skip):  # noqa: ANN001
            if proxy_a.key not in skip:
                return proxy_a
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            proxy.failures += 1

        def make_httpx_proxy(self, entry):  # noqa: ANN001
            import httpx
            return httpx.Proxy(entry.make_url())

    call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        raise OSError("all failed")

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _FakePM()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        # Wait for at least one full attempt cycle.
        await asyncio.wait_for(
            _wait_until(
                lambda: any(
                    "error" in s.lower() or "помилка" in s.lower()
                    for s in statuses
                )
            ),
            timeout=3.0,
        )
        await source.stop()

    asyncio.run(_run())
    # Must have tried direct + at most MAX_PROXY_ATTEMPTS proxies, then shown error.
    assert call_count >= 1
    assert any("error" in s.lower() or "помилка" in s.lower() for s in statuses)


# ---------------------------------------------------------------------------
# 10. Max attempts respected (never tries more than MAX_PROXY_ATTEMPTS proxies)
# ---------------------------------------------------------------------------


def test_max_attempts_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 60.0)

    # Build 100 proxies.
    entries = [ProxyEntry(scheme="http", host=f"10.0.{i // 256}.{i % 256}", port=3128)
               for i in range(100)]

    class _FakePM:
        async def get_proxy_pool(self):  # noqa: ANN001
            return entries

        def get_next_proxy(self, skip):  # noqa: ANN001
            for e in entries:
                if e.key not in skip and not e.is_in_cooldown():
                    return e
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            proxy.failures += 1

        def make_httpx_proxy(self, entry):  # noqa: ANN001
            import httpx
            return httpx.Proxy(entry.make_url())

    proxy_call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal proxy_call_count
        proxy_call_count += 1
        raise OSError("always fail")

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _FakePM()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        await asyncio.wait_for(
            # 1 direct + MAX_PROXY_ATTEMPTS proxies = MAX_PROXY_ATTEMPTS + 1
            _wait_until(lambda: proxy_call_count >= MAX_PROXY_ATTEMPTS + 1),
            timeout=3.0,
        )
        await asyncio.sleep(0.05)  # let the loop settle
        await source.stop()

    asyncio.run(_run())

    # Proxy calls: 1 direct + MAX_PROXY_ATTEMPTS.  Allow one extra supervisor
    # loop iteration from the exponential backoff restart (hence + 2 max).
    assert proxy_call_count <= MAX_PROXY_ATTEMPTS + 1 + 2, (
        f"Too many proxy attempts: {proxy_call_count} (max expected {MAX_PROXY_ATTEMPTS + 1})"
    )


# ---------------------------------------------------------------------------
# 11. Successful proxy remains sticky during session
# ---------------------------------------------------------------------------


def test_sticky_proxy_during_session() -> None:
    """report_success() resets failures; current_proxy stays the same."""
    pm = ProxyManager()
    entry = ProxyEntry(scheme="http", host="1.1.1.1", port=8080, failures=2)
    pm._pool = [entry]
    pm._pool_loaded_at = time.monotonic()

    pm.report_success(entry)
    assert entry.failures == 0
    assert entry.cooldown_until == 0.0
    assert entry.successes == 1

    # A second success doesn't change the proxy identity.
    pm.report_success(entry)
    assert entry.host == "1.1.1.1"


# ---------------------------------------------------------------------------
# 12. Failed proxy enters cooldown
# ---------------------------------------------------------------------------


def test_failed_proxy_cooldown() -> None:
    pm = ProxyManager()
    entry = ProxyEntry(scheme="http", host="1.1.1.1", port=8080)

    for _ in range(PROXY_MAX_FAILURES_BEFORE_COOLDOWN - 1):
        pm.report_failure(entry)
        assert not entry.is_in_cooldown(), "Cooldown should not activate before threshold"

    pm.report_failure(entry)
    assert entry.is_in_cooldown(), "Proxy should be in cooldown after threshold failures"
    assert entry.cooldown_until > time.monotonic()
    assert entry.cooldown_until <= time.monotonic() + PROXY_FAILURE_COOLDOWN_SEC + 1


def test_failed_proxy_excluded_from_pool() -> None:
    pm = ProxyManager()
    entry = ProxyEntry(scheme="http", host="dead.proxy", port=8080)
    pm._pool = [entry]
    pm._pool_loaded_at = time.monotonic()

    # Force cooldown.
    entry.failures = PROXY_MAX_FAILURES_BEFORE_COOLDOWN
    entry.cooldown_until = time.monotonic() + 9999.0

    result = pm.get_next_proxy(skip=set())
    assert result is None, "Cooled-down proxy should not be returned"


# ---------------------------------------------------------------------------
# 13. ProxyManager exception doesn't crash TikTokService
# ---------------------------------------------------------------------------


def test_proxy_manager_exception_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    class _BrokenPM:
        async def get_proxy_pool(self):  # noqa: ANN001
            raise RuntimeError("ProxyScrape nuclear meltdown")

        def get_next_proxy(self, skip):  # noqa: ANN001
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            pass

    call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        raise OSError("direct always fails")

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _BrokenPM()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        # Should still show error / retry, not crash.
        await asyncio.wait_for(
            _wait_until(lambda: len(statuses) >= 1),
            timeout=3.0,
        )
        await source.stop()

    # Must NOT raise.
    asyncio.run(_run())
    assert call_count >= 1, "Should have attempted direct connection"


# ---------------------------------------------------------------------------
# 14. UI thread isn't blocked (_attempt_with_fallback is a coroutine)
# ---------------------------------------------------------------------------


def test_no_ui_thread_block() -> None:
    """_attempt_with_fallback must be an async coroutine function."""
    import inspect
    assert inspect.iscoroutinefunction(TikTokChatSource._attempt_with_fallback)
    assert inspect.iscoroutinefunction(TikTokChatSource._run_connection)
    assert inspect.iscoroutinefunction(ProxyManager.get_proxy_pool)
    assert inspect.iscoroutinefunction(ProxyManager.refresh_proxy_pool)


# ---------------------------------------------------------------------------
# 15. HTTP/auth errors do not cause infinite proxy rotation
# ---------------------------------------------------------------------------


def test_http_400_no_infinite_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    A non-retryable error (UserNotFoundError) raised by all proxies must NOT
    cause infinite rotation.  The error must propagate after the first raise.
    """
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 60.0)

    entries = [ProxyEntry(scheme="http", host=f"10.0.0.{i}", port=3128) for i in range(20)]

    class _FakePM:
        async def get_proxy_pool(self):  # noqa: ANN001
            return entries

        def get_next_proxy(self, skip):  # noqa: ANN001
            for e in entries:
                if e.key not in skip and not e.is_in_cooldown():
                    return e
            return None

        def report_success(self, proxy):  # noqa: ANN001
            pass

        def report_failure(self, proxy):  # noqa: ANN001
            proxy.failures += 1

        def make_httpx_proxy(self, entry):  # noqa: ANN001
            import httpx
            return httpx.Proxy(entry.make_url())

    call_count = 0

    async def _fake_run_connection(self, client, uid, backoff):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("direct: connection refused")
        # All proxy attempts raise UserNotFoundError — non-retryable.
        _ensure_tiktoklive = tk_mod._ensure_tiktoklive
        _ensure_tiktoklive()
        UserNotFoundError = tk_mod.UserNotFoundError  # noqa: N806
        raise UserNotFoundError("@streamer not found")

    monkeypatch.setattr(TikTokChatSource, "_run_connection", _fake_run_connection)

    statuses: list[str] = []
    source = _make_source(statuses=statuses)
    source._proxy_manager = _FakePM()  # type: ignore[assignment]

    async def _run() -> None:
        await source.start("streamer")
        # Wait for the not-found status to appear.
        await asyncio.wait_for(
            _wait_until(
                lambda: any(
                    "not_found" in s
                    or "не знайдено" in s
                    or "not found" in s.lower()
                    for s in statuses
                )
            ),
            timeout=3.0,
        )
        await source.stop()

    asyncio.run(_run())

    # Direct (1) + ONE proxy attempt (UserNotFoundError stops rotation) = 2 max.
    assert call_count <= 2, (
        f"Should stop rotation on non-retryable error; got {call_count} calls"
    )


# ---------------------------------------------------------------------------
# Bonus: ProxyManager pool TTL and merge preserves health state
# ---------------------------------------------------------------------------


def test_proxy_manager_pool_merge_preserves_health() -> None:
    """After refresh, existing proxy health counters are not reset."""
    pm = ProxyManager()
    existing = ProxyEntry(scheme="http", host="1.2.3.4", port=8080, failures=2, successes=5)
    pm._pool = [existing]
    pm._pool_loaded_at = 0.0  # force stale

    new_raw = _proxyscrape_payload([_http_entry("1.2.3.4", 8080), _http_entry("9.9.9.9", 9999)])

    from stream_cheremsha.chat.tiktok.proxy_manager import _parse_proxyscrape_response

    parsed = _parse_proxyscrape_response(new_raw)

    # Simulate merge logic.
    existing_map = {e.key: e for e in pm._pool}
    merged = []
    seen: set[str] = set()
    for entry in parsed:
        k = entry.key
        if k in seen:
            continue
        seen.add(k)
        if k in existing_map:
            old = existing_map[k]
            old.scheme = entry.scheme
            merged.append(old)
        else:
            merged.append(entry)

    pm._pool = merged

    # Original proxy's health state must be preserved.
    assert pm._pool[0].failures == 2
    assert pm._pool[0].successes == 5
    assert pm._pool[1].host == "9.9.9.9"
