from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class _TopGifterEntry:
    coins: int
    display_name: str
    avatar_url: str


class TikTokSessionTopGifters:
    """Per-live-session TikTok gift diamond totals per user (stable id, else display name)."""

    def __init__(self) -> None:
        self._by_key: dict[str, _TopGifterEntry] = {}

    def reset(self) -> None:
        self._by_key.clear()

    def add_coins(
        self,
        *,
        user_key: str,
        display_name: str,
        n: int,
        avatar_url: str,
    ) -> None:
        if n <= 0:
            return
        key = (user_key or "").strip()
        if not key:
            key = (display_name or "").strip().casefold() or "?"
        name = (display_name or "").strip() or "?"
        av = (avatar_url or "").strip()
        cur = self._by_key.get(key)
        if cur is None:
            self._by_key[key] = _TopGifterEntry(coins=n, display_name=name, avatar_url=av)
            return
        next_av = av if av else cur.avatar_url
        self._by_key[key] = _TopGifterEntry(
            coins=cur.coins + n,
            display_name=name or cur.display_name,
            avatar_url=next_av,
        )

    def leaders(self, *, limit: int, sort: str = "likes_desc") -> list[dict[str, str | int]]:
        lim = max(1, min(10, int(limit)))
        mode = (sort or "likes_desc").strip().lower()
        items = list(self._by_key.items())
        if mode == "likes_asc":
            ranked = sorted(
                items,
                key=lambda kv: (kv[1].coins, kv[1].display_name.casefold()),
            )
        elif mode == "name_asc":
            ranked = sorted(
                items,
                key=lambda kv: (kv[1].display_name.casefold(), -kv[1].coins),
            )
        else:
            ranked = sorted(
                items,
                key=lambda kv: (-kv[1].coins, kv[1].display_name.casefold()),
            )
        out: list[dict[str, str | int]] = []
        for i, (_k, ent) in enumerate(ranked[:lim], start=1):
            out.append(
                {
                    "key": str(_k),
                    "rank": i,
                    "user": ent.display_name,
                    "coins": int(ent.coins),
                    "avatar_url": ent.avatar_url,
                }
            )
        return out
