# Soundpad Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Library" button to the Soundpad tab that opens an animated modal browsing MyInstants sounds (language follows the app locale), with preview playback, one-click add-to-soundpad, safe rate-limited fetching, and bounded caching.

**Architecture:** A new Qt-free synchronous client module (`soundpad/myinstants.py`) handles Cloudflare-safe fetching via lazily-imported curl_cffi, min-interval rate limiting, an in-memory index LRU (TTL + page cap), and a disk MP3 cache evicted by count AND size. `SoundpadAudioEngine` gains preview play/stop on the existing audio sink; `SoundpadQmlApi` exposes async slots that emit signals to QML; a new `SoundpadLibraryPanel.qml` renders rows/pagination/states inside the existing `CheremshaModal`.

**Tech Stack:** Python 3.11, PySide6 (Qt 6.8+), qasync, curl_cffi (Chrome TLS impersonation — already in pyproject.toml), pytest, QML (QtQuick.Controls).

**Spec:** No separate spec document — the user request is the spec: "soundpad tab. Need to add button (Library), library opens popup windows… fetch sounds from https://www.myinstants.com/en/index/<language_code>/ … choose based on chosen app language in settings… play preview and button Add, and this sound automatically add to soundpad. proper safe fetching from myinstants. caching, don't grow up use pc memory. pagination. rate limit safety. UI WITH APP PATTERNS. MODERN APP UI SMOOTH ANIMATIONS."

## Global Constraints

- Python `>=3.11,<3.12`; **no new dependencies** (curl_cffi is already declared in pyproject.toml).
- Never run blocking I/O on the Qt GUI thread — network/disk work goes through `asyncio.to_thread` inside tasks spawned from slots; when no loop is running (unit tests) fall back to inline execution, exactly like `_schedule_metadata` in `soundpad_qml_api.py`.
- curl_cffi must be imported **lazily** (never at app startup) — copy the proven pattern from `src/stream_cheremsha/actions/actions_play_random_myinstants_ua.py` (`_ensure_curl_cffi` + module `__getattr__`).
- Caches are bounded: in-memory index results ≤ 32 pages with 600 s TTL; disk MP3 cache ≤ 128 files AND ≤ 256 MB, evicting oldest mtime first. Audio bytes are never retained in memory beyond the active preview/playback call.
- Rate limit: ≥ 1.2 s between any two MyInstants requests (constant `MIN_REQUEST_INTERVAL_SEC`), plus a single in-flight fetch guard at the API layer (`_lib_inflight`).
- Only `.mp3/.wav/.ogg` may enter the soundpad (`ALLOWED_AUDIO_SUFFIXES`, models.py); MyInstants serves `.mp3`.
- Locale: app locale is `uk`/`en` (l10n key `ui/locale`, `DEFAULT_LOCALE = "uk"`). Map uk→"ua", en→"en" for MyInstants, with fallback to "en". New UI strings need both uk and en l10n entries; Ukrainian must use standard orthography.
- Added library sounds must be **COPIED** into the store's own directory (`SoundpadStore.library_dir`) — never reference cache files that can be evicted (the existing `addSound` slot references files in place; do not copy that behavior for library adds).
- Lint: `.venv/bin/ruff check src tests` (line-length 100, rules E,F,I,UP); format with `.venv/bin/ruff format`; run tests via `PYTHONPATH=. .venv/bin/pytest tests/<file>`.
- Commit style follows recent history: `feat(soundpad): …`, `test(soundpad): …`.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/stream_cheremsha/soundpad/myinstants.py` | Create | Qt-free MyInstants client: parsing, lang mapping, rate limit, bounded caches, download |
| `src/stream_cheremsha/soundpad/engine.py` | Modify | `play_preview()` / `stop_preview()` + `previewFinished` signal on the existing sink |
| `src/stream_cheremsha/ui/soundpad_qml_api.py` | Modify | Library slots/signals, `libraryStrings`, `tr()`, `set_locale()` |
| `src/stream_cheremsha/l10n.py` | Modify | `soundpad.library.*` keys (uk/en) |
| `src/stream_cheremsha/ui/main_window.py` | Modify | Apply locale to the soundpad API at creation + on retranslate |
| `src/stream_cheremsha/qml/components/CheremshaModal.qml` | Modify | Optional `preferredWidth` (default 560, backward compatible) |
| `src/stream_cheremsha/qml/components/SoundpadLibraryPanel.qml` | Create | Modal body: rows, preview/add buttons, pagination, loading/error/empty states |
| `src/stream_cheremsha/qml/components/qmldir` | Modify | Register SoundpadLibraryPanel |
| `src/stream_cheremsha/qml/SoundpadView.qml` | Modify | Library header button + modal instance + state + signal wiring |
| `tests/test_soundpad_myinstants.py` | Create | Client unit tests (parsing, rate limit, caches) with a fake session |
| `tests/test_soundpad_engine.py` | Modify | Preview play/stop tests |
| `tests/test_soundpad_library_api.py` | Create | QML API library slot tests with a stub client + FakeSink |
| `tests/test_soundpad_nav_lazy.py` | Modify | Static wiring checks (locale, qmldir) |

Existing fixtures to reuse: `tests/fixtures/myinstants_ua_index.html`, `tests/fixtures/myinstants_instant_page.html`.

---

### Task 1: MyInstants client — data model, language mapping, HTML parsing

**Files:**
- Create: `src/stream_cheremsha/soundpad/myinstants.py`
- Test: `tests/test_soundpad_myinstants.py`

**Interfaces:**
- Consumes: existing fixtures in `tests/fixtures/`; nothing else.
- Produces: `LibrarySound(path, title)` frozen dataclass; `candidate_langs(locale) -> list[str]`; `extract_instant_entries(html) -> list[LibrarySound]`; `extract_mp3_url(html) -> str` (raises `ValueError`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_soundpad_myinstants.py`:

```python
from __future__ import annotations

import pathlib

import pytest


def _fixture(name: str) -> str:
    return (pathlib.Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


def test_candidate_langs_mapping():
    from stream_cheremsha.soundpad.myinstants import candidate_langs

    assert candidate_langs("uk") == ["ua", "en"]
    assert candidate_langs("UA ") == ["ua", "en"]
    assert candidate_langs("en") == ["en"]
    assert candidate_langs("") == ["en"]
    assert candidate_langs("xx") == ["en"]


def test_extract_instant_entries_from_fixture():
    from stream_cheremsha.soundpad.myinstants import LibrarySound, extract_instant_entries

    entries = extract_instant_entries(_fixture("myinstants_ua_index.html"))
    assert len(entries) >= 5
    assert all(isinstance(e, LibrarySound) for e in entries)
    assert all(e.path.startswith("/en/instant/") for e in entries)
    assert entries[0].title == "Slava Ukraini"


def test_extract_instant_entries_edge_cases():
    from stream_cheremsha.soundpad.myinstants import extract_instant_entries

    assert extract_instant_entries(None) == []
    assert extract_instant_entries("") == []
    one = '<a href="/en/instant/abc-1/">X</a>'
    out = extract_instant_entries(one)
    assert [e.path for e in out] == ["/en/instant/abc-1/"]
    # duplicates collapse; non-instant links are ignored
    dup = one + " " + one + ' <a href="/en/categories/funny/">F</a>'
    assert len(extract_instant_entries(dup)) == 1


def test_extract_mp3_url_from_fixture():
    from stream_cheremsha.soundpad.myinstants import extract_mp3_url

    url = extract_mp3_url(_fixture("myinstants_instant_page.html"))
    assert url.startswith("https://") and ".mp3" in url and "myinstants" in url


def test_extract_mp3_url_rejects_foreign_hosts_and_empty():
    from stream_cheremsha.soundpad.myinstants import extract_mp3_url

    with pytest.raises(ValueError):
        extract_mp3_url("")
    with pytest.raises(ValueError):
        extract_mp3_url('<a href="https://evil.example.com/x.mp3">x</a>')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_myinstants.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stream_cheremsha.soundpad.myinstants'`

- [ ] **Step 3: Write the implementation (part 1 of myinstants.py)**

Create `src/stream_cheremsha/soundpad/myinstants.py`:

