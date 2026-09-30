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

# App locale (l10n: uk/en) -> MyInstants sound-language code. "ua" is accepted
# as an alias so a raw MyInstants language code also resolves correctly.
_LOCALE_TO_LANG = {"uk": "ua", "ua": "ua", "en": "en"}
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
