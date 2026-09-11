from __future__ import annotations

import argparse
import ctypes
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import QCloseEvent, QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from stream_cheremsha.paths import stream_cheremsha_root
from stream_cheremsha.updates.downloader import (
    DownloadCancelled,
    download_file,
    sha256_file,
)

logger = logging.getLogger(__name__)

_MUTEX_NAME = "Local\\CheremshaVisibleUpdater"
_ERROR_ALREADY_EXISTS = 183
_SYNCHRONIZE = 0x00100000
_WAIT_TIMEOUT = 258

_TEXT = {
    "uk": {
        "title": "Оновлення Cheremsha",
        "heading": "Оновлення Cheremsha",
        "version": "Оновлення до версії {version}",
        "preparing": "Підготовка оновлення…",
        "downloading": "Завантаження оновлення…",
        "verifying": "Перевірка оновлення…",
        "installing": "Встановлення оновлення…",
        "finishing": "Запуск Cheremsha…",
        "cancelling": "Скасування…",
        "retry": "Повторити",
        "close": "Закрити",
        "download_error": (
            "Не вдалося завантажити оновлення.\n\n"
            "Перевірте з’єднання з інтернетом і повторіть спробу."
        ),
        "verify_error": (
            "Не вдалося перевірити оновлення.\n\n"
            "Завантажений файл пошкоджений або недійсний."
        ),
        "install_error": "Не вдалося встановити оновлення.\n\nПоточну версію не було видалено.",
        "duplicate": "Оновлення Cheremsha вже запущено.",
    },
    "en": {
        "title": "Cheremsha Update",
        "heading": "Updating Cheremsha",
        "version": "Updating to version {version}",
        "preparing": "Preparing update…",
        "downloading": "Downloading update…",
        "verifying": "Verifying update…",
        "installing": "Installing update…",
        "finishing": "Starting Cheremsha…",
        "cancelling": "Cancelling…",
        "retry": "Retry",
        "close": "Close",
        "download_error": (
            "Unable to download the update.\n\n"
            "Please check your internet connection and try again."
        ),
        "verify_error": (
            "Update verification failed.\n\n"
            "The downloaded update appears to be corrupted or invalid."
        ),
        "install_error": (
            "The update could not be installed.\n\nYour current version has not been removed."
        ),
        "duplicate": "A Cheremsha update is already running.",
    },
}

_STYLESHEET = """
QDialog#updaterWindow { background: transparent; }
QFrame#updateCard {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910);
    border: 1px solid #2a3142;
    border-radius: 18px;
}
QLabel { color: #d7deea; background: transparent; }
QLabel#heading { color: #e8eaed; font-size: 22px; font-weight: 600; }
QLabel#version { color: #8b95a5; font-size: 12px; }
QLabel#status { color: #d7deea; font-size: 14px; font-weight: 600; }
QLabel#details { color: #8b95a5; font-size: 12px; }
QLabel#error { color: #fca5a5; font-size: 12px; }
QProgressBar {
    min-height: 12px; max-height: 12px; border: 1px solid #2a3142;
    border-radius: 6px; background: #10141c; text-align: center; color: transparent;
}
QProgressBar::chunk { border-radius: 5px; background: #14b8a6; }
QPushButton {
    min-height: 36px; padding: 7px 18px; border-radius: 8px;
    color: #e6e6e6; background: #1a2130; border: 1px solid #2f3a4d;
}
QPushButton:hover { background: #202a3a; border-color: #3b4458; }
QPushButton:pressed { background: #2a3446; }
QPushButton#primaryButton {
    color: #ecfdf5; background: #0f766e; border: 1px solid #2dd4bf;
}
QPushButton#primaryButton:hover { background: #14b8a6; border-color: #5eead4; }
"""


class VerificationError(Exception):
    pass


class InstallationError(Exception):
    pass


