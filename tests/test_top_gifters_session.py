from stream_cheremsha.overlays.top_gifters_session import TikTokSessionTopGifters


def test_top_gifters_orders_by_coins_then_name() -> None:
    s = TikTokSessionTopGifters()
    s.add_coins(user_key="a", display_name="Bob", n=10, avatar_url="")
    s.add_coins(user_key="b", display_name="Ann", n=20, avatar_url="")
    s.add_coins(user_key="c", display_name="Zed", n=20, avatar_url="")
    leaders = s.leaders(limit=10, sort="likes_desc")
    assert [x["user"] for x in leaders] == ["Ann", "Zed", "Bob"]


def test_top_gifters_reset_clears() -> None:
    s = TikTokSessionTopGifters()
    s.add_coins(user_key="a", display_name="Bob", n=1, avatar_url="")
    s.reset()
    assert s.leaders(limit=10, sort="likes_desc") == []


def test_top_gifters_sort_likes_asc() -> None:
    s = TikTokSessionTopGifters()
    s.add_coins(user_key="a", display_name="Bob", n=10, avatar_url="")
    s.add_coins(user_key="b", display_name="Ann", n=5, avatar_url="")
    leaders = s.leaders(limit=10, sort="likes_asc")
    assert [x["user"] for x in leaders] == ["Ann", "Bob"]


def test_top_gifters_sort_name_asc() -> None:
    s = TikTokSessionTopGifters()
    s.add_coins(user_key="a", display_name="Bob", n=100, avatar_url="")
    s.add_coins(user_key="b", display_name="Ann", n=100, avatar_url="")
    leaders = s.leaders(limit=10, sort="name_asc")
    assert [x["user"] for x in leaders] == ["Ann", "Bob"]


def test_top_gifters_empty_key_falls_back_to_name() -> None:
    s = TikTokSessionTopGifters()
    s.add_coins(user_key="", display_name="Same", n=3, avatar_url="")
    s.add_coins(user_key="", display_name="Same", n=2, avatar_url="")
    leaders = s.leaders(limit=10, sort="likes_desc")
    assert len(leaders) == 1
    assert leaders[0]["coins"] == 5