```python
"""MyInstants library client for the Soundpad Library browser.

Safe-fetching rules implemented here:
- curl_cffi with Chrome TLS impersonation (Cloudflare); imported lazily so
  application startup never pays its cost.
- Minimum interval between any two requests (rate limit).
- Bounded caches: in-memory index results (TTL + page cap) and an on-disk
  MP3 cache evicted by file count AND total size, oldest mtime first.

The client is synchronous by design — call it from a worker thread
(``asyncio.to_thread``), never directly on the Qt GUI thread.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


# App locale (l10n: uk/en) -> MyInstants sound-language code.
_LOCALE_TO_LANG = {"uk": "ua", "en": "en"}
_FALLBACK_LANGS = ("en",)


@dataclass(frozen=True, slots=True)
class LibrarySound:
    path: str  # site path, e.g. "/en/instant/some-sound-123/"
    title: str


def candidate_langs(locale: str) -> list[str]:
    """Ordered MyInstants sound-language candidates for an app locale."""
    code = _LOCALE_TO_LANG.get(str(locale or "").strip().lower(), "en")
    out = [code]
    for fb in _FALLBACK_LANGS:
        if fb not in out:
            out.append(fb)
    return out


_INSTANT_ANCHOR_RE = re.compile(
    r'<a[^>]+href\s*=\s*(?:"|\')(?P<path>/[a-z]{2}/instant/[^"\']+)(?:"|\')[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

_MP3_URL_RE = re.compile(
    r'(?P<url>https?://[^\s"\'<>]+?\.mp3(?:[?#][^\s"\'<>]*)?)',
    re.IGNORECASE,
)


def extract_instant_entries(html: str | None) -> list[LibrarySound]:
    """Parse instant links (path + title) from a MyInstants index page."""
    if not html or not isinstance(html, str):
        return []
    out: list[LibrarySound] = []
    seen: set[str] = set()
    for m in _INSTANT_ANCHOR_RE.finditer(html):
        p = (m.group("path") or "").strip()
        if not p or p in seen:
            continue
        t = re.sub(r"<[^>]+>", " ", str(m.group("title") or ""))
        title = " ".join(t.split()).strip()
        seen.add(p)
        out.append(LibrarySound(path=p, title=title))
    return out


def extract_mp3_url(html: str | None) -> str:
    """First MyInstants-hosted .mp3 URL on an instant page; ValueError if none."""
    if not html or not isinstance(html, str):
        raise ValueError("No myinstants .mp3 URL found in HTML")
    for m in _MP3_URL_RE.finditer(html):
        url = (m.group("url") or "").strip()
        host = (urlparse(url).hostname or "").strip().lower()
        if host not in ("www.myinstants.com", "www.myinstantscdn.com"):
            continue
        return url
    raise ValueError("No myinstants .mp3 URL found in HTML")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_myinstants.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/soundpad/myinstants.py tests/test_soundpad_myinstants.py
git add src/stream_cheremsha/soundpad/myinstants.py tests/test_soundpad_myinstants.py
git commit -m "feat(soundpad): myinstants client core — lang mapping and HTML parsing"
```

---

### Task 2: MyInstants client — session, rate limit, bounded caches, download

**Files:**
- Modify: `src/stream_cheremsha/soundpad/myinstants.py` (append)
- Test: `tests/test_soundpad_myinstants.py` (append)

**Interfaces:**
- Consumes: Task 1's `LibrarySound`, `extract_instant_entries`, `extract_mp3_url`.
- Produces: `MyInstantsClient(session_factory=None, cache_dir=None, min_interval_sec=…, index_ttl_sec=…, max_cached_pages=…)` with methods `fetch_index_entries(lang, page) -> list[LibrarySound]`, `resolve_mp3_url(sound_path) -> str`, `ensure_cached_mp3(mp3_url) -> Path`; module functions `default_session()`, `default_cache_dir()`, `enforce_cache_bounds(cache_dir, *, max_files=…, max_bytes=…)`; constants `ORIGIN`, `MIN_REQUEST_INTERVAL_SEC`, `INDEX_TTL_SEC`, `INDEX_CACHE_MAX_PAGES`, `MP3_CACHE_MAX_FILES`, `MP3_CACHE_MAX_BYTES`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_soundpad_myinstants.py`:

```python
import os
import time as _time


class FakeResponse:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class FakeSession:
    """Canned responses per URL substring; records requested URLs."""

    def __init__(self, routes: dict[str, FakeResponse]):
        self.routes = routes
        self.requests: list[tuple[str, dict | None]] = []

    def get(self, url, headers=None):
        self.requests.append((url, headers))
        for key, resp in self.routes.items():
            if key in url:
                return resp
        raise AssertionError(f"no fake route for {url}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _client(tmp_path, routes, **kw):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    fake = FakeSession(routes)
    c = MyInstantsClient(session_factory=lambda: fake, cache_dir=tmp_path / "cache", **kw)
    return c, fake


def test_fetch_index_page_urls(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)})
    assert len(c.fetch_index_entries("ua", 1)) >= 5
    assert fake.requests[0][0] == "https://www.myinstants.com/en/index/ua/"

    c2, fake2 = _client(tmp_path, {"/en/index/ua/?page=3": FakeResponse(text=index_html)})
    c2.fetch_index_entries("ua", 3)
    assert fake2.requests[0][0] == "https://www.myinstants.com/en/index/ua/?page=3"


def test_rate_limit_sleeps_between_requests(monkeypatch, tmp_path):
    import stream_cheremsha.soundpad.myinstants as mi

    sleeps: list[float] = []
    real_mono = _time.monotonic

    class _FakeTime:
        @staticmethod
        def monotonic():
            return real_mono()

        @staticmethod
        def sleep(s):
            sleeps.append(float(s))

    monkeypatch.setattr(mi, "time", _FakeTime)
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, min_interval_sec=0.3
    )
    # page 1 and page 2 are different cache keys -> two network calls back-to-back
    c.fetch_index_entries("ua", 1)
    c._index_cache.clear()
    c.fetch_index_entries("ua", 2)
    assert len(fake.requests) == 2
    assert sleeps, "expected a rate-limit sleep between requests"
    assert sleeps[0] >= 0.25


def test_resolve_mp3_url_uses_referer(tmp_path):
    page_html = _fixture("myinstants_instant_page.html")
    c, fake = _client(tmp_path, {"/en/instant/": FakeResponse(text=page_html)})
    url = c.resolve_mp3_url("/en/instant/some-sound-1/")
    assert ".mp3" in url
    assert fake.requests[0][1] is not None and "Referer" in fake.requests[0][1]


def test_resolve_mp3_url_rejects_bad_path(tmp_path):
    c, _ = _client(tmp_path, {})
    import pytest

    with pytest.raises(ValueError):
        c.resolve_mp3_url("https://evil.example.com/x")


def test_ensure_cached_mp3_downloads_once(tmp_path):
    mp3_url = "https://www.myinstantscdn.com/audio/abc.mp3"
    c, fake = _client(tmp_path, {mp3_url: FakeResponse(content=b"ID3fake-mp3-bytes")})
    p1 = c.ensure_cached_mp3(mp3_url)
    assert p1.is_file() and p1.read_bytes() == b"ID3fake-mp3-bytes"
    p2 = c.ensure_cached_mp3(mp3_url)  # cache hit: no second network call
    assert p2 == p1
    assert len(fake.requests) == 1


def test_ensure_cached_mp3_rejects_non_mp3(tmp_path):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    c = MyInstantsClient(session_factory=lambda: FakeSession({}), cache_dir=tmp_path / "c")
    import pytest

    with pytest.raises(ValueError):
        c.ensure_cached_mp3("https://www.myinstants.com/x.wav")


def test_enforce_cache_bounds_count(tmp_path):
    from stream_cheremsha.soundpad.myinstants import enforce_cache_bounds

    d = tmp_path / "cache"
    d.mkdir()
    now = 1_700_000_000
    for i, name in enumerate(["a.mp3", "b.mp3", "c.mp3", "d.mp3"]):
        p = d / name
        p.write_bytes(b"x" * (10 + i * 10))
        os.utime(p, (now + i, now + i))

    enforce_cache_bounds(d, max_files=2)
    assert sorted(p.name for p in d.glob("*.mp3")) == ["c.mp3", "d.mp3"]


def test_enforce_cache_bounds_bytes(tmp_path):
    from stream_cheremsha.soundpad.myinstants import enforce_cache_bounds

    d = tmp_path / "cache"
    d.mkdir()
    now = 1_700_000_000
    for i, name in enumerate(["a.mp3", "b.mp3", "c.mp3", "d.mp3"]):
        p = d / name
        p.write_bytes(b"x" * (10 + i * 10))  # sizes: 10, 20, 30, 40
        os.utime(p, (now + i, now + i))

    enforce_cache_bounds(d, max_files=10, max_bytes=50)
    assert [p.name for p in d.glob("*.mp3")] == ["d.mp3"]


def test_index_cache_hit_avoids_network(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)})
    c.fetch_index_entries("ua", 1)
    c.fetch_index_entries("ua", 1)
    assert len(fake.requests) == 1


def test_index_cache_ttl_expiry(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, index_ttl_sec=0.0
    )
    c.fetch_index_entries("ua", 1)
    c.fetch_index_entries("ua", 1)
    assert len(fake.requests) == 2


def test_index_cache_bounded_pages(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, max_cached_pages=2
    )
    for page in (1, 2, 3):
        c.fetch_index_entries("ua", page)
    assert set(c._index_cache) == {("ua", 2), ("ua", 3)}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_myinstants.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'MyInstantsClient'` (Task 1 tests still pass)

- [ ] **Step 3: Write the implementation**

Append to `src/stream_cheremsha/soundpad/myinstants.py`. First extend the imports at the top of the file — replace the existing import block:

```python
import re
from dataclasses import dataclass
from urllib.parse import urlparse
```

with:

```python
import hashlib
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
```

Then append this code at the end of the file:

```python
ORIGIN = "https://www.myinstants.com"
MIN_REQUEST_INTERVAL_SEC = 1.2
INDEX_TTL_SEC = 600.0
INDEX_CACHE_MAX_PAGES = 32
MP3_CACHE_MAX_FILES = 128
MP3_CACHE_MAX_BYTES = 256 * 1024 * 1024

_BROWSER_IMPERSONATE = "chrome"
_BROWSER_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,uk-UA,uk;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# --- Lazy curl_cffi import (same pattern as actions_play_random_myinstants_ua) ---

