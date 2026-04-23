from __future__ import annotations

import re

_YT_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/live/)([0-9A-Za-z_-]{11})",
)


def extract_youtube_video_id(text: str) -> str | None:
    text = text.strip()
    if len(text) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", text):
        return text
    m = _YT_RE.search(text)
    if m:
        return m.group(1)
    return None
