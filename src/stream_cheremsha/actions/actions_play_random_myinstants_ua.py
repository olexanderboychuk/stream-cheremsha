from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx

from stream_cheremsha.actions.actions_play_sound import play_sound_from_file
from stream_cheremsha.domain.protocols import AudioSink

_INSTANT_ANCHOR_RE = re.compile(
    r'<a[^>]+href\s*=\s*(?:"|\')(?P<path>/en/instant/[^"\']+)(?:"|\')[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
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
    for path, _title in extract_instant_entries_from_ua_index_html(html):
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def extract_instant_entries_from_ua_index_html(html: str) -> list[tuple[str, str]]:
    if not html or not isinstance(html, str):
        return []

    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in _INSTANT_ANCHOR_RE.finditer(html):
        p = (m.group("path") or "").strip()
        if not p or not p.startswith("/en/instant/"):
            continue
        if p in seen:
            continue
        t = re.sub(r"<[^>]+>", " ", str(m.group("title") or ""))
        title = " ".join(t.split()).strip()
        seen.add(p)
        out.append((p, title))
    return out


def _parse_skip_words(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        parts = [str(x) for x in raw]
    else:
        parts = re.split(r"[,\n\r\t;]+", str(raw))
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        w = (p or "").strip().casefold()
        if not w or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def _title_matches_skip_words(title: str, skip_words: list[str]) -> bool:
    if not skip_words:
        return False
    t = (title or "").casefold()
    if not t:
        return False
    return any(w in t for w in skip_words)


def extract_mp3_url_from_instant_page_html(html: str) -> str:
    if not html or not isinstance(html, str):
        raise ValueError("No myinstants .mp3 URL found in HTML")

    for m in _MP3_URL_RE.finditer(html):
        url = (m.group("url") or "").strip()
        host = (urlparse(url).hostname or "").strip().lower()
        if host not in ("www.myinstants.com", "www.myinstantscdn.com"):
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
        raise ValueError(f"mp3_url must end with .mp3 (got {ext or 'no extension'})")
    key = hashlib.sha256(u.encode("utf-8")).hexdigest()[:24]
    return _myinstants_cache_dir() / f"{key}{ext}"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path_obj = Path(path)
    if not path_obj.parent.exists():
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    tmp_path_str: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(path_obj.parent),
            prefix=f"{path_obj.name}.",
            suffix=".tmp",
        ) as f:
            tmp_path_str = f.name
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path_str, path_obj)
    finally:
        if tmp_path_str is not None:
            try:
                Path(tmp_path_str).unlink(missing_ok=True)
            except OSError:
                # Best-effort cleanup; replace may have succeeded.
                pass


async def play_random_myinstants_ua(
    *,
    sink: AudioSink,
    volume_percent: int,
    skip_queue_if_same: bool,
    max_duration_seconds: float,
    max_page: int,
    skip_words: object,
    status: Callable[[str], None],
) -> None:
    try:
        max_s = float(max_duration_seconds)
        if max_s < 0:
            max_s = 0.0
        mp = int(max_page)
        if mp < 1:
            mp = 1
        sw = _parse_skip_words(skip_words)

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
        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            rng = random.SystemRandom()
            page_n = rng.randint(1, mp)
            index_url = (
                "https://www.myinstants.com/en/index/ua/"
                if page_n == 1
                else f"https://www.myinstants.com/en/index/ua/?page={page_n}"
            )
            index_resp = await client.get(index_url)
            index_resp.raise_for_status()
            entries = extract_instant_entries_from_ua_index_html(index_resp.text)
            if not entries:
                raise ValueError("No MyInstants UA instant paths found")

            remaining = list(entries)
            cache_path: Path | None = None
            data: bytes | None = None

            max_attempts = min(40, len(remaining))
            for attempt in range(max_attempts):
                chosen_path, chosen_title = rng.choice(list(remaining))
                try:
                    remaining.remove((chosen_path, chosen_title))
                except ValueError:
                    # Shouldn't happen, but keep the loop robust.
                    pass
                if _title_matches_skip_words(chosen_title, sw):
                    status("myinstants: skipped (word filter)…")
                    continue

                instant_page_url = f"https://www.myinstants.com{chosen_path}"
                status("myinstants: fetching instant page…")
                page_resp = await client.get(instant_page_url)
                page_resp.raise_for_status()
                mp3_url = extract_mp3_url_from_instant_page_html(page_resp.text)

                cache_path = _cache_path_for_mp3_url(mp3_url)
                if cache_path.exists() and cache_path.is_file():
                    if max_s > 0:
                        dur = _probe_mp3_duration_seconds(cache_path)
                        if dur is not None and dur > max_s:
                            status(
                                f"myinstants: skipped (duration {dur:.1f}s > max {max_s:.1f}s)…"
                            )
                            continue
                        if dur is None:
                            status("myinstants: duration unknown (no ffprobe/ffmpeg); playing…")
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

                _atomic_write_bytes(cache_path, data)
                try:
                    os.utime(cache_path, None)
                except OSError:
                    pass
                _enforce_cache_max_files(cache_path.parent, max_files=200)

                if max_s > 0:
                    dur = _probe_mp3_duration_seconds(cache_path)
                    if dur is not None and dur > max_s:
                        status(f"myinstants: skipped (duration {dur:.1f}s > max {max_s:.1f}s)…")
                        continue
                    if dur is None:
                        status("myinstants: duration unknown (no ffprobe/ffmpeg); playing…")

                status("myinstants: playing mp3…")
                await play_sound_from_file(
                    str(cache_path),
                    sink=sink,
                    volume_percent=volume_percent,
                    skip_queue_if_same=skip_queue_if_same,
                )
                return

            raise ValueError("No MyInstants sound matched duration filter")

    except (httpx.HTTPError, OSError, ValueError) as e:
        status(f"myinstants: failed: {e}")
        return


def _probe_mp3_duration_seconds(path: Path) -> float | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(p),
                ],
                capture_output=True,
                timeout=15,
                check=False,
                text=True,
                encoding="utf-8",
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc and proc.returncode == 0 and proc.stdout:
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                fmt = payload.get("format")
                if isinstance(fmt, dict):
                    d = fmt.get("duration")
                    try:
                        v = float(d)
                    except (TypeError, ValueError):
                        v = None
                    if v is not None and v >= 0:
                        return v

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        proc2 = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "info", "-i", str(p), "-f", "null", "-"],
            capture_output=True,
            timeout=20,
            check=False,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    s = (proc2.stderr or "") + "\n" + (proc2.stdout or "")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
        ss = float(m.group(3))
    except (TypeError, ValueError):
        return None
    return max(0.0, (hh * 3600.0) + (mm * 60.0) + ss)


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