_LAZY_CURL_NAMES = frozenset({"curl_requests"})


def _ensure_curl_cffi() -> None:
    g = globals()
    if all(n in g for n in _LAZY_CURL_NAMES):
        return
    from curl_cffi import requests as _curl_requests

    g.setdefault("curl_requests", _curl_requests)


def __getattr__(name: str):  # noqa: ANN001, ANN205
    if name in _LAZY_CURL_NAMES:
        _ensure_curl_cffi()
        try:
            return globals()[name]
        except KeyError:
            pass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def default_session():
    """A curl_cffi Session impersonating Chrome (Cloudflare-safe)."""
    _ensure_curl_cffi()
    return globals()["curl_requests"].Session(  # noqa: SLF001
        impersonate=_BROWSER_IMPERSONATE,
        headers=dict(_BROWSER_HEADERS),
        timeout=20.0,
        allow_redirects=True,
    )


def default_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "stream-cheremsha" / "soundpad-library-cache"


def _safe_mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path_str: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=str(path.parent), prefix=f"{path.name}.", suffix=".tmp"
        ) as f:
            tmp_path_str = f.name
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path_str, path)
    finally:
        if tmp_path_str is not None:
            try:
                Path(tmp_path_str).unlink(missing_ok=True)
            except OSError:
                pass


def enforce_cache_bounds(
    cache_dir: Path, *, max_files: int = MP3_CACHE_MAX_FILES, max_bytes: int = MP3_CACHE_MAX_BYTES
) -> None:
    """Evict oldest (mtime) files until both count and total size fit."""
    d = Path(cache_dir)
    if not d.is_dir():
        return

    def _size(p: Path) -> int:
        try:
            return int(p.stat().st_size)
        except OSError:
            return 0

    files = [p for p in d.glob("*.mp3") if p.is_file()]
    files.sort(key=_safe_mtime)  # oldest first
    total = sum(_size(p) for p in files)
    remaining = len(files)
    to_delete: list[Path] = []
    for p in files:
        if remaining <= max_files and total <= max_bytes:
            break
        to_delete.append(p)
        remaining -= 1
        total -= _size(p)
    for p in to_delete:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            continue


