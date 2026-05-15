from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yt_dlp
from yt_dlp.cookies import CookieLoadError
from yt_dlp.utils import DownloadError

from stream_cheremsha.chat.video_id import extract_youtube_video_id
from stream_cheremsha.config import constants

logger = logging.getLogger(__name__)

# Same shape as yt-dlp CLI `--cookies-from-browser` (see yt_dlp/__init__.py).
_BROWSER_COOKIE_RE = re.compile(
    r"""(?x)
    (?P<name>[^+:]+)
    (?:\s*\+\s*(?P<keyring>[^:]+))?
    (?:\s*:\s*(?!:)(?P<profile>.+?))?
    (?:\s*::\s*(?P<container>.+))?
""",
)

_cookie_opts_logged = False


@dataclass(frozen=True, slots=True)
class _YtdlpCookieEnv:
    """Validated cookie sources from env (shared by Python YoutubeDL and mpv ytdl_hook)."""

    cookiefile: str | None
    cookies_from_browser: str | None


_cookie_env_cached: _YtdlpCookieEnv | None = None


def _cookie_env() -> _YtdlpCookieEnv:
    """Read cookie env once per process (mpv and yt-dlp Python API must stay in sync)."""
    global _cookie_env_cached
    if _cookie_env_cached is not None:
        return _cookie_env_cached

    file_str: str | None = None
    cf = (os.environ.get(constants.ENV_YTDLP_COOKIESFILE) or "").strip()
    if cf:
        p = Path(cf).expanduser()
        if p.is_file():
            file_str = str(p.resolve())
        else:
            logger.warning(
                "yt-dlp: %s is set but file is missing or not a file: %s",
                constants.ENV_YTDLP_COOKIESFILE,
                cf,
            )

    br_ok: str | None = None
    br_raw = (os.environ.get(constants.ENV_YTDLP_COOKIES_FROM_BROWSER) or "").strip()
    if br_raw:
        if _BROWSER_COOKIE_RE.fullmatch(br_raw):
            br_ok = br_raw
        else:
            logger.warning(
                "yt-dlp: invalid %s=%r (expected e.g. chrome, chrome:Default, firefox+KWALLET)",
                constants.ENV_YTDLP_COOKIES_FROM_BROWSER,
                br_raw,
            )

    _cookie_env_cached = _YtdlpCookieEnv(file_str, br_ok)
    return _cookie_env_cached


def mpv_ytdl_raw_option_args() -> list[str]:
    """mpv CLI flags so built-in ytdl_hook passes the same cookie auth to the external yt-dlp."""
    cfg = _cookie_env()
    out: list[str] = []
    if cfg.cookiefile:
        out.append(f"--ytdl-raw-option=cookies={cfg.cookiefile}")
    if cfg.cookies_from_browser:
        out.append(f"--ytdl-raw-option=cookies-from-browser={cfg.cookies_from_browser}")
    return out


def _log_age_gate_hint(exc: BaseException) -> None:
    t = str(exc).lower()
    if "sign in to confirm your age" in t or "confirm your age" in t:
        logger.warning(
            "yt-dlp: age-restricted or login-only YouTube video. Set %s to a Netscape cookies.txt "
            "file, or %s (e.g. chrome or chrome:Default). Applies to both the in-app resolver and "
            "the mpv backend (ytdl_hook). See "
            "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp",
            constants.ENV_YTDLP_COOKIESFILE,
            constants.ENV_YTDLP_COOKIES_FROM_BROWSER,
        )


def _ytdlp_cookie_opts() -> dict[str, object]:
    """Optional cookiefile / cookies-from-browser from environment (MusicBrainz-style policy)."""
    global _cookie_opts_logged
    cfg = _cookie_env()
    out: dict[str, object] = {}
    if cfg.cookiefile:
        out["cookiefile"] = cfg.cookiefile
    if cfg.cookies_from_browser:
        m = _BROWSER_COOKIE_RE.fullmatch(cfg.cookies_from_browser)
        if m is not None:
            browser = m.group("name").strip().lower()
            keyring = m.group("keyring")
            if keyring is not None:
                keyring = keyring.upper()
            profile = m.group("profile")
            container = m.group("container")
            out["cookiesfrombrowser"] = (browser, profile, keyring, container)
    if out and not _cookie_opts_logged:
        logger.info("yt-dlp: using cookie auth keys: %s", ", ".join(sorted(out.keys())))
        _cookie_opts_logged = True
    return out


def _merge_ytdlp_opts(base: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    merged.update(_ytdlp_cookie_opts())
    return merged


def _extract_info(url: str, ydl_opts: dict[str, object], *, download: bool) -> dict:
    opts = _merge_ytdlp_opts(ydl_opts)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=download) or {}
    except DownloadError as e:
        _log_age_gate_hint(e)
        raise RuntimeError(str(e)) from e
    except CookieLoadError as e:
        logger.error("yt-dlp: cookie load failed: %s", e)
        raise RuntimeError("yt-dlp: failed to load cookies") from e


