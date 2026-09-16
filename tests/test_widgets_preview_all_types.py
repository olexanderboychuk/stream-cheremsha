"""Preview (▶) must publish to the targeted widget instance topic for every type."""

from __future__ import annotations

import asyncio

from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.widget_instances import WIDGET_TYPES
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


async def _preview_patch(widget_type: str, instance: str) -> dict:
    ps = OverlayPubSub()
    q = ps.subscribe(f"overlay:{widget_type}:{instance}")
    api = WidgetsQmlApi(pubsub=ps)
    api.previewLayoutWidget(widget_type, instance)
    return await asyncio.wait_for(q.get(), timeout=2.0)


def test_preview_targets_given_instance_for_all_types() -> None:
    iid = "testinst123"
    for widget_type in sorted(WIDGET_TYPES):
        patch = asyncio.run(_preview_patch(widget_type, iid))
        assert isinstance(patch, dict) and patch, widget_type


def test_preview_music_sets_demo_track() -> None:
    patch = asyncio.run(_preview_patch("music", "testinst123"))
    current = (patch.get("set_state") or {}).get("current") or {}
    assert current.get("video_id"), "music preview must set a demo video_id"


def test_preview_without_instance_does_nothing() -> None:
    """Preview without an explicit instance id must not touch 'main'."""

    async def _run() -> None:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:top_likers:main")
        api = WidgetsQmlApi(pubsub=ps)
        api.previewTopLikersOverlay()
        try:
            await asyncio.wait_for(q.get(), timeout=0.2)
            raise AssertionError("expected no patch without instance id")
        except TimeoutError:
            return

    asyncio.run(_run())