class MyInstantsClient:
    """Synchronous MyInstants fetcher with rate limiting and bounded caches.

    Call from a worker thread only (``asyncio.to_thread``). Network failures
    raise; the API layer maps them to user-facing error states.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], object] | None = None,
        cache_dir: str | Path | None = None,
        min_interval_sec: float = MIN_REQUEST_INTERVAL_SEC,
        index_ttl_sec: float = INDEX_TTL_SEC,
        max_cached_pages: int = INDEX_CACHE_MAX_PAGES,
    ) -> None:
        self._session_factory = session_factory or default_session
        self._cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self._min_interval_sec = float(min_interval_sec)
        self._index_ttl_sec = float(index_ttl_sec)
        self._max_cached_pages = int(max_cached_pages)
        self._last_request_mono = 0.0
        # (lang, page) -> (stored_at_mono, entries); insertion-ordered eviction.
        self._index_cache: dict[tuple[str, int], tuple[float, list[LibrarySound]]] = {}

    # -- rate limit ---------------------------------------------------------
    def _throttle(self) -> None:
        wait = self._min_interval_sec - (time.monotonic() - self._last_request_mono)
        if wait > 0:
            time.sleep(wait)
        self._last_request_mono = time.monotonic()

    # -- index pages --------------------------------------------------------
    def fetch_index_entries(self, lang: str, page: int) -> list[LibrarySound]:
        """Entries for one index page (in-memory cached; TTL + bounded)."""
        key = (str(lang or "").strip().lower(), max(1, int(page)))
        now = time.monotonic()
        hit = self._index_cache.get(key)
        if hit is not None and now - hit[0] <= self._index_ttl_sec:
            return list(hit[1])

        url = f"{ORIGIN}/en/index/{key[0]}/" + ("" if key[1] == 1 else f"?page={key[1]}")
        self._throttle()
        with self._session_factory() as session:
            resp = session.get(url)
            resp.raise_for_status()
            entries = extract_instant_entries(resp.text)

        self._index_cache[key] = (now, list(entries))
        while len(self._index_cache) > self._max_cached_pages:
            oldest_key = next(iter(self._index_cache))
            del self._index_cache[oldest_key]
        return entries

    # -- instant pages / mp3 -------------------------------------------------
    def resolve_mp3_url(self, sound_path: str) -> str:
        p = (sound_path or "").strip()
        if not p.startswith("/"):
            raise ValueError("sound_path must be a site path like /en/instant/x/")
        self._throttle()
        with self._session_factory() as session:
            resp = session.get(
                ORIGIN + p, headers={"Referer": f"{ORIGIN}/", "Sec-Fetch-Site": "same-origin"}
            )
            resp.raise_for_status()
            return extract_mp3_url(resp.text)

    def ensure_cached_mp3(self, mp3_url: str) -> Path:
        """Local file for ``mp3_url`` — cached hit or fresh download (bounded)."""
        dest = self._cache_path_for(mp3_url)
        if dest.is_file():
            try:
                os.utime(dest, None)  # refresh LRU position
            except OSError:
                pass
            return dest
        self._throttle()
        with self._session_factory() as session:
            resp = session.get(
                (mp3_url or "").strip(),
                headers={
                    "Referer": f"{ORIGIN}/",
                    "Accept": "*/*",
                    "Sec-Fetch-Dest": "audio",
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            resp.raise_for_status()
            data = bytes(resp.content or b"")
        if not data:
            raise ValueError("Downloaded mp3 is empty")
        _atomic_write_bytes(dest, data)
        enforce_cache_bounds(self._cache_dir)
        return dest

    def _cache_path_for(self, mp3_url: str) -> Path:
        u = (mp3_url or "").strip()
        if not u:
            raise ValueError("mp3_url is required")
        ext = Path(urlparse(u).path).suffix.lower()
        if ext != ".mp3":
            raise ValueError(f"mp3_url must end with .mp3 (got {ext or 'no extension'})")
        key = hashlib.sha256(u.encode("utf-8")).hexdigest()[:24]
        return self._cache_dir / f"{key}{ext}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_myinstants.py -v`
Expected: PASS (all 16 tests)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/soundpad/myinstants.py tests/test_soundpad_myinstants.py
git add src/stream_cheremsha/soundpad/myinstants.py tests/test_soundpad_myinstants.py
git commit -m "feat(soundpad): myinstants client — rate limit, bounded caches, safe download"
```

---

### Task 3: Engine preview playback (play/stop on the existing sink)

**Files:**
- Modify: `src/stream_cheremsha/soundpad/engine.py`
- Test: `tests/test_soundpad_engine.py` (append; it already defines a `FakeSink` with `play_mp3_parallel_with_volume_deduped`)

**Interfaces:**
- Consumes: existing `SoundpadAudioEngine`, its `_ensure_sink()`, sink methods `play_mp3_parallel_with_volume_deduped(data, vol, dedupe_key=...)` / `play_mp3_with_volume(data, vol)` / `stop_sfx_by_key_prefix(prefix)`.
- Produces: `engine.play_preview(data: bytes) -> str` ("PLAYING" | "BLOCKED"), `engine.stop_preview() -> None`, signal `previewFinished()` (fires only on natural completion — never for cancelled/stopped playback), and `stop_all()` now also stops the preview.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_soundpad_engine.py`:

```python
def test_play_preview_uses_sink():
    import asyncio

    sink = FakeSink()
    eng = SoundpadAudioEngine(sink=sink)

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.01)

    asyncio.run(main())
    assert len(sink.calls) == 1
    data, vol = sink.calls[0]
    assert data == b"abc" and 0.0 <= vol <= 1.0


def test_play_preview_rejects_empty():
    eng = SoundpadAudioEngine(sink=FakeSink())
    assert eng.play_preview(b"") == "BLOCKED"


def test_preview_finished_emits_once_on_natural_end():
    import asyncio

    sink = FakeSink()
    eng = SoundpadAudioEngine(sink=sink)
    finished: list[int] = []
    eng.previewFinished.connect(lambda: finished.append(1))

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.02)

    asyncio.run(main())
    assert finished == [1]


def test_stop_preview_cancels_without_emit():
    import asyncio

    class SlowSink(FakeSink):
        async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
            self.calls.append((bytes(data), float(volume)))
            await asyncio.sleep(5)  # long playback
            return True

    sink = SlowSink()
    eng = SoundpadAudioEngine(sink=sink)
    finished: list[int] = []
    eng.previewFinished.connect(lambda: finished.append(1))

    async def main():
        assert eng.play_preview(b"abc") == "PLAYING"
        await asyncio.sleep(0.01)  # let it start
        eng.stop_preview()
        await asyncio.sleep(0.02)  # let cancellation unwind

    asyncio.run(main())
    assert len(sink.calls) == 1
    assert finished == []  # cancelled playback must not report "finished"


def test_stop_all_stops_preview_without_error():
    eng = SoundpadAudioEngine(sink=FakeSink())
    eng.stop_all()  # must not raise even with no preview running
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_engine.py -v`
Expected: new tests FAIL with `AttributeError: 'SoundpadAudioEngine' object has no attribute 'play_preview'` (existing tests still pass)

- [ ] **Step 3: Write the implementation**

In `src/stream_cheremsha/soundpad/engine.py`:

1. Add the signal after `duckingChanged = Signal(bool)` in the class body:

```python
    previewFinished = Signal()  # a library preview ended naturally (not stopped)
```

2. In `__init__`, add after `self._held: set[str] = set()`:

```python
        self._preview_tasks: set[asyncio.Task] = set()
```

3. Add the module constant near the top of the file, after the imports (next to where `logger` is defined):

```python
_PREVIEW_PREFIX = "soundpad-preview:"
```

4. Add these methods to `SoundpadAudioEngine`, right before `def stop_all(self)`:

```python
    def play_preview(self, data: bytes) -> str:
        """Play raw audio as a one-shot library preview (restart semantics)."""
        if not bytes(data or b""):
            return "BLOCKED"
        self.stop_preview()
        vol = max(0.0, min(1.0, float(self._global_volume)))

        async def _run() -> None:
            cancelled = False
            try:
                sink = self._ensure_sink()
                fn = getattr(sink, "play_mp3_parallel_with_volume_deduped", None)
                if callable(fn):
                    await fn(data, vol, dedupe_key=_PREVIEW_PREFIX + "active")
                else:
                    await sink.play_mp3_with_volume(data, vol)
            except asyncio.CancelledError:
                cancelled = True
                raise
            except (RuntimeError, OSError) as e:
                logger.warning("soundpad preview failed: %s", e)
            finally:
                if not cancelled:
                    self.previewFinished.emit()

        if _loop_running():
            t = asyncio.get_running_loop().create_task(_run())
            self._preview_tasks.add(t)
            t.add_done_callback(self._preview_tasks.discard)
        # No running loop (unit tests): nothing audible; state stays consistent.
        return "PLAYING"

    def stop_preview(self) -> None:
        had = bool(self._preview_tasks)  # guard: don't touch the sink when idle
        for t in list(self._preview_tasks):
            if not t.done():
                try:
                    t.cancel()
                except RuntimeError:
                    pass
        self._preview_tasks.clear()
        if had:
            stop_voice = getattr(self._sink, "stop_sfx_by_key_prefix", None)
            if callable(stop_voice):
                try:
                    stop_voice(_PREVIEW_PREFIX)
                except RuntimeError:
                    pass
```

5. In `stop_all`, add as the first line of the method body (before `self._queues.clear()`):

```python
        self.stop_preview()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_engine.py -v`
Expected: PASS (all engine tests, old and new)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/soundpad/engine.py tests/test_soundpad_engine.py
git add src/stream_cheremsha/soundpad/engine.py tests/test_soundpad_engine.py
git commit -m "feat(soundpad): engine preview play/stop for library sounds"
```

---

### Task 4: l10n keys + locale-aware strings on SoundpadQmlApi

**Files:**
- Modify: `src/stream_cheremsha/l10n.py` (insert after the `"soundpad.title"` entry, ~line 238)
- Modify: `src/stream_cheremsha/ui/soundpad_qml_api.py`
- Test: `tests/test_soundpad_library_api.py` (create)

**Interfaces:**
- Consumes: `l10n.tr(locale, key)` (raises `KeyError` on unknown keys), `l10n.normalize_locale(raw)`, `l10n.DEFAULT_LOCALE`.
- Produces: `api.libraryStrings -> dict[str, str]` (property, notify=`stringsChanged`), `api.tr(key) -> str` slot, `api.set_locale(locale)` method, signal `stringsChanged()`. Keys exposed: `button, title, subtitle, add, added, loading, error_title, retry, empty_title, page, prev, next`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_soundpad_library_api.py`:

```python
from __future__ import annotations


class FakeSink:
    def __init__(self):
        self.calls: list[tuple[bytes, float]] = []

    async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        self.calls.append((bytes(data), float(volume)))
        return True


def _api(tmp_path):
    from PySide6.QtCore import QSettings

    from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
    from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager
    from stream_cheremsha.soundpad.store import SoundpadStore
    from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi

    store = SoundpadStore(settings=QSettings("sp-lib", "x"), root_dir=tmp_path)
    eng = SoundpadAudioEngine(sink=FakeSink())
    hk = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    return SoundpadQmlApi(store=store, engine=eng, hotkeys=hk), store


def test_library_strings_localization(tmp_path):
    api, _ = _api(tmp_path)
    s = api.libraryStrings
    assert s["title"] == "Бібліотека звуків"
    assert s["add"] == "Додати"

    events: list[int] = []
    api.stringsChanged.connect(lambda: events.append(1))
    api.set_locale("en")
    assert events, "stringsChanged must fire on locale change"
    assert api.libraryStrings["title"] == "Sound Library"


def test_tr_falls_back_to_key(tmp_path):
    api, _ = _api(tmp_path)
    assert api.tr("no.such.key") == "no.such.key"
    assert api.tr("") == ""
    assert api.tr("soundpad.library.add") in ("Додати", "Add")


def test_set_locale_same_value_no_emit(tmp_path):
    api, _ = _api(tmp_path)
    events: list[int] = []
    api.stringsChanged.connect(lambda: events.append(1))
    api.set_locale("uk")  # default locale — no change
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_api.py -v`
Expected: FAIL with `AttributeError: 'SoundpadQmlApi' object has no attribute 'libraryStrings'`

- [ ] **Step 3: Add the l10n keys**

In `src/stream_cheremsha/l10n.py`, insert immediately after the line `"soundpad.title": {"uk": "Soundpad", "en": "Soundpad"},`:

```python
    "soundpad.library.button": {"uk": "Бібліотека", "en": "Library"},
    "soundpad.library.title": {"uk": "Бібліотека звуків", "en": "Sound Library"},
    "soundpad.library.subtitle": {
        "uk": "Оберіть звук з онлайн бібліотеки — прослухайте та додайте до саундпаду",
        "en": "Pick a sound from the online library — preview it, then add to your soundpad",
    },
    "soundpad.library.add": {"uk": "Додати", "en": "Add"},
    "soundpad.library.added": {"uk": "Додано", "en": "Added"},
    "soundpad.library.loading": {"uk": "Завантаження звуків…", "en": "Loading sounds…"},
    "soundpad.library.error_title": {
        "uk": "Не вдалося завантажити звуки",
        "en": "Couldn't load sounds",
    },
    "soundpad.library.retry": {"uk": "Спробувати ще раз", "en": "Try again"},
    "soundpad.library.empty_title": {
        "uk": "На цій сторінці немає звуків",
        "en": "No sounds on this page",
    },
    "soundpad.library.page": {"uk": "Сторінка {n}", "en": "Page {n}"},
    "soundpad.library.prev": {"uk": "Назад", "en": "Previous"},
    "soundpad.library.next": {"uk": "Далі", "en": "Next"},
```

- [ ] **Step 4: Add locale support to SoundpadQmlApi**

In `src/stream_cheremsha/ui/soundpad_qml_api.py`:

1. Extend the PySide6 import — replace:

```python
from PySide6.QtCore import QCoreApplication, QObject, QTimer, QUrl, Signal, Slot
```

with:

```python
from PySide6.QtCore import (
    QCoreApplication,
    QObject,
    Property,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
```

2. Add the import to the top-level import block — insert `from stream_cheremsha import l10n` on its own line immediately BEFORE the existing `from stream_cheremsha.soundpad.models import (` line (isort order: parent package first). Then add this constant after the existing `logger = logging.getLogger(__name__)` line:

```python
_LIBRARY_L10N_KEYS = (
    "button",
    "title",
    "subtitle",
    "add",
    "added",
    "loading",
    "error_title",
    "retry",
    "empty_title",
    "page",
    "prev",
    "next",
)
```

3. Add the new signals to the class body, right after `importNeeded = Signal(str)`:

```python
    stringsChanged = Signal()  # locale changed; QML re-reads libraryStrings
```

4. In `__init__`, add at the end of the method (after the hotkey signal connections block):

```python
        self._locale = l10n.normalize_locale(l10n.DEFAULT_LOCALE)
```

5. Add these methods to the class, after `_schedule_metadata`:

```python
    @Property("QVariantMap", notify=stringsChanged)
    def libraryStrings(self) -> dict[str, str]:  # noqa: ANN201 - PySide pattern
        out = {}
        for short in _LIBRARY_L10N_KEYS:
            try:
                out[short] = l10n.tr(self._locale, f"soundpad.library.{short}")
            except KeyError:
                out[short] = ""
        return out

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        k = (key or "").strip()
        if not k:
            return ""
        try:
            return l10n.tr(self._locale, k)
        except KeyError:
            return k

    def set_locale(self, locale: str) -> None:
        nl = l10n.normalize_locale(locale)
        if nl == self._locale:
            return
        self._locale = nl
        self.stringsChanged.emit()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_api.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/l10n.py src/stream_cheremsha/ui/soundpad_qml_api.py tests/test_soundpad_library_api.py
git add src/stream_cheremsha/l10n.py src/stream_cheremsha/ui/soundpad_qml_api.py tests/test_soundpad_library_api.py
git commit -m "feat(soundpad): library l10n keys and locale-aware strings on QML api"
```

---

### Task 5: Library slots on SoundpadQmlApi (load / preview / add)

**Files:**
- Modify: `src/stream_cheremsha/ui/soundpad_qml_api.py`
- Test: `tests/test_soundpad_library_api.py` (append; created in Task 4)

**Interfaces:**
- Consumes: Task 2's `MyInstantsClient` (`fetch_index_entries`, `resolve_mp3_url`, `ensure_cached_mp3`) + `candidate_langs`; Task 3's `engine.play_preview(data)` / `engine.stop_preview()`; store's `resolve_library_path(src, sid) -> Path`, `upsert(entry) -> list[str]`, `next_order()`.
- Produces on `SoundpadQmlApi`:
  - Signals: `libraryRowsChanged()`, `libraryStatusChanged(str)`, `libraryPageChanged(int)`, `previewPlayingChanged(str)`, `libraryAdded(str)` (sound id), `libraryAddFailed(str)` (sound path).
  - Properties: `libraryRowsJson -> str` (JSON array of `{path, title}` — codebase convention, same as `soundsJson`), `libraryStatus -> str` (`""` | `"loading"` | `"error"`), `libraryPage -> int`, `previewPlayingId -> str` (`""` when idle).
  - Slots: `openLibrary()`, `loadLibraryPage(int)`, `previewSound(str)`, `stopPreview()`, `addLibrarySound(str)`.
  - Constructor kwarg: `library_client=None` (inject a fake-backed client in tests; default lazily creates the real one — no curl_cffi import at startup).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_soundpad_library_api.py`:

```python
import json as _json
from pathlib import Path


class FakeResponse:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class FakeSession:
    """Canned responses per URL substring; records requested URLs."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.requests: list[tuple[str, object]] = []

    def get(self, url, headers=None):
        self.requests.append((url, headers))
        for key, resp in self.routes.items():
            if key in url:
                return resp
        raise AssertionError(f"no fake route for {url}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _index_html() -> str:
    p = Path(__file__).resolve().parent / "fixtures" / "myinstants_ua_index.html"
    return p.read_text(encoding="utf-8")


_INSTANT_HTML = (
    '<html><body>var mp3_url="https://www.myinstants.com/music/x.mp3";</body></html>'
)


def _client_with(tmp_path, session):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    return MyInstantsClient(
        session_factory=lambda: session, cache_dir=tmp_path / "cache", min_interval_sec=0
    )


def test_load_library_page_populates_rows(tmp_path):
    api, _ = _api(tmp_path)
    fake = FakeSession({"index/ua": FakeResponse(text=_index_html())})
    api._library = _client_with(tmp_path, fake)

    api.loadLibraryPage(1)
    rows = _json.loads(api.libraryRowsJson)
    assert [r["path"] for r in rows][:2] == [
        "/en/instant/slava-ukraini-12345/",
        "/en/instant/ptn-pnh-23456/",
    ]
    assert all(r["title"] for r in rows)
    assert api.libraryStatus == ""
    assert api.libraryPage == 1


def test_load_library_page_error_state(tmp_path):
    class BoomSession(FakeSession):
        def get(self, url, headers=None):
            raise RuntimeError("network down")

    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, BoomSession())
    api.loadLibraryPage(1)
    assert api.libraryStatus == "error"


