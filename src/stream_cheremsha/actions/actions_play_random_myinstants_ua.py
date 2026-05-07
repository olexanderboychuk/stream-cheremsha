from __future__ import annotations

import re
from pathlib import Path


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