def _safe_url_for_log(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _format_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in {"B", "KB"} else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _verify_windows_signature(path: Path, expected_publisher: str) -> bool:
    if not sys.platform.startswith("win"):
        return True
    escaped_path = str(path).replace("'", "''")
    escaped_publisher = expected_publisher.replace("'", "''")
    script = (
        f"$sig = Get-AuthenticodeSignature -FilePath '{escaped_path}';"
        "$subject = '';"
        "if ($sig.SignerCertificate -ne $null) { $subject = $sig.SignerCertificate.Subject };"
        f"if ($sig.Status -eq 'Valid' -and $subject -like '*{escaped_publisher}*') "
        "{ exit 0 } else { exit 1 }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return result.returncode == 0


def _windows_kernel32():  # noqa: ANN202
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _wait_for_parent(pid: int, cancelled: threading.Event) -> None:
    if pid <= 0:
        return
    if sys.platform.startswith("win"):
        kernel32 = _windows_kernel32()
        handle = kernel32.OpenProcess(_SYNCHRONIZE, False, pid)
        if not handle:
            return
        try:
            while not cancelled.is_set():
                if kernel32.WaitForSingleObject(handle, 100) != _WAIT_TIMEOUT:
                    return
        finally:
            kernel32.CloseHandle(handle)
        raise DownloadCancelled

    while not cancelled.wait(0.1):
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return
    raise DownloadCancelled


class UpdateWorker(QObject):
    state = Signal(str)
    progress = Signal(int, object, float)
    outcome = Signal(str, str)
    finished = Signal()

    def __init__(self, ns: argparse.Namespace, installer_path: Path) -> None:
        super().__init__()
        self._ns = ns
        self._installer_path = installer_path
        self._cancelled = threading.Event()
        self._started_at = 0.0

    def cancel(self) -> None:
        self._cancelled.set()

    def _on_progress(self, downloaded: int, total: int | None) -> None:
        elapsed = max(0.001, time.monotonic() - self._started_at)
        self.progress.emit(downloaded, total, downloaded / elapsed)

    def run(self) -> None:
        try:
            self.state.emit("preparing")
            _wait_for_parent(self._ns.parent_pid, self._cancelled)
            self._installer_path.unlink(missing_ok=True)

            logger.info("Download started: %s", _safe_url_for_log(self._ns.url))
            self.state.emit("downloading")
            self._started_at = time.monotonic()
            download_file(
                self._ns.url,
                self._installer_path,
                progress=self._on_progress,
                cancelled=self._cancelled.is_set,
            )
            size = self._installer_path.stat().st_size
            logger.info("Download completed: size=%s", size)

            self.state.emit("verifying")
            logger.info("SHA-256 verification started")
            try:
                actual = sha256_file(self._installer_path)
            except OSError as exc:
                raise VerificationError(str(exc)) from exc
            if actual.lower() != self._ns.sha256.lower():
                logger.error("SHA-256 verification result: mismatch")
                self._installer_path.unlink(missing_ok=True)
                raise VerificationError
            logger.info("SHA-256 verification result: valid")
            if self._ns.require_signature and not _verify_windows_signature(
                self._installer_path,
                self._ns.expected_publisher,
            ):
                logger.error("Authenticode verification result: invalid")
                self._installer_path.unlink(missing_ok=True)
                raise VerificationError

            if self._cancelled.is_set():
                raise DownloadCancelled
            self.state.emit("installing")
            # NSIS requires /D= to be the final, unquoted remainder of the raw command line.
            # Passing a normal Python argument list quotes paths containing spaces and can make
            # NSIS ignore the explicit install directory.
            command = (
                f'"{self._installer_path}" /S /D={self._ns.install_dir}'
                if sys.platform.startswith("win")
                else [str(self._installer_path), "/S", f"/D={self._ns.install_dir}"]
            )
            logger.info("Installer started")
            try:
                installer = subprocess.Popen(
                    command,
                    executable=str(self._installer_path),
                    close_fds=True,
                )
            except (OSError, ValueError) as exc:
                raise InstallationError(str(exc)) from exc
            try:
                return_code = installer.wait()
            except (OSError, subprocess.SubprocessError) as exc:
                raise InstallationError(str(exc)) from exc
            logger.info("Installer exit code: %s", return_code)
            if return_code != 0:
                raise InstallationError(f"Installer exited with code {return_code}")

            self.state.emit("finishing")
            logger.info("Application relaunch delegated to NSIS: %s", self._ns.app)
            try:
                self._installer_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Unable to remove completed installer", exc_info=True)
            self.outcome.emit("success", "")
        except DownloadCancelled:
            try:
                self._installer_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Unable to remove cancelled installer", exc_info=True)
            self.outcome.emit("cancelled", "")
        except VerificationError as exc:
            self.outcome.emit("verify", str(exc))
        except InstallationError as exc:
            logger.exception("Installation failed")
            self.outcome.emit("install", str(exc))
        except (OSError, ValueError, httpx.HTTPError, subprocess.SubprocessError) as exc:
            logger.warning("Update download failed: %s", exc)
            self._installer_path.unlink(missing_ok=True)
            self.outcome.emit("download", str(exc))
        finally:
            self.finished.emit()


class _DraggableCard(QFrame):
    """Rounded updater surface that retains native window dragging."""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)


class UpdaterWindow(QDialog):
    def __init__(self, ns: argparse.Namespace, icon_path: Path) -> None:
        super().__init__()
        self._ns = ns
        self._lang = ns.locale if ns.locale in _TEXT else "uk"
        self._thread: QThread | None = None
        self._worker: UpdateWorker | None = None
        self._state = "preparing"
        self._cancel_requested = False
        self._outcome = ""
        self._outcome_details = ""

        self.setObjectName("updaterWindow")
        self.setWindowTitle(self._tr("title"))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(500, 460)
        self.setStyleSheet(_STYLESHEET)
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        card = _DraggableCard()
        card.setObjectName("updateCard")
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 12, 34, 26)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(82, 82)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path.is_file():
            logo.setPixmap(
                QPixmap(str(icon_path)).scaled(
                    74,
                    74,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(32)

        heading = QLabel(self._tr("heading"))
        heading.setObjectName("heading")
        heading.setMinimumHeight(32)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        version = QLabel(self._tr("version").format(version=ns.version))
        version.setObjectName("version")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        layout.addSpacing(12)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)
        self._percent = QLabel("")
        self._percent.setObjectName("details")
        self._percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._percent)
        self._status = QLabel(self._tr("preparing"))
        self._status.setObjectName("status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)
        self._details = QLabel("")
        self._details.setObjectName("details")
        self._details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._details)
        self._error = QLabel("")
        self._error.setObjectName("error")
        self._error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error.setWordWrap(True)
        self._error.hide()
        layout.addWidget(self._error)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._retry = QPushButton(self._tr("retry"))
        self._retry.setObjectName("primaryButton")
        self._retry.clicked.connect(self._start)
        self._retry.hide()
        buttons.addWidget(self._retry)
        self._close = QPushButton(self._tr("close"))
        self._close.clicked.connect(self.close)
        self._close.hide()
        buttons.addWidget(self._close)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        QTimer.singleShot(0, self._start)

    def _tr(self, key: str) -> str:
        return _TEXT[self._lang][key]

    def _start(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self._outcome = ""
        self._outcome_details = ""
        self._cancel_requested = False
        self._retry.hide()
        self._close.hide()
        self._error.hide()
        self._details.clear()
        self._percent.clear()
        self._progress.setRange(0, 0)

        installer_path = Path(self._ns.work_dir) / "Cheremsha-Update-Installer.exe"
        thread = QThread(self)
        worker = UpdateWorker(self._ns, installer_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.state.connect(self._set_state)
        worker.progress.connect(self._set_progress)
        worker.outcome.connect(self._set_outcome)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _set_state(self, state: str) -> None:
        self._state = state
        self._status.setText(self._tr(state))
        self._error.hide()
        if state != "downloading":
            self._progress.setRange(0, 0)
            self._percent.clear()
            self._details.clear()

    def _set_progress(self, downloaded: int, total_value: object, speed: float) -> None:
        total = total_value if isinstance(total_value, int) and total_value > 0 else None
        if total is not None:
            percent = min(100, round(downloaded * 100 / total))
            self._progress.setRange(0, 100)
            self._progress.setValue(percent)
            self._percent.setText(f"{percent}%")
            detail = f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
            if speed > 0:
                remaining = max(0, total - downloaded)
                detail += f"  •  {_format_bytes(round(speed))}/s  •  {round(remaining / speed)} s"
            self._details.setText(detail)
        else:
            self._progress.setRange(0, 0)
            self._percent.clear()
            self._details.setText(
                f"{_format_bytes(downloaded)}  •  {_format_bytes(round(speed))}/s"
            )

    def _set_outcome(self, outcome: str, details: str) -> None:
        self._outcome = outcome
        self._outcome_details = details

    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        outcome = self._outcome
        if outcome in {"success", "cancelled"}:
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(900 if outcome == "success" else 0, app.quit)
            return
        if not outcome:
            return
        logger.error("Updater error state=%s details=%s", outcome, self._outcome_details)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._percent.clear()
        self._details.clear()
        self._status.clear()
        self._error.setText(self._tr(f"{outcome}_error"))
        self._error.show()
        self._retry.show()
        self._close.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread is not None and self._thread.isRunning() and self._outcome:
            event.ignore()
            return
        if self._state == "installing" and not self._outcome:
            event.ignore()
            return
        if self._worker is not None and not self._outcome:
            self._cancel_requested = True
            self._worker.cancel()
            self._status.setText(self._tr("cancelling"))
            self._retry.hide()
            self._close.hide()
            event.ignore()
            return
        event.accept()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="CheremshaUpdater")
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--install-dir", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--parent-pid", required=True, type=int)
    parser.add_argument("--locale", choices=("uk", "en"), default="uk")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--require-signature", action="store_true")
    parser.add_argument("--expected-publisher", default="")
    ns = parser.parse_args(argv)
    if urlsplit(ns.url).scheme not in {"http", "https"}:
        parser.error("--url must be HTTP(S)")
    if len(ns.sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in ns.sha256):
        parser.error("--sha256 must be 64 hexadecimal characters")
    if ns.require_signature and not ns.expected_publisher.strip():
        parser.error("--expected-publisher is required with --require-signature")
    ns.install_dir = str(Path(ns.install_dir).resolve())
    ns.app = str(Path(ns.app).resolve())
    ns.work_dir = str(Path(ns.work_dir).resolve())
    ns.ready_file = str(Path(ns.ready_file).resolve())
    return ns


