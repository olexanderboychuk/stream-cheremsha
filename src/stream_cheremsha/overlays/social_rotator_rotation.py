from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from stream_cheremsha.overlays.social_platforms import build_platform_url, get_platform


@dataclass(frozen=True, slots=True)
class SocialRotationEntry:
    entry_id: str
    platform: str
    username: str
    url: str


def _clamp_interval_ms(value: int) -> int:
    return max(1000, min(120_000, int(value)))


def enabled_rotation_entries(platforms: list[dict[str, object]]) -> list[SocialRotationEntry]:
    rows: list[tuple[int, SocialRotationEntry]] = []
    for raw in platforms:
        if not isinstance(raw, dict):
            continue
        enabled = bool(raw.get("enabled", True))
        if not enabled:
            continue
        platform = str(raw.get("platform") or "").strip().lower()
        if get_platform(platform) is None:
            continue
        username = str(raw.get("username") or "").strip()
        if not username:
            continue
        entry_id = str(raw.get("id") or "").strip() or platform
        url_override = str(raw.get("url") or "").strip()
        url = build_platform_url(platform, username, url_override=url_override)
        try:
            order = int(raw.get("order", 0))
        except (TypeError, ValueError):
            order = 0
        rows.append(
            (
                order,
                SocialRotationEntry(
                    entry_id=entry_id,
                    platform=platform,
                    username=username,
                    url=url,
                ),
            )
        )
    rows.sort(key=lambda t: t[0])
    return [e for _, e in rows]


@dataclass(slots=True)
class SocialRotatorRotationEngine:
    entries: list[SocialRotationEntry]
    active_index: int = 0
    transition_token: int = 1
    started_at_ms: int = 0
    interval_ms: int = 8000

    def __post_init__(self) -> None:
        self.interval_ms = _clamp_interval_ms(self.interval_ms)
        if self.started_at_ms <= 0:
            self.started_at_ms = int(time.time() * 1000)
        if not self.entries:
            self.active_index = 0
            return
        self.active_index = max(0, int(self.active_index)) % len(self.entries)

    @classmethod
    def from_entries(
        cls,
        entries: list[SocialRotationEntry],
        *,
        interval_ms: int,
        now_ms: int | None = None,
    ) -> SocialRotatorRotationEngine:
        started = int(now_ms if now_ms is not None else time.time() * 1000)
        return cls(
            entries=list(entries),
            active_index=0,
            transition_token=1,
            started_at_ms=started,
            interval_ms=_clamp_interval_ms(interval_ms),
        )

    @property
    def current_entry(self) -> SocialRotationEntry | None:
        if not self.entries:
            return None
        return self.entries[self.active_index % len(self.entries)]

    def replace_entries(
        self,
        entries: list[SocialRotationEntry],
        *,
        interval_ms: int,
        now_ms: int | None = None,
        preserve_position: bool = True,
    ) -> None:
        old = self.current_entry
        self.entries = list(entries)
        self.interval_ms = _clamp_interval_ms(interval_ms)
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        if not self.entries:
            self.active_index = 0
            self.transition_token += 1
            self.started_at_ms = now
            return
        if preserve_position and old is not None:
            for i, entry in enumerate(self.entries):
                if entry.entry_id == old.entry_id:
                    self.active_index = i
                    return
            for i, entry in enumerate(self.entries):
                if entry.platform == old.platform and entry.username == old.username:
                    self.active_index = i
                    return
        self.active_index = 0
        self.transition_token += 1
        self.started_at_ms = now

    def advance(self, *, now_ms: int | None = None) -> SocialRotationEntry | None:
        if not self.entries:
            return None
        n = len(self.entries)
        self.active_index = (self.active_index + 1) % n
        self.transition_token += 1
        self.started_at_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        return self.current_entry

    def tick(self, *, now_ms: int | None = None) -> bool:
        if len(self.entries) < 2:
            return False
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        elapsed = now - int(self.started_at_ms)
        if elapsed < int(self.interval_ms):
            return False
        self.advance(now_ms=now)
        return True

    def remaining_ms(self, *, now_ms: int | None = None) -> int:
        if len(self.entries) < 2:
            return 0
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        elapsed = now - int(self.started_at_ms)
        return max(0, int(self.interval_ms) - elapsed)

    def presentation_dict(self, *, server_now_ms: int | None = None) -> dict[str, Any]:
        now = int(server_now_ms if server_now_ms is not None else time.time() * 1000)
        entry = self.current_entry
        if entry is None:
            return {
                "active_index": -1,
                "platform_id": "",
                "entry_id": "",
                "started_at_ms": int(self.started_at_ms),
                "interval_ms": int(self.interval_ms),
                "transition_token": int(self.transition_token),
                "remaining_ms": 0,
                "server_now_ms": now,
            }
        return {
            "active_index": int(self.active_index),
            "platform_id": entry.platform,
            "entry_id": entry.entry_id,
            "started_at_ms": int(self.started_at_ms),
            "interval_ms": int(self.interval_ms),
            "transition_token": int(self.transition_token),
            "remaining_ms": int(self.remaining_ms(now_ms=now)),
            "server_now_ms": now,
        }
