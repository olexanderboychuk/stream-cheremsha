from PySide6.QtWidgets import QApplication

from stream_cheremsha.ui.youtube_analytics_api import YouTubeAnalyticsApi


def _app() -> QApplication:
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


def test_youtube_analytics_counters_and_reset() -> None:
    _app()
    a = YouTubeAnalyticsApi()
    a._apply_event("chat", "alice", "hello", 1)
    a._apply_event("chat", "bob", "yo", 1)
    a._apply_event("superchat", "carol", "$5 · great", 1)
    a._apply_event("member", "dave", "", 1)

    assert a.messagesSession == 2
    assert a.uniqueChattersSession == 4
    assert a.superChatsSession == 1
    assert a.membershipsSession == 1
    assert a.feedModel.rowCount() == 4

    a.resetSession()
    assert a.messagesSession == 0
    assert a.uniqueChattersSession == 0
    assert a.superChatsSession == 0
    assert a.membershipsSession == 0
    assert a.feedModel.rowCount() == 0