@dataclass(slots=True)
class YtDlpResolveResult:
    title: str
    audio_bytes: bytes


@dataclass(slots=True)
class YtDlpVideoMeta:
    title: str
    duration_seconds: int | None


def _watch_url(video_id_or_url: str) -> str:
    s = (video_id_or_url or "").strip()
    if not s:
        raise ValueError("video id is empty")
    if "://" in s:
        return s
    return f"https://www.youtube.com/watch?v={s}"


def _best_audio_url_from_formats(info: dict) -> str | None:
    formats = info.get("formats")
    if not isinstance(formats, list):
        return None
    best: dict | None = None
    best_abr = -1
    for f in formats:
        if not isinstance(f, dict):
            continue
        u = str(f.get("url") or "").strip()
        if not u:
            continue
        vc = f.get("vcodec")
        if vc not in ("none", None):
            continue
        ac = f.get("acodec")
        if ac in (None, "none"):
            continue
        try:
            abr = int(f.get("abr") or 0)
        except (TypeError, ValueError):
            abr = 0
        if abr >= best_abr:
            best_abr = abr
            best = f
    if best is None:
        return None
    out = str(best.get("url") or "").strip()
    return out or None


def resolve_youtube_stream_url_for_mpv(video_id_or_url: str) -> str | None:
    """Return a direct HTTP(S) audio URL for mpv, or None (caller uses watch URL).

    Uses the same bundled yt_dlp as in-app playback. Does not set mpv HTTP headers;
    many signed googlevideo URLs play without extra headers.
    """
    if not extract_youtube_video_id(video_id_or_url):
        return None
    url = _watch_url(video_id_or_url)
    ydl_opts: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best",
    }
    try:
        info = _extract_info(url, ydl_opts, download=False)
    except RuntimeError as e:
        logger.warning("yt-dlp: could not resolve stream URL for mpv: %s", e)
        return None
    except Exception:
        logger.warning("yt-dlp: could not resolve stream URL for mpv", exc_info=True)
        return None

    stream_url = str(info.get("url") or "").strip()
    if not stream_url:
        stream_url = _best_audio_url_from_formats(info) or ""
    return stream_url or None


def resolve_youtube_audio_bytes(video_id_or_url: str) -> YtDlpResolveResult:
    """Download and return WAV/MP3 bytes using yt-dlp.

    Notes:
    - Requires `ffmpeg` in PATH.
    - Uses WAV output to avoid mp3 encoder availability issues.
    """
    url = _watch_url(video_id_or_url)
    with tempfile.TemporaryDirectory(prefix="cheremsha_ytdlp_") as td:
        base = str(Path(td) / "%(id)s.%(ext)s")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": base,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
        }
        opts = _merge_ytdlp_opts(ydl_opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except DownloadError as e:
                _log_age_gate_hint(e)
                raise RuntimeError(str(e)) from e
            except CookieLoadError as e:
                logger.error("yt-dlp: cookie load failed: %s", e)
                raise RuntimeError("yt-dlp: failed to load cookies") from e
            title = str((info or {}).get("title") or "").strip()

            # yt-dlp surfaces exact paths here in newer versions.
            fp = ""
            rds = (info or {}).get("requested_downloads") or []
            if isinstance(rds, list) and rds:
                rd0 = rds[0] if isinstance(rds[0], dict) else {}
                fp = str(rd0.get("filepath") or "").strip()
            if not fp:
                # Fallback: compute from template and expected codec.
                try:
                    fp = str(ydl.prepare_filename(info))
                except Exception:
                    fp = ""
                if fp:
                    fp = str(Path(fp).with_suffix(".wav"))

            if not fp:
                raise RuntimeError("yt-dlp: could not determine output file path")

            data = Path(fp).read_bytes()
            if not data:
                raise RuntimeError("yt-dlp: empty audio output")
            return YtDlpResolveResult(title=title, audio_bytes=data)


def fetch_youtube_title(video_id_or_url: str) -> str:
    """Best-effort: return title without downloading media."""
    url = _watch_url(video_id_or_url)
    ydl_opts: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    info = _extract_info(url, ydl_opts, download=False)
    return str((info or {}).get("title") or "").strip()


def fetch_youtube_meta(video_id_or_url: str) -> YtDlpVideoMeta:
    """Best-effort: fetch title + duration (seconds) without downloading media.

    Notes:
    - For live streams / premieres yt-dlp may not provide duration. In that case
      duration_seconds is None.
    """
    url = _watch_url(video_id_or_url)
    ydl_opts: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    info = _extract_info(url, ydl_opts, download=False)
    title = str(info.get("title") or "").strip()
    dur_raw = info.get("duration")
    duration_seconds: int | None
    try:
        duration_seconds = int(dur_raw) if dur_raw is not None else None
    except (TypeError, ValueError):
        duration_seconds = None
    if duration_seconds is not None and duration_seconds <= 0:
        duration_seconds = None
    return YtDlpVideoMeta(title=title, duration_seconds=duration_seconds)
