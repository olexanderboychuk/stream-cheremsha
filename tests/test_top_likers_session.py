from __future__ import annotations

from stream_cheremsha.overlays.top_likers_session import TikTokSessionTopLikers


def test_top_likers_orders_by_likes_then_name() -> None:
    s = TikTokSessionTopLikers()
    s.add_likes(user_key="a", display_name="Bob", n=5, avatar_url="")
    s.add_likes(user_key="b", display_name="Ann", n=10, avatar_url="")
    s.add_likes(user_key="c", display_name="Zed", n=10, avatar_url="")
    rows = s.leaders(limit=8)
    assert [r["user"] for r in rows] == ["Ann", "Zed", "Bob"]
    assert rows[0]["likes"] == 10
    assert "key" in rows[0]


def test_top_likers_reset_clears() -> None:
    s = TikTokSessionTopLikers()
    s.add_likes(user_key="x", display_name="X", n=3, avatar_url="")
    s.reset()
    assert s.leaders(limit=5) == []


def test_top_likers_sort_likes_asc() -> None:
    s = TikTokSessionTopLikers()
    s.add_likes(user_key="a", display_name="Zed", n=10, avatar_url="")
    s.add_likes(user_key="b", display_name="Ann", n=5, avatar_url="")
    rows = s.leaders(limit=8, sort="likes_asc")
    assert [r["user"] for r in rows] == ["Ann", "Zed"]


def test_top_likers_sort_name_asc() -> None:
    s = TikTokSessionTopLikers()
    s.add_likes(user_key="a", display_name="Zed", n=10, avatar_url="")
    s.add_likes(user_key="b", display_name="Ann", n=10, avatar_url="")
    rows = s.leaders(limit=8, sort="name_asc")
    assert [r["user"] for r in rows] == ["Ann", "Zed"]


def test_leaders_limit_capped_at_ten() -> None:
    s = TikTokSessionTopLikers()
    for i in range(15):
        s.add_likes(user_key=str(i), display_name=f"U{i}", n=1, avatar_url="")
    assert len(s.leaders(limit=20, sort="likes_desc")) == 10


def test_top_likers_empty_key_falls_back_to_name() -> None:
    s = TikTokSessionTopLikers()
    s.add_likes(user_key="", display_name="Same", n=2, avatar_url="")
    s.add_likes(user_key="", display_name="Same", n=3, avatar_url="")
    rows = s.leaders(limit=5)
    assert len(rows) == 1
    assert rows[0]["likes"] == 5