def test_preview_sound_plays_cached_mp3(tmp_path):
    fake = FakeSession({"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")})
    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    calls: list[bytes] = []
    api._engine.play_preview = lambda data: (calls.append(bytes(data)), "PLAYING")[1]

    api.previewSound("/en/instant/slava-ukraini-12345/")
    assert calls == [b"MP3DATA"]
    assert api.previewPlayingId == "/en/instant/slava-ukraini-12345/"


def test_add_library_sound_copies_into_store(tmp_path):
    fake = FakeSession({"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")})
    api, store = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    added: list[str] = []
    failed: list[str] = []
    api.libraryAdded.connect(added.append)
    api.libraryAddFailed.connect(failed.append)
    # Seed the row so the title resolves from the loaded page.
    api._lib_rows = [{"path": "/en/instant/slava-ukraini-12345/", "title": "Slava Ukraini"}]

    api.addLibrarySound("/en/instant/slava-ukraini-12345/")
    assert failed == []
    assert len(added) == 1
    e = store.get(added[0])
    assert e is not None
    assert e.name == "Slava Ukraini"
    assert Path(e.file_path).is_file()
    assert Path(e.file_path).parent == store.library_dir
    assert Path(e.file_path).read_bytes() == b"MP3DATA"


def test_add_library_sound_failure_emits_failed(tmp_path):
    class BoomSession(FakeSession):
        def get(self, url, headers=None):
            raise RuntimeError("network down")

    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, BoomSession())
    failed: list[str] = []
    api.libraryAddFailed.connect(failed.append)
    api.addLibrarySound("/en/instant/x/")
    assert failed == ["/en/instant/x/"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_api.py -v`
Expected: new tests FAIL with `AttributeError: 'SoundpadQmlApi' object has no attribute 'libraryRowsJson'` (Task 4's 3 tests still pass)

- [ ] **Step 3: Write the implementation**

In `src/stream_cheremsha/ui/soundpad_qml_api.py`:

1. In `__init__`, extend the signature and add library state — replace:

```python
    def __init__(self, *, store, engine, hotkeys, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._engine = engine
        self._hotkeys = hotkeys
        self._meta_tasks: set[asyncio.Task] = set()
```

with:

```python
    def __init__(
        self,
        *,
        store,
        engine,
        hotkeys,
        parent: QObject | None = None,
        library_client=None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._engine = engine
        self._hotkeys = hotkeys
        self._meta_tasks: set[asyncio.Task] = set()
        # Library (MyInstants): lazy client + UI state.
        self._library = library_client  # MyInstantsClient | None; created on first use
        self._lib_rows: list[dict] = []
        self._lib_status = ""  # "", "loading", "error"
        self._lib_page = 1
        self._lib_inflight = False
        self._lib_add_inflight = False
        self._preview_playing_id = ""
        self._lib_tasks: set[asyncio.Task] = set()
```

2. Add the new signals to the class body, right after `stringsChanged = Signal()` (added in Task 4):

```python
    libraryRowsChanged = Signal()
    libraryStatusChanged = Signal(str)
    libraryPageChanged = Signal(int)
    previewPlayingChanged = Signal(str)
    libraryAdded = Signal(str)  # sound id successfully added from the library
    libraryAddFailed = Signal(str)  # sound path that failed to add
```

3. Append this block at the END of the `SoundpadQmlApi` class (after `importDroppedUrls`):

```python
    # ------------------------------------------------------------------ library
    def _library_client(self):
        if self._library is None:
            from stream_cheremsha.soundpad.myinstants import MyInstantsClient

            self._library = MyInstantsClient()
        return self._library

    @Property(str, notify=libraryRowsChanged)
    def libraryRowsJson(self) -> str:
        return json.dumps(self._lib_rows, ensure_ascii=False)

    @Property(str, notify=libraryStatusChanged)
    def libraryStatus(self) -> str:
        return self._lib_status

    @Property(int, notify=libraryPageChanged)
    def libraryPage(self) -> int:
        return self._lib_page

    @Property(str, notify=previewPlayingChanged)
    def previewPlayingId(self) -> str:
        return self._preview_playing_id

    def _set_library_status(self, status: str) -> None:
        if status == self._lib_status:
            return
        self._lib_status = status
        self.libraryStatusChanged.emit(status)

    def _set_library_page(self, page: int) -> None:
        p = max(1, int(page))
        if p == self._lib_page:
            return
        self._lib_page = p
        self.libraryPageChanged.emit(p)

    def _load_page_worker(self, page: int) -> list[dict]:
        from stream_cheremsha.soundpad.myinstants import candidate_langs

        client = self._library_client()
        last_err: Exception | None = None
        for lang in candidate_langs(self._locale):
            try:
                entries = client.fetch_index_entries(lang, page)
            except Exception as e:  # noqa: BLE001 - network/HTTP failure: next language
                last_err = e
                continue
            if entries:
                return [{"path": s.path, "title": s.title} for s in entries]
        if last_err is not None:
            raise RuntimeError(f"myinstants fetch failed: {last_err}") from last_err
        return []

    def _finish_library_load(self, rows: list[dict] | None, err: Exception | None) -> None:
        self._lib_inflight = False
        if err is not None or rows is None:
            logger.warning("soundpad library load failed: %s", err)
            self._set_library_status("error")
            return
        self._lib_rows = rows
        self._set_library_status("")
        self.libraryRowsChanged.emit()

    @Slot(int)
    def loadLibraryPage(self, page: int) -> None:
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        if self._lib_inflight:
            return
        self.stopPreview()
        self._set_library_page(page)
        self._set_library_status("loading")
        self._lib_inflight = True

        async def _job() -> None:
            try:
                rows = await asyncio.to_thread(self._load_page_worker, page)
            except Exception as e:  # noqa: BLE001
                self._finish_library_load(None, e)
                return
            self._finish_library_load(rows, None)

        if _loop_running():
            t = asyncio.get_running_loop().create_task(_job())
            self._lib_tasks.add(t)
            t.add_done_callback(self._lib_tasks.discard)
        else:  # no running loop (unit tests): run inline
            try:
                rows = self._load_page_worker(page)
            except Exception as e:  # noqa: BLE001
                self._finish_library_load(None, e)
            else:
                self._finish_library_load(rows, None)

    @Slot()
    def openLibrary(self) -> None:
        self.loadLibraryPage(1)

    @Slot(str)
    def previewSound(self, sound_path: str) -> None:
        p = (sound_path or "").strip()
        if not p.startswith("/"):
            return
        client = self._library_client()

        async def _job() -> None:
            try:
                mp3_url = await asyncio.to_thread(client.resolve_mp3_url, p)
                local = await asyncio.to_thread(client.ensure_cached_mp3, mp3_url)
                data = await asyncio.to_thread(Path(local).read_bytes)
            except Exception as e:  # noqa: BLE001
                logger.warning("soundpad preview failed for %s: %s", p, e)
                return
            if self._engine.play_preview(data) == "PLAYING":
                self._preview_playing_id = p
                self.previewPlayingChanged.emit(p)

        if _loop_running():
            t = asyncio.get_running_loop().create_task(_job())
            self._lib_tasks.add(t)
            t.add_done_callback(self._lib_tasks.discard)
        else:  # no running loop (unit tests): run inline
            try:
                mp3_url = client.resolve_mp3_url(p)
                local = client.ensure_cached_mp3(mp3_url)
                data = Path(local).read_bytes()
            except Exception as e:  # noqa: BLE001
                logger.warning("soundpad preview failed for %s: %s", p, e)
            else:
                if self._engine.play_preview(data) == "PLAYING":
                    self._preview_playing_id = p
                    self.previewPlayingChanged.emit(p)

    @Slot()
    def stopPreview(self) -> None:
        self._engine.stop_preview()
        if self._preview_playing_id:
            self._preview_playing_id = ""
            self.previewPlayingChanged.emit("")

    def _library_title_for(self, sound_path: str) -> str:
        for row in self._lib_rows:
            if row.get("path") == sound_path:
                t = str(row.get("title") or "").strip()
                if t:
                    return t
        slug = (sound_path.strip("/").split("/")[-2] or "").strip()
        return slug.replace("-", " ").strip()

    def _commit_library_add(self, sound_path: str, local: Path) -> str:
        title = self._library_title_for(sound_path) or Path(local).stem or "Sound"
        sid = f"sp-{uuid.uuid4().hex[:8]}"
        dest = self._store.resolve_library_path(local, sid)
        entry = SoundEntry(
            id=sid,
            name=title.strip()[:80] or "Sound",
            file_path=str(dest),
            category="Library",
            hotkey="",
            volume=1.0,
            playback_mode=PlaybackMode.RESTART,
            cooldown_sec=0.0,
            triggers=(),
            waveform_peaks=(),
            duration_sec=0.0,
            play_count=0,
            last_played_at="",
            order=self._store.next_order(),
        )
        errs = self._store.upsert(entry)
        if errs:
            logger.warning("soundpad library add rejected %s: %s", sound_path, errs)
            return ""
        self.soundsChanged.emit()
        self._schedule_metadata(sid, dest)
        return sid

    @Slot(str)
    def addLibrarySound(self, sound_path: str) -> None:
        p = (sound_path or "").strip()
        if not p.startswith("/") or self._lib_add_inflight:
            return
        client = self._library_client()
        self._lib_add_inflight = True

        def _finish(local: Path | None, err: Exception | None) -> None:
            self._lib_add_inflight = False
            if local is None or err is not None:
                logger.warning("soundpad library add failed for %s: %s", p, err)
                self.libraryAddFailed.emit(p)
                return
            sid = self._commit_library_add(p, Path(local))
            if sid:
                self.libraryAdded.emit(sid)

        async def _job() -> None:
            try:
                mp3_url = await asyncio.to_thread(client.resolve_mp3_url, p)
                local = await asyncio.to_thread(client.ensure_cached_mp3, mp3_url)
            except Exception as e:  # noqa: BLE001
                _finish(None, e)
                return
            _finish(Path(local), None)

        if _loop_running():
            t = asyncio.get_running_loop().create_task(_job())
            self._lib_tasks.add(t)
            t.add_done_callback(self._lib_tasks.discard)
        else:  # no running loop (unit tests): run inline
            try:
                mp3_url = client.resolve_mp3_url(p)
                local = client.ensure_cached_mp3(mp3_url)
            except Exception as e:  # noqa: BLE001
                _finish(None, e)
            else:
                _finish(Path(local), None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_api.py -v`
Expected: PASS (8 tests — 3 from Task 4 + 5 new)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/ui/soundpad_qml_api.py tests/test_soundpad_library_api.py
git add src/stream_cheremsha/ui/soundpad_qml_api.py tests/test_soundpad_library_api.py
git commit -m "feat(soundpad): library load/preview/add slots on QML api"
```

---

### Task 6: Wire locale into the soundpad API from MainWindow

**Files:**
- Modify: `src/stream_cheremsha/ui/main_window.py` (2 small insertions)
- Test: `tests/test_soundpad_nav_lazy.py` (append one static check, same style as existing tests)

**Interfaces:**
- Consumes: Task 4's `SoundpadQmlApi.set_locale(locale)`; MainWindow's existing `self._locale`.
- Produces: the soundpad API receives the app locale at lazy creation AND on every retranslate (settings language switch), so `libraryStrings`/`tr()` and the MyInstants language candidate order (`uk → ua,en`) always match the UI language.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_soundpad_nav_lazy.py`:

```python
def test_soundpad_api_locale_wiring():
    i_lazy = MW.find("def _soundpad_api_lazy")
    i_retr = MW.find("def _retranslate_ui")
    assert i_lazy != -1 and i_retr > i_lazy, "both methods must exist"
    lazy_src = MW[i_lazy:i_retr]
    retr_src = MW[i_retr:]
    # Lazy creation applies the current locale...
    assert "set_locale(self._locale)" in lazy_src
    # ...and a settings language switch re-applies it to the cached api.
    assert "_soundpad_api" in retr_src and "set_locale(self._locale)" in retr_src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_nav_lazy.py -v`
Expected: new test FAILS (`assert "set_locale(self._locale)" in lazy_src`), existing tests pass

- [ ] **Step 3: Write the implementation**

In `src/stream_cheremsha/ui/main_window.py`:

1. In `_soundpad_api_lazy`, insert immediately after the line
   `api = SoundpadQmlApi(store=store, engine=engine, hotkeys=hotkeys, parent=self)`:

```python
        api.set_locale(self._locale)
```

2. In `_retranslate_ui`, insert immediately AFTER the existing docks block:

```python
        if getattr(self, "_docks_qml_api", None) is not None:
            self._docks_qml_api.set_locale(self._locale)
            self._docks_qml_api.refreshUi()
```

i.e. between that block and `if self._chat_popout is not None:`:

```python
        if getattr(self, "_soundpad_api", None) is not None:
            self._soundpad_api.set_locale(self._locale)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_nav_lazy.py -v`
Expected: PASS (all nav-lazy tests incl. the new one)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src/stream_cheremsha/ui/main_window.py tests/test_soundpad_nav_lazy.py
git add src/stream_cheremsha/ui/main_window.py tests/test_soundpad_nav_lazy.py
git commit -m "feat(soundpad): apply app locale to soundpad library api"
```

---

### Task 7: CheremshaModal — configurable dialog width

**Files:**
- Modify: `src/stream_cheremsha/qml/components/CheremshaModal.qml` (2 small edits)
- Test: `tests/test_soundpad_library_qml.py` (create; QML static checks live here, Task 8 appends more)

**Interfaces:**
- Consumes: existing CheremshaModal (`title`, `subtitle`, `opened`, `body`/`footer` Components, `closeRequested()`).
- Produces: `property real preferredWidth: 560` — dialog width becomes `Math.min(modal.preferredWidth, parent.width - 64)`; default keeps every existing modal pixel-identical.

- [ ] **Step 1: Write the failing test**

Create `tests/test_soundpad_library_qml.py`:

```python
from __future__ import annotations

from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml"


def _read(rel: str) -> str:
    return (QML / rel).read_text(encoding="utf-8")


def test_modal_has_preferred_width():
    src = _read("components/CheremshaModal.qml")
    assert "property real preferredWidth" in src
    assert "modal.preferredWidth" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_qml.py -v`
Expected: FAIL (`assert "property real preferredWidth" in src`)

- [ ] **Step 3: Write the implementation**

In `src/stream_cheremsha/qml/components/CheremshaModal.qml`:

1. Insert after the line `property bool opened: false`:

```qml
    property real preferredWidth: 560
```

2. Replace the dialog width line — change:

```qml
        width: Math.min(560, parent.width - 64)
```

to:

```qml
        width: Math.min(modal.preferredWidth, parent.width - 64)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_qml.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/qml/components/CheremshaModal.qml tests/test_soundpad_library_qml.py
git commit -m "feat(qml): CheremshaModal preferredWidth for wider dialogs"
```

---

### Task 8: SoundpadLibraryPanel + Library button/modal in SoundpadView

**Files:**
- Create: `src/stream_cheremsha/qml/components/SoundpadLibraryPanel.qml`
- Modify: `src/stream_cheremsha/qml/components/qmldir` (append one line)
- Modify: `src/stream_cheremsha/qml/SoundpadView.qml` (state property, header button, modal)
- Test: `tests/test_soundpad_library_qml.py` (append static checks + a QQmlEngine compile check with a fake `spApi`)

**Interfaces:**
- Consumes: Task 5's spApi properties/slots (`libraryRowsJson`, `libraryStatus`, `libraryPage`, `previewPlayingId`, `openLibrary()`, `loadLibraryPage(int)`, `previewSound(str)`, `stopPreview()`, `addLibrarySound(str)`, `libraryAddFailed` signal); Task 4's `spApi.libraryStrings`; Task 7's `preferredWidth`.
- Produces: a Library button in the Soundpad header (book icon, outline style), a 720px modal with the panel body; per-row Play/Stop preview + Add with "Додано" flash; loading/error+retry/empty states; prev/page-label/next pagination.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_soundpad_library_qml.py`:

```python
def test_qmldir_registers_panel():
    src = _read("components/qmldir")
    assert "SoundpadLibraryPanel 1.0 SoundpadLibraryPanel.qml" in src


def test_view_wires_library_button_and_modal():
    src = _read("SoundpadView.qml")
    assert "property bool showLibraryModal: false" in src
    assert "spApi.openLibrary()" in src
    assert "id: libraryModal" in src
    assert "preferredWidth: 720" in src
    assert "SoundpadLibraryPanel {}" in src


def test_panel_qml_compiles(qapp):
    """Load the panel with a fake spApi context property; no QML errors."""
    from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
    from PySide6.QtQml import QQmlEngine

    class FakeSpApi(QObject):
        rowsChanged = Signal()
        statusChanged = Signal(str)
        pageChanged = Signal(int)
        previewPlayingChanged = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._rows_json = "[]"
            self._status = ""
            self._page = 1
            self._preview_id = ""

        @Property(str, notify=rowsChanged)
        def libraryRowsJson(self):
            return self._rows_json

        @Property(str, notify=statusChanged)
        def libraryStatus(self):
            return self._status

        @Property(int, notify=pageChanged)
        def libraryPage(self):
            return self._page

        @Property(str, notify=previewPlayingChanged)
        def previewPlayingId(self):
            return self._preview_id

        @Property("QVariantMap")
        def libraryStrings(self):
            return {
                "button": "Бібліотека",
                "title": "Бібліотека звуків",
                "subtitle": "",
                "add": "Додати",
                "added": "Додано",
                "loading": "Завантаження звуків…",
                "error_title": "Не вдалося завантажити звуки",
                "retry": "Спробувати ще раз",
                "empty_title": "На цій сторінці немає звуків",
                "page": "Сторінка {n}",
                "prev": "Назад",
                "next": "Далі",
            }

        @Slot()
        def openLibrary(self):
            pass

        @Slot(int)
        def loadLibraryPage(self, page: int):
            pass

        @Slot(str)
        def previewSound(self, path: str):
            pass

        @Slot()
        def stopPreview(self):
            pass

        @Slot(str)
        def addLibrarySound(self, path: str):
            pass

    engine = QQmlEngine()
    engine.addImportPath(str(QML))
    fake = FakeSpApi()
    engine.rootContext().setContextProperty("spApi", fake)
    url = QUrl.fromLocalFile(str(QML / "components" / "SoundpadLibraryPanel.qml"))
    item = engine.load(url)
    errs = [str(e.errorString()) for e in engine.errors()]
    assert item is not None, "; ".join(errs)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_qml.py -v`
Expected: the 3 new tests FAIL (file/registration/wiring missing), Task 7's test still passes

- [ ] **Step 3a: Create the panel component**

Create `src/stream_cheremsha/qml/components/SoundpadLibraryPanel.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Body of the MyInstants library modal (used inside CheremshaModal).
// Talks to spApi directly: rows/status/page come from its properties,
// actions go through its slots. All strings via spApi.libraryStrings.
Item {
    id: panel
    implicitHeight: 430

    readonly property var rows: _rows()
    function _rows() {
        try { return JSON.parse(spApi.libraryRowsJson || "[]"); } catch (err) { return []; }
    }

    readonly property string status: spApi.libraryStatus
    readonly property int page: spApi.libraryPage
    readonly property bool loading: panel.status === "loading"
    readonly property bool failed: panel.status === "error"
    readonly property bool showStates: panel.loading || panel.failed || panel.rows.length === 0

    // Path of the row that was just added (drives the «Додано» flash).
    property string addedPath: ""
    Timer {
        id: addedTimer
        interval: 1600
        repeat: false
        onTriggered: panel.addedPath = ""
    }

    Connections {
        target: spApi
        function onLibraryAddFailed(path) {
            if (panel.addedPath === String(path)) panel.addedPath = "";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // ---- Loading / error / empty states ----
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: panel.showStates ? 340 : 0
            visible: panel.showStates

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                width: Math.min(360, parent.width - 40)

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: panel.loading ? (spApi.libraryStrings.loading || "Завантаження звуків…")
                                        : (panel.failed ? (spApi.libraryStrings.error_title || "Не вдалося завантажити звуки")
                                                        : (spApi.libraryStrings.empty_title || "На цій сторінці немає звуків"))
                    color: "#e8ecf5"
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                }

                BusyIndicator {
                    Layout.alignment: Qt.AlignHCenter
                    running: panel.loading
                    visible: panel.loading
                    width: 28; height: 28
                }

                Button {
                    id: retryBtn
                    visible: panel.failed && !panel.loading
                    text: spApi.libraryStrings.retry || "Спробувати ще раз"
                    hoverEnabled: true
                    focusPolicy: Qt.TabFocus
                    font.pixelSize: 13
                    implicitWidth: 170
                    implicitHeight: 36
                    contentItem: Text {
                        text: retryBtn.text; color: "white"; font: retryBtn.font
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: retryBtn.pressed ? "#7c3aed" : (retryBtn.hovered ? "#9d71f7" : "#9b5cff") }
                            GradientStop { position: 1.0; color: retryBtn.pressed ? "#6d28d9" : (retryBtn.hovered ? "#8b5cf6" : "#7c3aed") }
                        }
                    }
                    onClicked: spApi.loadLibraryPage(panel.page)
                }
            }
        }

        // ---- Sound list ----
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !panel.showStates
            model: panel.rows
            spacing: 8
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: rowItem
                width: listView.width
                height: 56
                radius: 10
                color: rowMa.containsMouse ? "#141d30" : "#0e1524"
                border.width: 1
                border.color: spApi.previewPlayingId === modelData.path ? "#7c3aed" : "#1e2942"
                Behavior on color { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title || modelData.path
                        color: "#e8ecf5"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    // Play / stop preview
                    Rectangle {
                        id: playBtn
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        radius: 17
                        readonly property bool playing: spApi.previewPlayingId === modelData.path
                        color: playing ? "#2a1e4d" : (playMa.containsMouse ? "#18233c" : "#101a2e")
                        border.width: 1
                        border.color: playing ? "#9b5cff" : (playMa.containsMouse ? "#3a4a6e" : "#26314a")
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Image {
                            anchors.centerIn: parent
                            width: 14; height: 14
                            source: playBtn.playing ? Qt.resolvedUrl("../assets/icons/stop.svg")
                                                    : Qt.resolvedUrl("../assets/icons/play.svg")
                            opacity: 0.95
                        }

                        MouseArea {
                            id: playMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (playBtn.playing) spApi.stopPreview();
                                else spApi.previewSound(modelData.path);
                            }
                        }
                    }

                    // Add to soundpad
                    Rectangle {
                        id: addBtn
                        Layout.preferredWidth: 92
                        Layout.preferredHeight: 34
                        radius: 9
                        readonly property bool justAdded: panel.addedPath === modelData.path
                        color: justAdded ? "#1d3a2a" : (addMa.containsMouse ? "#18233c" : "#101a2e")
                        border.width: 1
                        border.color: justAdded ? "#34d399" : (addMa.containsMouse ? "#3a4a6e" : "#26314a")
                        Behavior on color { ColorAnimation { duration: 120 } }

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Image {
                                width: 13; height: 13
                                source: addBtn.justAdded ? Qt.resolvedUrl("../assets/icons/check.svg")
                                                         : Qt.resolvedUrl("../assets/icons/web_plus.svg")
                                opacity: 0.95
                            }
                            Text {
                                text: addBtn.justAdded ? (spApi.libraryStrings.added || "Додано")
                                                       : (spApi.libraryStrings.add || "Додати")
                                color: addBtn.justAdded ? "#34d399" : "#c7d2e5"
                                font.pixelSize: 12
                            }
                        }

                        MouseArea {
                            id: addMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                panel.addedPath = modelData.path;
                                addedTimer.restart();
                                spApi.addLibrarySound(modelData.path);
                            }
                        }
                    }
                }

                MouseArea {
                    id: rowMa
                    anchors.fill: parent
                    hoverEnabled: true
                }
            }
        }

        // ---- Pagination ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            visible: !panel.showStates
            spacing: 10

            Button {
                id: prevBtn
                text: spApi.libraryStrings.prev || "Назад"
                enabled: panel.page > 1 && !panel.loading
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 12
                implicitWidth: 96
                implicitHeight: 34
                opacity: prevBtn.enabled ? 1.0 : 0.45
                contentItem: Text {
                    text: prevBtn.text; color: "#c7d2e5"; font: prevBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: (prevBtn.hovered && prevBtn.enabled) ? "#18233c" : "#0f1728"
                    border.width: 1; border.color: (prevBtn.hovered && prevBtn.enabled) ? "#3a4a6e" : "#26314a"
                }
                onClicked: spApi.loadLibraryPage(panel.page - 1)
            }

            Item { Layout.fillWidth: true }

            Text {
                text: (spApi.libraryStrings.page || "Сторінка {n}").replace("{n}", String(panel.page))
                color: "#7f8aa3"
                font.pixelSize: 12
            }

            Item { Layout.fillWidth: true }

            Button {
                id: nextBtn
                text: spApi.libraryStrings.next || "Далі"
                enabled: !panel.loading
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 12
                implicitWidth: 96
                implicitHeight: 34
                contentItem: Text {
                    text: nextBtn.text; color: "#c7d2e5"; font: nextBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: nextBtn.hovered ? "#18233c" : "#0f1728"
                    border.width: 1; border.color: nextBtn.hovered ? "#3a4a6e" : "#26314a"
                }
                onClicked: spApi.loadLibraryPage(panel.page + 1)
            }
        }
    }
}
```

- [ ] **Step 3b: Register the component**

Append this line to `src/stream_cheremsha/qml/components/qmldir` (after the `SoundpadAddDialog` line):

```
SoundpadLibraryPanel 1.0 SoundpadLibraryPanel.qml
```

- [ ] **Step 3c: Wire SoundpadView.qml**

In `src/stream_cheremsha/qml/SoundpadView.qml`:

1. Insert after the line `property string addErrorMsg: ""` (in the state block):

```qml
    property bool showLibraryModal: false