def _configure_logging() -> None:
    log_root = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "stream-cheremsha" / "logs"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_root.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_root / "updater.log", encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _acquire_mutex() -> object | None:
    if not sys.platform.startswith("win"):
        return object()
    kernel32 = _windows_kernel32()
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle or ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        if handle:
            kernel32.CloseHandle(handle)
        return None
    return handle


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)
    _configure_logging()
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass
    logger.info("Updater started")
    logger.info("Target version: %s", ns.version)
    logger.info("Installer URL: %s", _safe_url_for_log(ns.url))

    app = QApplication([sys.argv[0]])
    app.setApplicationName("Cheremsha Updater")
    app.setApplicationDisplayName("Cheremsha Updater")
    mutex = _acquire_mutex()
    if mutex is None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(None, _TEXT[ns.locale]["title"], _TEXT[ns.locale]["duplicate"])
        return 0

    icon_path = stream_cheremsha_root() / "assets" / "icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = UpdaterWindow(ns, icon_path)
    window.show()
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        window.move(geometry.center() - window.rect().center())
    app.processEvents()
    try:
        Path(ns.ready_file).touch()
    except OSError:
        logger.exception("Unable to signal updater readiness")
        return 1
    app.aboutToQuit.connect(lambda: logger.info("Updater exit"))
    result = app.exec()
    if sys.platform.startswith("win") and mutex is not None:
        _windows_kernel32().CloseHandle(mutex)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
