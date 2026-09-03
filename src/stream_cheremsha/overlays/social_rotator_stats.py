from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SocialRotatorStatsSession:
    latest_follower: str | None = None
    latest_donation_name: str | None = None
    latest_donation_value: float = 0.0
    latest_donation_source: str | None = None
    top_donator_name: str | None = None
    top_donator_value: float = 0.0
    stream_started_at_ms: int | None = None
    viewers_by_platform: dict[str, int] = field(default_factory=dict)

    def reset(self) -> None:
        self.latest_follower = None
        self.latest_donation_name = None
        self.latest_donation_value = 0.0
        self.latest_donation_source = None
        self.top_donator_name = None
        self.top_donator_value = 0.0
        self.stream_started_at_ms = None
        self.viewers_by_platform.clear()

    def set_stream_started_at_ms(self, ms: int | None) -> None:
        if ms is None:
            self.stream_started_at_ms = None
            return
        self.stream_started_at_ms = int(ms)

    def on_follow(self, name: str) -> None:
        n = str(name or "").strip()
        if not n:
            return
        self.latest_follower = n

    def on_donation(
        self,
        *,
        name: str,
        amount: float,
        source: str,
        coin_rate: float = 1.0,
    ) -> None:
        n = str(name or "").strip() or "—"
        src = str(source or "").strip().lower()
        try:
            amt = float(amount)
        except (TypeError, ValueError):
            return
        if amt < 0:
            amt = 0.0
        if src == "tiktok_gift":
            try:
                rate = float(coin_rate)
            except (TypeError, ValueError):
                rate = 1.0
            if rate < 0:
                rate = 0.0
            value = amt * rate
        else:
            value = amt
        self.latest_donation_name = n
        self.latest_donation_value = value
        self.latest_donation_source = src or "unknown"
        if self.top_donator_name is None or value > self.top_donator_value:
            self.top_donator_name = n
            self.top_donator_value = value

    def set_viewers(self, platform: str, count: int) -> None:
        key = str(platform or "").strip().lower()
        if not key:
            return
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 0
        self.viewers_by_platform[key] = max(0, n)

    def clear_viewers(self, platform: str) -> None:
        key = str(platform or "").strip().lower()
        if key in self.viewers_by_platform:
            del self.viewers_by_platform[key]

    def to_public_dict(self) -> dict[str, Any]:
        viewers = {k: int(v) for k, v in self.viewers_by_platform.items()}
        total = sum(viewers.values())
        latest_follower = {"name": self.latest_follower} if self.latest_follower else None
        latest_donation = None
        if self.latest_donation_name is not None:
            latest_donation = {
                "name": self.latest_donation_name,
                "value": int(round(self.latest_donation_value)),
                "source": self.latest_donation_source or "",
            }
        top_donator = None
        if self.top_donator_name is not None:
            top_donator = {
                "name": self.top_donator_name,
                "value": int(round(self.top_donator_value)),
            }
        return {
            "latest_follower": latest_follower,
            "latest_donation": latest_donation,
            "top_donator": top_donator,
            "stream_started_at_ms": self.stream_started_at_ms,
            "viewers_by_platform": viewers,
            "viewers_total": int(total),
        }
