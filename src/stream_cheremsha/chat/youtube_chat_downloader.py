from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

try:
    from chat_downloader import ChatDownloader
except ImportError:  # pragma: no cover
    ChatDownloader = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ChatDownloaderMessage:
    author: str
    text: str
    received_at: datetime


def normalize_chat_downloader_item(item: Any) -> ChatDownloaderMessage | None:
    if not isinstance(item, dict):
        return None
    author = str(item.get("author") or item.get("author_name") or "unknown").strip() or "unknown"
    text = str(item.get("message") or item.get("text") or "").strip()
    if not text:
        return None
    return ChatDownloaderMessage(author=author, text=text, received_at=datetime.now(UTC))


def pump_messages_to_queue(
    items: Iterable[Any],
    q: asyncio.Queue[ChatDownloaderMessage],
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Blocking pump; safe to call from a worker thread via asyncio.to_thread."""
    for it in items:
        msg = normalize_chat_downloader_item(it)
        if msg is None:
            continue
        loop.call_soon_threadsafe(q.put_nowait, msg)


def iter_youtube_live_chat(watch_url: str) -> Iterable[Any]:
    """Return a blocking iterable of raw chat items for the given watch URL."""
    if ChatDownloader is None:
        raise RuntimeError(
            "chat-downloader is not installed. Install project dependencies "
            "(e.g. `pip install -e .` or `pip install chat-downloader`).",
        )
    return ChatDownloader().get_chat(watch_url)  # type: ignore[operator]
