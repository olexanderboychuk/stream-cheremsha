import pytest

from stream_cheremsha.chat.twitch_helix import TwitchHelixClient, TwitchUser, _parse_users


def test_parse_users_includes_profile_image_url() -> None:
    users = _parse_users(
        {
            "data": [
                {
                    "id": "1",
                    "login": "alice",
                    "display_name": "Alice",
                    "profile_image_url": "https://static-cdn.jtvnw.net/alice.png",
                }
            ]
        }
    )
    assert len(users) == 1
    assert users[0].profile_image_url == "https://static-cdn.jtvnw.net/alice.png"


@pytest.mark.asyncio
async def test_resolve_profile_image_url_uses_cache_without_http() -> None:
    client = TwitchHelixClient(client_id="cid", access_token="tok")
    client._cache_user(
        TwitchUser(
            id="42",
            login="alice",
            display_name="Alice",
            profile_image_url="https://static-cdn.jtvnw.net/alice.png",
        )
    )
    try:
        by_login = await client.resolve_profile_image_url(login="alice")
        by_id = await client.resolve_profile_image_url(user_id="42")
    finally:
        await client.aclose()
    assert by_login == "https://static-cdn.jtvnw.net/alice.png"
    assert by_id == by_login
