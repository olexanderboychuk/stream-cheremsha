from __future__ import annotations

import asyncio

from stream_cheremsha.asyncio_qt import complete_future_safely, install_qasync_compat, to_thread


def test_to_thread_yields_before_return() -> None:
    def _add_sync(a: int, b: int) -> int:
        return a + b

    async def _run() -> None:
        result = await to_thread(_add_sync, 2, 3)
        assert result == 5

    asyncio.run(_run())


def test_install_qasync_compat_patches_to_thread() -> None:
    install_qasync_compat()
    assert asyncio.to_thread is to_thread


def test_complete_future_safely_defers_set_result() -> None:
    async def _run() -> None:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[int] = loop.create_future()

        async def _complete_later() -> None:
            await asyncio.sleep(0.01)
            complete_future_safely(fut, result=42)

        waiter = asyncio.create_task(_complete_later())
        assert await fut == 42
        await waiter

    asyncio.run(_run())
