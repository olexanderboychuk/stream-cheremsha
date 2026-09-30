from __future__ import annotations

import json as _json
from pathlib import Path


class FakeSink:
    def __init__(self):
        self.calls: list[tuple[bytes, float]] = []

    async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        self.calls.append((bytes(data), float(volume)))
        return True


def _api(tmp_path):
    from PySide6.QtCore import QSettings

    from stream_cheremsha.soundpad.engine import SoundpadAudioEngine
    from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager
    from stream_cheremsha.soundpad.store import SoundpadStore
    from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi

    store = SoundpadStore(settings=QSettings("sp-lib", "x"), root_dir=tmp_path)
    eng = SoundpadAudioEngine(sink=FakeSink())
    hk = GlobalHotkeyManager(backend=FakeHotkeyBackend())
    return SoundpadQmlApi(store=store, engine=eng, hotkeys=hk), store


def test_library_strings_localization(tmp_path):
    api, _ = _api(tmp_path)
    s = api.libraryStrings
    assert s["title"] == "Бібліотека звуків"
    assert s["add"] == "Додати"

    events: list[int] = []
    api.stringsChanged.connect(lambda: events.append(1))
    api.set_locale("en")
    assert events, "stringsChanged must fire on locale change"
    assert api.libraryStrings["title"] == "Sound Library"


def test_tr_falls_back_to_key(tmp_path):
    api, _ = _api(tmp_path)
    assert api.tr("no.such.key") == "no.such.key"
    assert api.tr("") == ""
    assert api.tr("soundpad.library.add") in ("Додати", "Add")


def test_set_locale_same_value_no_emit(tmp_path):
    api, _ = _api(tmp_path)
    events: list[int] = []
    api.stringsChanged.connect(lambda: events.append(1))
    api.set_locale("uk")  # default locale — no change
    assert events == []


def test_view_strings_localization(tmp_path):
    api, _ = _api(tmp_path)
    s = api.strings
    assert s["title"] == "Soundpad"
    assert s["add_button"] == "+ Додати звук"
    assert s["category_all"] == "Усі"
    assert s["count"] == "{n} звуків"

    events: list[int] = []
    api.stringsChanged.connect(lambda: events.append(1))
    api.set_locale("en")
    assert events, "stringsChanged must fire on locale change"
    s = api.strings
    assert s["add_button"] == "+ Add sound"
    assert s["category_all"] == "All"
    assert s["count"] == "{n} sounds"


def test_view_strings_cover_qml_keys(tmp_path):
    """Every short key the QML view reads must exist in both locales."""
    from stream_cheremsha import l10n
    from stream_cheremsha.ui.soundpad_qml_api import _VIEW_L10N_KEYS

    for short in _VIEW_L10N_KEYS:
        for locale in ("uk", "en"):
            assert l10n.tr(locale, f"soundpad.{short}"), (locale, short)


class FakeResponse:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Canned responses per URL substring; records requested URLs."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.requests: list[tuple[str, object]] = []

    def get(self, url, headers=None):
        self.requests.append((url, headers))
        for key, resp in self.routes.items():
            if key in url:
                return resp
        raise AssertionError(f"no fake route for {url}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _index_html() -> str:
    p = Path(__file__).resolve().parent / "fixtures" / "myinstants_ua_index.html"
    return p.read_text(encoding="utf-8")


_INSTANT_HTML = '<html><body>var mp3_url="https://www.myinstants.com/music/x.mp3";</body></html>'


def _client_with(tmp_path, session):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    return MyInstantsClient(
        session_factory=lambda: session, cache_dir=tmp_path / "cache", min_interval_sec=0
    )


def test_load_library_page_populates_rows(tmp_path):
    api, _ = _api(tmp_path)
    fake = FakeSession({"trending": FakeResponse(text=_index_html())})
    api._library = _client_with(tmp_path, fake)

    api.loadLibraryPage(1)
    rows = _json.loads(api.libraryRowsJson)
    assert [r["path"] for r in rows][:2] == [
        "/en/instant/slava-ukraini-12345/",
        "/en/instant/ptn-pnh-23456/",
    ]
    assert all(r["title"] for r in rows)
    assert api.libraryStatus == ""
    assert api.libraryPage == 1


def test_load_library_page_error_state(tmp_path):
    class BoomSession(FakeSession):
        def get(self, url, headers=None):
            raise RuntimeError("network down")

    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, BoomSession())
    api.loadLibraryPage(1)
    assert api.libraryStatus == "error"