```

2. In the header RowLayout, insert BEFORE the `// primary add` comment (i.e. between the search Rectangle and the add Button):

```qml
            // library (MyInstants) — secondary action, outline style
            Button {
                id: libraryBtn
                text: spApi.libraryStrings.button || "Бібліотека"
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 13
                implicitWidth: 140
                implicitHeight: 38
                contentItem: RowLayout {
                    spacing: 7
                    Image { source: Qt.resolvedUrl("../assets/icons/book.svg"); width: 15; height: 15 }
                    Text { text: libraryBtn.text; color: "#c7d2e5"; font: libraryBtn.font }
                }
                background: Rectangle {
                    radius: 9
                    color: libraryBtn.hovered ? "#141d30" : "transparent"
                    border.width: 1
                    border.color: libraryBtn.hovered ? "#7c3aed" : "#26314a"
                    Behavior on border.color { ColorAnimation { duration: 130 } }
                }
                scale: libraryBtn.pressed ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: 100 } }
                onClicked: { spApi.openLibrary(); root.showLibraryModal = true; }
            }
```

3. Insert the modal AFTER the add-sound modal block (the `CheremshaModal { id: addModal ... }` that ends right before the comment `// Hotkey capture for the add dialog:`):

```qml
    // ---- Library modal (MyInstants) ----
    CheremshaModal {
        id: libraryModal
        anchors.fill: parent
        preferredWidth: 720
        title: spApi.libraryStrings.title || "Бібліотека звуків"
        subtitle: spApi.libraryStrings.subtitle || ""
        opened: root.showLibraryModal
        onCloseRequested: { root.showLibraryModal = false; spApi.stopPreview(); }

        body: Component {
            SoundpadLibraryPanel {}
        }
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_soundpad_library_qml.py -v`
Expected: PASS (4 tests — static checks + QQmlEngine compile check)

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/qml/components/SoundpadLibraryPanel.qml \
        src/stream_cheremsha/qml/components/qmldir \
        src/stream_cheremsha/qml/SoundpadView.qml \
        tests/test_soundpad_library_qml.py
