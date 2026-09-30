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

import hashlib
import os
import re
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class LibrarySound:
    path: str  # site path, e.g. "/en/instant/some-sound-123/"
    title: str


_INSTANT_ANCHOR_RE = re.compile(
    r'<a[^>]+href\s*=\s*(?:"|\')(?P<path>/[a-z]{2}/instant/[^"\']+)(?:"|\')[^>]*>'
    r"(?P<title>.*?)</a>",
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
        # page -> (stored_at_mono, entries); insertion-ordered eviction.
        self._index_cache: dict[int, tuple[float, list[LibrarySound]]] = {}

    # -- rate limit ---------------------------------------------------------
    def _throttle(self) -> None:
        wait = self._min_interval_sec - (time.monotonic() - self._last_request_mono)
        if wait > 0:
            time.sleep(wait)
        self._last_request_mono = time.monotonic()

    # -- trending pages -----------------------------------------------------
    def fetch_trending(self, page: int) -> list[LibrarySound]:
        """Entries for one trending page (in-memory cached; TTL + bounded).

        The base URL is country-free on purpose: the site geo-redirects it to
        the visitor's country index (/en/trending/ → 302 → /en/index/{cc}/),
        so each user gets their own country's sounds without locale mapping.
        """
        key = max(1, int(page))
        now = time.monotonic()
        hit = self._index_cache.get(key)
        if hit is not None and now - hit[0] <= self._index_ttl_sec:
            return list(hit[1])

        url = f"{ORIGIN}/en/trending/" + ("" if key == 1 else f"?page={key}")
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
