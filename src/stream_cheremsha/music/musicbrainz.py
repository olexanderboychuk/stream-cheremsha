"""MusicBrainz API: artist area (country) for release screening."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from stream_cheremsha.config import constants

logger = logging.getLogger(__name__)

_MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
# MusicBrainz requires a descriptive User-Agent with contact (see https://musicbrainz.org/doc/MusicBrainz_API).
_ENV_MB_CONTACT = constants.ENV_MUSICBRAINZ_CONTACT
_DEFAULT_USER_AGENT = (
    "stream-cheremsha/0.4.0 ( https://pypi.org/project/stream-cheremsha/ ; "
    "set STREAM_CHEREMSHA_MUSICBRAINZ_CONTACT to your email or project URL )"
)

# Be polite: one request per second per application (MusicBrainz policy).
_MIN_INTERVAL_SEC = 1.05

_mb_lock = asyncio.Lock()
_last_request_mono: float = 0.0


def _user_agent() -> str:
    extra = (os.environ.get(_ENV_MB_CONTACT) or "").strip()
    if extra:
        return f"stream-cheremsha/0.4.0 ( {extra} )"
    return _DEFAULT_USER_AGENT


def _strip_youtube_title_noise(title: str) -> str:
    t = (title or "").strip()
    if not t:
        return ""
    t = re.sub(r"\s*[\[(]\s*(official\s*)?(music\s*)?video.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[\[(]\s*lyrics.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[\[(]\s*audio.*$", "", t, flags=re.I)
    return t.strip()


def _lucene_escape(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if ch in '\\+-&|!(){}[]^"~*?:':
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _build_recording_query(clean_title: str) -> str | None:
    t = (clean_title or "").strip()
    if not t:
        return None
    if " - " in t:
        left, right = t.split(" - ", 1)
        artist = left.strip()
        rec = right.strip()
        if artist and rec:
            return f'artist:"{_lucene_escape(artist)}" AND recording:"{_lucene_escape(rec)}"'
    return f'recording:"{_lucene_escape(t)}"'


def _area_dict_is_russia(area: Any) -> bool:
    if not isinstance(area, dict):
        return False
    codes = area.get("iso-3166-1-codes")
    if isinstance(codes, list) and any(str(c).strip().upper() == "RU" for c in codes):
        return True
    name = str(area.get("name") or "").strip().lower()
    sort_name = str(area.get("sort-name") or "").strip().lower()
    for n in (name, sort_name):
        if n in ("russia", "russian federation"):
            return True
    return False


def _artist_json_area_is_russia(data: dict[str, Any]) -> bool:
    if _area_dict_is_russia(data.get("area")):
        return True
    if _area_dict_is_russia(data.get("begin-area")):
        return True
    country = str(data.get("country") or "").strip().upper()
    return country == "RU"


def _recording_artist_mbids(recording: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    ac = recording.get("artist-credit")
    if not isinstance(ac, list):
        return out
    for entry in ac:
        if not isinstance(entry, dict):
            continue
        art = entry.get("artist")
        if not isinstance(art, dict):
            continue
        aid = str(art.get("id") or "").strip()
        if aid and aid not in seen:
            seen.add(aid)
            out.append(aid)
    return out


async def _rate_limited_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    global _last_request_mono
    async with _mb_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL_SEC - (now - _last_request_mono)
        if wait > 0:
            await asyncio.sleep(wait)
        resp = await client.get(
            url,
            headers={"User-Agent": _user_agent(), "Accept": "application/json"},
        )
        _last_request_mono = time.monotonic()
        return resp


async def youtube_title_indicates_russian_artist_area(
    youtube_title: str,
    *,
    timeout_s: float = 25.0,
    max_recordings: int = 3,
    max_artists: int = 6,
) -> bool:
    """
    Return ``True`` if MusicBrainz associates a credited artist with Russia (area / ISO RU).

    On search miss, HTTP errors, or parse issues returns ``False`` (do not block the request).
    """
    clean = _strip_youtube_title_noise(youtube_title)
    q = _build_recording_query(clean)
    if not q:
        return False

    search_params = urlencode({"fmt": "json", "limit": str(max_recordings), "query": q})
    search_url = f"{_MUSICBRAINZ_BASE}/recording?{search_params}"

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await _rate_limited_get(client, search_url)
            if r.status_code != 200:
                logger.debug(
                    "MusicBrainz recording search HTTP %s for %r",
                    r.status_code,
                    clean[:80],
                )
                return False
            data = r.json()
            if not isinstance(data, dict):
                return False
            recordings = data.get("recordings")
            if not isinstance(recordings, list) or not recordings:
                return False

            checked_artists = 0
            for rec in recordings:
                if not isinstance(rec, dict):
                    continue
                for mbid in _recording_artist_mbids(rec):
                    if checked_artists >= max_artists:
                        return False
                    checked_artists += 1
                    artist_url = f"{_MUSICBRAINZ_BASE}/artist/{mbid}?fmt=json"
                    try:
                        ar = await _rate_limited_get(client, artist_url)
                        if ar.status_code != 200:
                            continue
                        artist_data = ar.json()
                    except (httpx.HTTPError, ValueError, OSError) as e:
                        logger.debug("MusicBrainz artist %s fetch failed: %s", mbid, e)
                        continue
                    if isinstance(artist_data, dict) and _artist_json_area_is_russia(artist_data):
                        logger.info(
                            "MusicBrainz: Russian-area artist match mbid=%s title=%r",
                            mbid,
                            clean[:80],
                        )
                        return True
            return False
    except (httpx.HTTPError, ValueError, OSError) as e:
        logger.debug("MusicBrainz recording search failed: %s", e)
        return False
