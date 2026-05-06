from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from obsws_python.error import OBSSDKRequestError

from stream_cheremsha.obs_ws.control import (
    ObsControlError,
    obs_list_canvases,
    obs_list_scene_sources,
    obs_list_scenes,
    obs_test_connection,
    run_obs_scene_action,
)


def test_run_obs_program_scene_calls_set_current() -> None:
    mock_cl = MagicMock()
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        run_obs_scene_action("127.0.0.1", 4455, "", mode="program_scene", scene_name="Game")
    mock_cl.set_current_program_scene.assert_called_once_with("Game")
    mock_cl.disconnect.assert_called_once()


def test_run_obs_source_visible_uses_send() -> None:
    mock_cl = MagicMock()
    mock_cl.send.side_effect = [
        {"sceneItemId": 42},
        None,
    ]
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        run_obs_scene_action(
            "127.0.0.1",
            4455,
            "pw",
            mode="source_visible",
            scene_name="Main",
            source_name="Webcam",
            visible=False,
        )
    mock_cl.send.assert_any_call(
        "GetSceneItemId",
        {"sceneName": "Main", "sourceName": "Webcam"},
        raw=True,
    )
    mock_cl.send.assert_any_call(
        "SetSceneItemEnabled",
        {"sceneName": "Main", "sceneItemId": 42, "sceneItemEnabled": False},
        raw=True,
    )
    mock_cl.disconnect.assert_called_once()


def test_run_obs_source_visible_passes_canvas_uuid() -> None:
    mock_cl = MagicMock()
    mock_cl.send.side_effect = [{"sceneItemId": 7}, None]
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        run_obs_scene_action(
            "127.0.0.1",
            4455,
            "",
            mode="source_visible",
            scene_name="SceneA",
            source_name="Alert",
            visible=True,
            canvas_uuid="abc-def",
        )
    mock_cl.send.assert_any_call(
        "GetSceneItemId",
        {"sceneName": "SceneA", "sourceName": "Alert", "canvasUuid": "abc-def"},
        raw=True,
    )
    mock_cl.send.assert_any_call(
        "SetSceneItemEnabled",
        {
            "sceneName": "SceneA",
            "sceneItemId": 7,
            "sceneItemEnabled": True,
            "canvasUuid": "abc-def",
        },
        raw=True,
    )


def test_run_obs_rejects_empty_scene() -> None:
    with pytest.raises(ObsControlError, match="scene_name"):
        run_obs_scene_action("127.0.0.1", 4455, "", mode="program_scene", scene_name="  ")


def test_run_obs_source_requires_source_name() -> None:
    mock_cl = MagicMock()
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        with pytest.raises(ObsControlError, match="source_name"):
            run_obs_scene_action(
                "127.0.0.1",
                4455,
                "",
                mode="source_visible",
                scene_name="Main",
                source_name="",
                visible=True,
            )
    mock_cl.disconnect.assert_called_once()


def test_obs_test_connection_returns_version() -> None:
    mock_cl = MagicMock()
    ver = MagicMock()
    ver.obs_version = "31.0.0"
    mock_cl.get_version.return_value = ver
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        out = obs_test_connection("localhost", 4455, "x")
    assert out == "31.0.0"
    mock_cl.disconnect.assert_called_once()


def test_obs_list_scenes_calls_get_scene_list() -> None:
    mock_cl = MagicMock()
    mock_cl.send.return_value = {"scenes": [{"sceneName": "A"}, {"sceneName": "B"}]}
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        rows, err = obs_list_scenes("127.0.0.1", 4455, "pw", canvas_uuid="")
    assert err is None
    assert rows == [{"name": "A", "value": "A"}, {"name": "B", "value": "B"}]
    mock_cl.send.assert_called_once_with("GetSceneList", {}, raw=True)


def test_obs_list_scenes_with_canvas_uuid() -> None:
    mock_cl = MagicMock()
    mock_cl.send.return_value = {"scenes": [{"sceneName": "X"}]}
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        rows, err = obs_list_scenes("127.0.0.1", 4455, "", canvas_uuid="uuid-1")
    assert err is None
    assert rows == [{"name": "X", "value": "X"}]
    mock_cl.send.assert_called_once_with("GetSceneList", {"canvasUuid": "uuid-1"}, raw=True)


def test_obs_list_scene_sources() -> None:
    mock_cl = MagicMock()
    mock_cl.send.return_value = {
        "sceneItems": [
            {"sourceName": "Cam"},
            {"sourceName": "Overlay"},
        ],
    }
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        rows, err = obs_list_scene_sources(
            "127.0.0.1",
            4455,
            "",
            canvas_uuid="c1",
            scene_name="Main",
        )
    assert err is None
    assert rows == [{"name": "Cam", "value": "Cam"}, {"name": "Overlay", "value": "Overlay"}]
    mock_cl.send.assert_called_once_with(
        "GetSceneItemList",
        {"sceneName": "Main", "canvasUuid": "c1"},
        raw=True,
    )


def test_obs_list_scene_sources_requires_scene() -> None:
    rows, err = obs_list_scene_sources("127.0.0.1", 4455, "", scene_name="  ")
    assert rows == []
    assert err == "scene_name is required"


def test_obs_list_canvases_from_get_canvas_list() -> None:
    mock_cl = MagicMock()
    mock_cl.send.return_value = {
        "canvases": [
            {"canvasUuid": "u1", "canvasName": "Main"},
            {"canvasUuid": "u2", "canvasName": "Vertical"},
        ],
    }
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        rows, err = obs_list_canvases("127.0.0.1", 4455, "")
    assert err is None
    assert rows == [{"name": "Main", "value": "u1"}, {"name": "Vertical", "value": "u2"}]


def test_obs_list_canvases_fallback_when_rpc_missing() -> None:
    mock_cl = MagicMock()
    mock_cl.send.side_effect = OBSSDKRequestError("GetCanvasList", 500, "nope")
    with patch("stream_cheremsha.obs_ws.control.ReqClient", return_value=mock_cl):
        rows, err = obs_list_canvases("127.0.0.1", 4455, "")
    assert err is None
    assert rows == [{"name": "", "value": ""}]