git commit -m "feat(soundpad): library modal — browse, preview, add from MyInstants"
```

---

### Task 9: Full verification + agent-knowledge update

**Files:**
- Create: `.agent/domains/soundpad.md` (new subsystem → required by AGENTS.md "Knowledge Freshness")
- Modify: `.agent/index.md` (tab index table + core classes)
- No new tests; this task runs the whole suite and lints.

- [ ] **Step 1: Run the complete soundpad test surface**

```bash
PYTHONPATH=. .venv/bin/pytest \
    tests/test_soundpad_myinstants.py \
    tests/test_soundpad_engine.py \
    tests/test_soundpad_library_api.py \
    tests/test_soundpad_nav_lazy.py \
    tests/test_soundpad_library_qml.py -v
```

Expected: ALL PASS. If anything fails, fix the implementation (not the assertions) and re-run until green.

- [ ] **Step 2: Lint + format check**

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/stream_cheremsha/soundpad/myinstants.py \
    src/stream_cheremsha/ui/soundpad_qml_api.py \
    src/stream_cheremsha/soundpad/engine.py \
    src/stream_cheremsha/l10n.py tests/
```

Expected: no errors. Apply `.venv/bin/ruff format` to any file it flags, then re-run Step 1 for the affected module only.

- [ ] **Step 3: Create the soundpad domain doc**

