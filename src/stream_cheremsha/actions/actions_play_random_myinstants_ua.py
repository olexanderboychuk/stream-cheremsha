from __future__ import annotations

import hashlib
import os
import random
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx

from stream_cheremsha.actions.actions_play_sound import play_sound_from_file
from stream_cheremsha.domain.protocols import AudioSink


_INSTANT_PATH_RE = re.compile(
    r'href\s*=\s*(?:"|\')(?P<path>/en/instant/[^"\']+)(?:"|\')',
    re.IGNORECASE,
)
_MP3_URL_RE = re.compile(
    r'(?P<url>https?://[^\s"\']+?\.mp3(?:[?#][^\s"\']*)?)',
    re.IGNORECASE,
)


def extract_instant_page_paths_from_ua_index_html(html: str) -> list[str]:
    if not html or not isinstance(html, str):
        return []

    paths: list[str] = []
    seen: set[str] = set()
    for m in _INSTANT_PATH_RE.finditer(html):
        p = (m.group("path") or "").strip()
        if not p:
            continue
        if not p.startswith("/en/instant/"):
            continue
        if p in seen:
            continue
        seen.add(p)
        paths.append(p)
    return paths


def extract_mp3_url_from_instant_page_html(html: str) -> str:
    if not html or not isinstance(html, str):
        raise ValueError("No myinstants .mp3 URL found in HTML")

    for m in _MP3_URL_RE.finditer(html):
        url = (m.group("url") or "").strip()
        if "myinstants" not in url.lower():
            continue
        return url
    raise ValueError("No myinstants .mp3 URL found in HTML")


def pick_random_instant_path(paths: list[str], *, rng: random.Random) -> str:
    if not paths:
        raise ValueError("paths is empty")
    return rng.choice(list(paths))


def _myinstants_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "stream-cheremsha" / "myinstants-cache"


def _cache_path_for_mp3_url(mp3_url: str) -> Path:
    u = (mp3_url or "").strip()
    if not u:
        raise ValueError("mp3_url is required")
    parsed = urlparse(u)
    ext = Path(parsed.path).suffix.lower()
    if ext != ".mp3":
        ext = ".mp3"
    key = hashlib.sha256(u.encode("utf-8")).hexdigest()[:24]
    return _myinstants_cache_dir() / f"{key}{ext}"


async def play_random_myinstants_ua(
    *,
    sink: AudioSink,
    volume_percent: int,
    skip_queue_if_same: bool,
    status: Callable[[str], None],
) -> None:
    status("myinstants: fetching UA index…")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,uk-UA,uk;q=0.8",
    }
    timeout = httpx.Timeout(connect=10.0, read=20.0, write=20.0, pool=10.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        index_url = "https://www.myinstants.com/en/index/ua/"
        index_resp = await client.get(index_url)
        index_resp.raise_for_status()
        paths = extract_instant_page_paths_from_ua_index_html(index_resp.text)
        if not paths:
            raise ValueError("No MyInstants UA instant paths found")

        chosen_path = pick_random_instant_path(paths, rng=random.Random())
        instant_page_url = f"https://www.myinstants.com{chosen_path}"

        status("myinstants: fetching instant page…")
        page_resp = await client.get(instant_page_url)
        page_resp.raise_for_status()
        mp3_url = extract_mp3_url_from_instant_page_html(page_resp.text)

        cache_path = _cache_path_for_mp3_url(mp3_url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        if cache_path.exists() and cache_path.is_file():
            try:
                os.utime(cache_path, None)
            except OSError:
                pass
            status("myinstants: playing cached mp3…")
            _enforce_cache_max_files(cache_path.parent, max_files=200)
            await play_sound_from_file(
                str(cache_path),
                sink=sink,
                volume_percent=volume_percent,
                skip_queue_if_same=skip_queue_if_same,
            )
            return

        status("myinstants: downloading mp3…")
        mp3_resp = await client.get(mp3_url)
        mp3_resp.raise_for_status()
        data = mp3_resp.content
        if not data:
            raise ValueError("Downloaded mp3 is empty")

    cache_path.write_bytes(data)
    try:
        os.utime(cache_path, None)
    except OSError:
        pass
    _enforce_cache_max_files(cache_path.parent, max_files=200)

    status("myinstants: playing mp3…")
    await play_sound_from_file(
        str(cache_path),
        sink=sink,
        volume_percent=volume_percent,
        skip_queue_if_same=skip_queue_if_same,
    )


def _enforce_cache_max_files(cache_dir: Path, *, max_files: int) -> None:
    max_files_int = int(max_files)
    if max_files_int < 0:
        raise ValueError("max_files must be >= 0")

    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return
    if not cache_path.is_dir():
        raise NotADirectoryError(str(cache_path))

    mp3_files: list[Path] = [p for p in cache_path.glob("*.mp3") if p.is_file()]
    if len(mp3_files) <= max_files_int:
        return

    def _mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    mp3_files.sort(key=_mtime, reverse=True)  # newest first
    to_delete = mp3_files[max_files_int:]
    for p in to_delete:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            # Best-effort eviction: ignore transient filesystem issues.
            continue
