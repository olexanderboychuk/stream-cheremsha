import asyncio

import pytest

import stream_cheremsha.chat.tiktok_source as tk_mod
from stream_cheremsha.chat.tiktok_source import TikTokChatSource
from stream_cheremsha.pipeline.coordinator import StreamCoordinator


class _FakeCoordinator(StreamCoordinator):
    def __init__(self) -> None:
        # Coordinator is only used for enqueue_chat; keep it minimal.
        # We don't start any workers here.
        super().__init__(
            tts=None,  # type: ignore[arg-type]
            audio_sink=None,  # type: ignore[arg-type]
            on_chat=lambda _msg: None,
            on_status=lambda _msg: None,
        )


class _FakeTikTokClient:
    def __init__(self, unique_id: str) -> None:
        self.unique_id = unique_id
        self.is_live_calls = 0
        self.start_called = False
        self._handlers: list[object] = []
        self._gate_live: asyncio.Event | None = None

    def on(self, _event_type: object):  # noqa: ANN001
        def _decorator(fn):  # noqa: ANN001
            self._handlers.append(fn)
            return fn

        return _decorator

    async def is_live(self) -> bool:
        self.is_live_calls += 1
        # Allow the test to deterministically pause before "becoming live".
        if self.is_live_calls >= 3:
            if self._gate_live is not None:
                await self._gate_live.wait()
            return True
        return False

    async def start(self, **_kwargs):  # noqa: ANN001
        self.start_called = True

        async def _run() -> None:
            await asyncio.sleep(0.02)

        return asyncio.create_task(_run())

    async def disconnect(self, **_kwargs):  # noqa: ANN001
        return None

    async def close(self) -> None:
        return None


def test_tiktok_source_polls_is_live_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    # Speed up retries.
    monkeypatch.setattr(tk_mod, "TIKTOK_RECONNECT_SEC", 0.01)

    client = _FakeTikTokClient("user1")

    def _factory(unique_id: str):
        assert unique_id == "user1"
        return client

    statuses: list[str] = []
    src = TikTokChatSource(
        coordinator=_FakeCoordinator(),
        on_status=statuses.append,
        on_gift=None,
        get_locale=lambda: "uk",
        client_factory=_factory,  # type: ignore[arg-type]
    )

    async def _run() -> None:
        client._gate_live = asyncio.Event()
        await src.start("user1")
        # After two polls (still offline), we should NOT have called start/connect yet.
        await asyncio.wait_for(_wait_until(lambda: client.is_live_calls >= 2), timeout=1.0)
        assert client.start_called is False

        # Eventually is_live becomes True and we connect.
        client._gate_live.set()
        await asyncio.wait_for(_wait_until(lambda: client.start_called), timeout=1.0)
        await src.stop()

    asyncio.run(_run())


async def _wait_until(pred, timeout_sec: float = 1.0) -> None:  # noqa: ANN001
    start = asyncio.get_running_loop().time()
    while True:
        if pred():
            return
        if (asyncio.get_running_loop().time() - start) > timeout_sec:
            raise TimeoutError("predicate not satisfied")
        await asyncio.sleep(0.005)

