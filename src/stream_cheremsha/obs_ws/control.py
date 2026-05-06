"""Synchronous OBS WebSocket helpers (run from a worker thread via asyncio.to_thread)."""

from __future__ import annotations

from typing import Any

from obsws_python import ReqClient
from obsws_python.error import OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError


class ObsControlError(Exception):
    """User-facing OBS WebSocket failure."""


def _client(host: str, port: int, password: str, *, timeout: float = 5.0) -> ReqClient:
    h = (host or "").strip() or "127.0.0.1"
    try:
        p = int(port)
    except (TypeError, ValueError) as e:
        raise ObsControlError("WebSocket port must be a number") from e
    if p < 1 or p > 65535:
        raise ObsControlError("WebSocket port must be between 1 and 65535")
    return ReqClient(host=h, port=p, password=password or "", timeout=timeout)


def _disconnect_safe(cl: ReqClient) -> None:
    try:
        cl.disconnect()
    except OBSSDKError:
        pass


def _send_raw(cl: ReqClient, request_type: str, data: dict[str, Any] | None) -> dict[str, Any]:
    raw = cl.send(request_type, data or {}, raw=True)
    if not isinstance(raw, dict):
        return {}
    return raw


def _pick_nonempty_str(d: dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s
    return ""


def obs_test_connection(host: str, port: int, password: str) -> str:
    """Connect, read OBS version, disconnect. Returns a short version string."""
    cl = _client(host, port, password, timeout=5.0)
    try:
        resp = cl.get_version()
        return str(getattr(resp, "obs_version", "") or getattr(resp, "obsVersion", "") or "?")
    except (OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError) as e:
        raise ObsControlError(str(e)) from e
    finally:
        _disconnect_safe(cl)


def obs_list_canvases(host: str, port: int, password: str) -> tuple[list[dict[str, str]], str | None]:
    """Return (rows, error). Each row: ``name`` (label), ``value`` (canvasUuid, empty = main).

    Uses ``GetCanvasList`` when available (OBS 31+ / obs-websocket 5.7+); otherwise one default row.
    """
    cl = _client(host, port, password, timeout=8.0)
    try:
        try:
            data = _send_raw(cl, "GetCanvasList", {})
            rows: list[dict[str, str]] = []
            for it in data.get("canvases") or []:
                if not isinstance(it, dict):
                    continue
                u = _pick_nonempty_str(it, "canvasUuid", "canvas_uuid")
                n = _pick_nonempty_str(it, "canvasName", "canvas_name", "name")
                rows.append({"name": n, "value": u})
            if rows:
                return rows, None
        except OBSSDKRequestError:
            pass
        return [{"name": "", "value": ""}], None
    except (OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError) as e:
        return [], str(e)
    finally:
        _disconnect_safe(cl)


def obs_list_scenes(host: str, port: int, password: str, canvas_uuid: str = "") -> tuple[list[dict[str, str]], str | None]:
    """Return scene rows: ``name`` and ``value`` both set to scene name (protocol ``sceneName``)."""
    cl = _client(host, port, password, timeout=8.0)
    try:
        req: dict[str, Any] = {}
        cu = (canvas_uuid or "").strip()
        if cu:
            req["canvasUuid"] = cu
        data = _send_raw(cl, "GetSceneList", req)
        out: list[dict[str, str]] = []
        for it in data.get("scenes") or []:
            if not isinstance(it, dict):
                continue
            name = _pick_nonempty_str(it, "sceneName", "scene_name")
            if not name:
                continue
            out.append({"name": name, "value": name})
        return out, None
    except (OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError) as e:
        return [], str(e)
    finally:
        _disconnect_safe(cl)


def obs_list_scene_sources(
    host: str,
    port: int,
    password: str,
    *,
    canvas_uuid: str = "",
    scene_name: str,
) -> tuple[list[dict[str, str]], str | None]:
    """Return source names for scene items (``GetSceneItemList``)."""
    scene = (scene_name or "").strip()
    if not scene:
        return [], "scene_name is required"

    cl = _client(host, port, password, timeout=8.0)
    try:
        req: dict[str, Any] = {"sceneName": scene}
        cu = (canvas_uuid or "").strip()
        if cu:
            req["canvasUuid"] = cu
        data = _send_raw(cl, "GetSceneItemList", req)
        seen: set[str] = set()
        out: list[dict[str, str]] = []
        for it in data.get("sceneItems") or []:
            if not isinstance(it, dict):
                continue
            src = _pick_nonempty_str(it, "sourceName", "source_name", "inputName", "input_name")
            if not src or src in seen:
                continue
            seen.add(src)
            out.append({"name": src, "value": src})
        return out, None
    except (OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError) as e:
        return [], str(e)
    finally:
        _disconnect_safe(cl)


def run_obs_scene_action(
    host: str,
    port: int,
    password: str,
    *,
    mode: str,
    scene_name: str,
    source_name: str = "",
    visible: bool = True,
    canvas_uuid: str = "",
) -> None:
    """Perform one OBS action (program scene switch or scene-item visibility).

    ``mode``:
    - ``program_scene`` — SetCurrentProgramScene (live program output).
    - ``source_visible`` — show/hide a source inside a scene (eye icon in OBS).

    Optional ``canvas_uuid`` is sent on item requests per protocol (multi-canvas).

    See OBS WebSocket protocol: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
    """
    scene = (scene_name or "").strip()
    if not scene:
        raise ObsControlError("scene_name is required")

    m = (mode or "").strip().lower().replace("-", "_")
    cu = (canvas_uuid or "").strip()
    cl = _client(host, port, password, timeout=8.0)
    try:
        if m in ("program_scene", "program", "switch_program_scene"):
            cl.set_current_program_scene(scene)
            return
        if m in ("source_visible", "scene_item", "item_visible"):
            src = (source_name or "").strip()
            if not src:
                raise ObsControlError("source_name is required for source visibility")
            gid_payload: dict[str, Any] = {"sceneName": scene, "sourceName": src}
            if cu:
                gid_payload["canvasUuid"] = cu
            raw = cl.send("GetSceneItemId", gid_payload, raw=True)
            if not isinstance(raw, dict):
                raw = {}
            item_id = int(raw.get("sceneItemId") or raw.get("scene_item_id") or 0)
            if item_id <= 0:
                raise ObsControlError(f"Source {src!r} not found in scene {scene!r}")
            en_payload: dict[str, Any] = {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemEnabled": bool(visible),
            }
            if cu:
                en_payload["canvasUuid"] = cu
            cl.send("SetSceneItemEnabled", en_payload, raw=True)
            return
        raise ObsControlError(f"Unknown OBS mode: {mode!r}")
    except ObsControlError:
        raise
    except (OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError) as e:
        raise ObsControlError(str(e)) from e
    finally:
        _disconnect_safe(cl)
