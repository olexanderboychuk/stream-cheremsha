from __future__ import annotations

import pytest

from stream_cheremsha.music.queue_controller import MusicQueueController


@pytest.mark.asyncio
async def test_music_queue_advances_on_ended_event() -> None:
    ctl = MusicQueueController(instance="main")

    await ctl.enqueue(video_id="dQw4w9WgXcQ", requested_by="u1")
    await ctl.enqueue(video_id="aaaaaaaaaaa", requested_by="u2")

    cur, q = await ctl.list_queue(limit=10)
    assert cur is not None
    assert cur.video_id == "dQw4w9WgXcQ"
    assert [t.video_id for t in q] == ["aaaaaaaaaaa"]

    await ctl.skip()

    cur2, q2 = await ctl.list_queue(limit=10)
    assert cur2 is not None
    assert cur2.video_id == "aaaaaaaaaaa"
    assert q2 == []


@pytest.mark.asyncio
async def test_music_queue_ignores_late_ended_for_previous_track() -> None:
    # Overlay event bus removed; ensure explicit skip works.
    ctl = MusicQueueController(instance="main")
    await ctl.enqueue(video_id="dQw4w9WgXcQ", requested_by="u1")
    await ctl.enqueue(video_id="aaaaaaaaaaa", requested_by="u2")
    await ctl.skip()
    cur2, _q2 = await ctl.list_queue(limit=10)
    assert cur2 is not None and cur2.video_id == "aaaaaaaaaaa"


@pytest.mark.asyncio
async def test_music_queue_ignores_ended_without_track_id() -> None:
    ctl = MusicQueueController(instance="main")
    await ctl.enqueue(video_id="dQw4w9WgXcQ", requested_by="u1")
    await ctl.enqueue(video_id="aaaaaaaaaaa", requested_by="u2")
    cur, q = await ctl.list_queue(limit=10)
    assert cur is not None and cur.video_id == "dQw4w9WgXcQ"
    assert len(q) == 1


@pytest.mark.asyncio
async def test_music_queue_remove_at() -> None:
    ctl = MusicQueueController(instance="main")

    await ctl.enqueue(video_id="dQw4w9WgXcQ", requested_by="u1")
    await ctl.enqueue(video_id="aaaaaaaaaaa", requested_by="u2")
    await ctl.enqueue(video_id="bbbbbbbbbbb", requested_by="u3")

    removed = await ctl.remove_at(0)
    assert removed is not None
    assert removed.video_id == "aaaaaaaaaaa"

    cur, q = await ctl.list_queue(limit=10)
    assert cur is not None and cur.video_id == "dQw4w9WgXcQ"
    assert [t.video_id for t in q] == ["bbbbbbbbbbb"]


@pytest.mark.asyncio
async def test_music_queue_set_track_title() -> None:
    ctl = MusicQueueController(instance="main")
    t1 = await ctl.enqueue(video_id="dQw4w9WgXcQ", requested_by="u1")
    ok = await ctl.set_track_title(t1.id, "My title")
    assert ok
    cur, _q = await ctl.list_queue(limit=10)
    assert cur is not None
    assert cur.title == "My title"
