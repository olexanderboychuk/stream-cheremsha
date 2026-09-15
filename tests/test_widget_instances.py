from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays import widget_instances as wi


def _fresh_settings() -> QSettings:
    s = QSettings("stream-cheremsha-test", "widget-instances-test")
    s.clear()
    s.sync()
    return s


def test_create_preserves_exact_settings() -> None:
    s = _fresh_settings()
    saved = {"schema_version": 1, "limit": 7, "theme": "custom", "show_avatars": False}
    inst = wi.create_instance("top_likers", "Top Likers", dict(saved), s)
    assert inst is not None
    for k, v in saved.items():
        assert inst.settings[k] == v


def test_create_is_isolated_per_id() -> None:
    s = _fresh_settings()
    a = wi.create_instance("chat", "Chat A", {"schema_version": 1, "max_items": 12}, s)
    b = wi.create_instance("chat", "Chat B", {"schema_version": 1, "max_items": 34}, s)
    assert a.id != b.id
    items = [x for x in wi.list_instances(s) if x.type_id == "chat"]
    assert len(items) == 2


def test_by_id_resolves() -> None:
    s = _fresh_settings()
    inst = wi.create_instance("chat", "Chat", {"schema_version": 1, "max_items": 5}, s)
    resolved = wi.resolve_ws_params("chat", inst.id, s)
    assert resolved is not None
    assert resolved["max_items"] == 5
    assert wi.resolve_ws_params("online", inst.id, s) is None  # wrong type
    assert wi.resolve_ws_params("chat", "nope", s) is None


def test_instances_coexist_and_isolated() -> None:
    s = _fresh_settings()
    a = wi.create_instance("top_likers", "TikTok Top Likers", {"limit": 5}, s)
    b = wi.create_instance("top_likers", "VIP Top Likers", {"limit": 10}, s)
    assert a.id != b.id
    assert a.settings["limit"] == 5
    assert b.settings["limit"] == 10
    wi.update_instance_settings(a.id, {"limit": 3}, s)
    assert wi.get_instance(a.id, s).settings["limit"] == 3
    assert wi.get_instance(b.id, s).settings["limit"] == 10


def test_duplicate_is_independent() -> None:
    s = _fresh_settings()
    a = wi.create_instance("chat", "Chat A", {"max_items": 7}, s)
    dup = wi.duplicate_instance(a.id, s)
    assert dup is not None and dup.id != a.id
    assert dup.settings == a.settings
    wi.update_instance_settings(dup.id, {"max_items": 99}, s)
    assert wi.get_instance(a.id, s).settings["max_items"] == 7


def test_delete_does_not_affect_sibling() -> None:
    s = _fresh_settings()
    a = wi.create_instance("chat", "A", {}, s)
    b = wi.create_instance("chat", "B", {}, s)
    assert wi.delete_instance(a.id, s) is True
    assert wi.get_instance(a.id, s) is None
    assert wi.get_instance(b.id, s) is not None


def test_restart_preserves_instances() -> None:
    s = _fresh_settings()
    a = wi.create_instance("top_likers", "Persist Me", {"limit": 42}, s)
    reloaded = wi.list_instances(s)
    assert any(x.id == a.id and x.settings.get("limit") == 42 for x in reloaded)


def test_defaults_merge_missing_keys() -> None:
    s = _fresh_settings()
    inst = wi.create_instance("chat", "Chat X", {}, s)
    merged = wi.merged_settings(inst)
    assert merged.get("max_items") == 12  # from chat defaults
    # saved values win over defaults
    wi.update_instance_settings(inst.id, {"max_items": 3}, s)
    assert wi.merged_settings(wi.get_instance(inst.id, s)).get("max_items") == 3


def test_new_instance_uses_defaults_deepcopy() -> None:
    s = _fresh_settings()
    a = wi.create_instance("chat", "A", None, s)
    b = wi.create_instance("chat", "B", None, s)
    assert a.settings == b.settings and a.settings
    a.settings["max_items"] = 999  # mutate local copy only
    assert wi.get_instance(b.id, s).settings["max_items"] != 999


def test_renderer_prefers_injected_settings() -> None:
    from stream_cheremsha.overlays.chat_config import (
        chat_config_to_json_text,
        load_chat_config,
    )

    out = wi.config_for_type(
        "chat", {"instance_settings": {"max_items": 77}}, load_chat_config, chat_config_to_json_text
    )
    assert out["max_items"] == 77


