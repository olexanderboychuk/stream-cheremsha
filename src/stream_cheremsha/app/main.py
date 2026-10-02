from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path

# Linux/NVIDIA needs the documented ANGLE/native-Vulkan path to avoid the
# crashing GBM allocation path. Windows and macOS retain Qt WebEngine defaults.
if sys.platform.startswith("linux"):
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--use-gl=angle --enable-features=Vulkan --use-vulkan=native"
    )
    # Native system file pickers: without a platform theme Qt falls back to
    # its built-in QFileDialog (dark, alien on every DE). Prefer the
    # freedesktop portal so the OS-native chooser appears (KDE/GNOME/GTK
    # handled by the installed portal backends). Respected user override via
    # setdefault; Qt falls back gracefully when portals are unavailable.
    # Must be set before QApplication is constructed (any launch path: this
    # module top runs first since __main__ imports it).
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")

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


def _install_gui_gap_watchdog(app: QApplication) -> None:
    """Warn when the GUI event loop is starved for >0.5s.

    Hotkey presses reach the GUI as queued cross-thread signals; if the main
    thread is blocked, the press -> audio path stalls invisibly. The timer is
    coarse and only logs when a real gap occurs, so it is silent in normal
    operation.
    """
    last = [0.0]

    def tick() -> None:
        t = time.monotonic()
        if last[0] and t - last[0] > 0.5:
            logger.warning("GUI event loop gap %.2fs", t - last[0])
        last[0] = t

    timer = QTimer(app)
    timer.setTimerType(Qt.TimerType.CoarseTimer)
    timer.timeout.connect(tick)
    timer.start(200)


def _configure_logging() -> None:
    """
    In standalone Windows builds we usually disable the console window, so stdout logs
    vanish. Always log to a file as well to make debugging user-reported issues possible.
    """
    log_level = logging.INFO
    # Diagnostic override: CHEREMSHA_LOG_LEVEL=DEBUG captures hotkey
    # suppression lines for input-latency investigations.
    _env_level = (os.getenv("CHEREMSHA_LOG_LEVEL") or "").strip().upper()
    if _env_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
        log_level = getattr(logging, _env_level)
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
    # Third-party chatter that buries diagnostics: per-request lines from
    # the update checker (httpx INFO) on every run.
    logging.getLogger("httpx").setLevel(logging.WARNING)


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
    # Ensure QML has loaded before accessing rootObject.
    app.processEvents()
    # Localize the initial loader text (QSettings persists ui/locale; default uk).
    try:
        from PySide6.QtCore import QSettings

        from stream_cheremsha import l10n

        saved = str(
            QSettings("stream-cheremsha", "Stream Cheremsha").value(
                l10n.SETTINGS_UI_LOCALE, l10n.DEFAULT_LOCALE
            )
            or l10n.DEFAULT_LOCALE
        )
        _locale = l10n.normalize_locale(saved)
        _root = splash.rootObject()
        if _root is not None:
            _root.setProperty("statusText", l10n.tr(_locale, "splash.starting"))
            _root.setProperty("progress", 0.0)
    except Exception:
        logger.debug("Splash l10n init failed; using QML defaults", exc_info=True)
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
    _install_gui_gap_watchdog(app)

    def _start_main_window() -> None:
        # Heavy import happens here, while the splash is already visible.
        from stream_cheremsha.ui.main_window import MainWindow

        window = MainWindow()
        # Keep the main window hidden until all secondary pages are warmed.
        # The first page (Connections QML) is loaded synchronously inside
        # MainWindow.__init__, but we do not show the window until the splash
        # warm-up finishes to avoid displaying a half-constructed UI.
        asyncio.ensure_future(_warm_and_reveal(window))

    async def _warm_and_reveal(window) -> None:  # noqa: ANN001
        """Splash-phase warm-up, then reveal: staged preload with live status.

        Uses already-hidden splash time to compile heavy QML pages once into
        the navigation cache (kept alive, never unloaded). Yields between
        pages so the splash keeps rendering. The main window is shown only
        after all secondary pages are fully lazy-loaded and the splash phase
        completes; all remaining startup work runs deferred in run_startup()
        afterwards.
        """

        def _set_splash_status(text: str, progress: float = -1.0) -> None:
            try:
                root = splash.rootObject()
                if root is not None:
                    # status_cb receives already-translated text from MainWindow.tr
                    root.setProperty("statusText", text)
                    if progress >= 0:
                        root.setProperty("progress", float(progress))
            except RuntimeError:
                pass

        try:
            await window.warm_overlay_server(status_cb=_set_splash_status)
        except Exception:
            logger.exception("Overlay server warm-up failed; retrying post-show")
        try:
            await window.warm_secondary_pages(status_cb=_set_splash_status)
        except Exception:
            logger.exception("QML warm-up failed; continuing with lazy loading")

        # Main window remains hidden until warm-up completes.
        # Show the fully-ready window only after splash warm-up finishes.
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
