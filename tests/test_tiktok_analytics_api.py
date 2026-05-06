"""TikTok analytics QObject (counters + feed model)."""

from PySide6.QtWidgets import QApplication

from stream_cheremsha.ui.tiktok_analytics_api import TikTokAnalyticsApi


def _app() -> QApplication:
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


def test_tiktok_analytics_reset_clears_feed_and_totals() -> None:
    _app()
    a = TikTokAnalyticsApi()
    a._apply_viewers_current(12)
    a._apply_viewers_total(345)
    a._apply_follow("alice")
    a._apply_join("bob")
    a._apply_gift("gifter", "1", "Rose", 2, 20, "")
    assert a.feedModel.rowCount() == 3
    assert a.giftUnitsTotal == 2
    assert a.diamondsTotal == 20
    assert a.onlineViewersCurrent == 12
    assert a.onlineViewersTotal == 345
    assert bool(a.feedModel.data(a.feedModel.index(0, 0), a.feedModel._TIME))
    a.resetSession()
    assert a.feedModel.rowCount() == 0
    assert a.giftUnitsTotal == 0
    assert a.diamondsTotal == 0
    assert a.onlineViewersCurrent == 0
    assert a.onlineViewersTotal == 0


def test_tiktok_analytics_viewers_updates() -> None:
    _app()
    a = TikTokAnalyticsApi()
    a._apply_viewers_current(42)
    assert a.onlineViewersCurrent == 42
    a._apply_viewers_current(42)
    assert a.onlineViewersCurrent == 42
    a._apply_viewers_current(10)
    assert a.onlineViewersCurrent == 10

    a._apply_viewers_total(500)
    assert a.onlineViewersTotal == 500
    a._apply_viewers_total(500)
    assert a.onlineViewersTotal == 500
    a._apply_viewers_total(3)
    assert a.onlineViewersTotal == 3