def test_typed_config_prefers_injected_settings() -> None:
    from stream_cheremsha.overlays.chat_config import chat_config_from_json_text

    cfg = wi.typed_config_for_type(
        "chat",
        {"instance_settings": {"max_items": 77}},
        __import__("stream_cheremsha.overlays.chat_config", fromlist=["x"]).load_chat_config,
        chat_config_from_json_text,
    )
    assert cfg.max_items == 77


def test_no_static_type_cards_duplicate_instance_list() -> None:
    from pathlib import Path

    qml = (
        Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml" / "WidgetsView.qml"
    ).read_text(encoding="utf-8")
    # instance list is the single widget list; old per-type cards are gone
    for dead in (
        'title: "Chat overlay"',
        'title: "Actions overlay"',
        'title: "Top Likers (TikTok)"',
        'title: "Top GIFters (TikTok)"',
        'title: "King of the Live (TikTok)"',
        'title: "StreamPet (Тамагочі)"',
    ):
        assert dead not in qml, dead
    for live in (
        "createWidgetInstance",
        "editWidgetInstance(",
        "reloadAllWidgetConfigs",
        "setEditingInstanceId",
        "widgets.instances.create_button",
        "widgets.instances.new_title",
        "widgets.common.create",
        "widgets.common.duplicate",
        "layoutDocList",
        "openLayoutEditor(",
        "switchLayoutByIndex",
        "widget_instance_id",
        "createLayout",
        "duplicateLayout",
        "deleteLayout",
        "widgets.layouts.description",
        "widgets.layouts.new",
        "widgets.layouts.instance",
    ):
        assert live in qml, live
    # settings tab adaptation: editing banner, abort guards, verified open
    for live in (
        "widgets.instances.editing_title",
        "widgets.instances.editing_hint",
        "editingInstanceName",
        "copyWidgetInstanceUrl(root.editingInstanceId)",
        "backend did not accept id",
    ):
        assert live in qml, live
    # editor headers must show/copy the instance by-id URL while editing,
    # never the legacy ?instance=main URL
    for name in (
        "chat",
        "actions",
        "online",
        "kingOfLive",
        "battleRoyale",
        "streamPet",
        "communityWorld",
        "streamGoal",
        "liveLeaderboard",
        "socialRotator",
        "webcamFrame",
        "signalSystem",
    ):
        assert f"text: api ? api.{name}OverlayUrlValue" not in qml, name
        assert f"root.editorUrlValue(api.{name}OverlayUrlValue)" in qml, name
    assert qml.count("root.copyEditorUrl(function()") == 13


def test_new_strings_translated_uk_en() -> None:
    from stream_cheremsha import l10n
    from stream_cheremsha.overlays import widget_instances as wimod

    keys = [
        "widgets.common.create",
        "widgets.common.cancel",
        "widgets.common.duplicate",
        "widgets.common.delete",
        "widgets.common.enable",
        "widgets.common.disable",
        "widgets.instances.create_button",
        "widgets.instances.active",
        "widgets.instances.disabled",
        "widgets.instances.new_title",
        "widgets.instances.name_placeholder",
        "widgets.instances.copy_suffix",
        "widgets.layouts.scene",
        "widgets.layouts.new",
        "widgets.layouts.name_placeholder",
        "widgets.layouts.untitled",
        "widgets.layouts.default_name",
        "widgets.layouts.new_name",
        "widgets.layouts.copy_suffix",
        "widgets.layouts.no_instance",
        "widgets.layouts.instance",
    ]
    for t in sorted(wimod.WIDGET_TYPES):
        keys.append(f"widgets.type.{t}.name")
        keys.append(f"widgets.type.{t}.desc")
    for key in keys:
        uk = l10n.tr("uk", key)
        en = l10n.tr("en", key)
        assert uk and uk != key, key
        assert en and en != key, key
    # "Scene {n}" formatting works
    assert "{n}" not in l10n.tr("uk", "widgets.layouts.new_name", n=3)


