from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SOURCE_LIKERS = "likers"
SOURCE_GIFTERS = "gifters"
SOURCE_SHARERS = "sharers"
SOURCE_COMMENTERS = "commenters"
SOURCE_CONTRIBUTORS = "contributors"

ALL_SOURCES = (
    SOURCE_LIKERS,
    SOURCE_GIFTERS,
    SOURCE_SHARERS,
    SOURCE_COMMENTERS,
    SOURCE_CONTRIBUTORS,
)

_SOURCE_UNITS = {
    SOURCE_LIKERS: "likes",
    SOURCE_GIFTERS: "coins",
    SOURCE_SHARERS: "shares",
    SOURCE_COMMENTERS: "comments",
    SOURCE_CONTRIBUTORS: "score",
}

_SOURCE_LABELS = {
    SOURCE_LIKERS: "TOP LIKERS",
    SOURCE_GIFTERS: "TOP GIFTERS",
    SOURCE_SHARERS: "TOP SHARERS",
    SOURCE_COMMENTERS: "TOP COMMENTERS",
    SOURCE_CONTRIBUTORS: "TOP CONTRIBUTORS",
}


@dataclass(slots=True)
class _UserMetrics:
    likes: int = 0
    gift_coins: int = 0
    shares: int = 0
    comments: int = 0
    display_name: str = "?"
    avatar_url: str = ""


@dataclass(slots=True)
class ContributorWeights:
    like: int = 1
    gift_coin: int = 10
    share: int = 50
    comment: int = 5


@dataclass(slots=True)
class LiveLeaderboardRankingEngine:
    """Aggregates per-user TikTok metrics for one live stream session.

    Presentation-agnostic: never knows about scenes or rotation.
    """

    weights: ContributorWeights = field(default_factory=ContributorWeights)
    _by_key: dict[str, _UserMetrics] = field(default_factory=dict)
    _pending_likes: dict[str, tuple[int, str, str]] = field(default_factory=dict)

    def reset(self) -> None:
        self._by_key.clear()
        self._pending_likes.clear()

    def _resolve_key(self, user_key: str, display_name: str) -> str:
        key = (user_key or "").strip()
        if key:
            return key
        return (display_name or "").strip().casefold() or "?"

    def _entry(self, key: str, display_name: str, avatar_url: str) -> _UserMetrics:
        cur = self._by_key.get(key)
        name = (display_name or "").strip() or "?"
        av = (avatar_url or "").strip()
        if cur is None:
            ent = _UserMetrics(display_name=name, avatar_url=av)
            self._by_key[key] = ent
            return ent
        if name and name != "?":
            cur.display_name = name
        if av:
            cur.avatar_url = av
        return cur

    def add_likes(
        self,
        *,
        user_key: str,
        display_name: str,
        n: int,
        avatar_url: str = "",
        immediate: bool = False,
    ) -> None:
        try:
            count = int(n)
        except (TypeError, ValueError):
            return
        if count <= 0:
            return
        key = self._resolve_key(user_key, display_name)
        name = (display_name or "").strip() or "?"
        av = (avatar_url or "").strip()
        if immediate:
            ent = self._entry(key, name, av)
            ent.likes += count
            return
        prev = self._pending_likes.get(key)
        if prev is None:
            self._pending_likes[key] = (count, name, av)
            return
        prev_n, prev_name, prev_av = prev
        self._pending_likes[key] = (
            prev_n + count,
            name if name != "?" else prev_name,
            av or prev_av,
        )

    def flush_likes(self) -> int:
        """Apply batched likes. Returns total likes flushed."""
        if not self._pending_likes:
            return 0
        total = 0
        pending = self._pending_likes
        self._pending_likes = {}
        for key, (n, name, av) in pending.items():
            ent = self._entry(key, name, av)
            ent.likes += n
            total += n
        return total

    def add_gift_coins(
        self,
        *,
        user_key: str,
        display_name: str,
        coins: int,
        avatar_url: str = "",
    ) -> None:
        try:
            n = int(coins)
        except (TypeError, ValueError):
            return
        if n <= 0:
            return
        key = self._resolve_key(user_key, display_name)
        ent = self._entry(key, display_name, avatar_url)
        ent.gift_coins += n

    def add_shares(
        self,
        *,
        user_key: str,
        display_name: str,
        n: int,
        avatar_url: str = "",
    ) -> None:
        try:
            count = int(n)
        except (TypeError, ValueError):
            return
        if count <= 0:
            return
        key = self._resolve_key(user_key, display_name)
        ent = self._entry(key, display_name, avatar_url)
        ent.shares += count

    def add_comment(
        self,
        *,
        user_key: str,
        display_name: str,
        avatar_url: str = "",
    ) -> None:
        key = self._resolve_key(user_key, display_name)
        ent = self._entry(key, display_name, avatar_url)
        ent.comments += 1

    def contribution_score(self, ent: _UserMetrics) -> int:
        w = self.weights
        return (
            ent.likes * max(0, int(w.like))
            + ent.gift_coins * max(0, int(w.gift_coin))
            + ent.shares * max(0, int(w.share))
            + ent.comments * max(0, int(w.comment))
        )

    def _metric_value(self, source: str, ent: _UserMetrics) -> int:
        if source == SOURCE_LIKERS:
            return int(ent.likes)
        if source == SOURCE_GIFTERS:
            return int(ent.gift_coins)
        if source == SOURCE_SHARERS:
            return int(ent.shares)
        if source == SOURCE_COMMENTERS:
            return int(ent.comments)
        if source == SOURCE_CONTRIBUTORS:
            return int(self.contribution_score(ent))
        return 0

    def leaders(self, *, source: str, limit: int) -> list[dict[str, Any]]:
        src = (source or "").strip().lower()
        if src not in ALL_SOURCES:
            return []
        lim = max(1, min(10, int(limit)))
        items = list(self._by_key.items())
        ranked = sorted(
            items,
            key=lambda kv: (-self._metric_value(src, kv[1]), kv[1].display_name.casefold()),
        )
        out: list[dict[str, Any]] = []
        for key, ent in ranked:
            value = self._metric_value(src, ent)
            if value <= 0:
                continue
            out.append(
                {
                    "key": str(key),
                    "rank": len(out) + 1,
                    "user": ent.display_name,
                    "value": int(value),
                    "avatar_url": ent.avatar_url,
                    "unit": _SOURCE_UNITS[src],
                }
            )
            if len(out) >= lim:
                break
        return out

    def all_rankings(self, *, limit: int) -> dict[str, list[dict[str, Any]]]:
        return {src: self.leaders(source=src, limit=limit) for src in ALL_SOURCES}

    @staticmethod
    def source_label(source: str) -> str:
        return _SOURCE_LABELS.get((source or "").strip().lower(), "LEADERBOARD")
