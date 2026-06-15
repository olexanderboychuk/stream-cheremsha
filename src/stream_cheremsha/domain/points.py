"""Points/balance economy for ordering songs.

Engagement earns (likes, shares, follow, watch) are intentionally uncapped over time,
but guarded against obvious abuse:

* **Follow** — at most once per viewer per stream, plus a cross-stream cooldown
  (default 24 h) so unfollow/follow cycles cannot be farmed.
* **Share** — cross-stream cooldown (default 5 min) between share awards.
* **Likes / watch / gifts** — likes require real volume; watch needs periodic
  activity each interval; gifts cost TikTok coins.
"""

from __future__ import annotations

from dataclasses import dataclass


def normalize_tiktok_username(raw: str) -> str:
    """Lowercase, trim and strip a leading ``@`` from a TikTok handle."""
    return (raw or "").strip().lstrip("@").strip().lower()


@dataclass(frozen=True, slots=True)
class PointsConfig:
    """Economy parameters."""

    song_cost: int = 100
    points_per_coin: int = 1
    likes_per_point: int = 50
    points_per_share: int = 10
    points_per_follow: int = 25
    watch_points_per_interval: int = 5
    watch_interval_minutes: int = 10

    # Anti-abuse cooldowns (seconds). ``0`` disables the cross-stream ledger check.
    follow_cooldown_sec: int = 86_400
    share_cooldown_sec: int = 300

    def sanitized(self) -> PointsConfig:
        """Return a copy with out-of-range values clamped to safe bounds."""
        return PointsConfig(
            song_cost=max(0, int(self.song_cost)),
            points_per_coin=max(0, int(self.points_per_coin)),
            likes_per_point=max(1, int(self.likes_per_point)),
            points_per_share=max(0, int(self.points_per_share)),
            points_per_follow=max(0, int(self.points_per_follow)),
            watch_points_per_interval=max(0, int(self.watch_points_per_interval)),
            watch_interval_minutes=max(1, int(self.watch_interval_minutes)),
            follow_cooldown_sec=max(0, int(self.follow_cooldown_sec)),
            share_cooldown_sec=max(0, int(self.share_cooldown_sec)),
        )

    def coins_to_points(self, diamonds_total: int) -> int:
        """Convert a gift's total diamonds to points."""
        return max(0, int(diamonds_total)) * max(0, int(self.points_per_coin))


def earn_rate_template_vars(config: PointsConfig) -> dict[str, str]:
    """Template placeholders for user-facing earn-rate copy (Telegram, etc.)."""
    cfg = config.sanitized()
    return {
        "per_coin": str(cfg.points_per_coin),
        "likes_per_point": str(cfg.likes_per_point),
        "per_share": str(cfg.points_per_share),
        "per_follow": str(cfg.points_per_follow),
        "watch_points": str(cfg.watch_points_per_interval),
        "watch_interval": str(cfg.watch_interval_minutes),
    }


@dataclass(slots=True)
class _ViewerLikeState:
    like_accum: int = 0
    like_points: int = 0


class StreamEarnTracker:
    """Computes engagement earn deltas for TikTok live events.

      Per-stream guards (e.g. follow once) live here. Cross-stream cooldowns are
    checked against the points ledger before calling these methods.
    """

    def __init__(self, config: PointsConfig) -> None:
        self._cfg = config.sanitized()
        self._like_state: dict[str, _ViewerLikeState] = {}
        self._follow_awarded: set[str] = set()

    @property
    def config(self) -> PointsConfig:
        return self._cfg

    def set_config(self, config: PointsConfig) -> None:
        self._cfg = config.sanitized()

    def reset(self) -> None:
        """Clear per-stream state (call on stream start)."""
        self._like_state.clear()
        self._follow_awarded.clear()

    def _like_state_for(self, key: str) -> _ViewerLikeState | None:
        k = (key or "").strip()
        if not k:
            return None
        st = self._like_state.get(k)
        if st is None:
            st = _ViewerLikeState()
            self._like_state[k] = st
        return st

    def on_like(self, key: str, n: int) -> int:
        st = self._like_state_for(key)
        if st is None:
            return 0
        try:
            n_i = max(0, int(n))
        except (TypeError, ValueError):
            n_i = 0
        st.like_accum += n_i
        target = st.like_accum // self._cfg.likes_per_point
        delta = target - st.like_points
        if delta <= 0:
            return 0
        st.like_points = target
        return delta

    def on_share(self, key: str, n: int = 1) -> int:
        if not (key or "").strip():
            return 0
        try:
            n_i = max(1, int(n))
        except (TypeError, ValueError):
            n_i = 1
        return n_i * self._cfg.points_per_share

    def on_follow(self, key: str) -> int:
        """Award follow points at most once per viewer per stream."""
        k = (key or "").strip()
        if not k:
            return 0
        if k in self._follow_awarded:
            return 0
        self._follow_awarded.add(k)
        return self._cfg.points_per_follow

    def on_watch_tick(self, key: str) -> int:
        if not (key or "").strip():
            return 0
        return self._cfg.watch_points_per_interval