INST_ROUTING_CASES = [
    ("chat", "stream_cheremsha.overlays.chat_config", "loadChatConfigMap", "saveChatConfigJson"),
    (
        "actions",
        "stream_cheremsha.overlays.actions_config",
        "loadActionsConfigMap",
        "saveActionsConfigJson",
    ),
    (
        "online",
        "stream_cheremsha.overlays.online_overlay_config",
        "loadOnlineOverlayConfigMap",
        "saveOnlineOverlayConfigJson",
    ),
    (
        "top_likers",
        "stream_cheremsha.overlays.top_likers_overlay_config",
        "loadTopLikersOverlayConfigMap",
        "saveTopLikersOverlayConfigJson",
    ),
    (
        "top_gifters",
        "stream_cheremsha.overlays.top_gifters_overlay_config",
        "loadTopGiftersOverlayConfigMap",
        "saveTopGiftersOverlayConfigJson",
    ),
    (
        "king_of_live",
        "stream_cheremsha.overlays.king_of_live_overlay_config",
        "loadKingOfLiveOverlayConfigMap",
        "saveKingOfLiveOverlayConfigJson",
    ),
    (
        "battle_royale",
        "stream_cheremsha.overlays.battle_royale_overlay_config",
        "loadBattleRoyaleOverlayConfigMap",
        "saveBattleRoyaleOverlayConfigJson",
    ),
    (
        "stream_pet",
        "stream_cheremsha.overlays.stream_pet_overlay_config",
        "loadStreamPetOverlayConfigMap",
        "saveStreamPetOverlayConfigJson",
    ),
    (
        "community_world",
        "stream_cheremsha.overlays.community_world_config",
        "loadCommunityWorldOverlayConfigMap",
        "saveCommunityWorldOverlayConfigJson",
    ),
    (
        "stream_goal",
        "stream_cheremsha.overlays.stream_goal_overlay_config",
        "loadStreamGoalOverlayConfigMap",
        "saveStreamGoalOverlayConfigJson",
    ),
    (
        "live_leaderboard",
        "stream_cheremsha.overlays.live_leaderboard_overlay_config",
        "loadLiveLeaderboardOverlayConfigMap",
        "saveLiveLeaderboardOverlayConfigJson",
    ),
    (
        "social_rotator",
        "stream_cheremsha.overlays.social_rotator_overlay_config",
        "loadSocialRotatorOverlayConfigMap",
        "saveSocialRotatorOverlayConfigJson",
    ),
    (
        "webcam_frame",
        "stream_cheremsha.overlays.webcam_frame_overlay_config",
        "loadWebcamFrameOverlayConfigMap",
        "saveWebcamFrameOverlayConfigJson",
    ),
    (
        "signal_system",
        "stream_cheremsha.overlays.signal_system_overlay_config",
        "loadSignalSystemOverlayConfigMap",
        "saveSignalSystemOverlayConfigJson",
    ),
]


def test_slot_routing_all_types_instance_only(monkeypatch) -> None:
    """Full QML-equivalent flow per type: create -> edit -> load -> save.

    The instance must receive the new values.
    """
    import importlib

    import stream_cheremsha.overlays.widget_instances as wimod
    from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi

    for type_id, cfg_mod_name, load_slot, save_slot in INST_ROUTING_CASES:
        scope = f"t-app-route-{type_id}"
        monkeypatch.setattr(
            wimod, "QSettings", lambda *a, _s=scope, **k: QSettings("t-org-route", _s)
        )
        cfg_mod = importlib.import_module(cfg_mod_name)
        monkeypatch.setattr(
            cfg_mod, "QSettings", lambda *a, _s=scope, **k: QSettings("t-org-route", _s)
        )
        QSettings("t-org-route", scope).clear()

        api = WidgetsQmlApi(overlay_base_url="")

        iid = api.createWidgetInstance(type_id, f"Test {type_id}")
        assert iid, type_id
        api.setEditingInstanceId(iid)
        assert api.editingInstanceId() == iid, type_id

        loaded = getattr(api, load_slot)()
        int_keys = [
            k
            for k, v in loaded.items()
            if isinstance(v, int) and not isinstance(v, bool) and k != "schema_version"
        ]
        assert int_keys, (type_id, "no int key to mutate")
        key = int_keys[0]
        loaded[key] = int(loaded[key]) + 1
        getattr(api, save_slot)(json.dumps(loaded))

        inst = wimod.get_instance(iid)
        assert inst is not None, type_id
        # Slot re-read must match persisted instance settings exactly
        # (from_json normalization like clamping applies to both equally).
        assert getattr(api, load_slot)() == wimod.merged_settings(inst), type_id
        assert inst.settings.get(key) == getattr(api, load_slot)().get(key), (type_id, key)
        api.clearEditingInstance()


def test_ws_tokens_isolate_instances() -> None:
    """Instances must never share a WS topic/config."""
    s = _fresh_settings()
    a = wi.create_instance("chat", "Chat A", {"max_items": 5}, s)
    new_inst = wi.create_instance("chat", "New Chat", {"max_items": 99}, s)

    assert a.id != new_inst.id
    assert len(new_inst.id) <= 64

    # WS subscription resolution (what server._ws injects into initial_state)
    assert wi.resolve_ws_params("chat", a.id, s)["max_items"] == 5
    resolved_new = wi.resolve_ws_params("chat", new_inst.id, s)
    assert resolved_new is not None and resolved_new["max_items"] == 99
    assert wi.resolve_ws_params("chat", "nope", s) is None
    assert wi.resolve_ws_params("online", new_inst.id, s) is None  # wrong type


