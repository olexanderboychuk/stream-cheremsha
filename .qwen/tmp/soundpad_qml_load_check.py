"""One-off offscreen load check for SoundpadView.qml (Task 9 verification).

Mirrors the real app path: QQuickWidget + rootContext().setContextProperty.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings, QUrl  # noqa: E402
from PySide6.QtQuickWidgets import QQuickWidget  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from stream_cheremsha.soundpad.engine import SoundpadAudioEngine  # noqa: E402
from stream_cheremsha.soundpad.hotkeys import FakeHotkeyBackend, GlobalHotkeyManager  # noqa: E402
from stream_cheremsha.soundpad.store import SoundpadStore  # noqa: E402
from stream_cheremsha.ui.soundpad_qml_api import SoundpadQmlApi  # noqa: E402


class FakeSink:
    async def play_mp3_parallel_with_volume_deduped(self, data, volume, *, dedupe_key=""):
        return True


tmp = Path(tempfile.mkdtemp())
store = SoundpadStore(settings=QSettings("sp-qml-load", "check"), root_dir=tmp)
engine = SoundpadAudioEngine(sink=FakeSink())
hotkeys = GlobalHotkeyManager(backend=FakeHotkeyBackend())
api = SoundpadQmlApi(store=store, engine=engine, hotkeys=hotkeys)

widget = QQuickWidget()
widget.resize(1280, 900)
widget.engine().addImportPath(str(ROOT / "src/stream_cheremsha/qml"))
widget.rootContext().setContextProperty("spApi", api)
widget.setSource(QUrl.fromLocalFile(str(ROOT / "src/stream_cheremsha/qml/SoundpadView.qml")))

root_obj = widget.rootObject()
if root_obj is None:
    print("LOAD FAILED — no root object")
    sys.exit(1)

app.processEvents()

# Exercise the now-playing signal path.
api.nowPlayingChanged.emit("", 0.5, 2.0)
app.processEvents()

print("root object:", type(root_obj).__name__)
print("implicit size:", root_obj.property("implicitWidth"), "x", root_obj.property("implicitHeight"))
print("categoryList:", root_obj.property("categoryList"))
print("LOAD OK — SoundpadView instantiated via QQuickWidget, bindings settled")
sys.exit(0)