def test_preview_sound_plays_cached_mp3(tmp_path):
    fake = FakeSession(
        {"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")}
    )
    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    calls: list[bytes] = []
    api._engine.play_preview = lambda data: (calls.append(bytes(data)), "PLAYING")[1]

    api.previewSound("/en/instant/slava-ukraini-12345/")
    assert calls == [b"MP3DATA"]
    assert api.previewPlayingId == "/en/instant/slava-ukraini-12345/"


def test_preview_loading_state_during_download(tmp_path):
    fake = FakeSession(
        {"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")}
    )
    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    seen: list[str] = []
    orig = api._library.resolve_mp3_url

    def spy(path):
        seen.append(api.previewLoadingId)
        return orig(path)

    api._library.resolve_mp3_url = spy  # type: ignore[method-assign]

    events: list[str] = []
    api.previewLoadingChanged.connect(lambda v: events.append(v))

    api.previewSound("/en/instant/slava-ukraini-12345/")
    assert seen == ["/en/instant/slava-ukraini-12345/"]  # loading while downloading
    assert api.previewLoadingId == ""  # cleared once playback starts
    assert api.previewPlayingId == "/en/instant/slava-ukraini-12345/"
    assert events[-1] == ""


def test_preview_failure_clears_loading(tmp_path):
    class BoomMp3(FakeSession):
        def get(self, url, headers=None):
            if "instant/" in url:
                return FakeResponse(text=_INSTANT_HTML)
            raise RuntimeError("download failed")

    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, BoomMp3())

    seen: list[str] = []
    orig = api._library.resolve_mp3_url

    def spy(path):
        seen.append(api.previewLoadingId)
        return orig(path)

    api._library.resolve_mp3_url = spy  # type: ignore[method-assign]

    api.previewSound("/en/instant/x/")
    assert seen == ["/en/instant/x/"]
    assert api.previewLoadingId == ""
    assert api.previewPlayingId == ""


def test_preview_finished_clears_playing_state(tmp_path):
    fake = FakeSession(
        {"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")}
    )
    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    events: list[str] = []
    api.previewPlayingChanged.connect(lambda v: events.append(v))

    api.previewSound("/en/instant/slava-ukraini-12345/")
    assert api.previewPlayingId == "/en/instant/slava-ukraini-12345/"

    # Audio ends naturally — engine notifies, API must clear the playing state.
    api._engine.previewFinished.emit()
    assert api.previewPlayingId == ""
    assert events[-1] == ""


def test_stop_preview_clears_loading_and_playing(tmp_path):
    fake = FakeSession(
        {"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")}
    )
    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    api.previewSound("/en/instant/slava-ukraini-12345/")
    assert api.previewPlayingId == "/en/instant/slava-ukraini-12345/"

    # Simulate an in-flight request for another sound, then stop.
    api._set_preview_loading("/en/instant/other/")
    api.stopPreview()
    assert api.previewLoadingId == ""
    assert api.previewPlayingId == ""


def test_add_library_sound_copies_into_store(tmp_path):
    fake = FakeSession(
        {"instant/": FakeResponse(text=_INSTANT_HTML), ".mp3": FakeResponse(content=b"MP3DATA")}
    )
    api, store = _api(tmp_path)
    api._library = _client_with(tmp_path, fake)

    added: list[str] = []
    failed: list[str] = []
    api.libraryAdded.connect(added.append)
    api.libraryAddFailed.connect(failed.append)
    # Seed the row so the title resolves from the loaded page.
    api._lib_rows = [{"path": "/en/instant/slava-ukraini-12345/", "title": "Slava Ukraini"}]

    api.addLibrarySound("/en/instant/slava-ukraini-12345/")
    assert failed == []
    assert len(added) == 1
    e = store.get(added[0])
    assert e is not None
    assert e.name == "Slava Ukraini"
    assert Path(e.file_path).is_file()
    assert Path(e.file_path).parent == store.library_dir
    assert Path(e.file_path).read_bytes() == b"MP3DATA"


def test_add_library_sound_failure_emits_failed(tmp_path):
    class BoomSession(FakeSession):
        def get(self, url, headers=None):
            raise RuntimeError("network down")

    api, _ = _api(tmp_path)
    api._library = _client_with(tmp_path, BoomSession())
    failed: list[str] = []
    api.libraryAddFailed.connect(failed.append)
    api.addLibrarySound("/en/instant/x/")
    assert failed == ["/en/instant/x/"]