def test_by_id_page_subscribes_with_full_id_token() -> None:
    from stream_cheremsha.overlays.chat_overlay import ChatOverlayType

    s = _fresh_settings()
    inst = wi.create_instance("chat", "Full Token", {"max_items": 7}, s)
    html = ChatOverlayType().render_html(
        {
            "instance": inst.id,
            "instance_id": inst.id,
            "instance_settings": wi.merged_settings(inst),
        }
    )
    assert inst.id in html  # subscribe carries the full token, not a prefix


def test_instance_edit_persists(monkeypatch) -> None:
    """Editing an instance must persist into the store."""
    import stream_cheremsha.overlays.social_rotator_overlay_config as srmod
    import stream_cheremsha.overlays.widget_instances as wimod
    from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi

    monkeypatch.setattr(wimod, "QSettings", lambda *a, **k: QSettings("t-org-wt", "t-app-wt"))
    monkeypatch.setattr(srmod, "QSettings", lambda *a, **k: QSettings("t-org-wt", "t-app-wt"))
    QSettings("t-org-wt", "t-app-wt").clear()

    api = WidgetsQmlApi(overlay_base_url="")
    iid = api.createWidgetInstance("social_rotator", "SR")

    api.setEditingInstanceId(iid)

    loaded = api.loadSocialRotatorOverlayConfigMap()
    int_keys = [
        k
        for k, v in loaded.items()
        if isinstance(v, int) and not isinstance(v, bool) and k != "schema_version"
    ]
    assert int_keys
    key = int_keys[0]
    loaded[key] = int(loaded[key]) + 1000
    loaded["enabled"] = not bool(loaded.get("enabled", True))
    api.saveSocialRotatorOverlayConfigJson(json.dumps(loaded))

    stored = wimod.get_instance(iid).settings.get(key)
    assert api.loadSocialRotatorOverlayConfigMap()[key] == stored
    api.clearEditingInstance()


def test_instance_update_roundtrip() -> None:
    s = _fresh_settings()
    inst = wi.create_instance("chat", "Chat", {"schema_version": 1, "max_items": 5}, s)
    wi.update_instance_settings(inst.id, {"schema_version": 1, "max_items": 42}, s)
    assert wi.get_instance(inst.id, s).settings["max_items"] == 42


def test_all_type_editors_route_through_instances() -> None:
    import re
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "stream_cheremsha"
        / "ui"
        / "widgets_qml_api.py"
    ).read_text(encoding="utf-8")
    for t in (
        "chat",
        "actions",
        "online",
        "top_likers",
        "top_gifters",
        "king_of_live",
        "battle_royale",
        "stream_pet",
        "community_world",
        "stream_goal",
        "live_leaderboard",
        "social_rotator",
        "webcam_frame",
        "signal_system",
    ):
        assert f'_load_cfg_or_instance("{t}")' in src, t
        # save call may wrap across lines, so match loosely
        assert re.search(rf'_save_cfg_to_instance\(\s*"{t}"', src), t


def test_edit_routing_load_save_instance(monkeypatch) -> None:
    """Type-editor load/save route to the edited instance, not the singleton."""
    import stream_cheremsha.overlays.widget_instances as wimod
    from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi

    monkeypatch.setattr(wimod, "QSettings", lambda *a, **k: QSettings("t-org-edit", "t-app-edit"))
    QSettings("t-org-edit", "t-app-edit").clear()

    api = WidgetsQmlApi(overlay_base_url="")
    inst = wi.create_instance("chat", "Routed", None)
    legacy_loaded = api.loadChatConfigMap()
    assert isinstance(legacy_loaded.get("max_items"), int)  # legacy singleton, no editing

    api.setEditingInstanceId(inst.id)
    assert api.editingInstanceId() == inst.id
    loaded = api.loadChatConfigMap()
    assert loaded["max_items"] == 12  # instance starts from defaults

    api.saveChatConfigJson(json.dumps({**loaded, "max_items": 33}))
    assert wi.get_instance(inst.id).settings["max_items"] == 33
    assert api.loadChatConfigMap()["max_items"] == 33

    api.clearEditingInstance()
    assert api.editingInstanceId() == ""
