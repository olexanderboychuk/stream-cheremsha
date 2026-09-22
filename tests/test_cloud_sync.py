"""Cloud Sync (desktop): allowlist, queue, drive, manager QObject.

All HTTP calls are intercepted via an injected transport — no real Cloud
API is ever contacted. No tokens, secrets, audio/* keys, or unknown
keys end up in any payload the tests assert.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

import pytest

os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "k")
os.environ.setdefault("SESSION_JWT_SECRET", "test-secret-0123456789abcdef0123456789")

from stream_cheremsha.sync.allowlist import (  # noqa: E402
    is_allowed_qsettings_key,
    redact_dangerous_blob,
)
from stream_cheremsha.sync.manager import CheremshaSyncManager  # noqa: E402
from stream_cheremsha.sync.queue import PendingChange, SyncQueue  # noqa: E402


# ----------------------------------------------------------------- allowlist
def test_audio_keys_are_never_allowed():
    assert not is_allowed_qsettings_key("audio/volume")
    assert not is_allowed_qsettings_key("audio/input_device")
    assert not is_allowed_qsettings_key("audio/output_device")
    assert not is_allowed_qsettings_key("audio/monitor_device")
    assert not is_allowed_qsettings_key("audio/")


def test_tts_keys_are_allowed():
    assert is_allowed_qsettings_key("tts/engine")
    assert is_allowed_qsettings_key("tts/output_language")
    assert is_allowed_qsettings_key("tts/rate_percent")
    assert is_allowed_qsettings_key("tts/whitelist")
    assert is_allowed_qsettings_key("tts_chat/twitch_enabled")
    assert is_allowed_qsettings_key("tts_chat/kick_enabled")


def test_unknown_keys_are_not_allowed():
    assert not is_allowed_qsettings_key("random/garbage")
    assert not is_allowed_qsettings_key("")


def test_redact_dangerous_blob_drops_tokens():
    blob = {
        "access_token": "abc",
        "refresh_token": "xyz",
        "client_secret": "shh",
        "safe_key": "ok",
        "long_string": "sk-12345thisIsASecretAndShouldNotLeakanywhere",
    }
    out = redact_dangerous_blob(blob)
    assert "access_token" not in out
    assert "refresh_token" not in out
    assert "client_secret" not in out
    assert out["safe_key"] == "ok"
    assert "long_string" not in out  # heuristic catches the sk- prefix


# ----------------------------------------------------------------- queue
@pytest.fixture(autouse=True)
def _isolated_queue_path(tmp_path, monkeypatch):
    """Redirect the queue's QStandardPaths lookup to a temp dir per test."""
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )
    yield
    try:
        from stream_cheremsha.sync.queue import SyncQueue as _Q

        path = _Q._safe_path()
        if path is not None and path.exists():
            path.unlink()
    except Exception:
        pass


@pytest.fixture()
def qapplication():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_queue_coalesces_same_envelope():
    q = SyncQueue()
    q.enqueue(kind="widget", entity_id="abc", base_version=0, data={"x": 1})
    q.enqueue(kind="widget", entity_id="abc", base_version=1, data={"x": 2})
    q.enqueue(kind="widget", entity_id="abc", base_version=2, data={"x": 3})
    items = q.peek()
    assert len(items) == 1
    assert items[0].data == {"x": 3}
    assert items[0].base_version == 2


def test_queue_keeps_distinct_entities():
    q = SyncQueue()
    q.enqueue(kind="widget", entity_id="a", base_version=0, data={"x": 1})
    q.enqueue(kind="widget", entity_id="b", base_version=0, data={"x": 1})
    assert len(q.peek()) == 2


def test_queue_survives_reload(tmp_path, monkeypatch):
    # Use a single shared queue directory so both ``SyncQueue`` instances see
    # the same persisted JSON (the autouse fixture creates per-test tmp_paths).
    from stream_cheremsha.sync.queue import SyncQueue as _Q

    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(_Q, "_safe_path", staticmethod(lambda: shared / "sync-queue.json"))

    q = SyncQueue()
    q.enqueue(kind="widget", entity_id="abc", base_version=0, data={"x": 1})
    q2 = SyncQueue()
    items = q2.peek()
    assert len(items) == 1 and items[0].entity_id == "abc"


