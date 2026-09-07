from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import sys
from pathlib import Path

# Linux/NVIDIA needs the documented ANGLE/native-Vulkan path to avoid the
# crashing GBM allocation path. Windows and macOS retain Qt WebEngine defaults.
if sys.platform.startswith("linux"):
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--use-gl=angle --enable-features=Vulkan --use-vulkan=native"
    )

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from stream_cheremsha.diagnostics.runtime import install_runtime_diagnostics
from stream_cheremsha.paths import stream_cheremsha_root

logger = logging.getLogger(__name__)

# NOTE: MainWindow (and its heavy dependency chain: chat sources, TTS, music,
# telegram, httpx, ...) is imported lazily inside _start_main_window so the
# splash screen can appear before ~1.5s of Python imports block the main thread.


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
    install_runtime_diagnostics(app, loop)
    # Ensure qasync loop stops when Qt is quitting, otherwise the Python process can linger.
    app.aboutToQuit.connect(loop.stop)

    def _start_main_window() -> None:
        # Heavy import happens here, while the splash is already visible.
        from stream_cheremsha.ui.main_window import MainWindow

        window = MainWindow()
        # The first page (Connections QML) is loaded synchronously inside
        # MainWindow.__init__, so by this point the window is coherent:
        # sidebar rendered, first page ready. Show it behind the splash so it
        # can paint/composite while secondary pages warm up.
        window.show()
        app.processEvents()
        asyncio.ensure_future(_warm_and_reveal(window))

    async def _warm_and_reveal(window) -> None:  # noqa: ANN001
        """Splash-phase warm-up, then reveal: staged preload with live status.

        Uses already-hidden splash time to compile heavy QML pages once into
        the navigation cache (kept alive, never unloaded). Yields between
        pages so the splash keeps rendering. The splash closes only after the
        MainWindow is fully ready; all remaining startup work (overlay server,
        music player, TTS backend, workers, telegram, autostart, updates) runs
        deferred in run_startup() afterwards.
        """

        def _set_splash_status(text: str) -> None:
            try:
                root = splash.rootObject()
                if root is not None:
                    root.setProperty("statusText", text)
            except RuntimeError:
                pass

        try:
            await window.warm_secondary_pages(status_cb=_set_splash_status)
        except Exception:
            logger.exception("QML warm-up failed; continuing with lazy loading")
        # Show the fully-ready window underneath BEFORE closing the splash so
        # the user never sees a half-constructed UI or a desktop flash. The
        # yield lets the shown window paint through the normal event loop
        # (never app.processEvents() here — this runs inside a task).
        try:
            window.show()
        except RuntimeError:
            pass
        await asyncio.sleep(0)
        try:
            splash.close()
        except RuntimeError:
            pass
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
