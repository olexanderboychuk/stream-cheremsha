from __future__ import annotations

from stream_cheremsha.overlays.social_platforms import (
    ALL_PLATFORM_IDS,
    build_platform_url,
    get_platform,
    normalize_username,
)


def test_builtin_platforms_present() -> None:
    for pid in (
        "twitch",
        "youtube",
        "kick",
        "telegram",
        "tiktok",
        "instagram",
        "discord",
        "x",
        "facebook",
    ):
        assert pid in ALL_PLATFORM_IDS
        p = get_platform(pid)
        assert p is not None
        assert p.name
        assert p.accent.startswith("#")
        assert "{username}" in p.url_template or p.url_template == ""


def test_normalize_and_url_twitch() -> None:
    assert normalize_username("twitch", "@Kodi_The_Cat") == "kodi_the_cat"
    assert build_platform_url("twitch", "Kodi_The_Cat") == "https://twitch.tv/kodi_the_cat"


def test_url_override_wins() -> None:
    assert (
        build_platform_url("twitch", "x", url_override="https://example.com/me")
        == "https://example.com/me"
    )


def test_unknown_platform() -> None:
    assert get_platform("nope") is None
    assert build_platform_url("nope", "x") == ""
