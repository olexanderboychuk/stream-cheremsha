import pytest

from stream_cheremsha.audio import qt_sink


@pytest.fixture(autouse=True)
def reset_ffmpeg_log_state() -> None:
    qt_sink._ffmpeg_log_state["no_path_logged"] = False
    yield


def test_try_louder_mp3_returns_same_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qt_sink.shutil, "which", lambda _: None)
    raw = b"\xff\xd3fake-mp3"
    assert qt_sink._try_louder_mp3(raw, 14) == raw
