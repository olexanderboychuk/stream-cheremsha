"""qasync-safe asyncio helpers.

qasync runs asyncio on the Qt GUI thread. When ``asyncio.to_thread`` completes, other
tasks may wake in the same loop turn and trigger:

``RuntimeError: Cannot enter into task ... while another task ... is being executed``.

Yield once after thread-pool work so wakeups run in a separate loop iteration.
See ``ui/qt_async_dialog.py`` for the same issue with blocking ``QMessageBox.exec()``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")

_orig_to_thread = asyncio.to_thread


async def to_thread(func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
    result = await _orig_to_thread(func, *args, **kwargs)
    await asyncio.sleep(0)
    return result


def complete_future_safely(
    fut: asyncio.Future[R],
    /,
    *,
    result: R | None = None,
    exc: BaseException | None = None,
) -> None:
    """Complete a Future from a Qt slot without qasync task re-entry crashes."""
    if fut.done():
        return

    async def _finish() -> None:
        await asyncio.sleep(0)
        if fut.done():
            return
        if exc is not None:
            fut.set_exception(exc)
        else:
            fut.set_result(result)  # type: ignore[arg-type]

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
    loop.call_soon(lambda: asyncio.ensure_future(_finish()))


def schedule_coroutine(
    coro,
    *,
    name: str | None = None,
) -> None:
    """Schedule a coroutine from a Qt timer/slot (avoids bare ``ensure_future`` re-entry)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return

    def _start() -> None:
        from stream_cheremsha.diagnostics.runtime import track_background_task

        track_background_task(asyncio.create_task(coro, name=name))

    loop.call_soon(_start)


def install_qasync_compat() -> None:
    """Install qasync workarounds; call once at startup before scheduling tasks."""
    asyncio.to_thread = to_thread  # type: ignore[attr-defined, assignment]
