from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
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
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return str((info or {}).get("title") or "").strip()


def fetch_youtube_meta(video_id_or_url: str) -> YtDlpVideoMeta:
    """Best-effort: fetch title + duration (seconds) without downloading media.

    Notes:
    - For live streams / premieres yt-dlp may not provide duration. In that case
      duration_seconds is None.
    """
    url = _watch_url(video_id_or_url)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}
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
