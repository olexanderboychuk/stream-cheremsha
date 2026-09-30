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
    assert "preferredWidth: 720" in src
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

        def __init__(self, parent=None):
            super().__init__(parent)
            self._rows_json = "[]"
            self._status = ""
            self._page = 1
            self._preview_id = ""

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
