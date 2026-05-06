from PySide6.QtWidgets import QApplication

from stream_cheremsha.ui.twitch_analytics_api import TwitchAnalyticsApi


def _app() -> QApplication:
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


def test_twitch_analytics_counters_and_reset() -> None:
    _app()
    a = TwitchAnalyticsApi()
    a._apply_viewers(10)
    a._apply_viewers(3)
    assert a.viewersCurrent == 3
    assert a.viewersPeak == 10

    a._apply_follow("alice")
    a._apply_sub("bob", "sub", 0)
    a._apply_cheer("carol", 250)
    a._apply_raid("dave", 42)

    assert a.followsSession == 1
    assert a.subsSession == 1
    assert a.bitsSession == 250
    assert a.raidsSession == 1
    assert a.feedModel.rowCount() == 4

    a.resetSession()
    assert a.viewersCurrent == 0
    assert a.viewersPeak == 0
    assert a.followsSession == 0
    assert a.subsSession == 0
    assert a.bitsSession == 0
    assert a.raidsSession == 0
    assert a.feedModel.rowCount() == 0

