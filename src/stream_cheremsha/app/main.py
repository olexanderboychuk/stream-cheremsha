from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from stream_cheremsha.paths import stream_cheremsha_root
from stream_cheremsha.ui.main_window import MainWindow


def _configure_logging() -> None:
    """
    In standalone Windows builds we usually disable the console window, so stdout logs
    vanish. Always log to a file as well to make debugging user-reported issues possible.
    """
    log_level = logging.INFO
    handlers: list[logging.Handler] = []

    # Always keep console handler for dev (or when console is enabled).
    handlers.append(logging.StreamHandler())

    # Optional override for support/debug sessions.
    log_file_env = (os.getenv("CHEREMSHA_LOG_FILE") or "").strip()
    if log_file_env:
        log_path = Path(log_file_env)
    else:
        local_app_data = (os.getenv("LOCALAPPDATA") or "").strip()
        base = Path(local_app_data) if local_app_data else Path.home()
        log_path = base / "stream-cheremsha" / "logs" / "app.log"

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    except OSError:
        # If file logging fails (permissions/ro filesystem), still run with console logging.
        pass

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    _configure_logging()
    # Standalone builds may not have access to system CA cert store.
    # Ensure Python/ssl/httpx can find a CA bundle.
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except ImportError:
        pass
    # Windows/PyInstaller safety for multiprocessing spawn children.
    multiprocessing.freeze_support()
    # Force a predictable Qt Quick Controls style (avoid native Windows hover overlays).
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setOrganizationName("stream-cheremsha")
    app.setApplicationName("Stream Cheremsha")
    app.setApplicationDisplayName("Stream Cheremsha")
    pkg_root = stream_cheremsha_root()
    icon_path = pkg_root / "assets" / "icon.png"
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
    splash_qml = pkg_root / "qml" / "SplashScreen.qml"
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
