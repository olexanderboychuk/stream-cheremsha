from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Track:
    id: str
    video_id: str
    requested_by: str
    requested_at_iso: str
    title: str = ""

