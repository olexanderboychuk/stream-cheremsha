from __future__ import annotations

from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml"


def _read(rel: str) -> str:
    return (QML / rel).read_text(encoding="utf-8")


def test_modal_has_preferred_width():
    src = _read("components/CheremshaModal.qml")
    assert "property real preferredWidth" in src
    assert "modal.preferredWidth" in src


def test_qmldir_registers_panel():
    src = _read("components/qmldir")
    assert "SoundpadLibraryPanel 1.0 SoundpadLibraryPanel.qml" in src


def test_view_wires_library_button_and_modal():
    src = _read("SoundpadView.qml")
    assert "property bool showLibraryModal: false" in src
    assert "spApi.openLibrary()" in src
    assert "id: libraryModal" in src
    assert "preferredWidth: 780" in src
    assert "SoundpadLibraryPanel {}" in src


def test_panel_qml_compiles(qapp):
    """Load the panel with a fake spApi context property; no QML errors."""
    from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    class FakeSpApi(QObject):
        rowsChanged = Signal()
        statusChanged = Signal(str)
        pageChanged = Signal(int)
        previewPlayingChanged = Signal(str)
        previewLoadingChanged = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._rows_json = "[]"
            self._status = ""
            self._page = 1
            self._preview_id = ""
            self._loading_id = ""

        @Property(str, notify=rowsChanged)
        def libraryRowsJson(self):
            return self._rows_json

        @Property(str, notify=statusChanged)
        def libraryStatus(self):
            return self._status

        @Property(int, notify=pageChanged)
        def libraryPage(self):
            return self._page

        @Property(str, notify=previewPlayingChanged)
        def previewPlayingId(self):
            return self._preview_id

        @Property(str, notify=previewLoadingChanged)
        def previewLoadingId(self):
            return self._loading_id

        @Property("QVariantMap")
        def libraryStrings(self):
            return {
                "button": "Бібліотека",
                "title": "Бібліотека звуків",
                "subtitle": "",
                "add": "Додати",
                "added": "Додано",
                "loading": "Завантаження звуків…",
                "error_title": "Не вдалося завантажити звуки",
                "retry": "Спробувати ще раз",
                "empty_title": "На цій сторінці немає звуків",
                "page": "Сторінка {n}",
                "prev": "Назад",
                "next": "Далі",
            }

        @Slot()
        def openLibrary(self):
            pass

        @Slot(int)
        def loadLibraryPage(self, page: int):
            pass

        @Slot(str)
        def previewSound(self, path: str):
            pass

        @Slot()
        def stopPreview(self):
            pass

        @Slot(str)
        def addLibrarySound(self, path: str):
            pass

    engine = QQmlEngine()
    engine.addImportPath(str(QML))
    fake = FakeSpApi()
    engine.rootContext().setContextProperty("spApi", fake)
    url = QUrl.fromLocalFile(str(QML / "components" / "SoundpadLibraryPanel.qml"))
    comp = QQmlComponent(engine, url)
    item = None if comp.isError() else comp.create()
    errs = [str(e.errorString()) for e in comp.errors()]
    assert item is not None, "; ".join(errs)


_VIEW_STRING_KEYS = (
    "title",
    "subtitle",
    "search_ph",
    "add_button",
    "category_all",
    "count",
    "no_results",
    "add_title",
    "add_subtitle",
    "add_error_file",
    "edit_title",
    "name_label",
    "category_label",
    "volume_label",
    "mode_label",
    "cooldown_label",
    "edit_hint",
    "enabled",
    "cancel",
    "save",
    "hotkey_title",
    "hotkey_prompt",
    "hotkey_conflict",
    "hotkey_assigned",
    "hotkey_replace",
    "hotkey_clear",
    "hotkey_label",
    "hotkey_listening",
    "hotkey_assign",
    "optional",
    "hotkey_in_use",
    "empty_title",
    "empty_hint",
    "empty_drag",
    "np_playing",
    "np_idle",
    "card_playing",
    "file_missing",
    "menu_play",
    "menu_stop",
    "menu_retry",
    "menu_relink",
    "menu_hotkey",
    "menu_edit",
    "menu_duplicate",
    "menu_remove",
    "view_grid",
    "view_list",
)


def _make_fake_sp_api():
    """Fake spApi covering every member the soundpad QML files reference."""
    from PySide6.QtCore import Property, QObject, Signal, Slot

    class FakeSpApi(QObject):
        soundsChanged = Signal()
        importNeeded = Signal(str)
        nowPlayingChanged = Signal(str, float, float)
        stringsChanged = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)

        @Property("QVariantMap", notify=stringsChanged)
        def strings(self):
            return {k: k for k in _VIEW_STRING_KEYS}

        @Property("QVariantMap")
        def libraryStrings(self):
            return {}

        @Slot()
        def soundsJson(self):
            return "[]"

        @Slot()
        def globalStateJson(self):
            return (
                '{"volume": 0.78, "output_device": "", "monitor": false, '
                '"stream_out": false, "view_mode": "list"}'
            )

        @Slot()
        def outputDevices(self):
            return "[]"

        @Slot()
        def openLibrary(self):
            pass

        @Slot()
        def stopPreview(self):
            pass

        @Slot(str)
        def playSound(self, sound_id: str):
            pass

        @Slot(str)
        def stopSound(self, sound_id: str):
            pass

        @Slot(str)
        def duplicateSound(self, sound_id: str):
            return ""

        @Slot(str)
        def removeSound(self, sound_id: str):
            return True

        @Slot(str, str)
        def assignHotkey(self, sound_id: str, combo: str):
            return "ok"

        @Slot(str)
        def clearHotkey(self, sound_id: str):
            return True

        @Slot(str)
        def hotkeyOwnerName(self, combo: str):
            return ""

        @Slot(str, str, str, str, float, str)
        def addSound(self, file_url, name, category, hotkey, volume, mode):
            return ""

        @Slot(str, str)
        def updateSoundJson(self, sound_id: str, patch_json: str):
            return True

        @Slot()
        def pickAudioFile(self):
            return ""

        @Slot(str)
        def importDroppedUrls(self, urls_json: str):
            return "[]"

        @Slot(float)
        def setGlobalVolume(self, v: float):
            pass

        @Slot(str)
        def setOutputDevice(self, desc: str):
            pass

    return FakeSpApi()


def test_soundpad_qml_files_compile(qapp):
    """Every soundpad QML file compiles and instantiates with a fake spApi."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    rels = (
        "SoundpadView.qml",
        "components/SoundpadAddDialog.qml",
        "components/SoundpadEmptyState.qml",
        "components/SoundpadNowPlaying.qml",
        "components/CheremshaSoundCard.qml",
    )
    for rel in rels:
        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        fake = _make_fake_sp_api()
        engine.rootContext().setContextProperty("spApi", fake)
        url = QUrl.fromLocalFile(str(QML / rel))
        comp = QQmlComponent(engine, url)
        item = None if comp.isError() else comp.create()
        errs = [str(e.errorString()) for e in comp.errors()]
        assert item is not None, f"{rel}: " + "; ".join(errs)