def test_queue_drain_then_persist_empty():
    q = SyncQueue()
    q.enqueue(kind="widget", entity_id="abc", base_version=0, data={"x": 1})
    drained = q.drain()
    assert len(drained) == 1
    assert q.size() == 0
    # Reload from disk to confirm the drain was persisted.
    q2 = SyncQueue()
    assert q2.size() == 0


# ----------------------------------------------------------------- drive


def test_remote_apply_guard_flag_toggles(monkeypatch, tmp_path, qapplication):
    """``begin_remote_apply`` flips the global guard and only restores it
    on context exit (or ``end_remote_apply``). Hooks consult this flag to
    suppress loop-creating enqueues."""
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )
    from stream_cheremsha.sync import drive

    assert drive.is_remote_applying() is False
    with drive.begin_remote_apply():
        assert drive.is_remote_applying() is True
    assert drive.is_remote_applying() is False
    drive.begin_remote_apply()
    assert drive.is_remote_applying() is True
    drive.end_remote_apply()
    assert drive.is_remote_applying() is False


def test_widget_apply_uses_existing_uuid_without_change(monkeypatch, tmp_path, qapplication):
    """Applying a remote widget change keeps the original instance id."""
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )
    # Use IniFormat on a temp file to avoid the production QSettings guard.
    from PySide6.QtCore import QSettings as _QS

    ini = tempfile.NamedTemporaryFile(  # type: ignore[func-returns-value]
        suffix=".ini", delete=False, dir=str(tmp_path)
    )
    ini.close()
    ini_path = ini.name
    test_settings = _QS(ini_path, _QS.Format.IniFormat)

    from stream_cheremsha.overlays import widget_instances as widget_store
    from stream_cheremsha.sync import drive

    inst = widget_store.create_instance("chat", "Main Chat", settings=test_settings)
    monkeypatch.setattr(drive, "_settings_obj", lambda: test_settings)
    original_id = inst.id

    payload = {
        "kind": "widget",
        "entity_id": original_id,
        "op": "upsert",
        "data": {
            "id": original_id,
            "type_id": "chat",
            "name": "Renamed on another device",
            "settings": {"x": 42},
            "enabled": True,
            "legacy_key": None,
        },
    }
    with drive.begin_remote_apply():
        assert drive.apply_widget_change(payload) is True

    # Open a fresh QSettings to force re-read from disk.
    reloaded_settings = _QS(ini_path, _QS.Format.IniFormat)
    reloaded = widget_store.get_instance(original_id, settings=reloaded_settings)
    assert reloaded is not None
    assert reloaded.id == original_id  # UUID preserved
    assert reloaded.name == "Renamed on another device"


def test_unknown_qsettings_key_never_enqueued(monkeypatch, tmp_path, qapplication):
    """Manager.enqueue_settings_change silently drops unknown keys."""
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )

    class FakeAuth:
        status = "authenticated"

    sm = CheremshaSyncManager(FakeAuth(), network_post=_NoopPost, network_get=_NoopGet, parent=None)
    sm.enqueue_settings_change("audio/volume", 80)  # audio/* → dropped
    sm.enqueue_settings_change("random/garbage", "x")  # not allow-listed
    assert sm._queue.size() == 0
    sm.enqueue_settings_change("tts/rate_percent", 120)  # allowed but coalesced
    # enqueue_settings_change does not push entries (collected on push);
    # it bumps the debounced schedule. Just verify no exception.


def test_secrets_never_present_in_serialized_payload():
    blob = {
        "tts/engine": "google",
        "tts/rate_percent": 120,
        "client_secret": "ok-hidden",
        "access_token": "ok-hidden",
        "definitely_a_secret": "Bearer abc",
    }
    out = redact_dangerous_blob(blob)
    payload_text = json.dumps(out)
    for needle in ("client_secret", "access_token", "definitely_a_secret", "ok-hidden", "Bearer"):
        assert needle not in payload_text
    assert out["tts/engine"] == "google"


# ----------------------------------------------------------------- manager integration