Create `.agent/domains/soundpad.md`:

````markdown
# Soundpad (tab 11)

Instant sounds for streaming: hotkey-triggered playback, categories, waveform cards, and a MyInstants **Library** (browse → preview → add).

## Key files

| Symbol | File | Responsibility |
|--------|------|----------------|
| `SoundpadStore` | `src/stream_cheremsha/soundpad/store.py` | QSettings-backed entries; `library_dir`; `resolve_library_path()` copies into `<AppData>/soundpad/sounds/` |
| `SoundpadAudioEngine` | `src/stream_cheremsha/soundpad/engine.py` | Playback modes (restart/overlap/replace/queue/hold), cooldowns, ducking; preview via `play_preview()` / `stop_preview()` (sink key prefix `soundpad-preview:`) |
| `GlobalHotkeyManager` + backends | `src/stream_cheremsha/soundpad/hotkeys.py` | pynput X11 backend; `FakeHotkeyBackend` for tests |
| `MyInstantsClient` | `src/stream_cheremsha/soundpad/myinstants.py` | Rate-limited (≥1.2 s between requests) MyInstants fetcher; bounded caches: index LRU ≤32 pages / TTL 600 s, MP3 disk cache ≤128 files & ≤256 MB with atomic writes |
| `SoundpadQmlApi` | `src/stream_cheremsha/ui/soundpad_qml_api.py` | QML bridge: grid CRUD + library slots (`openLibrary`, `loadLibraryPage`, `previewSound`, `stopPreview`, `addLibrarySound`) + l10n (`libraryStrings`, `tr()`, `set_locale()`) |
| `SoundpadView.qml` / `components/SoundpadLibraryPanel.qml` | `src/stream_cheremsha/qml/` | UI; library modal via `CheremshaModal` (`preferredWidth: 720`) |

## Invariants & decisions

- **Lazy everything**: the soundpad stack is built only on first tab open (`MainWindow._soundpad_api_lazy`, called from `_bind_qml_context_properties`); never in `_build_ui`.
- **curl_cffi stays a lazy import** inside `myinstants.py` (module `__getattr__`) — Chrome TLS impersonation to get past Cloudflare; must not appear in startup imports.
- **Library adds are copied into the store dir** (`resolve_library_path`) so bounded cache eviction can never break an added sound. The MP3 cache is disposable by design.
- **Locale**: app locale uk → MyInstants `ua` (fallback `en`), en → `en`. `l10n.tr()` raises `KeyError` on unknown keys — API slots catch and fall back to the key itself.
- **Preview** uses sink dedupe-key prefix `soundpad-preview:`; a cancelled preview must NOT emit `previewFinished`.
- QML collections are exposed as JSON strings (`soundsJson`, `libraryRowsJson`) — codebase convention, not QVariantList.

## Tests

`tests/test_soundpad_myinstants.py` (parsing/client/caches), `test_soundpad_engine.py` (playback/hold/preview), `test_soundpad_library_api.py` (l10n + library slots with FakeSession DI), `test_soundpad_nav_lazy.py` (static wiring checks), `test_soundpad_library_qml.py` (QML static + QQmlEngine compile check).
````

- [ ] **Step 4: Update the symbol index**

In `.agent/index.md`:

1. In section 3's table, append this row after the `_IX_MUSIC` row:

```markdown
| 11 | `_IX_SOUNDPAD` | Soundpad | Lazy / Warm | `_load_qml_page(11)` + `_soundpad_api_lazy()` (context prop `spApi`) |
```

2. In section 1's table, append this row after the `KeyringStore` row:

```markdown
| `MyInstantsClient` | `src/stream_cheremsha/soundpad/myinstants.py` | Rate-limited MyInstants fetcher with bounded index/MP3 caches (lazy curl_cffi) |
```

- [ ] **Step 5: Commit**

```bash
git add .agent/domains/soundpad.md .agent/index.md
git commit -m "docs(agent): soundpad domain doc and library subsystem in symbol index"
```

---

## Self-review notes (plan author)

- Every task is TDD-shaped: failing test → minimal implementation → green → lint → commit. No placeholders, no "similar to X".
- Cross-task contracts are explicit in each task's **Interfaces** block; Task 5 consumes exactly what Tasks 2–4 produce (verified against the real `store.py`, `models.py`, `engine.py`, `l10n.py` sources).
- Known pitfalls pre-handled: cancelled previews must not emit `previewFinished`; `stop_preview()` must not touch the sink when idle (existing `test_stop_all_halts_every_voice` asserts exact prefix lists); library adds copy into the store dir so cache eviction is safe; curl_cffi never imported at startup; QML rows via JSON string per codebase convention.
- Out of scope: search-within-library, favorites, max-page detection, non-myinstants sources, i18n beyond uk/en (matches app's existing locale set).

