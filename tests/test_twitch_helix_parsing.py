from stream_cheremsha.chat.twitch_helix import _parse_stream_viewer_count, _parse_users


def test_parse_users_minimal() -> None:
    users = _parse_users({"data": [{"id": "1", "login": "Streamer", "display_name": "Streamer"}]})
    assert len(users) == 1
    assert users[0].id == "1"
    assert users[0].login == "streamer"


def test_parse_stream_viewers_offline_is_zero() -> None:
    assert _parse_stream_viewer_count({"data": []}) == 0


def test_parse_stream_viewers_reads_viewer_count() -> None:
    assert _parse_stream_viewer_count({"data": [{"viewer_count": 123}]}) == 123