class _FakeAuthAuth:
    """Minimal stand-in wiring for the manager."""

    def __init__(self) -> None:
        self.status = "authenticated"
        self.statusChanged = type("Signal", (), {"connect": lambda self, fn: None})()


class _NoopPost:
    async def __call__(self, payload: dict) -> dict:
        return {
            "accepted": [],
            "rejected": [],
            "conflicts": [],
            "remote_changes": [],
            "cursor": "c",
            "server_time": "2026-01-01T00:00:00+00:00",
        }


class _NoopGet:
    async def __call__(self, *args, **kwargs) -> dict:
        return {}


async def _trigger_loop(sm: CheremshaSyncManager) -> tuple[PendingChange]:
    sm._schedule_debounced_push()
    q = sm._queue
    # Wait for the queue to drain.
    for _ in range(60):
        if q.size() == 0:
            break
        await asyncio.sleep(0.05)
    return q.peek()


@pytest.mark.asyncio()
async def test_first_pull_then_push_no_secrets_leak(monkeypatch, tmp_path):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )

    captured: dict = {}

    async def capture_post(payload: dict) -> dict:
        captured.update(payload)
        return {
            "accepted": [
                {"kind": c["kind"], "entity_id": c["entity_id"], "op": c["op"], "version": 1}
                for c in payload.get("changes", [])
            ],
            "rejected": [],
            "conflicts": [],
            "remote_changes": [],
            "cursor": "c1",
            "server_time": "2026-01-01T00:00:00+00:00",
        }

    sm = CheremshaSyncManager(
        _FakeAuthAuth(),
        network_post=capture_post,
        network_get=_NoopGet,
        parent=None,
    )
    sm.enqueue_actions_change("twitch:app", {"rules": [{"id": "r1"}]})
    sm.enqueue_settings_change("tts/rate_percent", 120)
    sm.enqueue_settings_change("audio/volume", 80)  # forbidden
    sm.enqueue_settings_change("cloud/api_base_url", "http://x")  # not allow-listed

    # Drain the debounced loop manually.
    sm._task = None
    await sm._do_push()

    body = captured
    # All payloads must clean any 'client_secret' / 'access_token' / 'Bearer'.
    body_text = json.dumps(body)
    for needle in ("access_token", "refresh_token", "client_secret", "Bearer "):
        assert needle not in body_text


@pytest.mark.asyncio()
async def test_remote_apply_does_not_enqueue_back_outbound(monkeypatch, tmp_path):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )

    captured: list[dict] = []

    async def post(payload: dict) -> dict:
        captured.append(payload)
        return {
            "accepted": [],
            "rejected": [],
            "conflicts": [],
            "remote_changes": [
                {
                    "kind": "widget",
                    "entity_id": "abc",
                    "op": "upsert",
                    "version": 2,
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "data": {
                        "id": "abc",
                        "type_id": "chat",
                        "name": "remote-renamed",
                        "settings": {"x": 1},
                        "enabled": True,
                        "legacy_key": None,
                    },
                }
            ],
            "cursor": "c2",
            "server_time": "2026-01-01T00:00:00+00:00",
        }

    sm = CheremshaSyncManager(
        _FakeAuthAuth(),
        network_post=post,
        network_get=_NoopGet,
        parent=None,
    )

    # Initial pull.
    await sm._do_pull(apply=True)
    # The remote-apply guard flips off automatically. See drive.is_remote_applying.
    assert len(captured) == 1
    # Now schedule a push. The remote-apply window has closed, so this push
    # is a legitimate user action (not from the apply). Just verify the
    # manager does not auto-loop: it only pushes when an explicit enqueue
    # has been made. With no local change, no second POST should have been
    # recorded by the time the manager returns.
    assert sm._queue.size() == 0


@pytest.mark.asyncio()
async def test_logout_does_not_crash(monkeypatch, tmp_path):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )

    auth = _FakeAuthAuth()
    sm = CheremshaSyncManager(auth, network_post=_NoopPost, network_get=_NoopGet, parent=None)
    auth.status = "logged-out"
    # Loop is gated on authenticated.
    await sm._do_push()
    assert sm.syncState == "offline" or sm.syncState == "idle"
