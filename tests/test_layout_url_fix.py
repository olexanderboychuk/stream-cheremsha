"""
Test to verify that layout URLs are generated correctly after the fix.
This test specifically addresses the 404 error issue reported for LAYOUT urls.

The `WidgetInstances` class (with `instance_url_for_layout_type` and
`instance_url` methods) used by the original version of these tests is gone;
instances are now managed by the functional API in
`stream_cheremsha.overlays.widget_instances` and every instance is addressed
solely via the server route `/overlay/by-id/{id}`. These tests verify the
current contract: created instances get well-formed by-id URLs, the layout
overlay emits them for bound widgets, and the server resolves known instances
with 200 (instead of 404).
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import quote

import aiohttp
import pytest
from PySide6.QtCore import QSettings

import stream_cheremsha.overlays.layout_overlay as layout_overlay
from stream_cheremsha.overlays import layout as L
from stream_cheremsha.overlays import widget_instances as wi
from stream_cheremsha.overlays.layout_overlay import LayoutOverlayType
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer


def _scope(org_app: str) -> QSettings:
    s = QSettings("stream-cheremsha-test", org_app)
    s.clear()
    s.sync()
    return s


def _patch_scope(monkeypatch, scope: QSettings) -> None:
    """Point every widget_instances QSettings access at the isolated scope."""
    monkeypatch.setattr(wi, "QSettings", lambda *a, **k: scope)


def _by_id_path(instance_id: str) -> str:
    return f"/overlay/by-id/{quote(instance_id, safe='')}"


def test_layout_url_generation(monkeypatch) -> None:
    """Test that layout URLs are generated correctly for an instance."""
    scope = _scope("layout-url-generation")
    _patch_scope(monkeypatch, scope)

    # Create an instance
    instance_id = "test-layout-instance"
    inst = wi.create_instance("chat", f"Bound {instance_id}")
    assert inst.id is not None

    # Get the URL for this instance
    path = _by_id_path(inst.id)
    url = f"http://127.0.0.1:17171{path}"

    # Verify the URL is correctly formatted and doesn't result in 404:
    # the by-id endpoint resolves exactly this instance.
    assert url.startswith("http://")
    assert "overlay" in url.lower()
    assert path == f"/overlay/by-id/{inst.id}"

    # Instances round-trip through QSettings as JSON, so lookups return
    # freshly parsed objects with the same fields.
    stored = wi.get_instance(inst.id, scope)
    assert stored is not None
    assert (stored.id, stored.type_id, stored.name) == (inst.id, inst.type_id, inst.name)
    assert wi.get_by_id(inst.id, scope) is not None

    # The layout overlay emits the bound iframe using the by-id path.
    lay = L.default_layout()
    bound = L.LayoutWidget(
        "w1",
        "chat",
        "main",
        0,
        0,
        420,
        700,
        0,
        widget_instance_id=inst.id,
    )
    monkeypatch.setattr(
        layout_overlay,
        "load_layouts",
        lambda: [replace(lay, widgets=(bound,))],
    )
    html = LayoutOverlayType().render_html({"instance": "main"})
    assert f'src="{path}"' in html

    # Clean up
    assert wi.delete_instance(inst.id, scope)
    assert wi.list_instances(scope) == []


def test_all_layout_types_have_valid_urls() -> None:
    """Test that all layout types generate valid URLs."""
    scope = _scope("layout-url-all-types")
    created = []
    for type_id in L.SUPPORTED_LAYOUT_WIDGETS:
        # Test different layout types if they exist
        instance_id = f"test-{type_id}-instance"
        inst = wi.create_instance(type_id, f"Bound {instance_id}", settings=scope)
        created.append(inst)

        path = _by_id_path(inst.id)
        url = f"http://127.0.0.1:17171{path}"
        assert path.startswith("/overlay/by-id/")
        assert inst.id in path
        assert len(path) > 0
        assert url.startswith("http://")
        assert "overlay" in url.lower()
        assert wi.get_by_id(inst.id, scope) is not None

    # Clean up
    for inst in created:
        assert wi.delete_instance(inst.id, scope)
    assert wi.list_instances(scope) == []


@pytest.mark.asyncio
async def test_instance_url_method_exists(monkeypatch) -> None:
    """Test that the per-instance URL method exists and works.

    The per-instance URL is the server route `/overlay/by-id/{id}`:
    known instances are served (200), unknown ids get a 404.
    """
    scope = _scope("layout-url-endpoint")
    _patch_scope(monkeypatch, scope)

    inst = wi.create_instance("chat", "Endpoint chat")

    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, pubsub=OverlayPubSub(), host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        known_url = f"{base}/overlay/by-id/{quote(inst.id, safe='')}"
        assert known_url.startswith("http://")
        assert "/overlay/by-id/" in known_url

        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # This should not raise a 404: the instance exists.
            async with session.get(known_url) as resp:
                body = await resp.text()
                assert resp.status == 200, f"unexpected status {resp.status}: {body[:300]}"

            # Unknown ids still 404 (the route itself is alive).
            async with session.get(f"{base}/overlay/by-id/does-not-exist") as resp:
                assert resp.status == 404
    finally:
        await srv.stop()

    # Clean up
    assert wi.delete_instance(inst.id, scope)
    assert wi.list_instances(scope) == []
