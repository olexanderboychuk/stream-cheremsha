from __future__ import annotations

import asyncio
import faulthandler
import logging
import os
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

_DEFAULT_HEARTBEAT_SEC = 2.0
_DEFAULT_STALL_SEC = 15.0


def _truthy_env(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _default_crash_log_path() -> Path:
    log_file_env = (os.getenv("CHEREMSHA_LOG_FILE") or "").strip()
    if log_file_env:
        return Path(log_file_env).with_name("crash.log")
    local_app_data = (os.getenv("LOCALAPPDATA") or "").strip()
    base = Path(local_app_data) if local_app_data else Path.home()
    return base / "stream-cheremsha" / "logs" / "crash.log"


def _open_crash_log() -> object | None:
    path = (os.getenv("CHEREMSHA_CRASH_LOG") or "").strip()
    target = Path(path) if path else _default_crash_log_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.open("a", encoding="utf-8")
    except OSError as e:
        logger.warning("Crash log unavailable (%s): %s", target, e)
        return None


def _asyncio_exception_handler(
    loop: asyncio.AbstractEventLoop,
    context: dict[str, object],
) -> None:
    msg = context.get("message", "asyncio exception")
    exc = context.get("exception")
    if isinstance(exc, BaseException):
        logger.error("Asyncio: %s", msg, exc_info=exc)
        return
    logger.error("Asyncio: %s context=%r", msg, context)


def _thread_exception_handler(args: threading.ExceptHookArgs) -> None:
    if args.exc_value is None:
        logger.error("Thread %r died without exception", args.thread)
        return
    logger.error(
        "Thread %r raised %s",
        args.thread,
        args.exc_value,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _log_task_exception(task: asyncio.Task[object]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Background task %r failed", task.get_name(), exc_info=exc)


def track_background_task(task: asyncio.Task[object]) -> asyncio.Task[object]:
    """Retrieve and log task failures instead of silently dropping them."""
    task.add_done_callback(_log_task_exception)
    return task


def _heavy_diagnostics_enabled() -> bool:
    """Stall watchdog + extra probes — opt-in on Windows, on by default elsewhere."""
    if sys.platform == "win32":
        if _truthy_env("CHEREMSHA_HEAVY_DIAGNOSTICS"):
            return True
        return False
    if _truthy_env("CHEREMSHA_HEAVY_DIAGNOSTICS"):
        return True
    raw = (os.getenv("CHEREMSHA_DIAGNOSTICS") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if _truthy_env("CHEREMSHA_DEBUG"):
        return True
    return raw in {"1", "true", "yes", "on"}


def _dump_stall_tracebacks(*, crash_fp: object | None) -> None:
    if crash_fp is not None:
        try:
            faulthandler.dump_traceback(file=crash_fp, all_threads=False)
            crash_fp.flush()
        except OSError as e:
            logger.warning("Could not write stall dump: %s", e)
    try:
        faulthandler.dump_traceback(file=sys.stderr, all_threads=False)
    except OSError as e:
        logger.warning("Could not write stall dump to stderr: %s", e)


def _install_crash_log_handler() -> object | None:
    """faulthandler into crash.log: Python stacks at the moment of a native fault (AV/segfault)."""
    if _truthy_env("CHEREMSHA_DISABLE_CRASH_LOG"):
        return None
    crash_fp = _open_crash_log()
    if crash_fp is not None:
        try:
            faulthandler.enable(file=crash_fp, all_threads=True)
            logger.info("Native crash logging enabled: %s", getattr(crash_fp, "name", crash_fp))
        except OSError as e:
            logger.warning("faulthandler.enable failed: %s", e)
            return None
    return crash_fp


async def _process_heartbeat_loop() -> None:
    """Periodic alive log so silent native exits show the last timestamp in app.log."""
    pid = os.getpid()
    n = 0
    while True:
        await asyncio.sleep(30.0)
        n += 1
        logger.info("Process alive pid=%s beat=%s", pid, n)


def install_runtime_diagnostics(
    app: QApplication,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Always log asyncio/thread failures to app.log; heavy probes are opt-in (non-Windows)."""
    loop.set_exception_handler(_asyncio_exception_handler)
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_exception_handler  # type: ignore[assignment]

    crash_fp = _install_crash_log_handler()

    def _start_heartbeat() -> None:
        track_background_task(
            asyncio.create_task(_process_heartbeat_loop(), name="cheremsha-alive"),
        )

    loop.call_soon(_start_heartbeat)

    if not _heavy_diagnostics_enabled():
        return

    try:
        stall_sec = float(os.getenv("CHEREMSHA_STALL_SEC", str(_DEFAULT_STALL_SEC)).strip())
    except ValueError:
        stall_sec = _DEFAULT_STALL_SEC
    stall_sec = max(5.0, min(120.0, stall_sec))

    try:
        beat_sec = float(os.getenv("CHEREMSHA_HEARTBEAT_SEC", str(_DEFAULT_HEARTBEAT_SEC)).strip())
    except ValueError:
        beat_sec = _DEFAULT_HEARTBEAT_SEC
    beat_sec = max(0.5, min(30.0, beat_sec))

    import time

    last_beat = {"mono": time.monotonic()}
    lock = threading.Lock()
    stop = threading.Event()
    last_report = {"mono": 0.0}

    from PySide6.QtCore import QTimer

    pulse = QTimer(app)
    pulse.setInterval(int(beat_sec * 1000))

    def _pulse() -> None:
        with lock:
            last_beat["mono"] = time.monotonic()

    pulse.timeout.connect(_pulse)
    pulse.start()

    def _watchdog() -> None:
        while not stop.wait(beat_sec):
            with lock:
                age = time.monotonic() - float(last_beat["mono"])
            if age < stall_sec:
                continue
            now = time.monotonic()
            with lock:
                if now - float(last_report["mono"]) < stall_sec:
                    continue
                last_report["mono"] = now
            logger.error(
                "Main thread stall detected (~%.1fs without Qt heartbeat); dumping thread stacks",
                age,
            )
            _dump_stall_tracebacks(crash_fp=crash_fp)

    threading.Thread(
        target=_watchdog,
        name="cheremsha-stall-watchdog",
        daemon=True,
    ).start()

    def _on_quit() -> None:
        stop.set()

    app.aboutToQuit.connect(_on_quit)
    logger.info(
        "Heavy runtime diagnostics enabled (heartbeat=%.1fs stall=%.1fs crash_log=%s)",
        beat_sec,
        stall_sec,
        getattr(crash_fp, "name", None),
    )
