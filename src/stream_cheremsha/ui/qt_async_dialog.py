"""Async-friendly QDialog helpers for qasync.

Blocking ``QDialog.exec()`` from inside a coroutine keeps the current asyncio Task
as "running" while Qt processes nested events; thread-pool completions (e.g.
``asyncio.to_thread``) then try to resume other tasks and can trigger:

``RuntimeError: Cannot enter into task ... while another task ... is being executed``.
"""

from __future__ import annotations

import asyncio
import contextlib

from PySide6.QtWidgets import QDialog


async def async_dialog_code(dialog: QDialog) -> int:
    """Show ``dialog`` non-modally and await ``finished`` (replaces ``exec()``)."""
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[int] = loop.create_future()

    def _on_finished(result: int) -> None:
        if not fut.done():
            fut.set_result(int(result))

    dialog.finished.connect(_on_finished)
    dialog.open()
    try:
        return await fut
    finally:
        with contextlib.suppress(TypeError):
            dialog.finished.disconnect(_on_finished)
