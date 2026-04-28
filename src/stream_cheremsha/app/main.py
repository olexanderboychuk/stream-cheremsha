from __future__ import annotations

import asyncio
import logging
import multiprocessing
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from stream_cheremsha.ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Windows/PyInstaller safety for multiprocessing spawn children.
    multiprocessing.freeze_support()
    # Force a predictable Qt Quick Controls style (avoid native Windows hover overlays).
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName("Stream Cheremsha")
    app.setApplicationDisplayName("Stream Cheremsha")
    icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Show splash immediately (before MainWindow heavy init).
    splash = QQuickView()
    # Size the native window to the QML root item (avoid huge black window).
    splash.setResizeMode(QQuickView.ResizeMode.SizeViewToRootObject)
    splash.setFlags(
        Qt.WindowType.SplashScreen
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint,
    )
    if icon_path.is_file():
        splash.setIcon(QIcon(str(icon_path)))
    splash.setColor(Qt.GlobalColor.transparent)
    splash_qml = Path(__file__).resolve().parent.parent / "qml" / "SplashScreen.qml"
    splash.setSource(QUrl.fromLocalFile(str(splash_qml)))
    screen = app.primaryScreen()
    if screen is not None:
        ag = screen.availableGeometry()
        splash.setPosition(
            int(ag.x() + (ag.width() - splash.width()) / 2),
            int(ag.y() + (ag.height() - splash.height()) / 2),
        )
    splash.show()
    app.processEvents()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    # Ensure qasync loop stops when Qt is quitting, otherwise the Python process can linger.
    app.aboutToQuit.connect(loop.stop)

    def _start_main_window() -> None:
        window = MainWindow()
        window.startup_finished.connect(splash.close)
        window.show()
        asyncio.ensure_future(window.run_startup())

    # Start heavy QWidget init after the Qt loop begins,
    # so QML animations can run while the main window constructs.
    QTimer.singleShot(0, _start_main_window)

    with loop:
        loop.run_forever()
    # Qt is down; still exit the interpreter if native/CUDA threads outlived the loop.
    sys.exit(0)


if __name__ == "__main__":
    main()
