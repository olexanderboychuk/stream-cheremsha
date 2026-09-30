from __future__ import annotations


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
