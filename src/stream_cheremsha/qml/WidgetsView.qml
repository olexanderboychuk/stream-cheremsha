import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

import components

Item {
    id: root
    implicitWidth: 720
    implicitHeight: 520

    // Micro entrance transition, retriggered by MainWindow (enterPulse toggle)
    // on every cached navigation. GPU-cheap root opacity only, 120ms.
    property bool enterPulse: false
    onEnterPulseChanged: {
        enterFade.restart();
        // The QQuickWidget is cached. Rehydrate the Layout collection when
        // the cached Layouts page is shown again instead of recreating it.
        if (root.layoutsOnly)
            root.showLayoutList();
    }
    NumberAnimation {
        id: enterFade
        target: root
        property: "opacity"
        from: 0.97
        to: 1.0
        duration: 120
        easing.type: Easing.OutCubic
    }

    readonly property color base: "#090a0d"
    readonly property color cardBase: "#10141a"
    readonly property color cardEdge: "#242b36"
    readonly property color cardEdgeStrong: "#2d3748"
    readonly property color ink: "#e8eaed"
    readonly property color inkSecondary: "#b8c0cc"
    readonly property color inkMuted: "#8b95a5"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0a0d12"
    readonly property color accent: "#14b8a6"
    readonly property color accentHover: "#0d9488"
    readonly property color accentPress: "#0f766e"
    readonly property color accentSoft: "#14b8a620"
    readonly property color selection: "#14b8a640"
    readonly property color overlayBg: "#07090c"
    readonly property color canvasGrid: "#1a2332"
    readonly property color canvasBorder: "#2d3748"

    readonly property int spacingXS: 4
    readonly property int spacingSM: 8
    readonly property int spacingMD: 12
    readonly property int spacingLG: 16
    readonly property int spacingXL: 24
    readonly property int radiusSM: 6
    readonly property int radiusMD: 8
    readonly property int radiusLG: 12
    readonly property int radiusXL: 14
    property var layoutDoc: ({})
    property int selectedLayoutWidget: -1
    property int layoutRevision: 0
    property int canvasPresetIndex: 0

    property string _editorState: "idle" // "idle" | "moving" | "resizing"
    property int _dragWidgetIndex: -1
    property real _dragWidgetStartX: 0
    property real _dragWidgetStartY: 0
    property string _dragLibType: ""
    property string _dragLibLabel: ""
    property var _undoStack: []
    property var _redoStack: []
    property bool _inspectorUpdating: false
    // The layout editor is also hosted by the dedicated Layouts navigation page.
    // Keeping it in this component avoids duplicating the canvas/CRUD logic.
    property bool layoutsOnly: false
    property string layoutViewMode: "list" // list | create | edit
    property var _snapGuides: []
    property string layoutLibrarySearch: ""
    property real layoutCanvasZoom: 1.0
    property bool layoutCanvasGridVisible: true
    property bool layoutSaveSucceeded: true

    readonly property var layoutWidgetTypes: [
        {type: "chat", label: "Чат", iconName: "chat.svg"},
        {type: "actions", label: "Дії та алерти", iconName: "web_alert.svg"},
        {type: "activity", label: "Активність", iconName: "activity.svg"},
        {type: "online", label: "Онлайн / глядачі", iconName: "users.svg"},
        {type: "top_likers", label: "Топ лайкерів", iconName: "heart.svg"},
        {type: "top_gifters", label: "Топ GIFтерів", iconName: "gift.svg"},
        {type: "king_of_live", label: "King of the Live", iconName: "web_crown.svg"},
        {type: "battle_royale", label: "Battle Royale", iconName: "web_swords.svg"},
        {type: "stream_pet", label: "Stream Pet", iconName: "web_paw.svg"},
        {type: "community_world", label: "Community World", iconName: "web_globe.svg"},
        {type: "stream_goal", label: "Stream Goal", iconName: "web_target.svg"},
        {type: "live_leaderboard", label: "Live Leaderboard", iconName: "web_trophy.svg"},
        {type: "social_rotator", label: "Social Rotator", iconName: "web_refresh.svg"},
        {type: "webcam_frame", label: "Webcam Frame", iconName: "web_camera.svg"},
        {type: "signal_system", label: "Signal System", iconName: "web_signal.svg"},
        {type: "music", label: "Музика", iconName: "web_music.svg"}
    ]

    function defaultWidgetSize(type) {
        switch (type) {
            case "chat": return {w: 420, h: 540};
            case "actions": return {w: 380, h: 240};
            case "activity": return {w: 320, h: 180};
            case "online": return {w: 280, h: 120};
            case "top_likers": return {w: 340, h: 260};
            case "top_gifters": return {w: 340, h: 260};
            case "king_of_live": return {w: 360, h: 220};
            case "battle_royale": return {w: 420, h: 280};
            case "stream_pet": return {w: 240, h: 240};
            case "community_world": return {w: 480, h: 320};
            case "stream_goal": return {w: 400, h: 160};
            case "live_leaderboard": return {w: 360, h: 280};
            case "social_rotator": return {w: 360, h: 120};
            case "webcam_frame": return {w: 480, h: 360};
            case "signal_system": return {w: 1920, h: 1080};
            case "music": return {w: 340, h: 140};
            default: return {w: 360, h: 200};
        }
    }

    function widgetTypeInfo(type) {
        var list = root.layoutWidgetTypes || [];
        for (var i = 0; i < list.length; ++i) {
            if (list[i].type === type) return list[i];
        }
        return {type: type, label: type, iconName: "web_layout.svg"};
    }

    function filteredLayoutWidgetTypes() {
        var query = String(root.layoutLibrarySearch || "").trim().toLowerCase();
        if (!query) return root.layoutWidgetTypes;
        return root.layoutWidgetTypes.filter(function(item) {
            return String(item.label || "").toLowerCase().indexOf(query) !== -1
                || String(item.type || "").toLowerCase().indexOf(query) !== -1;
        });
    }

    function setLayoutCanvasZoom(value) {
        root.layoutCanvasZoom = Math.max(0.5, Math.min(2.0, Math.round(value * 10) / 10));
    }

    // ---- Widget instances (Type -> Instances) state (root scope) ----
    property var widgetInstanceList: []
    property var widgetTypeList: []
    property string newInstanceType: "top_likers"
    property string newInstanceName: ""
    property bool showCreateWidget: false
    property string editingInstanceId: ""
    property string editingInstanceName: ""
    property string gallerySearch: ""
    property string galleryCategory: "all"
    property int gallerySort: 0
    // Platform categories allowed: all | tiktok | twitch | youtube | kick.
    // A widget may list several platforms; "all" = platform-agnostic (shown under every filter).
    function galleryPlatforms(t) {
        var p = (t && t.platforms) || ["all"];
        if (!Array.isArray(p) || !p.length) return ["all"];
        return p;
    }
    function galleryMatchesCategory(t, cat) {
        if (cat === "all") return true;
        var p = (t && t.platforms) || ["all"];
        if (!Array.isArray(p)) return false;
        return p.indexOf(cat) >= 0 || p.indexOf("all") >= 0;
    }
    function galleryPrimaryPlatform(t) {
        var p = root.galleryPlatforms(t);
        return p.length ? p[0] : "all";
    }
    // No placeholders: a type without an instance still renders with default
    // settings (fallback), so it counts as active.
    function galleryTypeStatus(typeId) {
        var list = root.widgetInstanceList || [];
        var found = false; var active = false;
        for (var i = 0; i < list.length; ++i) {
            if (list[i].type_id === typeId) {
                found = true;
                if (list[i].enabled) { active = true; break; }
            }
        }
        if (!found) return "active";
        return active ? "active" : "disabled";
    }
    function galleryTypeById(typeId) {
        var src = root.widgetTypeList || [];
        for (var i = 0; i < src.length; ++i)
            if (src[i].type_id === typeId) return src[i];
        return {type_id: typeId, name: typeId, description: "", icon: "📦", platforms: ["all"]};
    }
    function galleryCards() {
        // One card per widget INSTANCE (user-created included) +
        // one "needs setup" card per type that has zero instances.
        var q = (root.gallerySearch || "").toLowerCase().trim();
        var out = [];
        var seen = {};
        var insts = root.widgetInstanceList || [];
        for (var i = 0; i < insts.length; ++i) {
            var inst = insts[i];
            var t = root.galleryTypeById(inst.type_id);
            if (!root.galleryMatchesCategory(t, root.galleryCategory)) continue;
            if (q !== "") {
                var hay = (String(inst.name || "") + " " + String(t.name || "")
                    + " " + String(t.description || "") + " " + String(inst.type_id || "")).toLowerCase();
                if (hay.indexOf(q) < 0) continue;
            }
            seen[inst.type_id] = true;
            out.push({instance: inst, wtype: t});
        }
        var types = root.widgetTypeList || [];
        for (var j = 0; j < types.length; ++j) {
            var t2 = types[j];
            if (seen[t2.type_id]) continue;
            if (!root.galleryMatchesCategory(t2, root.galleryCategory)) continue;
            if (q !== "") {
                var hay2 = (String(t2.name || "") + " " + String(t2.description || "") + " " + String(t2.type_id || "")).toLowerCase();
                if (hay2.indexOf(q) < 0) continue;
            }
            out.push({instance: null, wtype: t2});
        }
        var rank = function(c) {
            if (!c.instance) return 2;
            return c.instance.enabled ? 0 : 1;
        };
        out.sort(function(a, b) {
            if (root.gallerySort === 1) {
                var ra = rank(a); var rb = rank(b);
                if (ra !== rb) return ra - rb;
            } else if (root.gallerySort === 2) {
                var pa = root.galleryPrimaryPlatform(a.wtype); var pb = root.galleryPrimaryPlatform(b.wtype);
                if (pa !== pb) return pa < pb ? -1 : 1;
            }
            var na = String((a.instance && a.instance.name) || a.wtype.name || a.wtype.type_id);
            var nb = String((b.instance && b.instance.name) || b.wtype.name || b.wtype.type_id);
            return na.localeCompare(nb);
        });
        return out;
    }
    function galleryFilteredTypes() {
        return root.galleryCards();
    }

    // ---- Miniature widget preview renderers (static, lightweight) ----
    // Data-driven building blocks for gallery card previews. Each renderer
    // fills the shared preview container; per-type DATA lives in the
    // delegate (previewSpec), never type conditionals in the visuals.
    component WidgetFeedPreview: ColumnLayout {
        property var rows: []
        anchors.fill: parent
        anchors.margins: 8
        spacing: 5
        Repeater {
            model: rows
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 6
                Image {
                    source: Qt.resolvedUrl("../assets/icons/" + modelData.icon + ".svg")
                    Layout.preferredWidth: 13
                    Layout.preferredHeight: 13
                    Layout.alignment: Qt.AlignVCenter
                }
                Text { text: modelData.label; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignVCenter }
                Text { text: modelData.user; color: "#9aa7bc"; font.pixelSize: 10; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; elide: Text.ElideRight }
                Text { text: modelData.time; color: root.muted; font.pixelSize: 9; Layout.alignment: Qt.AlignVCenter }
            }
        }
    }

    component WidgetChatPreview: ColumnLayout {
        property var rows: []
        anchors.fill: parent
        anchors.margins: 8
        spacing: 5
        Repeater {
            model: rows
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 5
                Image {
                    source: Qt.resolvedUrl("../assets/" + modelData.platform + ".svg")
                    Layout.preferredWidth: 12
                    Layout.preferredHeight: 12
                    Layout.alignment: Qt.AlignVCenter
                }
                Text { text: modelData.html; textFormat: Text.RichText; font.pixelSize: 9; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; elide: Text.ElideRight }
            }
        }
    }

    component WidgetStatsPreview: RowLayout {
        property var cols: []
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Repeater {
            model: cols
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 3
                Text { text: modelData.value; color: "#e8eaed"; font.pixelSize: 13; font.bold: true }
                Text { text: modelData.label; color: root.muted; font.pixelSize: 9 }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 3
                    radius: 1.5
                    color: "#1c2536"
                    Rectangle {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width * modelData.frac
                        height: 3
                        radius: 1.5
                        color: modelData.color
                    }
                }
            }
        }
    }

    component WidgetEmblemPreview: ColumnLayout {
        property string iconSource: ""
        property string caption: ""
        property real progress: -1
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6
        Item { Layout.fillWidth: true; Layout.fillHeight: true }
        Image {
            source: iconSource
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: caption
            color: "#9aa7bc"
            font.pixelSize: 10
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            maximumLineCount: 1
        }
        Rectangle {
            visible: progress >= 0
            Layout.fillWidth: true
            Layout.leftMargin: 14
            Layout.rightMargin: 14
            Layout.preferredHeight: 4
            radius: 2
            color: "#1c2536"
            Rectangle {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width * Math.max(0, Math.min(1, progress))
                height: 4
                radius: 2
                color: "#34d399"
            }
        }
        Item { Layout.fillWidth: true; Layout.fillHeight: true }
    }

    component WidgetBattlePreview: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Rectangle { width: 7; height: 7; radius: 3.5; color: "#ef4444"; Layout.alignment: Qt.AlignVCenter }
            Text { text: "luna"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignVCenter }
            Text { text: "82%"; color: root.muted; font.pixelSize: 9; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; horizontalAlignment: Text.AlignRight }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 4
            radius: 2
            color: "#1c2536"
            Rectangle {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width * 0.82
                height: 4
                radius: 2
                color: "#ef4444"
            }
        }
        Text {
            text: "VS"
            color: "#5b6575"
            font.pixelSize: 10
            font.bold: true
            font.letterSpacing: 2
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 4
            radius: 2
            color: "#1c2536"
            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width * 0.64
                height: 4
                radius: 2
                color: "#60a5fa"
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Rectangle { width: 7; height: 7; radius: 3.5; color: "#60a5fa"; Layout.alignment: Qt.AlignVCenter }
            Text { text: "void"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignVCenter }
            Text { text: "64%"; color: root.muted; font.pixelSize: 9; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; horizontalAlignment: Text.AlignRight }
        }
    }
    // Counts follow galleryCards(): every stored instance is a card, plus one active
    // fallback card for each type that has no stored instances.
    function galleryStats(cat) {
        var out = {total: 0, active: 0, disabled: 0};
        var instances = root.widgetInstanceList || [];
        var seen = {};
        for (var i = 0; i < instances.length; ++i) {
            var inst = instances[i];
            var instType = root.galleryTypeById(inst.type_id);
            if (!root.galleryMatchesCategory(instType, cat)) continue;
            ++out.total;
            seen[inst.type_id] = true;
            if (inst.enabled) ++out.active;
            else ++out.disabled;
        }
        var types = root.widgetTypeList || [];
        for (var j = 0; j < types.length; ++j) {
            var type = types[j];
            if (seen[type.type_id] || !root.galleryMatchesCategory(type, cat)) continue;
            ++out.total;
            ++out.active;
        }
        return out;
    }
    function galleryCount(cat) { return root.galleryStats(cat).total; }
    function galleryActiveCount() { return root.galleryStats("all").active; }
    function galleryDisabledCount() { return root.galleryStats("all").disabled; }

    function editWidgetInstance(inst) {
        if (!inst || !inst.id) {
            console.warn("editWidgetInstance: missing instance id, staying on grid");
            return;
        }
        root.editingInstanceId = inst.id;
        root.editingInstanceName = inst.name || inst.type_id || "";
        if (typeof api === "undefined" || !api) {
            console.warn("editWidgetInstance: api unavailable");
            return;
        }
        api.setEditingInstanceId(root.editingInstanceId);
        try {
            var echoed = api.editingInstanceId();
            if (echoed !== root.editingInstanceId) {
                console.warn("editWidgetInstance: backend did not accept id; "
                    + "saves would hit the default widget. Aborting.");
                root.clearEditingInstance();
                return;
            }
        } catch (e) { console.warn("editWidgetInstance verify failed:", e); }
        try {
            if (typeof apiGate !== "undefined" && apiGate && apiGate.item
                    && typeof apiGate.item.reloadAllWidgetConfigs === "function")
                apiGate.item.reloadAllWidgetConfigs();
        } catch (e) { console.warn("editWidgetInstance reload failed:", e); }
        root.widgetMode = inst.type_id;
    }

    function clearEditingInstance() {
        root.editingInstanceId = "";
        root.editingInstanceName = "";
        if (typeof api !== "undefined" && api) api.clearEditingInstance();
    }

    // Settings-tab adaptation: while an instance is being edited, the
    // editor header shows/copies the instance by-id URL, not the legacy
    // default (?instance=main) URL.
    function editorUrlValue(legacyUrl) {
        if (root.editingInstanceId !== "" && typeof api !== "undefined" && api)
            return api.widgetInstanceUrl(root.editingInstanceId);
        return legacyUrl;
    }

    function copyEditorUrl(legacyCopy) {
        if (root.editingInstanceId !== "" && typeof api !== "undefined" && api) {
            api.copyWidgetInstanceUrl(root.editingInstanceId);
            return;
        }
        if (legacyCopy) legacyCopy();
    }

    function refreshWidgetInstances() {
        try {
            if (typeof api === "undefined" || !api) return;
            if (api.widgetTypesJson) root.widgetTypeList = JSON.parse(api.widgetTypesJson());
            if (api.widgetInstancesJson) root.widgetInstanceList = JSON.parse(api.widgetInstancesJson());
        } catch (e) { console.warn("instances refresh failed:", e); }
    }

    Timer {
        id: widgetInstancesInitTimer
        interval: 400
        repeat: false
        running: true
        onTriggered: { root.refreshWidgetInstances(); root.refreshLayouts(); }
    }

    Rectangle {
        anchors.fill: parent
        color: base
    }

    // SpinBox/controls can emit value signals after the first frame; keep autosave blocked longer.
    Timer {
        id: overlayCfgInitGuardTimer
        interval: 850
        repeat: false
        onTriggered: {
            root._loadingCfg = false;
            root._loadingActionsCfg = false;
            root._loadingOnlineCfg = false;
            root._loadingTopLikersCfg = false;
            root._loadingTopGiftersCfg = false;
            root._loadingKingCfg = false;
            root._loadingBattleCfg = false;
            root._loadingStreamPetCfg = false;
            root._loadingCommunityWorldCfg = false;
            root._loadingStreamGoalCfg = false;
            root._loadingSocialRotatorCfg = false;
            root._loadingLiveLeaderboardCfg = false;
            root._loadingWebcamFrameCfg = false;
            root._loadingSignalSystemCfg = false;
        }
    }

    readonly property int titleBarH: 44
    property string widgetMode: "grid" // grid | chat | actions | online | top_likers | top_gifters | king_of_live | battle_royale | stream_pet | community_world | stream_goal | live_leaderboard | social_rotator | webcam_frame | signal_system
    readonly property bool universalEditorActive: root.editingInstanceId !== "" && root.widgetMode !== "grid" && root.widgetMode !== "layout"

    function universalInstance() {
        var list = root.widgetInstanceList || [];
        for (var i = 0; i < list.length; ++i)
            if (list[i].id === root.editingInstanceId) return list[i];
        return null;
    }

    function universalSchema(typeId, cfg) {
        // This is the presentation schema for the legacy editors. Values and keys are
        // intentionally the same as the old forms and their config dataclasses.
        var value = function(key, fallback) { return cfg && cfg[key] !== undefined ? cfg[key] : fallback; };
        var c = function(label, key, type, fallback, more) {
            var item = {label: label, field: key, type: type, value: value(key, fallback)};
            if (more) for (var k in more) item[k] = more[k];
            return item;
        };
        var bl = function(key) { return root.loc("widgets.battle_royale." + key); };
        var s = function(title, description, controls, icon, expanded) {
            return {title: title, description: description, icon: icon || "", controls: controls, expanded: expanded !== false};
        };
        var sections = [];
        var general = [];
        var appearance = [];
        var behavior = [];
        var animation = [];
        var advanced = [];

        if (typeId === "chat") {
            general = [
                c("Maximum messages", "max_items", "number", 12, {minimum: 1, maximum: 200}),
                c("Font family", "font_family", "text", "Segoe UI"),
                c("Font size", "font_size_px", "number", 18, {minimum: 8, maximum: 96}),
                c("Show platform icons", "show_platform_icon", "toggle", true),
                c("Fade after (seconds)", "fade_seconds", "number", 0, {minimum: 0, maximum: 600})
            ];
            appearance = [
                c("Widget background", "widget_bg_enabled", "toggle", false),
                c("Widget background color", "widget_bg_rgba", "color", "rgba(10,12,18,0.45)"),
                c("Widget corner radius", "widget_bg_radius_px", "number", 14, {minimum: 0, maximum: 60}),
                c("Widget padding", "widget_bg_padding_px", "number", 10, {minimum: 0, maximum: 48}),
                c("Message bubbles", "bubble_bg_enabled", "toggle", true),
                c("Bubble background", "bubble_bg_rgba", "color", "rgba(10,12,18,0.55)"),
                c("Bubble radius", "bubble_radius_px", "number", 10, {minimum: 0, maximum: 60}),
                c("Username color mode", "username_color_mode", "select", "auto", {options: ["auto", "platform", "custom"]}),
                c("Custom username color", "username_color_custom", "color", "#93c5fd"),
                c("Text color", "text_color", "color", "#e5e7eb")
            ];
            animation = [
                c("Text shadow", "text_shadow_enabled", "toggle", true),
                c("Shadow color", "text_shadow_rgba", "color", "rgba(0,0,0,0.65)"),
                c("Shadow blur", "text_shadow_blur_px", "number", 4, {minimum: 0, maximum: 24}),
                c("Shadow offset X", "text_shadow_offset_x_px", "number", 0, {minimum: -12, maximum: 12}),
                c("Shadow offset Y", "text_shadow_offset_y_px", "number", 1, {minimum: -12, maximum: 12})
            ];
        } else if (typeId === "actions") {
            general = [
                c("Font family", "font_family", "text", "Segoe UI"),
                c("Font size", "font_size_px", "number", 40, {minimum: 8, maximum: 200}),
                c("Line spacing", "font_line_spacing_px", "number", 0, {minimum: 0, maximum: 200}),
                c("Letter spacing", "font_letter_spacing_px", "number", 0, {minimum: -200, maximum: 200}),
                c("Profile picture", "show_profile_picture", "toggle", true),
                c("Gift picture", "show_gift_picture", "toggle", true),
                c("Action platform icon", "show_action_platform_icon", "toggle", true),
                c("Platform icon size", "platform_icon_size_px", "number", 40, {minimum: 16, maximum: 128}),
                c("Flip platform icon", "platform_icon_flip_enabled", "toggle", false),
                c("Single text line", "single_text_line", "toggle", false),
                c("Parallel popups", "parallel_popups_enabled", "toggle", false)
            ];
            appearance = [
                c("Text color", "text_color", "color", "#e5e7eb"),
                c("Text shadow", "text_shadow_enabled", "toggle", false),
                c("Shadow color", "text_shadow_color", "color", "#000000"),
                c("Font border", "font_border_enabled", "toggle", false),
                c("Border color", "font_border_color", "color", "#242424"),
                c("Custom username color", "username_custom_color_enabled", "toggle", false),
                c("Username color", "username_custom_color", "color", "#32c3a6"),
                c("Username effect", "username_text_effect", "select", "none", {options: ["none", "rainbow", "aurora", "neon", "fire"]}),
                c("Picture size", "picture_size_px", "number", 65, {minimum: 1, maximum: 512}),
                c("Username size", "username_size_px", "number", 65, {minimum: 1, maximum: 512}),
                c("Name/text gap", "name_text_gap_px", "number", 8, {minimum: 0, maximum: 80})
            ];
            behavior = [
                c("Bubble background", "bubble_bg_enabled", "toggle", true),
                c("Bubble opacity", "bubble_bg_alpha", "slider", 0.55, {minimum: 0, maximum: 1}),
                c("Bubble radius", "bubble_radius_px", "number", 16, {minimum: 0, maximum: 60}),
                c("Auto-hide seconds", "auto_hide_seconds", "number", 0, {minimum: 0, maximum: 600}),
                c("Wave effect", "wave_enabled", "toggle", false),
                c("Move effect", "move_enabled", "toggle", false),
                c("3D effect", "effect_3d_enabled", "toggle", false),
                c("Wiggle effect", "wiggle_enabled", "toggle", false)
            ];
        } else if (typeId === "online") {
            general = [
                c("Layout mode", "layout_mode", "select", "combined", {options: ["combined", "per_platform"]}),
                c("Twitch", "platform_twitch_enabled", "toggle", true), c("TikTok", "platform_tiktok_enabled", "toggle", true),
                c("YouTube", "platform_youtube_enabled", "toggle", true), c("Kick", "platform_kick_enabled", "toggle", true),
                c("Font family", "font_family", "text", "Segoe UI"), c("Font size", "font_size_px", "number", 36, {minimum: 8, maximum: 200}),
                c("Line spacing", "font_line_spacing_px", "number", 0, {minimum: 0, maximum: 200}), c("Letter spacing", "font_letter_spacing_px", "number", 0, {minimum: -200, maximum: 200}),
                c("Icon size", "platform_icon_size_px", "number", 28, {minimum: 16, maximum: 128}), c("Icon/number gap", "icon_number_gap_px", "number", 12, {minimum: 0, maximum: 80})
            ];
            appearance = [
                c("Text color", "text_color", "color", "#e5e7eb"), c("Text shadow", "text_shadow_enabled", "toggle", false),
                c("Shadow color", "text_shadow_color", "color", "#000000"), c("Font border", "font_border_enabled", "toggle", false),
                c("Border color", "font_border_color", "color", "#242424"), c("Text effect", "text_effect", "select", "none", {options: ["none", "glow", "neon", "rainbow", "aurora", "fire"]}),
                c("Block background", "bubble_bg_enabled", "toggle", true), c("Background opacity", "bubble_bg_alpha", "slider", 0.45, {minimum: 0, maximum: 1}),
                c("Block radius", "bubble_radius_px", "number", 14, {minimum: 0, maximum: 60})
            ];
        } else if (typeId === "top_likers" || typeId === "top_gifters") {
            var gifters = typeId === "top_gifters";
            general = [
                c("Font family", "font_family", "text", "Segoe UI"), c("Font size", "font_size_px", "number", 22, {minimum: 8, maximum: 120}),
                c("Line spacing", "font_line_spacing_px", "number", 4, {minimum: 0, maximum: 80}), c("Letter spacing", "font_letter_spacing_px", "number", 0, {minimum: -20, maximum: 40}),
                c("Show rank", "show_rank", "toggle", true), c(gifters ? "Show coins" : "Show likes", "show_likes", "toggle", true),
                c("Right-to-left", "rtl", "toggle", false), c("Top 1 crown", "show_top1_crown", "toggle", true), c("Top 3 medal", "show_top3_medal", "toggle", true)
            ];
            appearance = [
                c("Username color", "color_username", "color", gifters ? "#ff69b4" : "#c4b5fd"), c(gifters ? "Coins color" : "Likes color", "color_points", "color", gifters ? "#ffd700" : "#f4f4f5"), c("Rank color", "color_rank", "color", gifters ? "#f4f4f5" : "#d9d9d9"),
                c("Show heart", "show_heart", "toggle", true), c("Animated heart", "heart_animated", "toggle", true), c("Heart size", "heart_size_px", "number", 14, {minimum: 8, maximum: 48}),
                c("Panel shadow", "bg_shadow_enabled", "toggle", false), c("Panel shadow color", "bg_shadow_color", "color", "rgba(33,33,33,0.4)"),
                c("Font border", "font_border_enabled", "toggle", true), c("Border color", "font_border_color", "color", "#242424"),
                c("Username shadow", "username_text_shadow_enabled", "toggle", false), c("Username shadow color", "username_text_shadow_color", "color", "#000000"),
                c(gifters ? "Coins shadow" : "Likes shadow", "likes_text_shadow_enabled", "toggle", false), c(gifters ? "Coins shadow color" : "Likes shadow color", "likes_text_shadow_color", "color", "#000000"),
                c("Username effect", "text_effect_username", "select", "none", {options: ["none", "rainbow", "aurora", "cyberpunk", "fire", "ice", "cold", "freeze", "strong"]}),
                c("List background", "list_bg_enabled", "toggle", true), c("List background color", "list_bg_rgba", "color", gifters ? "rgba(26,26,26,0.92)" : "rgba(18,20,28,0.72)"), c("List radius", "list_radius_px", "number", 12, {minimum: 0, maximum: 40})
            ];
            behavior = [
                c("Wave effect", "wave_enabled", "toggle", false), c("Wave speed", "wave_speed", "select", "normal", {options: ["slow", "normal", "fast"]}),
                c("Sort leaders", "leader_sort", "select", "likes_desc", {options: ["likes_desc", "likes_asc", "name_asc"]}), c("Top count", "top_count", "number", 8, {minimum: 1, maximum: 10}),
                c("Avatar size", "avatar_size_px", "number", 48, {minimum: 24, maximum: 120}), c("Row gap", "row_gap_px", "number", 10, {minimum: 0, maximum: 40}),
                c("List scroll interval", "list_scroll_interval_sec", "number", 0, {minimum: 0, maximum: 600})
            ];
        } else if (typeId === "king_of_live") {
            general = [c("Preset", "preset", "select", "imperial_gold", {options: ["imperial_gold", "cyber_king", "dark_overlord", "minimalist"]}), c("Title", "title_text", "text", "KING OF THE LIVE"), c("Danger threshold", "danger_threshold_pct", "number", 90, {minimum: 50, maximum: 99}), c("Show gap strip", "show_gap_strip", "toggle", true), c("Avatar size", "avatar_size_px", "number", 120, {minimum: 64, maximum: 220}), c("Font family", "font_family", "text", "Segoe UI")];
            appearance = [c("Backdrop blur", "backdrop_blur_px", "number", 0, {minimum: 0, maximum: 48}), c("Bubble blur", "backdrop_bubble_blur_px", "number", 0, {minimum: 0, maximum: 48}), c("Rays intensity", "rays_intensity_pct", "number", 130, {minimum: 40, maximum: 200}), c("Text scale", "text_scale_pct", "number", 100, {minimum: 70, maximum: 160})];
            animation = [c("Animation intensity", "anim_intensity_pct", "number", 100, {minimum: 25, maximum: 200}), c("Avatar motion", "anim_avatar_motion", "toggle", true), c("Crown float", "anim_crown_float", "toggle", true), c("Rays spin", "anim_rays_spin", "toggle", true), c("Coins fall", "anim_coins_fall", "toggle", true), c("Gem pulse", "anim_gem_pulse", "toggle", true), c("Title shimmer", "anim_title_shimmer", "toggle", true), c("Presence fireworks", "anim_fireworks_on_presence", "toggle", true)];
        } else if (typeId === "battle_royale") {
            general = [c(bl("hide_when_idle"), "hide_when_idle", "toggle", true), c(bl("max_hp"), "max_hp", "number", 1000, {minimum: 100, maximum: 10000}), c(bl("round_duration"), "round_duration_s", "number", 120, {minimum: 30, maximum: 600}), c(bl("critical_threshold"), "crit_threshold_diamonds", "number", 500, {minimum: 50, maximum: 50000}), c(bl("gifts_per_fighter"), "gifts_per_fighter", "number", 3, {minimum: 1, maximum: 6}), c(bl("auto_start"), "auto_arm_enabled", "toggle", true)];
            appearance = [c(bl("base_font_size"), "base_font_size_px", "number", 14, {minimum: 10, maximum: 32}), c(bl("scale_percent"), "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            behavior = [c(bl("automatic_threshold"), "auto_threshold_each", "number", 100, {minimum: 1, maximum: 10000}), c(bl("automatic_window"), "auto_window_s", "number", 30, {minimum: 5, maximum: 120})];
        } else if (typeId === "stream_pet") {
            general = [c("Preset", "preset", "select", "classic_gold", {options: ["classic_gold", "cyber_purple", "cotton_candy", "forest_fox", "midnight_shadow", "sunset_shiba", "custom"]}), c("Enabled", "enabled", "toggle", true), c("Show energy bar", "show_energy_bar", "toggle", true), c("Evolution enabled", "evolution_enabled", "toggle", true), c("Pet scale", "pet_scale_pct", "number", 100, {minimum: 50, maximum: 200})];
            appearance = [c("Collar enabled", "collar_enabled", "toggle", true), c("Blush enabled", "blush_enabled", "toggle", true), c("Body color", "pet_body_color", "color", "#fbbf24"), c("Ear color", "pet_ear_color", "color", "#f59e0b"), c("Collar color", "collar_color", "color", "#ef4444"), c("Bubble color", "bubble_bg_color", "color", "#ffffff")];
            behavior = [c("Bubble max characters", "bubble_max_chars", "number", 110, {minimum: 40, maximum: 200}), c("VIP level 3 interval", "level3_vip_interval_sec", "number", 180, {minimum: 30, maximum: 3600}), c("Post-evolution energy", "post_evolution_energy", "number", 50, {minimum: 31, maximum: 100}), c("Disco duration", "disco_duration_ms", "number", 5000, {minimum: 1000, maximum: 30000}), c("Initial energy", "initial_energy", "number", 70, {minimum: 0, maximum: 100}), c("Decay per 2 minutes", "decay_per_2min", "number", 1, {minimum: 0, maximum: 10}), c("Sleep idle seconds", "sleep_idle_sec", "number", 900, {minimum: 60, maximum: 3600})];
            advanced = [c("Bubble font", "bubble_font_family", "text", "Press Start 2P"), c("Bubble font size", "bubble_font_size_px", "number", 20, {minimum: 12, maximum: 48}), c("Pet sprite URL", "pet_sprite_url", "url", "")];
        } else if (typeId === "community_world") {
            general = [c("Enabled", "enabled", "toggle", true), c("Quiet mode", "quiet_mode", "toggle", false), c("Theme", "theme", "select", "ukrainian", {options: ["pixel", "fantasy", "cyber", "ukrainian"]}), c("Layout", "layout_mode", "select", "full", {options: ["full", "compact"]})];
            appearance = [c("Scale", "scale_pct", "number", 100, {minimum: 40, maximum: 200}), c("Font size", "font_size_px", "number", 16, {minimum: 8, maximum: 120}), c("Font family", "font_family", "text", "Segoe UI"), c("Show level", "show_level", "toggle", true), c("Show quests", "show_quests", "toggle", true), c("Show recognition", "show_recognition", "toggle", true), c("Show passports", "show_passports", "toggle", true), c("Show buildings", "show_buildings", "toggle", true), c("Show elders", "show_elders", "toggle", true)];
            behavior = [c("Quest 1 type", "quest1_type", "select", "likes", {options: ["likes", "shares", "gifts", "follows", "none"]}), c("Quest 2 type", "quest2_type", "select", "shares", {options: ["likes", "shares", "gifts", "follows", "none"]}), c("Quest 3 type", "quest3_type", "select", "gifts", {options: ["likes", "shares", "gifts", "follows", "none"]}), c("Quest 4 type", "quest4_type", "select", "follows", {options: ["likes", "shares", "gifts", "follows", "none"]}), c("Likes target", "quest_likes_target", "number", 5000, {minimum: 100, maximum: 100000000}), c("Shares target", "quest_shares_target", "number", 50, {minimum: 100, maximum: 100000}), c("Gifts target", "quest_gifts_target", "number", 1000, {minimum: 50, maximum: 100000000}), c("Follows target", "quest_follows_target", "number", 100, {minimum: 5, maximum: 100000})];
            advanced = [c("XP follow", "xp_follow", "number", 40, {minimum: 0, maximum: 1000}), c("XP join", "xp_join", "number", 5, {minimum: 0, maximum: 1000}), c("XP chat", "xp_chat", "number", 2, {minimum: 0, maximum: 1000}), c("XP like per 10", "xp_like_per_10", "number", 2, {minimum: 0, maximum: 1000}), c("XP share", "xp_share", "number", 25, {minimum: 0, maximum: 1000}), c("XP gift coins per 10", "xp_gift_coin_per_10", "number", 1, {minimum: 0, maximum: 1000}), c("XP battle win", "xp_battle_win", "number", 150, {minimum: 0, maximum: 10000})];
        } else if (typeId === "stream_goal") {
            general = [c("Enabled", "enabled", "toggle", true), c("Goal type", "goal_type", "select", "followers", {options: ["followers", "likes", "gifts", "shares", "comments"]}), c("Title", "title", "text", "FOLLOW GOAL"), c("Subtitle", "subtitle", "text", ""), c("Current value", "current_value", "number", 0, {minimum: 0, maximum: 10000000}), c("Target value", "target_value", "number", 10000, {minimum: 1, maximum: 10000000}), c("Next target", "next_target_value", "number", 25000, {minimum: 1, maximum: 50000000})];
            appearance = [c("Skin", "skin", "select", "digital_core", {options: ["digital_core", "boss", "reactor", "rocket", "vault", "tower", "creature"]}), c("Accent color", "accent_color", "color", "#00ffff"), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            animation = [c("Animation intensity", "animation_intensity", "select", "medium", {options: ["low", "medium", "high"]}), c("Combo", "enable_combo", "toggle", true), c("Milestones", "enable_milestones", "toggle", true), c("Particles", "enable_particles", "toggle", true), c("Glitch", "enable_glitch", "toggle", true), c("Reset behavior", "reset_behavior", "select", "after_completion", {options: ["after_completion", "manual", "new_stream"]})];
        } else if (typeId === "live_leaderboard") {
            general = [c("Enabled", "enabled", "toggle", true), c("Top entries", "top_n", "number", 10, {minimum: 1, maximum: 10}), c("Rotation sequence", "sequence", "list", "")];
            behavior = [c("Likers", "enable_likers", "toggle", true), c("Gifters", "enable_gifters", "toggle", true), c("Sharers", "enable_sharers", "toggle", true), c("Commenters", "enable_commenters", "toggle", true), c("Contributors", "enable_contributors", "toggle", true), c("Hall of fame", "enable_hall_of_fame", "toggle", true), c("Arena", "enable_arena", "toggle", true), c("Energy network", "enable_energy_network", "toggle", true)];
            animation = [c("Transition", "transition", "select", "glitch_morph", {options: ["glitch_morph", "digital_dissolve", "scan", "fade"]}), c("Animation intensity", "animation_intensity", "select", "medium", {options: ["low", "medium", "high"]}), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250}), c("Rank change animation", "enable_rank_change_anim", "toggle", true), c("Particles", "enable_particles", "toggle", true), c("CRT", "enable_crt", "toggle", true)];
        } else if (typeId === "social_rotator") {
            general = [c("Enabled", "enabled", "toggle", true), c("Platforms", "platforms", "list", ""), c("Rotation interval", "rotation_interval_ms", "number", 8000, {minimum: 1000, maximum: 120000})];
            appearance = [c("Transition", "transition", "select", "glitch_morph", {options: ["glitch_morph", "data_stream", "energy_burst", "scan", "pixel_dissolve", "fade"]}), c("Theme", "theme", "select", "neon_cyber", {options: ["neon_cyber", "synthwave", "toxic", "ice", "amber"]}), c("Background opacity", "background_opacity_percent", "slider", 85, {minimum: 0, maximum: 100}), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            behavior = [c("Show URL", "show_url", "toggle", true), c("Secondary platforms", "show_secondary_platforms", "toggle", true), c("Countdown", "show_countdown", "toggle", true), c("Glow", "enable_glow", "toggle", true), c("Particles", "enable_particles", "toggle", true), c("CRT", "enable_crt", "toggle", true), c("Latest follower", "show_latest_follower", "toggle", true), c("Latest donation", "show_latest_donation", "toggle", true), c("Stream time", "show_stream_time", "toggle", true), c("Top donator", "show_top_donator", "toggle", true), c("Online count", "show_online", "toggle", true), c("TikTok coin rate", "tiktok_coin_to_value_rate", "text", 1.0)];
        } else if (typeId === "webcam_frame") {
            general = [c("Enabled", "enabled", "toggle", true), c("Theme", "theme", "select", "neon_cyber", {options: ["neon_cyber", "synthwave", "toxic", "ice", "amber", "critical"]}), c("Intensity", "intensity", "select", "medium", {options: ["low", "medium", "high"]}), c("Frame style", "frame_style", "select", "primary", {options: ["primary", "minimal", "tactical", "broadcast", "hologram"]}), c("Camera label", "cam_label", "text", "CAM // 01"), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            animation = [c("Energy flow", "enable_energy_flow", "toggle", true), c("Breathing glow", "enable_breathing_glow", "toggle", true), c("Light sweep", "enable_light_sweep", "toggle", true), c("Micro glitch", "enable_micro_glitch", "toggle", true), c("Sparks", "enable_sparks", "toggle", true), c("CRT", "enable_crt", "toggle", true), c("Status indicator", "enable_status_indicator", "toggle", true), c("Boot animation", "enable_boot_animation", "toggle", true), c("Shutdown animation", "enable_shutdown_animation", "toggle", true)];
        } else if (typeId === "signal_system") {
            general = [c("Enabled", "enabled", "toggle", true), c("Theme", "theme", "select", "neon_cyber", {options: ["neon_cyber", "toxic_system", "ice_protocol", "amber_core", "critical"]}), c("Custom title", "custom_title", "text", "SIGNAL // SYSTEM")];
            appearance = [c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250}), c("Core vertical position", "core_vertical_pct", "number", 50, {minimum: 20, maximum: 80})];
            behavior = [c("Perimeter", "perimeter_enabled", "toggle", true), c("Particles", "particles_enabled", "toggle", true), c("Glitch", "glitch_enabled", "toggle", true), c("Sound", "sound_enabled", "toggle", false), c("Idle opacity", "idle_opacity_pct", "number", 35, {minimum: 0, maximum: 100}), c("Active opacity", "active_opacity_pct", "number", 100, {minimum: 50, maximum: 100}), c("Minimum gift coins", "min_gift_coins_for_event", "number", 100, {minimum: 1, maximum: 10000}), c("Cooldown", "cooldown_ms", "number", 3000, {minimum: 500, maximum: 15000})];
            advanced = [c("Milestones", "milestones_enabled", "toggle", true), c("Activity surge", "activity_surge_enabled", "toggle", true), c("AI observations", "ai_observations_enabled", "toggle", true), c("Unknown signals", "unknown_signals_enabled", "toggle", true)];
        }

        // Keep accepted persisted fields visible too, even where the legacy form exposed
        // them only through presets or runtime defaults. These are existing schema keys.
        if (typeId === "chat") advanced = advanced.concat([c("Show platform", "show_platform", "toggle", true)]);
        if (typeId === "battle_royale") advanced = advanced.concat([
            c(bl("preset"), "preset", "select", "arcade_royale", {options: ["arcade_royale", "cyber_arena", "dark_fight", "minimal_brawl"], optionLabels: [bl("preset_arcade_royale"), bl("preset_cyber_arena"), bl("preset_dark_fight"), bl("preset_minimal_brawl")]}), c(bl("title"), "title_text", "text", "BATTLE ROYALE"), c(bl("countdown"), "countdown_s", "number", 5, {minimum: 1, maximum: 30}),
            c(bl("critical_multiplier"), "crit_multiplier", "number", 1.5, {minimum: 1, maximum: 5}),
            c(bl("max_fighters"), "max_fighters", "number", 4, {minimum: 2, maximum: 4}), c(bl("vip_chat_hours"), "vip_chat_hours", "number", 1, {minimum: 1, maximum: 24}),
            c(bl("avatar_size"), "avatar_size_px", "number", 110, {minimum: 64, maximum: 200}), c(bl("font_family"), "font_family", "text", "Segoe UI"),
            c(bl("animation_intensity"), "anim_intensity_pct", "number", 100, {minimum: 25, maximum: 200}), c(bl("sfx_volume"), "sfx_volume_pct", "number", 80, {minimum: 0, maximum: 100}),
            c(bl("projectile_animation"), "anim_projectile", "toggle", true), c(bl("shake_animation"), "anim_shake", "toggle", true), c(bl("critical_flash"), "anim_crit_flash", "toggle", true), c(bl("fatality_animation"), "anim_fatality", "toggle", true)
        ]);
        if (typeId === "stream_pet") advanced = advanced.concat([
            c("Pet outline", "pet_outline_color", "color", "#111827"), c("Eye color", "pet_eye_color", "color", "#111827"), c("Mouth color", "pet_mouth_color", "color", "#111827"),
            c("Blanket color", "blanket_color", "color", "#111827"), c("Spark color", "spark_color", "color", "#fef3c7"), c("Hyper glow", "hyper_glow_color", "color", "#a78bfa"),
            c("Bubble border", "bubble_border_color", "color", "#111827"), c("Bubble text", "bubble_text_color", "color", "#111827")
        ]);
        if (typeId === "community_world") {
            advanced = advanced.concat([c("Feed max items", "feed_max_items", "number", 20, {minimum: 1, maximum: 200}), c("Title color", "color_title", "color", "#ffffff"), c("Progress color", "color_progress", "color", "#14b8a6"), c("Quest background", "color_quest_bg", "color", "#10141a"), c("Text color", "color_text", "color", "#e8eaed"), c("Accent color", "color_accent", "color", "#14b8a6")]);
        }
        if (typeId === "stream_goal") advanced = advanced.concat([
            c("Event animations", "enable_event_animations", "toggle", true), c("Completion animation", "enable_completion_animation", "toggle", true), c("Sound", "enable_sound", "toggle", false),
            c("Milestones JSON", "milestones_json", "text", "[]"), c("Gift coin progress", "gift_coin_per_progress", "number", 1, {minimum: 0, maximum: 100000}), c("Combo window", "combo_window_sec", "number", 5, {minimum: 0, maximum: 120})
        ]);
        if (typeId === "live_leaderboard") advanced = advanced.concat([c("Accent color", "accent_color", "color", "#14b8a6"), c("Like weight", "weight_like", "number", 1, {minimum: 0, maximum: 100}), c("Gift weight", "weight_gift_coin", "number", 1, {minimum: 0, maximum: 100}), c("Share weight", "weight_share", "number", 1, {minimum: 0, maximum: 100}), c("Comment weight", "weight_comment", "number", 1, {minimum: 0, maximum: 100})]);
        if (typeId === "social_rotator") advanced = advanced.concat([c("Accent color", "accent_color", "color", "#14b8a6")]);
        if (typeId === "signal_system") advanced = advanced.concat([
            c("Font family", "font_family", "text", "Segoe UI"), c("Intensity multiplier", "intensity_multiplier", "number", 1, {minimum: 0, maximum: 10}), c("Primary accent", "primary_accent", "color", "#14b8a6"), c("Secondary accent", "secondary_accent", "color", "#a78bfa"),
            c("Frame detail level", "frame_detail_level", "number", 1, {minimum: 0, maximum: 10}), c("Particle density", "particle_density", "number", 1, {minimum: 0, maximum: 10}), c("Gift icon", "gift_icon_enabled", "toggle", true), c("Gift quantity", "show_gift_quantity", "toggle", true), c("Coin value", "show_coin_value", "toggle", true), c("Gift name", "show_gift_name", "toggle", true), c("Reduced motion", "reduced_motion", "toggle", false),
            c("Global cooldown", "global_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000}), c("AI cooldown", "ai_observation_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000}), c("AI max per hour", "ai_observation_max_per_hour", "number", 10, {minimum: 0, maximum: 1000}), c("Unknown signal cooldown", "unknown_signal_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000})
        ]);

        if (general.length) sections.push(s(typeId === "battle_royale" ? bl("section_general") : "General", typeId === "battle_royale" ? bl("desc_general") : "Core settings for this widget instance.", general, "◇"));
        if (appearance.length) sections.push(s(typeId === "battle_royale" ? bl("section_appearance") : "Appearance", typeId === "battle_royale" ? bl("desc_appearance") : "Visual presentation and display options.", appearance, "✦"));
        if (behavior.length) sections.push(s(typeId === "battle_royale" ? bl("section_behavior") : "Gameplay / Behavior", typeId === "battle_royale" ? bl("desc_behavior") : "Rules, sources, timing, and widget behavior.", behavior, "≡"));
        if (animation.length) sections.push(s("Animation", "Motion and visual effect controls.", animation, "⌁"));
        if (advanced.length) sections.push(s(typeId === "battle_royale" ? bl("section_advanced") : "Advanced", typeId === "battle_royale" ? bl("desc_advanced") : "Technical settings for this widget.", advanced, "⚙", false));
        return sections;
    }

    function universalConfig() {
        if (root.widgetMode === "chat") return root.cfg;
        if (root.widgetMode === "actions") return root.actionsCfg;
        if (root.widgetMode === "online") return root.onlineCfg;
        if (root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") return root.tierOverlayCfg;
        if (root.widgetMode === "king_of_live") return root.kingCfg;
        if (root.widgetMode === "battle_royale") return root.battleCfg;
        if (root.widgetMode === "stream_pet") return root.streamPetCfg;
        if (root.widgetMode === "community_world") return root.communityWorldCfg;
        if (root.widgetMode === "stream_goal") return root.streamGoalCfg;
        if (root.widgetMode === "live_leaderboard") return root.liveLeaderboardCfg;
        if (root.widgetMode === "social_rotator") return root.socialRotatorCfg;
        if (root.widgetMode === "webcam_frame") return root.webcamFrameCfg;
        if (root.widgetMode === "signal_system") return root.signalSystemCfg;
        return null;
    }

    function applyUniversalSetting(field, value) {
        var cfg = root.universalConfig();
        if (!cfg || field === "instance_id") return;
        if (root.widgetMode === "stream_pet" && field === "preset") {
            root._applyStreamPetPreset(value);
            universalPreviewSaveDebounce.restart();
            universalPreviewUpdateDebounce.restart();
            return;
        }
        cfg[field] = value;
        universalPreviewSaveDebounce.restart();
        universalPreviewUpdateDebounce.restart();
    }

    Timer {
        id: universalPreviewSaveDebounce
        interval: 250
        repeat: false
        onTriggered: root._saveAndApplyCurrentWidget()
    }

    Timer {
        id: universalPreviewUpdateDebounce
        interval: 300
        repeat: false
        onTriggered: {
            if (root._canSaveCurrentWidget && api)
                api.updateWidgetPreview(root.editingInstanceId);
        }
    }

    function _deepCopy(obj) {
        try {
            return JSON.parse(JSON.stringify(obj));
        } catch (e) {
            return {};
        }
    }

    function _pushUndo() {
        if (!root.layoutDoc) return;
        var copy = root._deepCopy(root.layoutDoc);
        var stack = (root._undoStack || []).slice();
        stack.push(copy);
        if (stack.length > 50) stack.shift();
        root._undoStack = stack;
        root._redoStack = [];
    }

    function undo() {
        if (!root._undoStack || !root._undoStack.length) return;
        var undoStack = root._undoStack.slice();
        var prevDoc = undoStack.pop();
        root._undoStack = undoStack;

        var redoStack = (root._redoStack || []).slice();
        redoStack.push(root._deepCopy(root.layoutDoc));
        root._redoStack = redoStack;

        root._inspectorUpdating = true;
        root.layoutDoc = prevDoc;
        root._inspectorUpdating = false;

        var widgets = root.layoutDoc.widgets || [];
        if (root.selectedLayoutWidget >= widgets.length) {
            root.selectedLayoutWidget = widgets.length - 1;
        }
        root.saveLayoutEditor();
    }

    function redo() {
        if (!root._redoStack || !root._redoStack.length) return;
        var redoStack = root._redoStack.slice();
        var nextDoc = redoStack.pop();
        root._redoStack = redoStack;

        var undoStack = (root._undoStack || []).slice();
        undoStack.push(root._deepCopy(root.layoutDoc));
        root._undoStack = undoStack;

        root._inspectorUpdating = true;
        root.layoutDoc = nextDoc;
        root._inspectorUpdating = false;

        var widgets = root.layoutDoc.widgets || [];
        if (root.selectedLayoutWidget >= widgets.length) {
            root.selectedLayoutWidget = widgets.length - 1;
        }
        root.saveLayoutEditor();
    }

    property var layoutDocList: []
    property string activeLayoutId: "default"
    property string layoutCopiedId: ""
    property bool showCreateLayout: false
    property string newLayoutName: ""

    function layoutWidgetTotal() {
        var total = 0;
        var all = root.layoutDocList || [];
        for (var i = 0; i < all.length; ++i)
            total += (all[i] && all[i].widgets ? all[i].widgets.length : 0);
        return total;
    }

    function layoutActiveTotal() {
        var all = root.layoutDocList || [];
        if (!all.length || !root.activeLayoutId) return 0;
        for (var i = 0; i < all.length; ++i)
            if (all[i] && all[i].id === root.activeLayoutId) return 1;
        return 0;
    }

    function layoutPreviewLabel(type) {
        var info = root.widgetTypeInfo(type);
        var label = String((info && info.label) || type || "Widget");
        return label.length > 18 ? label.slice(0, 17) + "…" : label;
    }

    function layoutPreviewAccent(index) {
        var colors = ["#a78bfa", "#22d3ee", "#c084fc", "#2dd4bf", "#818cf8"];
        return colors[index % colors.length];
    }

    function refreshLayouts() {
        try {
            if (typeof api === "undefined" || !api) return;
            var all = JSON.parse(api.loadLayoutsJson()).layouts || [];
            root.layoutDocList = all;
            var aid = "";
            try { aid = api.activeLayoutId(); } catch (e2) {}
            var found = false;
            for (var i = 0; i < all.length; ++i) {
                if (all[i].id === aid) { found = true; break; }
            }
            root.activeLayoutId = (aid && found) ? aid : (all.length ? all[0].id : "default");
        } catch (e) { console.warn("layouts refresh failed:", e); }
    }

    function showLayoutList() {
        if (!root.layoutsOnly) return;
        var alreadyGrid = root.widgetMode === "grid";
        root.layoutViewMode = "list";
        root.widgetMode = "grid";
        root.layoutDoc = {};
        root.selectedLayoutWidget = -1;
        root._undoStack = [];
        root._redoStack = [];
        root._snapGuides = [];
        root.layoutCopiedId = "";
        // Changing widgetMode to grid invokes the existing refresh hook. If
        // it was already grid, perform the one required refresh here.
        if (alreadyGrid) root.refreshLayouts();
    }

    function createLayoutAndOpen() {
        if (!api) return;
        var id = api.createLayout("");
        if (!id) return;
        root.loadLayoutEditor(id);
        root.layoutViewMode = "create";
        root.widgetMode = "layout";
    }

    function openLayoutEditor(layoutId) {
        root.loadLayoutEditor(layoutId);
        try { if (api) api.setActiveLayoutId(root.activeLayoutId); } catch (e) {}
        root.layoutViewMode = "edit";
        root.widgetMode = "layout";
    }

    function switchLayoutByIndex(idx) {
        var all = root.layoutDocList || [];
        if (idx < 0 || idx >= all.length || !all[idx]) return;
        if (all[idx].id === root.activeLayoutId) return;
        try { if (api) api.setActiveLayoutId(all[idx].id); } catch (e) {}
        root.loadLayoutEditor(all[idx].id);
    }

    function layoutWidgetInstanceOptions(type) {
        var opts = [{id: "", label: root.loc("widgets.layouts.default_instance")}];
        var list = root.widgetInstanceList || [];
        for (var i = 0; i < list.length; ++i) {
            if (list[i].type_id === type)
                opts.push({id: list[i].id, label: (list[i].enabled ? "● " : "○ ") + (list[i].name || list[i].id)});
        }
        return opts;
    }

    function selectedLayoutWidgetInstanceId() {
        var item = root.selectedLayoutItem();
        return item ? (item.widget_instance_id || "") : "";
    }

    function layoutWidgetInstanceIndex() {
        var item = root.selectedLayoutItem();
        if (!item) return 0;
        var opts = root.layoutWidgetInstanceOptions(item.type);
        var cur = item.widget_instance_id || "";
        for (var i = 0; i < opts.length; ++i) {
            if (opts[i].id === cur) return i;
        }
        return 0;
    }

    function applyLayoutWidgetInstance(index) {
        var item = root.selectedLayoutItem();
        if (!item) return;
        var opts = root.layoutWidgetInstanceOptions(item.type);
        if (index < 0 || index >= opts.length) return;
        if ((item.widget_instance_id || "") === opts[index].id) return;
        root.updateLayoutItemStr("widget_instance_id", opts[index].id);
    }

    function loadLayoutEditor(layoutId) {
        root.refreshLayouts();
        try {
            var all = root.layoutDocList || [];
            var want = layoutId || root.activeLayoutId;
            var doc = null;
            for (var i = 0; i < all.length; ++i) {
                if (all[i].id === want) { doc = all[i]; break; }
            }
            if (!doc && all.length) doc = all[0];
            root.layoutDoc = doc || {};
            root.activeLayoutId = root.layoutDoc.id || "default";
        } catch (e) {
            root.layoutDoc = {};
        }
        var w = Number(root.layoutDoc.width || 1920), h = Number(root.layoutDoc.height || 1080);
        if (w === 1080 && h === 1920) root.canvasPresetIndex = 1;
        else if (w === 1080 && h === 1080) root.canvasPresetIndex = 2;
        else if (w === 1280 && h === 720) root.canvasPresetIndex = 3;
        else if (w === 1920 && h === 1080) root.canvasPresetIndex = 0;
        else root.canvasPresetIndex = 4;
        root.selectedLayoutWidget = -1;
        root._undoStack = [];
        root._redoStack = [];
        root._snapGuides = [];
        root.layoutCanvasZoom = 1.0;
        root.layoutSaveSucceeded = true;
    }

    function selectedLayoutItem() {
        var items = root.layoutDoc.widgets || [];
        return (items.length && root.selectedLayoutWidget >= 0 && root.selectedLayoutWidget < items.length)
            ? items[root.selectedLayoutWidget] : null;
    }

    function updateLayoutItem(key, value) {
        if (root._inspectorUpdating) return;
        var doc = root.layoutDoc;
        var items = (doc.widgets || []).slice();
        if (!items.length || root.selectedLayoutWidget < 0 || root.selectedLayoutWidget >= items.length) return;
        root._pushUndo();
        var item = Object.assign({}, items[root.selectedLayoutWidget]);
        item[key] = Number(value);
        items[root.selectedLayoutWidget] = item;
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, doc, {widgets: items});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function commitWidgetGeometry(widgetIndex, newX, newY, newW, newH) {
        var doc = root.layoutDoc;
        var items = (doc.widgets || []).slice();
        if (widgetIndex < 0 || widgetIndex >= items.length) return;
        var item = Object.assign({}, items[widgetIndex]);
        if (newX !== undefined) item.x = newX;
        if (newY !== undefined) item.y = newY;
        if (newW !== undefined) item.width = Math.max(32, newW);
        if (newH !== undefined) item.height = Math.max(24, newH);
        items[widgetIndex] = item;
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, doc, {widgets: items});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function saveLayoutEditor() {
        var saved = false;
        if (api && root.layoutDoc && root.layoutDoc.id) {
            // Keep the QML list as a display cache, but persist only the
            // selected object. This prevents stale QML state from replacing
            // a sibling Layout edited elsewhere.
            var all = (root.layoutDocList || []).slice();
            var replaced = false;
            for (var i = 0; i < all.length; ++i) {
                if (all[i] && all[i].id === root.layoutDoc.id) {
                    all[i] = root.layoutDoc;
                    replaced = true;
                    break;
                }
            }
            if (!replaced) all.push(root.layoutDoc);
            root.layoutDocList = all;
            if (typeof api.saveLayoutJson === "function")
                saved = api.saveLayoutJson(JSON.stringify(root.layoutDoc));
            else {
                api.saveLayoutsJson(JSON.stringify({schema_version: 1, layouts: all}));
                saved = true;
            }
        }
        root.layoutSaveSucceeded = saved;
        root.layoutRevision += 1;
        return saved;
    }

    function updateLayoutItemStr(key, value) {
        if (root._inspectorUpdating) return;
        var doc = root.layoutDoc;
        var items = (doc.widgets || []).slice();
        if (!items.length || root.selectedLayoutWidget < 0 || root.selectedLayoutWidget >= items.length) return;
        root._pushUndo();
        var item = Object.assign({}, items[root.selectedLayoutWidget]);
        item[key] = String(value === undefined || value === null ? "" : value);
        items[root.selectedLayoutWidget] = item;
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, doc, {widgets: items});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function addLayoutWidget(type, label, posX, posY) {
        root._pushUndo();
        var doc = root.layoutDoc;
        var items = (doc.widgets || []).slice();
        var n = items.length;
        var sz = root.defaultWidgetSize(type);
        var defaultW = sz.w;
        var defaultH = sz.h;
        var targetX = (posX !== undefined) ? (posX - Math.round(defaultW / 2)) : (80 + (n * 24) % 500);
        var targetY = (posY !== undefined) ? (posY - Math.round(defaultH / 2)) : (80 + (n * 24) % 300);

        items.push({
            id: type + "-" + Date.now(),
            type: type,
            instance: "main",
            x: targetX,
            y: targetY,
            width: defaultW,
            height: defaultH,
            z_index: n + 1,
            visible: true,
            locked: false
        });
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, doc, {widgets: items});
        root._inspectorUpdating = false;
        root.selectedLayoutWidget = items.length - 1;
        root.saveLayoutEditor();
    }

    function removeSelectedLayoutWidget() {
        var items = (root.layoutDoc.widgets || []).slice();
        if (!items.length || root.selectedLayoutWidget < 0 || root.selectedLayoutWidget >= items.length) return;
        root._pushUndo();
        var removedIdx = root.selectedLayoutWidget;
        items.splice(removedIdx, 1);
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: items});
        root._inspectorUpdating = false;
        root.selectedLayoutWidget = items.length ? Math.min(removedIdx, items.length - 1) : -1;
        root.saveLayoutEditor();
    }

    function moveWidgetLayer(fromIdx, toIdx) {
        var items = (root.layoutDoc.widgets || []).slice();
        if (fromIdx < 0 || fromIdx >= items.length || toIdx < 0 || toIdx >= items.length || fromIdx === toIdx) return;
        root._pushUndo();
        var moved = items.splice(fromIdx, 1)[0];
        items.splice(toIdx, 0, moved);
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: items});
        root._inspectorUpdating = false;
        root.selectedLayoutWidget = toIdx;
        root.saveLayoutEditor();
    }

    function toggleWidgetLock(index) {
        var items = (root.layoutDoc.widgets || []).slice();
        if (index < 0 || index >= items.length) return;
        root._pushUndo();
        var item = Object.assign({}, items[index]);
        item.locked = !item.locked;
        items[index] = item;
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: items});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function toggleWidgetVisibility(index) {
        var items = (root.layoutDoc.widgets || []).slice();
        if (index < 0 || index >= items.length) return;
        root._pushUndo();
        var item = Object.assign({}, items[index]);
        item.visible = item.visible === false;
        items[index] = item;
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: items});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function applyLayoutPreset(width, height, name) {
        root._pushUndo();
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {width: width, height: height, name: name});
        root._inspectorUpdating = false;
        root.saveLayoutEditor();
    }

    function nudgeSelected(dx, dy) {
        var item = root.selectedLayoutItem();
        if (!item || item.locked) return;
        root._pushUndo();
        var currentX = Number(item.x || 0);
        var currentY = Number(item.y || 0);
        root.commitWidgetGeometry(root.selectedLayoutWidget, currentX + dx, currentY + dy, undefined, undefined);
    }

    function selectCanvasPreset(index) {
        root.canvasPresetIndex = index;
        if (index === 1) root.applyLayoutPreset(1080, 1920, "TikTok вертикаль");
        else if (index === 2) root.applyLayoutPreset(1080, 1080, "Квадрат");
        else if (index === 3) root.applyLayoutPreset(1280, 720, "HD");
        else if (index === 0) root.applyLayoutPreset(1920, 1080, "Основна сцена");
    }

    component EditorIconButton: Button {
        id: editorIconButton
        property string iconName: ""
        property string toolTipText: ""
        property bool active: false
        implicitWidth: 32
        implicitHeight: 32
        padding: 7
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Image {
            source: editorIconButton.iconName ? Qt.resolvedUrl("../assets/icons/" + editorIconButton.iconName) : ""
            fillMode: Image.PreserveAspectFit
            opacity: editorIconButton.enabled ? 1.0 : 0.35
        }
        background: Rectangle {
            radius: 7
            color: editorIconButton.active
                ? root.accentSoft
                : (editorIconButton.pressed ? "#263653" : (editorIconButton.hovered ? "#1c2b42" : "transparent"))
            border.width: editorIconButton.active || editorIconButton.hovered ? 1 : 0
            border.color: editorIconButton.active ? root.accent : root.cardEdgeStrong
        }
        ToolTip.visible: editorIconButton.hovered && editorIconButton.toolTipText !== ""
        ToolTip.text: editorIconButton.toolTipText
        ToolTip.delay: 450
    }

    component LayoutPrimaryButton: Button {
        id: layoutPrimaryButton
        property string iconName: ""
        property int buttonFontSize: 12
        implicitHeight: 38
        leftPadding: 14
        rightPadding: 14
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 7
            Image {
                source: layoutPrimaryButton.iconName ? Qt.resolvedUrl("../assets/icons/" + layoutPrimaryButton.iconName) : ""
                visible: layoutPrimaryButton.iconName !== ""
                width: 16
                height: 16
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: layoutPrimaryButton.text
                color: "white"
                font.pixelSize: layoutPrimaryButton.buttonFontSize
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            radius: 9
            gradient: Gradient {
                GradientStop { position: 0.0; color: layoutPrimaryButton.pressed ? "#6d28d9" : (layoutPrimaryButton.hovered ? "#9d71f7" : "#8b5cf6") }
                GradientStop { position: 1.0; color: layoutPrimaryButton.pressed ? "#5b21b6" : (layoutPrimaryButton.hovered ? "#8b5cf6" : "#7c3aed") }
            }
            border.width: 1
            border.color: layoutPrimaryButton.hovered ? "#ddd6fe" : "#8b5cf6"
        }
    }

    component LayoutCardButton: Button {
        id: layoutCardButton
        property string iconName: ""
        property bool primary: false
        property int buttonFontSize: 11
        implicitHeight: 32
        leftPadding: 10
        rightPadding: 10
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: layoutCardButton.iconName ? Qt.resolvedUrl("../assets/icons/" + layoutCardButton.iconName) : ""
                visible: layoutCardButton.iconName !== ""
                width: 14
                height: 14
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: layoutCardButton.text
                color: layoutCardButton.primary ? "#f5f3ff" : root.ink
                font.pixelSize: layoutCardButton.buttonFontSize
                font.bold: layoutCardButton.primary
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            radius: 8
            color: layoutCardButton.primary
                ? (layoutCardButton.pressed ? "#5b21b6" : (layoutCardButton.hovered ? "#6d28d9" : "#351879"))
                : (layoutCardButton.pressed ? "#263653" : (layoutCardButton.hovered ? "#1c2b42" : "#121d30"))
            border.width: 1
            border.color: layoutCardButton.primary
                ? (layoutCardButton.hovered ? "#c4b5fd" : "#7c3aed")
                : (layoutCardButton.hovered ? "#52617a" : "#2a3850")
        }
    }

    component PillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property bool primary: false
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: pillFontSize
        transformOrigin: Item.Center
        scale: pillCtl.hovered ? 1.015 : 1.0
        Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
        contentItem: Text {
            text: pillCtl.text
            color: pillCtl.primary ? "#041615" : root.ink
            font.pixelSize: pillCtl.pillFontSize
            font.weight: pillCtl.primary ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: root.radiusMD
            color: pillCtl.primary
                ? (pillCtl.pressed ? root.accentPress : (pillCtl.hovered ? root.accentHover : root.accent))
                : (pillCtl.pressed ? root.cardEdgeStrong : (pillCtl.hovered ? root.cardEdgeStrong : root.cardBase))
            border.width: 1
            border.color: pillCtl.primary
                ? root.accentPress
                : (pillCtl.hovered ? root.cardEdgeStrong : root.cardEdge)
            Behavior on color { ColorAnimation { duration: 80; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 80; easing.type: Easing.OutCubic } }
        }
    }

    component StyledComboBox: ComboBox {
        id: cb
        // Custom delegate clicks do not emit C++ ComboBox.activated — use userActivated
        // (and onActivated bridge below for keyboard / native activation paths).
        signal userActivated(int index)
        property bool _userEmitGuard: false
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        font.pixelSize: 13
        padding: 10

        function _emitUserActivated(index) {
            if (cb._userEmitGuard)
                return;
            cb._userEmitGuard = true;
            cb.userActivated(index);
            cb._userEmitGuard = false;
        }

        contentItem: Text {
            text: cb.editable ? (cb.editText || "") : cb.displayText
            color: root.ink
            font.pixelSize: cb.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: root.radiusMD
            color: root.fieldBg
            border.width: 1
            border.color: cb.hovered ? root.cardEdgeStrong : root.cardEdge
            Behavior on border.color { ColorAnimation { duration: 80 } }
        }
        onActivated: function (index) {
            cb._emitUserActivated(index);
        }
        delegate: ItemDelegate {
            required property int index
            width: ListView.view ? ListView.view.width : implicitWidth
            implicitHeight: 36
            highlighted: cb.highlightedIndex === index
            onClicked: {
                cb.currentIndex = index;
                // Mouse path: C++ activated does not fire with this custom delegate.
                cb._emitUserActivated(index);
                cb.popup.close();
            }
            contentItem: Text {
                text: cb.textAt(index)
                color: root.ink
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 4
                color: highlighted ? root.accentSoft : "transparent"
                Behavior on color { ColorAnimation { duration: 60 } }
            }
        }
        popup: Popup {
            y: cb.height + 2
            width: cb.width
            implicitHeight: contentItem.implicitHeight
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: cb.popup.visible ? cb.delegateModel : null
                currentIndex: cb.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { width: 6 }
            }
            background: Rectangle {
                radius: root.radiusMD
                color: root.cardBase
                border.width: 1
                border.color: root.cardEdge
            }
        }
    }

    component StyledTextField: TextField {
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        font.pixelSize: 13
        padding: 10
        color: root.ink
        background: Rectangle {
            radius: root.radiusMD
            color: root.fieldBg
            border.width: 1
            border.color: hovered ? root.cardEdgeStrong : (activeFocus ? root.accent : root.cardEdge)
            Behavior on border.color { ColorAnimation { duration: 80 } }
        }
        placeholderTextColor: root.inkMuted
        selectionColor: root.accentSoft
        selectedTextColor: root.ink
    }

    component StyledSpinBox: SpinBox {
        id: sb
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        editable: true
        stepSize: 1
        wheelEnabled: true
        font.pixelSize: 13
        implicitHeight: 36
        implicitWidth: 140

        function _stepBy(delta) {
            var step = sb.stepSize > 0 ? sb.stepSize : 1;
            var next = sb.value + delta * step;
            if (next < sb.from)
                next = sb.from;
            if (next > sb.to)
                next = sb.to;
            if (next === sb.value)
                return;
            sb.value = next;
        }

        contentItem: TextInput {
            id: sbInput
            text: sb.displayText
            color: root.ink
            selectionColor: root.accentSoft
            selectedTextColor: root.ink
            font.pixelSize: sb.font.pixelSize
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter
            readOnly: !sb.editable
            selectByMouse: true
            validator: IntValidator {
                bottom: sb.from
                top: sb.to
            }
            onEditingFinished: {
                var t = (text || "").trim();
                if (!t.length) {
                    text = sb.displayText;
                    return;
                }
                var v = sb.valueFromText(t, sb.locale);
                if (v === undefined || v === null || isNaN(v)) {
                    text = sb.displayText;
                    return;
                }
                if (v < sb.from) v = sb.from;
                if (v > sb.to) v = sb.to;
                sb.value = v;
                text = sb.displayText;
            }
        }

        background: Rectangle {
            radius: root.radiusMD
            color: root.fieldBg
            border.width: 1
            border.color: sb.hovered ? root.cardEdgeStrong : (sb.activeFocus ? root.accent : root.cardEdge)
            Behavior on border.color { ColorAnimation { duration: 80 } }
        }

        down.indicator: Item {
            implicitWidth: 36
            implicitHeight: 36
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 0
            Rectangle {
                anchors.fill: parent
                radius: root.radiusMD
                color: downMa.pressed ? root.accentPress : (downMa.containsMouse ? root.cardEdgeStrong : root.cardBase)
                border.width: 1
                border.color: downMa.containsMouse ? root.cardEdgeStrong : root.cardEdge
                Behavior on color { ColorAnimation { duration: 80 } }
                Behavior on border.color { ColorAnimation { duration: 80 } }
                Text {
                    anchors.centerIn: parent
                    text: "−"
                    color: root.ink
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }
                MouseArea {
                    id: downMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: function (mouse) { mouse.accepted = true; sb._stepBy(-1); }
                }
            }
        }

        up.indicator: Item {
            implicitWidth: 36
            implicitHeight: 36
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 0
            Rectangle {
                anchors.fill: parent
                radius: root.radiusMD
                color: upMa.pressed ? root.accentPress : (upMa.containsMouse ? root.cardEdgeStrong : root.cardBase)
                border.width: 1
                border.color: upMa.containsMouse ? root.cardEdgeStrong : root.cardEdge
                Behavior on color { ColorAnimation { duration: 80 } }
                Behavior on border.color { ColorAnimation { duration: 80 } }
                Text {
                    anchors.centerIn: parent
                    text: "+"
                    color: root.ink
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }
                MouseArea {
                    id: upMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: function (mouse) { mouse.accepted = true; sb._stepBy(1); }
                }
            }
        }
    }

    component ResizeHandle: Item {
        id: handleRoot
        property var targetItem: null
        property int edgeX: 0
        property int edgeY: 0
        property int resizeCursor: Qt.ArrowCursor

        width: 20
        height: 20
        z: 100

        Rectangle {
            anchors.centerIn: parent
            width: 10
            height: 10
            radius: 2
            color: handleMouseArea.pressed ? "#38bdf8" : (handleMouseArea.containsMouse ? "#ffffff" : "#d9fffb")
            border.width: 1.5
            border.color: handleMouseArea.pressed ? "#0284c7" : "#0f766e"
        }

        MouseArea {
            id: handleMouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: handleRoot.resizeCursor
            preventStealing: true

            property real startCanvasX: 0
            property real startCanvasY: 0

            onPressed: function(mouse) {
                if (!targetItem) return;
                var pt = mapToItem(layoutCanvas, mouse.x, mouse.y);
                startCanvasX = pt.x / layoutCanvas.editorScale;
                startCanvasY = pt.y / layoutCanvas.editorScale;
                targetItem.beginResize(edgeX, edgeY);
                mouse.accepted = true;
            }

            onPositionChanged: function(mouse) {
                if (!pressed || !targetItem) return;
                var pt = mapToItem(layoutCanvas, mouse.x, mouse.y);
                var currentCanvasX = pt.x / layoutCanvas.editorScale;
                var currentCanvasY = pt.y / layoutCanvas.editorScale;
                var transX = currentCanvasX - startCanvasX;
                var transY = currentCanvasY - startCanvasY;
                var shiftHeld = (mouse.modifiers & Qt.ShiftModifier) !== 0;
                var altHeld = (mouse.modifiers & Qt.AltModifier) !== 0;
                targetItem.resizeWith(edgeX, edgeY, transX, transY, shiftHeld, altHeld);
                mouse.accepted = true;
            }

            onReleased: function(mouse) {
                if (!targetItem) return;
                targetItem.finishResize();
                mouse.accepted = true;
            }
        }
    }

    component StyledCheckBox: CheckBox {
        id: chk
        spacing: 8
        font.pixelSize: 13
        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: chk.leftPadding
            y: parent.height / 2 - height / 2
            radius: 4
            color: chk.down ? "#1a2232" : (chk.checked ? "#134e4a" : root.fieldBg)
            border.width: 1
            border.color: chk.checked ? "#14b8a6" : (chk.hovered ? "#3b4458" : root.cardEdge)
            Text {
                anchors.centerIn: parent
                text: "✓"
                font.pixelSize: 11
                font.bold: true
                color: root.ink
                visible: chk.checked
            }
        }
        contentItem: Text {
            text: chk.text
            font: chk.font
            opacity: chk.enabled ? 1.0 : 0.55
            color: root.ink
            verticalAlignment: Text.AlignVCenter
            leftPadding: chk.indicator.width + chk.spacing
        }
    }

    component StyledSlider: Slider {
        id: sl
        implicitHeight: 28
        background: Rectangle {
            x: sl.leftPadding
            y: sl.topPadding + sl.availableHeight / 2 - height / 2
            implicitWidth: 200
            implicitHeight: 4
            width: sl.availableWidth
            height: implicitHeight
            radius: 2
            color: "#252d3d"
            Rectangle {
                width: sl.visualPosition * parent.width
                height: parent.height
                color: "#14b8a6"
                radius: 2
            }
        }
        handle: Rectangle {
            x: sl.leftPadding + sl.visualPosition * (sl.availableWidth - width)
            y: sl.topPadding + sl.availableHeight / 2 - height / 2
            implicitWidth: 14
            implicitHeight: 14
            radius: 7
            color: sl.pressed ? root.ink : "#cbd5e1"
            border.width: 1
            border.color: sl.hovered ? "#14b8a6" : "#3b4a63"
        }
    }

    // SpinBox `value: root.someCfg.field` does not refresh when only nested keys on a `var` map change.
    component VarMapSpinBox: StyledSpinBox {
        id: vsb
        required property var hostMap
        required property string hostKey
        property int hostDefault: 0
        /// syncGroup must match a branch in _loadingForGroup / _persist / Connections pulls.
        required property string syncGroup
        property bool __vsync: false

        function _loadingForGroup() {
            if (vsb.syncGroup === "chat")
                return root._loadingCfg;
            if (vsb.syncGroup === "online")
                return root._loadingOnlineCfg;
            if (vsb.syncGroup === "actions")
                return root._loadingActionsCfg;
            if (vsb.syncGroup === "tier")
                return root._tierOverlayLoading;
            if (vsb.syncGroup === "king")
                return root._loadingKingCfg;
            if (vsb.syncGroup === "battle")
                return root._loadingBattleCfg;
            if (vsb.syncGroup === "community_world")
                return root._loadingCommunityWorldCfg;
            if (vsb.syncGroup === "stream_goal")
                return root._loadingStreamGoalCfg;
            if (vsb.syncGroup === "live_leaderboard")
                return root._loadingLiveLeaderboardCfg;
            if (vsb.syncGroup === "social_rotator")
                return root._loadingSocialRotatorCfg;
            if (vsb.syncGroup === "webcam_frame")
                return root._loadingWebcamFrameCfg;
            if (vsb.syncGroup === "signal_system")
                return root._loadingSignalSystemCfg;
            if (vsb.syncGroup === "stream_pet")
                return root._loadingStreamPetCfg;
            return true;
        }

        function _persist() {
            if (vsb.syncGroup === "chat")
                root._save();
            else if (vsb.syncGroup === "online")
                root._saveOnline();
            else if (vsb.syncGroup === "actions")
                root._saveActions();
            else if (vsb.syncGroup === "tier")
                root._saveTierOverlay();
            else if (vsb.syncGroup === "king")
                root._saveKing();
            else if (vsb.syncGroup === "battle")
                root._saveBattle();
            else if (vsb.syncGroup === "community_world")
                root._saveCommunityWorld();
            else if (vsb.syncGroup === "stream_goal")
                root._saveStreamGoal();
            else if (vsb.syncGroup === "live_leaderboard")
                root._saveLiveLeaderboard();
            else if (vsb.syncGroup === "social_rotator")
                root._saveSocialRotator();
            else if (vsb.syncGroup === "webcam_frame")
                root._saveWebcamFrame();
            else if (vsb.syncGroup === "signal_system")
                root._saveSignalSystem();
            else if (vsb.syncGroup === "stream_pet")
                root._saveStreamPet();
        }

        function _pull() {
            if (vsb.hostMap === null)
                return;
            var raw = vsb.hostMap[vsb.hostKey];
            var v = (raw !== undefined && raw !== null) ? parseInt(raw, 10) : vsb.hostDefault;
            if (isNaN(v))
                v = vsb.hostDefault;
            if (v < vsb.from)
                v = vsb.from;
            if (v > vsb.to)
                v = vsb.to;
            if (v === vsb.value)
                return;
            vsb.__vsync = true;
            vsb.value = v;
            vsb.__vsync = false;
        }

        Component.onCompleted: vsb._pull()
        Connections {
            target: root
            function onCfgChanged() {
                if (vsb.syncGroup === "chat")
                    vsb._pull();
            }
            function onChatCfgEpochChanged() {
                if (vsb.syncGroup === "chat")
                    vsb._pull();
            }
            function onOnlineCfgChanged() {
                if (vsb.syncGroup === "online")
                    vsb._pull();
            }
            function onOnlineCfgEpochChanged() {
                if (vsb.syncGroup === "online")
                    vsb._pull();
            }
            function onActionsCfgChanged() {
                if (vsb.syncGroup === "actions")
                    vsb._pull();
            }
            function onActionsCfgEpochChanged() {
                if (vsb.syncGroup === "actions")
                    vsb._pull();
            }
            function onTierOverlayCfgChanged() {
                if (vsb.syncGroup === "tier")
                    vsb._pull();
            }
            function onTopLikersCfgEpochChanged() {
                if (vsb.syncGroup === "tier")
                    vsb._pull();
            }
            function onTopGiftersCfgEpochChanged() {
                if (vsb.syncGroup === "tier")
                    vsb._pull();
            }
            function onKingCfgChanged() {
                if (vsb.syncGroup === "king")
                    vsb._pull();
            }
            function onKingCfgEpochChanged() {
                if (vsb.syncGroup === "king")
                    vsb._pull();
            }
            function onBattleCfgChanged() {
                if (vsb.syncGroup === "battle")
                    vsb._pull();
            }
            function onBattleCfgEpochChanged() {
                if (vsb.syncGroup === "battle")
                    vsb._pull();
            }
            function onCommunityWorldCfgChanged() {
                if (vsb.syncGroup === "community_world")
                    vsb._pull();
            }
            function onCommunityWorldCfgEpochChanged() {
                if (vsb.syncGroup === "community_world")
                    vsb._pull();
            }
            function onStreamGoalCfgChanged() {
                if (vsb.syncGroup === "stream_goal")
                    vsb._pull();
            }
            function onStreamGoalCfgEpochChanged() {
                if (vsb.syncGroup === "stream_goal")
                    vsb._pull();
            }
            function onLiveLeaderboardCfgChanged() {
                if (vsb.syncGroup === "live_leaderboard")
                    vsb._pull();
            }
            function onLiveLeaderboardCfgEpochChanged() {
                if (vsb.syncGroup === "live_leaderboard")
                    vsb._pull();
            }
            function onSocialRotatorCfgChanged() {
                if (vsb.syncGroup === "social_rotator")
                    vsb._pull();
            }
            function onSocialRotatorCfgEpochChanged() {
                if (vsb.syncGroup === "social_rotator")
                    vsb._pull();
            }
            function onWebcamFrameCfgChanged() {
                if (vsb.syncGroup === "webcam_frame")
                    vsb._pull();
            }
            function onWebcamFrameCfgEpochChanged() {
                if (vsb.syncGroup === "webcam_frame")
                    vsb._pull();
            }
            function onSignalSystemCfgChanged() {
                if (vsb.syncGroup === "signal_system")
                    vsb._pull();
            }
            function onSignalSystemCfgEpochChanged() {
                if (vsb.syncGroup === "signal_system")
                    vsb._pull();
            }
            function onStreamPetCfgChanged() {
                if (vsb.syncGroup === "stream_pet")
                    vsb._pull();
            }
            function onStreamPetCfgEpochChanged() {
                if (vsb.syncGroup === "stream_pet")
                    vsb._pull();
            }
        }

        onValueChanged: {
            if (vsb.__vsync || vsb._loadingForGroup() || vsb.hostMap === null)
                return;
            vsb.hostMap[vsb.hostKey] = value;
            vsb._persist();
        }
    }

    property var cfg: null
    property var actionsCfg: null
    property bool _loadingActionsCfg: false
    // QVariant map mutations don't notify dependents; bump this whenever actions overlay cfg is saved.
    property int actionsCfgEpoch: 0
    property color _bubbleColor: "#0a0c12"
    property real _bubbleAlpha: 0.55
    property color _usernameCustomColor: "#93c5fd"
    property color _textShadowColor: "#000000"
    property real _textShadowAlpha: 0.65
    property color _widgetBgColor: "#0a0c12"
    property real _widgetBgAlpha: 0.45

    property color _actionsTextShadowColor: "#000000"
    property color _actionsBorderColor: "#242424"
    property color _actionsCustomColor: "#32c3a6"
    property color _actionsTextColor: "#e5e7eb"

    property var onlineCfg: null
    property bool _loadingOnlineCfg: false
    property int onlineCfgEpoch: 0
    property color _onlineTextShadowColor: "#000000"
    property color _onlineBorderColor: "#242424"
    property color _onlineTextColor: "#e5e7eb"

    property var topLikersCfg: null
    property bool _loadingTopLikersCfg: false
    property int topLikersCfgEpoch: 0
    property var topGiftersCfg: null
    property bool _loadingTopGiftersCfg: false
    property int topGiftersCfgEpoch: 0
    property var kingCfg: null
    property bool _loadingKingCfg: false
    property int kingCfgEpoch: 0
    property var battleCfg: null
    property bool _loadingBattleCfg: false
    property int battleCfgEpoch: 0
    property var streamPetCfg: null
    property bool _loadingStreamPetCfg: false
    property int streamPetCfgEpoch: 0
    property var communityWorldCfg: null
    property bool _loadingCommunityWorldCfg: false
    property int communityWorldCfgEpoch: 0
    property var streamGoalCfg: null
    property bool _loadingStreamGoalCfg: false
    property int streamGoalCfgEpoch: 0
    property var liveLeaderboardCfg: null
    property bool _loadingLiveLeaderboardCfg: false
    property int liveLeaderboardCfgEpoch: 0
    property var socialRotatorCfg: null
    property bool _loadingSocialRotatorCfg: false
    property int socialRotatorCfgEpoch: 0
    property var webcamFrameCfg: null
    property bool _loadingWebcamFrameCfg: false
    property int webcamFrameCfgEpoch: 0
    property color _spBodyColor: "#fbbf24"
    property color _spEarColor: "#f59e0b"
    property color _spCollarColor: "#ef4444"
    property color _spBubbleBgColor: "#ffffff"
    property var tierOverlayCfg: null

    readonly property bool _tierOverlayLoading: (root.widgetMode === "top_gifters")
        ? root._loadingTopGiftersCfg
        : root._loadingTopLikersCfg

    property color _tlUsernameColor: "#c4b5fd"
    property color _tlPointsColor: "#f4f4f5"
    property color _tlRankColor: "#d9d9d9"
    property color _tlBorderColor: "#242424"
    property color _tlListBgColor: "#12141c"
    property real _tlListBgAlpha: 0.72
    property color _tlUsernameShadowColor: "#000000"
    property color _tlLikesShadowColor: "#000000"
    property color _tlPanelShadowColor: "#212121"
    property real _tlPanelShadowAlpha: 0.4

    function _tlColorFromCfg(s) {
        var t = (s || "").trim();
        if (t.length >= 4 && t.toLowerCase().indexOf("rgba") === 0)
            return _parseRgba(t).c;
        return Qt.color(t.length ? t : "#000000");
    }

    function _ensureDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (obj.max_items === undefined) obj.max_items = 12;
        if (obj.font_size_px === undefined) obj.font_size_px = 18;
        // Platform text labels are deprecated in UI (icons cover it).
        if (obj.show_platform === undefined) obj.show_platform = false;
        if (obj.show_platform_icon === undefined) obj.show_platform_icon = true;
        if (obj.fade_seconds === undefined) obj.fade_seconds = 0;
        if (obj.widget_bg_enabled === undefined) obj.widget_bg_enabled = false;
        if (!obj.widget_bg_rgba) obj.widget_bg_rgba = "rgba(10,12,18,0.45)";
        if (obj.widget_bg_radius_px === undefined) obj.widget_bg_radius_px = 14;
        if (obj.widget_bg_padding_px === undefined) obj.widget_bg_padding_px = 10;
        if (obj.bubble_bg_enabled === undefined) obj.bubble_bg_enabled = true;
        if (!obj.bubble_bg_rgba) obj.bubble_bg_rgba = "rgba(10,12,18,0.55)";
        if (obj.bubble_radius_px === undefined) obj.bubble_radius_px = 10;
        if (!obj.username_color_mode) obj.username_color_mode = "auto";
        if (!obj.username_color_custom) obj.username_color_custom = "#93c5fd";
        if (!obj.text_color) obj.text_color = "#e5e7eb";
        if (obj.text_shadow_enabled === undefined) obj.text_shadow_enabled = true;
        if (!obj.text_shadow_rgba) obj.text_shadow_rgba = "rgba(0,0,0,0.65)";
        if (obj.text_shadow_blur_px === undefined) obj.text_shadow_blur_px = 4;
        if (obj.text_shadow_offset_x_px === undefined) obj.text_shadow_offset_x_px = 0;
        if (obj.text_shadow_offset_y_px === undefined) obj.text_shadow_offset_y_px = 1;
        if (!obj.font_family) obj.font_family = "Segoe UI";
        return obj;
    }

    function _clamp01(v) {
        if (v === undefined || v === null) return 0;
        var n = Number(v);
        if (!isFinite(n)) return 0;
        if (n < 0) return 0;
        if (n > 1) return 1;
        return n;
    }

    function _toByte(v) {
        var n = Math.round(Number(v) * 255);
        if (!isFinite(n)) return 0;
        if (n < 0) return 0;
        if (n > 255) return 255;
        return n;
    }

    function _hex2(n) {
        var s = n.toString(16);
        return (s.length === 1) ? ("0" + s) : s;
    }

    function _colorToHex(c) {
        // QML color has r/g/b in 0..1
        return "#" + _hex2(_toByte(c.r)) + _hex2(_toByte(c.g)) + _hex2(_toByte(c.b));
    }

    function _rgbaString(c, a) {
        return "rgba(" + _toByte(c.r) + "," + _toByte(c.g) + "," + _toByte(c.b) + "," + _clamp01(a) + ")";
    }

    function _parseRgba(s) {
        // returns {c: color, a: alpha}
        var txt = (s || "").trim();
        var m = /^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)$/i.exec(txt);
        if (m) {
            var r = Math.max(0, Math.min(255, parseInt(m[1])));
            var g = Math.max(0, Math.min(255, parseInt(m[2])));
            var b = Math.max(0, Math.min(255, parseInt(m[3])));
            var a = _clamp01(parseFloat(m[4]));
            return { c: Qt.rgba(r/255.0, g/255.0, b/255.0, 1.0), a: a };
        }
        // Fallback: let Qt parse color; assume alpha from cfg or default.
        return { c: txt ? txt : "#0a0c12", a: 0.55 };
    }

    function _save() {
        if (!api || root.cfg === null) return;
        root.chatCfgEpoch += 1;
        if (typeof api.saveChatConfigMap === "function")
            api.saveChatConfigMap(root.cfg);
        else
            api.saveChatConfigJson(JSON.stringify(root.cfg));
    }

    property bool _loadingCfg: false
    property int chatCfgEpoch: 0

    function _ensureActionsDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (!obj.font_family) obj.font_family = "Segoe UI";
        if (obj.font_size_px === undefined) obj.font_size_px = 40;
        if (obj.font_line_spacing_px === undefined) obj.font_line_spacing_px = 0;
        if (obj.font_letter_spacing_px === undefined) obj.font_letter_spacing_px = 0;

        if (obj.wave_enabled === undefined) obj.wave_enabled = false;
        if (obj.move_enabled === undefined) obj.move_enabled = false;
        if (obj.effect_3d_enabled === undefined) obj.effect_3d_enabled = false;
        if (obj.wiggle_enabled === undefined) obj.wiggle_enabled = false;

        if (obj.text_shadow_enabled === undefined) obj.text_shadow_enabled = false;
        if (!obj.text_shadow_color) obj.text_shadow_color = "#000000";
        if (!obj.text_color) obj.text_color = "#e5e7eb";

        if (obj.font_border_enabled === undefined) obj.font_border_enabled = false;
        if (!obj.font_border_color) obj.font_border_color = "#242424";

        if (obj.username_custom_color_enabled === undefined) obj.username_custom_color_enabled = false;
        if (!obj.username_custom_color) obj.username_custom_color = "#32c3a6";
        if (!obj.username_text_effect) obj.username_text_effect = "none";

        if (obj.picture_size_px === undefined) obj.picture_size_px = 65;
        if (obj.username_size_px === undefined) obj.username_size_px = 65;
        if (obj.name_text_gap_px === undefined) obj.name_text_gap_px = 8;

        if (obj.show_profile_picture === undefined) obj.show_profile_picture = true;
        if (obj.show_gift_picture === undefined) obj.show_gift_picture = true;
        if (obj.show_action_platform_icon === undefined) obj.show_action_platform_icon = true;
        if (obj.platform_icon_flip_enabled === undefined) obj.platform_icon_flip_enabled = false;
        if (obj.platform_icon_size_px === undefined) obj.platform_icon_size_px = 40;
        if (obj.single_text_line === undefined) obj.single_text_line = false;
        if (obj.parallel_popups_enabled === undefined) obj.parallel_popups_enabled = false;
        if (obj.auto_hide_seconds === undefined) obj.auto_hide_seconds = 0;
        if (obj.bubble_bg_enabled === undefined) obj.bubble_bg_enabled = true;
        if (obj.bubble_bg_alpha === undefined) obj.bubble_bg_alpha = 0.55;
        if (obj.bubble_radius_px === undefined) obj.bubble_radius_px = 16;
        return obj;
    }

    function _saveActions() {
        if (!api || root.actionsCfg === null) return;
        root.actionsCfgEpoch += 1;
        if (typeof api.saveActionsConfigMap === "function")
            api.saveActionsConfigMap(root.actionsCfg);
        else
            api.saveActionsConfigJson(JSON.stringify(root.actionsCfg));
    }

    function _ensureOnlineDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (!obj.layout_mode) obj.layout_mode = "combined";

        if (obj.platform_twitch_enabled === undefined) obj.platform_twitch_enabled = true;
        if (obj.platform_tiktok_enabled === undefined) obj.platform_tiktok_enabled = true;
        if (obj.platform_youtube_enabled === undefined) obj.platform_youtube_enabled = true;
        if (obj.platform_kick_enabled === undefined) obj.platform_kick_enabled = true;

        if (!obj.font_family) obj.font_family = "Segoe UI";
        if (obj.font_size_px === undefined) obj.font_size_px = 36;
        if (obj.font_line_spacing_px === undefined) obj.font_line_spacing_px = 0;
        if (obj.font_letter_spacing_px === undefined) obj.font_letter_spacing_px = 0;

        if (obj.text_shadow_enabled === undefined) obj.text_shadow_enabled = false;
        if (!obj.text_shadow_color) obj.text_shadow_color = "#000000";
        if (!obj.text_color) obj.text_color = "#e5e7eb";

        if (obj.font_border_enabled === undefined) obj.font_border_enabled = false;
        if (!obj.font_border_color) obj.font_border_color = "#242424";

        if (!obj.text_effect) obj.text_effect = "none";

        if (obj.platform_icon_size_px === undefined) obj.platform_icon_size_px = 28;
        if (obj.icon_number_gap_px === undefined) obj.icon_number_gap_px = 12;

        if (obj.bubble_bg_enabled === undefined) obj.bubble_bg_enabled = true;
        if (obj.bubble_bg_alpha === undefined) obj.bubble_bg_alpha = 0.45;
        if (obj.bubble_radius_px === undefined) obj.bubble_radius_px = 14;
        return obj;
    }

    function _saveOnline() {
        if (!api || root.onlineCfg === null) return;
        root.onlineCfgEpoch += 1;
        if (typeof api.saveOnlineOverlayConfigMap === "function")
            api.saveOnlineOverlayConfigMap(root.onlineCfg);
        else
            api.saveOnlineOverlayConfigJson(JSON.stringify(root.onlineCfg));
    }

    function _saveTopGifters() {
        if (!api || root.topGiftersCfg === null) return;
        root.topGiftersCfgEpoch += 1;
        if (typeof api.saveTopGiftersOverlayConfigMap === "function")
            api.saveTopGiftersOverlayConfigMap(root.topGiftersCfg);
        else
            api.saveTopGiftersOverlayConfigJson(JSON.stringify(root.topGiftersCfg));
    }

    function _saveKing() {
        if (!api || root.kingCfg === null) return;
        root.kingCfgEpoch += 1;
        if (typeof api.saveKingOfLiveOverlayConfigMap === "function")
            api.saveKingOfLiveOverlayConfigMap(root.kingCfg);
        else
            api.saveKingOfLiveOverlayConfigJson(JSON.stringify(root.kingCfg));
    }

    function _saveTierOverlay() {
        if (root.widgetMode === "top_gifters")
            root._saveTopGifters();
        else
            root._saveTopLikers();
    }

    readonly property bool _canSaveCurrentWidget:
        typeof api !== "undefined" && api !== null && (
            (root.widgetMode === "chat" && root.cfg !== null) ||
            (root.widgetMode === "actions" && root.actionsCfg !== null) ||
            (root.widgetMode === "online" && root.onlineCfg !== null) ||
            ((root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") && root.tierOverlayCfg !== null) ||
            (root.widgetMode === "king_of_live" && root.kingCfg !== null) ||
            (root.widgetMode === "battle_royale" && root.battleCfg !== null) ||
            (root.widgetMode === "stream_pet" && root.streamPetCfg !== null) ||
            (root.widgetMode === "community_world" && root.communityWorldCfg !== null) ||
            (root.widgetMode === "stream_goal" && root.streamGoalCfg !== null) ||
            (root.widgetMode === "live_leaderboard" && root.liveLeaderboardCfg !== null) ||
            (root.widgetMode === "social_rotator" && root.socialRotatorCfg !== null) ||
            (root.widgetMode === "webcam_frame" && root.webcamFrameCfg !== null) ||
            (root.widgetMode === "signal_system" && root.signalSystemCfg !== null)
        )

    function _flushTierOverlayEditorsIntoCfg() {
        if (root.tierOverlayCfg === null)
            return;
        if (typeof tlFontFamily !== "undefined") {
            var ff = (tlFontFamily.editText || tlFontFamily.currentText || "").trim();
            if (ff.length)
                root.tierOverlayCfg.font_family = ff;
        }
        if (typeof tlTextFx !== "undefined" && tlTextFx.currentIndex >= 0 && tlTextFx.currentIndex < tlTextFx.count) {
            var fx = tlTextFx.model.get(tlTextFx.currentIndex).value;
            if (fx)
                root.tierOverlayCfg.text_effect_username = fx;
        }
        if (typeof tlWaveSpd !== "undefined" && tlWaveSpd.currentIndex >= 0 && tlWaveSpd.currentIndex < tlWaveSpd.count) {
            var ws = tlWaveSpd.model.get(tlWaveSpd.currentIndex).value;
            if (ws)
                root.tierOverlayCfg.wave_speed = ws;
        }
        if (typeof tlLeaderSort !== "undefined") {
            var li = tlLeaderSort.currentIndex;
            if (li === 0)
                root.tierOverlayCfg.leader_sort = "likes_desc";
            else if (li === 1)
                root.tierOverlayCfg.leader_sort = "likes_asc";
            else
                root.tierOverlayCfg.leader_sort = "name_asc";
        }
        root.tierOverlayCfg.color_username = _colorToHex(_tlUsernameColor);
        root.tierOverlayCfg.color_points = _colorToHex(_tlPointsColor);
        root.tierOverlayCfg.color_rank = _colorToHex(_tlRankColor);
        root.tierOverlayCfg.font_border_color = _colorToHex(_tlBorderColor);
        root.tierOverlayCfg.username_text_shadow_color = _colorToHex(_tlUsernameShadowColor);
        root.tierOverlayCfg.likes_text_shadow_color = _colorToHex(_tlLikesShadowColor);
        root.tierOverlayCfg.bg_shadow_color = _rgbaString(_tlPanelShadowColor, _tlPanelShadowAlpha);
        root.tierOverlayCfg.list_bg_rgba = _rgbaString(_tlListBgColor, _tlListBgAlpha);
    }

    function _saveAndApplyCurrentWidget() {
        if (!root._canSaveCurrentWidget)
            return;
        if (root.widgetMode === "chat")
            root._save();
        else if (root.widgetMode === "actions")
            root._saveActions();
        else if (root.widgetMode === "online")
            root._saveOnline();
        else if (root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") {
            root._flushTierOverlayEditorsIntoCfg();
            root._saveTierOverlay();
        } else if (root.widgetMode === "king_of_live") {
            root._saveKing();
        } else if (root.widgetMode === "battle_royale") {
            root._saveBattle();
        } else if (root.widgetMode === "stream_pet") {
            root._saveStreamPet();
        } else if (root.widgetMode === "community_world") {
            root._saveCommunityWorld();
        } else if (root.widgetMode === "stream_goal") {
            root._saveStreamGoal();
        } else if (root.widgetMode === "live_leaderboard") {
            root._saveLiveLeaderboard();
        } else if (root.widgetMode === "social_rotator") {
            root._saveSocialRotator();
        } else if (root.widgetMode === "webcam_frame") {
            root._saveWebcamFrame();
        } else if (root.widgetMode === "signal_system") {
            root._saveSignalSystem();
        }
    }


    function loc(key) {
        if (typeof navApi !== "undefined" && navApi) {
            navApi.refreshCounter
            return navApi.loc(key)
        }
        return key
    }

    function _comboIndexFor(mdl, val) {
        if (!mdl) return 0
        for (var i = 0; i < mdl.count; ++i) {
            if (mdl.get(i).value === val) return i
        }
        return 0
    }

    // NOTE: same scoping caveat as _rebuildWebcamFrameComboModels below - the sgXxx*/srXxx*
    // ids live inside the `gatedUi` Component, not on root, so they must be passed in explicitly
    // rather than bare-referenced here (bare references from root always silently no-op, which
    // used to leave every one of these combo boxes empty).
    function _rebuildStreamGoalComboModels(goalTypeModel, goalTypeBox, skinModel, skinBox, animModel, animBox, resetModel, resetBox) {
        var prevSgLoading = root._loadingStreamGoalCfg
        root._loadingStreamGoalCfg = true

        if (goalTypeModel) {
            var goalVal = (root.streamGoalCfg && root.streamGoalCfg.goal_type) ? root.streamGoalCfg.goal_type : "followers"
            goalTypeModel.clear()
            goalTypeModel.append({ value: "followers", text: root.loc("stream_goal.ui.type.followers") })
            goalTypeModel.append({ value: "likes", text: root.loc("stream_goal.ui.type.likes") })
            goalTypeModel.append({ value: "gifts", text: root.loc("stream_goal.ui.type.gifts") })
            goalTypeModel.append({ value: "shares", text: root.loc("stream_goal.ui.type.shares") })
            goalTypeModel.append({ value: "comments", text: root.loc("stream_goal.ui.type.comments") })
            if (goalTypeBox)
                goalTypeBox.currentIndex = root._comboIndexFor(goalTypeModel, goalVal)
        }
        if (skinModel) {
            var skinVal = (root.streamGoalCfg && root.streamGoalCfg.skin) ? root.streamGoalCfg.skin : "digital_core"
            skinModel.clear()
            skinModel.append({ value: "digital_core", text: root.loc("stream_goal.ui.skin.digital_core") })
            skinModel.append({ value: "boss", text: root.loc("stream_goal.ui.skin.boss") })
            skinModel.append({ value: "reactor", text: root.loc("stream_goal.ui.skin.reactor") })
            skinModel.append({ value: "rocket", text: root.loc("stream_goal.ui.skin.rocket") })
            skinModel.append({ value: "vault", text: root.loc("stream_goal.ui.skin.vault") })
            skinModel.append({ value: "tower", text: root.loc("stream_goal.ui.skin.tower") })
            skinModel.append({ value: "creature", text: root.loc("stream_goal.ui.skin.creature") })
            if (skinBox)
                skinBox.currentIndex = root._comboIndexFor(skinModel, skinVal)
        }
        if (animModel) {
            var animVal = (root.streamGoalCfg && root.streamGoalCfg.animation_intensity) ? root.streamGoalCfg.animation_intensity : "medium"
            animModel.clear()
            animModel.append({ value: "low", text: root.loc("stream_goal.ui.anim.low") })
            animModel.append({ value: "medium", text: root.loc("stream_goal.ui.anim.medium") })
            animModel.append({ value: "high", text: root.loc("stream_goal.ui.anim.high") })
            if (animBox)
                animBox.currentIndex = root._comboIndexFor(animModel, animVal)
        }
        if (resetModel) {
            var resetVal = (root.streamGoalCfg && root.streamGoalCfg.reset_behavior) ? root.streamGoalCfg.reset_behavior : "after_completion"
            resetModel.clear()
            resetModel.append({ value: "after_completion", text: root.loc("stream_goal.ui.reset.after_completion") })
            resetModel.append({ value: "manual", text: root.loc("stream_goal.ui.reset.manual") })
            resetModel.append({ value: "new_stream", text: root.loc("stream_goal.ui.reset.new_stream") })
            if (resetBox)
                resetBox.currentIndex = root._comboIndexFor(resetModel, resetVal)
        }

        root._loadingStreamGoalCfg = prevSgLoading
    }

    function _rebuildSocialRotatorComboModels(transitionModel, transitionBox, themeModel, themeBox) {
        var prevSrLoading = root._loadingSocialRotatorCfg
        root._loadingSocialRotatorCfg = true

        if (transitionModel) {
            var trVal = (root.socialRotatorCfg && root.socialRotatorCfg.transition) ? root.socialRotatorCfg.transition : "glitch_morph"
            transitionModel.clear()
            transitionModel.append({ value: "glitch_morph", text: root.loc("social_rotator.ui.transition.glitch_morph") })
            transitionModel.append({ value: "data_stream", text: root.loc("social_rotator.ui.transition.data_stream") })
            transitionModel.append({ value: "energy_burst", text: root.loc("social_rotator.ui.transition.energy_burst") })
            transitionModel.append({ value: "scan", text: root.loc("social_rotator.ui.transition.scan") })
            transitionModel.append({ value: "pixel_dissolve", text: root.loc("social_rotator.ui.transition.pixel_dissolve") })
            transitionModel.append({ value: "fade", text: root.loc("social_rotator.ui.transition.fade") })
            if (transitionBox)
                transitionBox.currentIndex = root._comboIndexFor(transitionModel, trVal)
        }
        if (themeModel) {
            var themeVal = (root.socialRotatorCfg && root.socialRotatorCfg.theme) ? root.socialRotatorCfg.theme : "neon_cyber"
            themeModel.clear()
            themeModel.append({ value: "neon_cyber", text: root.loc("social_rotator.ui.theme.neon_cyber") })
            themeModel.append({ value: "synthwave", text: root.loc("social_rotator.ui.theme.synthwave") })
            themeModel.append({ value: "toxic", text: root.loc("social_rotator.ui.theme.toxic") })
            themeModel.append({ value: "ice", text: root.loc("social_rotator.ui.theme.ice") })
            themeModel.append({ value: "amber", text: root.loc("social_rotator.ui.theme.amber") })
            if (themeBox)
                themeBox.currentIndex = root._comboIndexFor(themeModel, themeVal)
        }

        root._loadingSocialRotatorCfg = prevSrLoading
    }

    // NOTE: this function lives on the root Item, but wfThemeModel/wfTheme/wfIntensityModel/
    // wfIntensity are ids declared inside the `gatedUi` Component (see the Loader below). QML id
    // scoping only flows outward (child components can see ancestor scope, never the reverse),
    // so those ids are NOT resolvable via bare reference from here - hence the explicit
    // parameters instead of `typeof wfThemeModel !== "undefined"` bare-id lookups, which always
    // evaluated to false and silently left the combo boxes empty.
    function _rebuildWebcamFrameComboModels(themeModel, themeBox, intensityModel, intensityBox, frameStyleModel, frameStyleBox) {
        var prevWfLoading = root._loadingWebcamFrameCfg
        root._loadingWebcamFrameCfg = true

        if (themeModel) {
            var wfThemeVal = (root.webcamFrameCfg && root.webcamFrameCfg.theme) ? root.webcamFrameCfg.theme : "neon_cyber"
            themeModel.clear()
            themeModel.append({ value: "neon_cyber", text: root.loc("webcam_frame.ui.theme.neon_cyber") })
            themeModel.append({ value: "synthwave", text: root.loc("webcam_frame.ui.theme.synthwave") })
            themeModel.append({ value: "toxic", text: root.loc("webcam_frame.ui.theme.toxic") })
            themeModel.append({ value: "ice", text: root.loc("webcam_frame.ui.theme.ice") })
            themeModel.append({ value: "amber", text: root.loc("webcam_frame.ui.theme.amber") })
            themeModel.append({ value: "critical", text: root.loc("webcam_frame.ui.theme.critical") })
            if (themeBox)
                themeBox.currentIndex = root._comboIndexFor(themeModel, wfThemeVal)
        }
        if (intensityModel) {
            var wfIntensityVal = (root.webcamFrameCfg && root.webcamFrameCfg.intensity) ? root.webcamFrameCfg.intensity : "medium"
            intensityModel.clear()
            intensityModel.append({ value: "low", text: root.loc("webcam_frame.ui.intensity.low") })
            intensityModel.append({ value: "medium", text: root.loc("webcam_frame.ui.intensity.medium") })
            intensityModel.append({ value: "high", text: root.loc("webcam_frame.ui.intensity.high") })
            if (intensityBox)
                intensityBox.currentIndex = root._comboIndexFor(intensityModel, wfIntensityVal)
        }
        if (frameStyleModel) {
            var wfFrameStyleVal = (root.webcamFrameCfg && root.webcamFrameCfg.frame_style) ? root.webcamFrameCfg.frame_style : "primary"
            frameStyleModel.clear()
            frameStyleModel.append({ value: "primary", text: root.loc("webcam_frame.ui.frame_style.primary") })
            frameStyleModel.append({ value: "minimal", text: root.loc("webcam_frame.ui.frame_style.minimal") })
            frameStyleModel.append({ value: "tactical", text: root.loc("webcam_frame.ui.frame_style.tactical") })
            frameStyleModel.append({ value: "broadcast", text: root.loc("webcam_frame.ui.frame_style.broadcast") })
            frameStyleModel.append({ value: "hologram", text: root.loc("webcam_frame.ui.frame_style.hologram") })
            if (frameStyleBox)
                frameStyleBox.currentIndex = root._comboIndexFor(frameStyleModel, wfFrameStyleVal)
        }

        root._loadingWebcamFrameCfg = prevWfLoading
    }

    function _saveStreamGoal() {
        if (!api || root.streamGoalCfg === null) return;
        root.streamGoalCfgEpoch += 1;
        api.saveStreamGoalOverlayConfigJson(JSON.stringify(root.streamGoalCfg));
    }

    function _saveLiveLeaderboard() {
        if (!api || root.liveLeaderboardCfg === null) return;
        root.liveLeaderboardCfgEpoch += 1;
        if (root.liveLeaderboardCfg.sequence)
            root.liveLeaderboardCfg.sequence_json = JSON.stringify(root.liveLeaderboardCfg.sequence);
        api.saveLiveLeaderboardOverlayConfigJson(JSON.stringify(root.liveLeaderboardCfg));
    }

    function _saveSocialRotator() {
        if (!api || root.socialRotatorCfg === null) return;
        root.socialRotatorCfgEpoch += 1;
        api.saveSocialRotatorOverlayConfigJson(JSON.stringify(root.socialRotatorCfg));
    }

    function _saveWebcamFrame() {
        if (!api || root.webcamFrameCfg === null) return;
        root.webcamFrameCfgEpoch += 1;
        api.saveWebcamFrameOverlayConfigJson(JSON.stringify(root.webcamFrameCfg));
    }

    property var signalSystemCfg: null
    property int signalSystemCfgEpoch: 0
    property bool _loadingSignalSystemCfg: false

    function _saveSignalSystem() {
        if (!api || root.signalSystemCfg === null) return;
        root.signalSystemCfgEpoch += 1;
        if (typeof api.saveSignalSystemOverlayConfigMap === "function")
            api.saveSignalSystemOverlayConfigMap(root.signalSystemCfg);
        else
            api.saveSignalSystemOverlayConfigJson(JSON.stringify(root.signalSystemCfg));
    }

    function _rebuildSignalSystemComboModels(themeModel, themeBox) {
        var prevSsLoading = root._loadingSignalSystemCfg
        root._loadingSignalSystemCfg = true
        if (themeModel) {
            var themeVal = (root.signalSystemCfg && root.signalSystemCfg.theme) ? root.signalSystemCfg.theme : "neon_cyber"
            themeModel.clear()
            themeModel.append({ value: "neon_cyber", text: root.loc("signal_system.theme.neon_cyber") })
            themeModel.append({ value: "toxic_system", text: root.loc("signal_system.theme.toxic_system") })
            themeModel.append({ value: "ice_protocol", text: root.loc("signal_system.theme.ice_protocol") })
            themeModel.append({ value: "amber_core", text: root.loc("signal_system.theme.amber_core") })
            themeModel.append({ value: "critical", text: root.loc("signal_system.theme.critical") })
            if (themeBox)
                themeBox.currentIndex = root._comboIndexFor(themeModel, themeVal)
        }
        root._loadingSignalSystemCfg = prevSsLoading
    }

    function _srMovePlatform(index, delta) {
        if (!root.socialRotatorCfg || !root.socialRotatorCfg.platforms) return;
        var arr = root.socialRotatorCfg.platforms.slice();
        var j = index + delta;
        if (j < 0 || j >= arr.length) return;
        var tmp = arr[index];
        arr[index] = arr[j];
        arr[j] = tmp;
        for (var i = 0; i < arr.length; i++) arr[i].order = i;
        root.socialRotatorCfg.platforms = arr;
        root._saveSocialRotator();
    }

    function _srRemovePlatform(index) {
        if (!root.socialRotatorCfg || !root.socialRotatorCfg.platforms) return;
        var arr = root.socialRotatorCfg.platforms.slice();
        if (index < 0 || index >= arr.length) return;
        arr.splice(index, 1);
        for (var i = 0; i < arr.length; i++) arr[i].order = i;
        root.socialRotatorCfg.platforms = arr;
        root._saveSocialRotator();
    }

    function _srAddPlatform(platformId) {
        if (!root.socialRotatorCfg) return;
        var arr = (root.socialRotatorCfg.platforms || []).slice();
        arr.push({
            id: "p" + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
            platform: platformId || "twitch",
            username: "",
            url: "",
            enabled: true,
            order: arr.length
        });
        root.socialRotatorCfg.platforms = arr;
        root._saveSocialRotator();
    }

    function _ensureLiveLeaderboardSourceInSequence(sourceId) {
        if (!root.liveLeaderboardCfg) return;
        var arr = (root.liveLeaderboardCfg.sequence || []).slice();
        for (var i = 0; i < arr.length; i++) {
            if (arr[i] && String(arr[i].source_id || "") === sourceId)
                return;
        }
        arr.push({ source_id: sourceId, scene_id: "hall_of_fame", duration_sec: 8 });
        root.liveLeaderboardCfg.sequence = arr;
    }

    function _saveBattle() {
        if (!api || root.battleCfg === null) return;
        root.battleCfgEpoch += 1;
        // battleCfg is a cloned plain JS object; JSON.stringify is reliable (ConfigMap/toVariant often is not).
        var txt = JSON.stringify(root.battleCfg);
        if (!txt || txt === "{}")
            return;
        api.saveBattleRoyaleOverlayConfigJson(txt);
    }

    function _saveStreamPet() {
        if (!api || root.streamPetCfg === null) return;
        root.streamPetCfgEpoch += 1;
        if (typeof api.saveStreamPetOverlayConfigMap === "function")
            api.saveStreamPetOverlayConfigMap(root.streamPetCfg);
        else
            api.saveStreamPetOverlayConfigJson(JSON.stringify(root.streamPetCfg));
    }

    function _saveCommunityWorld() {
        if (!api || root.communityWorldCfg === null) return;
        root.communityWorldCfgEpoch += 1;
        // This config is a plain JS object (loaded through JSON.parse). Passing it
        // through QJSValue can be converted to an empty QVariantMap by some Qt builds.
        // JSON keeps the edited value intact and also publishes the live overlay patch.
        api.saveCommunityWorldOverlayConfigJson(JSON.stringify(root.communityWorldCfg));
    }

    function _applyStreamPetPreset(presetId) {
        if (!api || root.streamPetCfg === null) return;
        var pid = String(presetId || "classic_gold");
        if (typeof api.streamPetPresetDefaultsMap !== "function") {
            root.streamPetCfg.preset = pid;
            root._saveStreamPet();
            return;
        }
        var patch = api.streamPetPresetDefaultsMap(pid);
        if (!patch || typeof patch !== "object") return;
        root.streamPetCfg = JSON.parse(JSON.stringify(patch));
        root._spBodyColor = root.streamPetCfg.pet_body_color || "#fbbf24";
        root._spEarColor = root.streamPetCfg.pet_ear_color || "#f59e0b";
        root._spCollarColor = root.streamPetCfg.collar_color || "#ef4444";
        root._spBubbleBgColor = root.streamPetCfg.bubble_bg_color || "#ffffff";
        root._saveStreamPet();
    }

    readonly property bool _streamPetCustom:
        root.streamPetCfg && String(root.streamPetCfg.preset || "classic_gold").toLowerCase() === "custom"

    function _syncTierOverlayCombosFromCfg() {
        if (!root.tierOverlayCfg)
            return;
        if (typeof tlFontFamily !== "undefined" && root.tierOverlayCfg) {
            var tff = (root.tierOverlayCfg.font_family || "").trim();
            var ti = tlFontFamily.model.indexOf(tff);
            if (ti >= 0) tlFontFamily.currentIndex = ti;
            else { tlFontFamily.currentIndex = -1; tlFontFamily.editText = tff || "Segoe UI"; }
        }
        if (typeof tlTextFx !== "undefined" && root.tierOverlayCfg) {
            var tx = String(root.tierOverlayCfg.text_effect_username || "none").toLowerCase();
            var foundFx = false;
            for (var tj = 0; tj < tlTextFx.count; ++tj) {
                if (tlTextFx.model.get(tj).value === tx) {
                    tlTextFx.currentIndex = tj;
                    foundFx = true;
                    break;
                }
            }
            if (!foundFx)
                tlTextFx.currentIndex = 0;
        }
        if (typeof tlWaveSpd !== "undefined" && root.tierOverlayCfg) {
            var ws = String(root.tierOverlayCfg.wave_speed || "normal").toLowerCase();
            var foundWs = false;
            for (var wj = 0; wj < tlWaveSpd.count; ++wj) {
                if (tlWaveSpd.model.get(wj).value === ws) {
                    tlWaveSpd.currentIndex = wj;
                    foundWs = true;
                    break;
                }
            }
            if (!foundWs)
                tlWaveSpd.currentIndex = 1;
        }
        if (typeof tlLeaderSort !== "undefined" && root.tierOverlayCfg) {
            var r = String(root.tierOverlayCfg.leader_sort || "likes_desc").toLowerCase();
            if (r === "likes_asc") tlLeaderSort.currentIndex = 1;
            else if (r === "name_asc") tlLeaderSort.currentIndex = 2;
            else tlLeaderSort.currentIndex = 0;
        }
    }

    function _pullTierOverlayColorsFromCfg() {
        if (!root.tierOverlayCfg)
            return;
        _tlUsernameColor = root.tierOverlayCfg.color_username || "#c4b5fd";
        _tlPointsColor = root.tierOverlayCfg.color_points || "#f4f4f5";
        _tlRankColor = root.tierOverlayCfg.color_rank || "#d9d9d9";
        _tlBorderColor = root.tierOverlayCfg.font_border_color || "#242424";
        _tlUsernameShadowColor = _tlColorFromCfg(root.tierOverlayCfg.username_text_shadow_color);
        _tlLikesShadowColor = _tlColorFromCfg(root.tierOverlayCfg.likes_text_shadow_color);
        var bsp2 = _parseRgba(root.tierOverlayCfg.bg_shadow_color || "rgba(33,33,33,0.4)");
        _tlPanelShadowColor = bsp2.c;
        _tlPanelShadowAlpha = bsp2.a;
        var tlp2 = _parseRgba(root.tierOverlayCfg.list_bg_rgba || "rgba(18,20,28,0.72)");
        _tlListBgColor = tlp2.c;
        _tlListBgAlpha = tlp2.a;
        if (typeof tlListBgAlphaSb !== "undefined")
            tlListBgAlphaSb.value = Math.round(_tlListBgAlpha * 100);
        if (typeof tlPanelShadowAlphaSb !== "undefined")
            tlPanelShadowAlphaSb.value = Math.round(_tlPanelShadowAlpha * 100);
    }

    onLayoutsOnlyChanged: {
        if (root.layoutsOnly) {
            root.refreshWidgetInstances();
            root.showLayoutList();
        }
    }

    Connections {
        target: (typeof api !== "undefined" && api) ? api : null
        function onLayoutsChanged() {
            if (root.layoutsOnly)
                root.refreshLayouts();
        }
    }

    onWidgetModeChanged: {
        if (root.widgetMode === "grid") {
            root.clearEditingInstance();
            root.refreshWidgetInstances();
            root.refreshLayouts();
        }
        if (root.widgetMode === "top_likers")
            root.tierOverlayCfg = root.topLikersCfg;
        else if (root.widgetMode === "top_gifters")
            root.tierOverlayCfg = root.topGiftersCfg;
        else
            root.tierOverlayCfg = null;
        if (root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") {
            root._pullTierOverlayColorsFromCfg();
            Qt.callLater(function() { root._syncTierOverlayCombosFromCfg(); });
        }
    }

    // QVariantMap from load*ConfigMap() is not always a plain JS object; cloning avoids
    // JSON.stringify -> "{}" on save and prevents mutating engine-owned maps in-place.
    function _detachCfgMap(m) {
        var x = m;
        if (!x || typeof x !== "object")
            x = {};
        try {
            return JSON.parse(JSON.stringify(x));
        } catch (e) {
            console.warn("WidgetsView: cfg clone failed:", e);
            return {};
        }
    }

    function _detachTierOverlayCfgMap(m) {
        return root._detachCfgMap(m);
    }

    function _syncActionsCombosFromCfg() {
        if (!root.actionsCfg)
            return;
        if (typeof actionsFontFamily !== "undefined") {
            var ff = (root.actionsCfg.font_family || "").trim();
            var fi = actionsFontFamily.model.indexOf(ff);
            if (fi >= 0)
                actionsFontFamily.currentIndex = fi;
            else {
                actionsFontFamily.currentIndex = -1;
                actionsFontFamily.editText = ff || "Segoe UI";
            }
        }
        if (typeof actionsUsernameEffect !== "undefined") {
            var raw = (root.actionsCfg.username_text_effect || "none").trim().toLowerCase();
            actionsUsernameEffect.currentIndex =
                (raw === "rainbow") ? 1
                : (raw === "aurora") ? 2
                : (raw === "neon") ? 3
                : (raw === "fire") ? 4
                : 0;
        }
    }

    function _syncChatCombosFromCfg() {
        if (!root.cfg)
            return;
        if (typeof usernameColorMode !== "undefined") {
            var mode = root.cfg.username_color_mode || "auto";
            usernameColorMode.currentIndex =
                (mode === "platform") ? 1 : ((mode === "custom") ? 2 : 0);
        }
        if (typeof fontFamily !== "undefined") {
            var cff = (root.cfg.font_family || "").trim();
            var cfi = fontFamily.model.indexOf(cff);
            if (cfi >= 0)
                fontFamily.currentIndex = cfi;
            else {
                fontFamily.currentIndex = -1;
                fontFamily.editText = cff || "Segoe UI";
            }
        }
    }

    function _syncOnlineCombosFromCfg() {
        if (!root.onlineCfg)
            return;
        if (typeof onlineLayoutMode !== "undefined") {
            var lm = root.onlineCfg.layout_mode || "combined";
            onlineLayoutMode.currentIndex = (lm === "per_platform") ? 1 : 0;
        }
        if (typeof onlineFontFamily !== "undefined") {
            var off = (root.onlineCfg.font_family || "").trim();
            var ofi = onlineFontFamily.model.indexOf(off);
            if (ofi >= 0)
                onlineFontFamily.currentIndex = ofi;
            else {
                onlineFontFamily.currentIndex = -1;
                onlineFontFamily.editText = off || "Segoe UI";
            }
        }
        if (typeof onlineTextEffect !== "undefined") {
            var fx = (root.onlineCfg.text_effect || "none").trim().toLowerCase();
            onlineTextEffect.currentIndex =
                (fx === "glow") ? 1
                : (fx === "neon") ? 2
                : (fx === "rainbow") ? 3
                : (fx === "aurora") ? 4
                : (fx === "fire") ? 5
                : 0;
        }
    }

    function _ensureTopLikersDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (!obj.font_family) obj.font_family = "Segoe UI";
        if (obj.font_size_px === undefined) obj.font_size_px = 22;
        if (obj.font_line_spacing_px === undefined) obj.font_line_spacing_px = 4;
        if (obj.font_letter_spacing_px === undefined) obj.font_letter_spacing_px = 0;
        if (!obj.color_username) obj.color_username = "#c4b5fd";
        if (!obj.color_points) obj.color_points = "#f4f4f5";
        if (!obj.color_rank) obj.color_rank = "#d9d9d9";
        if (obj.bg_shadow_enabled === undefined) obj.bg_shadow_enabled = false;
        if (!obj.bg_shadow_color) obj.bg_shadow_color = "rgba(33,33,33,0.4)";
        if (obj.username_text_shadow_enabled === undefined) obj.username_text_shadow_enabled = false;
        if (!obj.username_text_shadow_color) obj.username_text_shadow_color = "#000000";
        if (obj.likes_text_shadow_enabled === undefined) obj.likes_text_shadow_enabled = false;
        if (!obj.likes_text_shadow_color) obj.likes_text_shadow_color = "#000000";
        if (!obj.leader_sort) obj.leader_sort = "likes_desc";
        if (obj.show_rank === undefined) obj.show_rank = true;
        if (obj.show_likes === undefined) obj.show_likes = true;
        if (obj.rtl === undefined) obj.rtl = false;
        if (obj.show_top1_crown === undefined) obj.show_top1_crown = true;
        if (obj.show_top3_medal === undefined) obj.show_top3_medal = true;
        if (obj.show_heart === undefined) obj.show_heart = true;
        if (obj.heart_animated === undefined) obj.heart_animated = true;
        if (obj.heart_size_px === undefined) obj.heart_size_px = 14;
        if (!obj.text_effect_username) obj.text_effect_username = "none";
        if (obj.wave_enabled === undefined) obj.wave_enabled = false;
        if (!obj.wave_speed) obj.wave_speed = "normal";
        if (obj.font_border_enabled === undefined) obj.font_border_enabled = true;
        if (!obj.font_border_color) obj.font_border_color = "#242424";
        if (obj.top_count === undefined) obj.top_count = 8;
        if (obj.avatar_size_px === undefined) obj.avatar_size_px = 48;
        if (obj.row_gap_px === undefined) obj.row_gap_px = 10;
        if (obj.list_bg_enabled === undefined) obj.list_bg_enabled = true;
        if (!obj.list_bg_rgba) obj.list_bg_rgba = "rgba(18,20,28,0.72)";
        if (obj.list_radius_px === undefined) obj.list_radius_px = 12;
        if (obj.list_scroll_interval_sec === undefined) obj.list_scroll_interval_sec = 0;
        return obj;
    }

    function _saveTopLikers() {
        if (!api || root.topLikersCfg === null) return;
        root.topLikersCfgEpoch += 1;
        if (typeof api.saveTopLikersOverlayConfigMap === "function")
            api.saveTopLikersOverlayConfigMap(root.topLikersCfg);
        else
            api.saveTopLikersOverlayConfigJson(JSON.stringify(root.topLikersCfg));
    }

    Loader {
        id: apiGate
        anchors.fill: parent
        active: typeof api !== "undefined" && api !== null
        sourceComponent: gatedUi
    }

    Text {
        anchors.centerIn: parent
        visible: !apiGate.active
        text: "Widgets API is not available yet."
        color: muted
        font.pixelSize: 13
    }

    Component {
        id: gatedUi
        ColumnLayout {
            id: cfgHost
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            // Custom title bar (frameless window controls).
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: root.titleBarH
                visible: typeof winApi !== "undefined" && winApi !== null
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onDoubleClicked: if (winApi) winApi.toggleMaximize()
                    onPressed: if (winApi) winApi.startMove()
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    Text {
                        text: root.layoutsOnly ? root.loc("ui.nav_layouts") : "Віджети"
                        color: ink
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    // Window controls
                    component WinBtn: Rectangle {
                        id: b
                        signal clicked()
                        property string glyph: "?"
                        property color bgRest: "#1c2434"
                        property color bgHover: "#263246"
                        property color bgPress: "#303a50"
                        property color fg: root.ink
                        property color bor: root.cardEdge
                        property color borHover: "#3b4458"
                        property bool danger: false
                        implicitWidth: 34
                        implicitHeight: 28
                        radius: 8
                        border.width: 1
                        color: ma.pressed ? (danger ? "#7f1d1d" : bgPress) : (ma.containsMouse ? (danger ? "#991b1b" : bgHover) : bgRest)
                        border.color: ma.containsMouse ? borHover : bor
                        Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                        Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }

                        Text {
                            anchors.centerIn: parent
                            text: b.glyph
                            color: b.fg
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }

                        MouseArea {
                            id: ma
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: b.clicked()
                        }
                    }

                    WinBtn {
                        glyph: "—"
                        Layout.alignment: Qt.AlignVCenter
                        onClicked: if (winApi) winApi.minimize()
                    }

                    WinBtn {
                        glyph: (typeof winApi !== "undefined" && winApi && winApi.isMaximized()) ? "❐" : "□"
                        Layout.alignment: Qt.AlignVCenter
                        onClicked: if (winApi) winApi.toggleMaximize()
                    }

                    WinBtn {
                        glyph: "×"
                        danger: true
                        Layout.alignment: Qt.AlignVCenter
                        onClicked: if (winApi) winApi.close()
                    }
                }
            }

            // Universal editor shell. It deliberately overlays the legacy per-type forms while
            // their proven configuration/save adapters remain available underneath.
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                z: 100
                visible: root.universalEditorActive
                Loader {
                    id: universalEditorLoader
                    anchors.fill: parent
                    active: root.universalEditorActive
                    source: "UniversalWidgetEditor.qml"
                    asynchronous: true

                    Binding { target: universalEditorLoader.item; property: "instanceName"; value: root.editingInstanceName || "Widget instance"; when: universalEditorLoader.item !== null }
                    Binding { target: universalEditorLoader.item; property: "instanceId"; value: root.editingInstanceId; when: universalEditorLoader.item !== null }
                    Binding { target: universalEditorLoader.item; property: "typeName"; value: root.galleryTypeById(root.widgetMode).name || root.widgetMode; when: universalEditorLoader.item !== null }
                    Binding { target: universalEditorLoader.item; property: "typeId"; value: root.widgetMode; when: universalEditorLoader.item !== null }
                    Binding { target: universalEditorLoader.item; property: "sections"; value: root.universalSchema(root.widgetMode, root.universalConfig()); when: universalEditorLoader.item !== null }

                    Connections {
                        target: universalEditorLoader.item
                        function onBackRequested() { root.clearEditingInstance(); root.widgetMode = "grid" }
                        function onResetRequested() { cfgHost.reloadAllWidgetConfigs(); if (universalEditorLoader.item) universalEditorLoader.item.saveState = "saved" }
                        function onSaveRequested() { root._saveAndApplyCurrentWidget() }
                        function onCopyRequested() { if (api) api.copyWidgetInstanceUrl(root.editingInstanceId) }
                        function onSettingChanged(field, value) { root.applyUniversalSetting(field, value) }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "grid" && !root.layoutsOnly
                implicitHeight: gridCol.implicitHeight + 20

                ColumnLayout {
                    id: gridCol
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: root.loc("widgets.gallery.title")
                                color: ink
                                font.pixelSize: 26
                                font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.loc("widgets.gallery.subtitle")
                                color: muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }
                        }
                        TextField {
                            id: gallerySearchField
                            Layout.preferredWidth: 230
                            Layout.preferredHeight: 38
                            placeholderText: root.loc("widgets.gallery.search_ph")
                            text: root.gallerySearch
                            color: ink
                            font.pixelSize: 12
                            leftPadding: 32
                            onTextChanged: root.gallerySearch = text
                            background: Rectangle {
                                radius: 8; color: "#0b0f17"; border.width: 1
                                border.color: gallerySearchField.activeFocus ? "#7c3aed" : (gallerySearchField.hovered ? "#4c1d95" : cardEdge)
                                Behavior on border.color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                Text { x: 10; anchors.verticalCenter: parent.verticalCenter; text: "⌕"; color: muted; font.pixelSize: 15 }
                            }
                        }
                        StyledComboBox {
                            id: galleryCatBox
                            Layout.preferredWidth: 180
                            Layout.preferredHeight: 38
                            model: [root.loc("widgets.gallery.all_categories"), "TikTok", "Twitch", "YouTube", "Kick"]
                            currentIndex: 0
                            onUserActivated: function(idx) {
                                root.galleryCategory = ["all","tiktok","twitch","youtube","kick"][idx] || "all";
                            }
                            onActivated: function(idx) {
                                root.galleryCategory = ["all","tiktok","twitch","youtube","kick"][idx] || "all";
                            }
                        }
                        Rectangle {
                            id: createWidgetButton
                            implicitWidth: 180; implicitHeight: 38; radius: 10
                            property bool hovered: createWidgetMa.containsMouse
                            transformOrigin: Item.Center
                            scale: createWidgetMa.pressed ? 0.98 : (hovered ? 1.018 : 1.0)
                            border.width: 1
                            border.color: hovered ? "#c4b5fd" : "transparent"
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: createWidgetMa.pressed ? "#9333ea" : (createWidgetButton.hovered ? "#b76cff" : "#a855f7") }
                                GradientStop { position: 0.55; color: createWidgetMa.pressed ? "#4f46e5" : (createWidgetButton.hovered ? "#7375ff" : "#6366f1") }
                                GradientStop { position: 1.0; color: createWidgetMa.pressed ? "#2563eb" : (createWidgetButton.hovered ? "#4f8dff" : "#3b82f6") }
                            }
                            Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                            Behavior on border.color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
                            RowLayout {
                                anchors.centerIn: parent; spacing: 6
                                Text { text: "+"; color: "white"; font.pixelSize: 18; font.bold: true }
                                Text { text: root.loc("widgets.gallery.create"); color: "white"; font.pixelSize: 13; font.bold: true }
                            }
                            MouseArea { id: createWidgetMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { root.refreshWidgetInstances(); root.showCreateWidget = true; } }
                        }
                    }

                    // ---- Stats row: three compact cards + simple promo ----
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        // Total
                        Rectangle {
                            Layout.fillWidth: false; Layout.preferredWidth: 200; implicitHeight: 64; radius: 9
                            color: "#0E1521"; border.width: 1; border.color: "#1f2940"
                            RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "◈"; color: "#8b7cf6"; font.pixelSize: 18 }
                                ColumnLayout { spacing: 1
                                    Text { text: String(root.galleryCount("all")); color: "#eef2f7"; font.pixelSize: 20; font.bold: true }
                                    Text { text: root.loc("widgets.gallery.total"); color: "#8b95a5"; font.pixelSize: 11 }
                                }
                            }
                        }
                        // Active
                        Rectangle {
                            Layout.fillWidth: false; Layout.preferredWidth: 200; implicitHeight: 64; radius: 9
                            color: "#0E1521"; border.width: 1; border.color: "#1f2940"
                            RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Rectangle { implicitWidth: 8; implicitHeight: 8; radius: 4; color: "#22c55e" }
                                ColumnLayout { spacing: 1
                                    Text { text: String(root.galleryActiveCount()); color: "#eef2f7"; font.pixelSize: 20; font.bold: true }
                                    Text { text: root.loc("widgets.gallery.active"); color: "#8b95a5"; font.pixelSize: 11 }
                                }
                            }
                        }
                        // Disabled
                        Rectangle {
                            Layout.fillWidth: false; Layout.preferredWidth: 200; implicitHeight: 64; radius: 9
                            color: "#0E1521"; border.width: 1; border.color: "#1f2940"
                            RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Rectangle { implicitWidth: 8; implicitHeight: 8; radius: 4; color: "#64748b" }
                                ColumnLayout { spacing: 1
                                    Text { text: String(root.galleryDisabledCount()); color: "#eef2f7"; font.pixelSize: 20; font.bold: true }
                                    Text { text: root.loc("widgets.gallery.disabled"); color: "#8b95a5"; font.pixelSize: 11 }
                                }
                            }
                        }
                        // Promo: simple dark violet surface, crown + texts + arrow
                        Rectangle {
                            Layout.fillWidth: true; Layout.minimumWidth: 280; implicitHeight: 64; radius: 9
                            color: "#141a33"; border.width: 1; border.color: "#2b3560"
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; anchors.topMargin: 8; anchors.bottomMargin: 8; spacing: 10
                                Rectangle { implicitWidth: 3; implicitHeight: 32; radius: 2; color: "#7c5cf0" }
                                Text { text: "♛"; color: "#8fa8ff"; font.pixelSize: 20 }
                                ColumnLayout { spacing: 1; Layout.fillWidth: true
                                    Text { text: root.loc("widgets.gallery.promo_title"); color: "#ffffff"; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight }
                                    Text { text: root.loc("widgets.gallery.promo_sub"); color: "#9aa7c2"; font.pixelSize: 11; elide: Text.ElideRight }
                                }
                                Text { text: "→"; color: "#8b95a5"; font.pixelSize: 14 }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: [
                                {id: "all", label: root.loc("widgets.gallery.filter_all") + " (" + root.galleryCount("all") + ")"},
                                {id: "tiktok", label: "♪ TikTok (" + root.galleryCount("tiktok") + ")"},
                                {id: "twitch", label: "◈ Twitch (" + root.galleryCount("twitch") + ")"},
                                {id: "youtube", label: "▷ YouTube (" + root.galleryCount("youtube") + ")"},
                                {id: "kick", label: "⚡ Kick (" + root.galleryCount("kick") + ")"}
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                implicitHeight: 32; implicitWidth: catLbl.implicitWidth + 28; radius: 16
                                property bool hovered: catMa.containsMouse
                                transformOrigin: Item.Center
                                scale: catMa.pressed ? 0.97 : (hovered ? 1.025 : 1.0)
                                color: catMa.pressed ? "#5b21b6" : (root.galleryCategory === modelData.id ? "#7c3aed" : (hovered ? "#1e1b4b" : "#0d1320"))
                                border.width: 1; border.color: root.galleryCategory === modelData.id ? "#a78bfa" : (hovered ? "#6d5acb" : cardEdge)
                                Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                Behavior on color { ColorAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                Behavior on border.color { ColorAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                Text { id: catLbl; anchors.centerIn: parent; text: parent.modelData.label; color: root.galleryCategory === parent.modelData.id ? "white" : inkSecondary; font.pixelSize: 12; font.bold: root.galleryCategory === parent.modelData.id }
                                MouseArea { id: catMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.galleryCategory = parent.modelData.id }
                            }
                        }
                        Item { Layout.fillWidth: true }
                        StyledComboBox {
                            id: gallerySortBox
                            Layout.preferredWidth: 210
                            Layout.preferredHeight: 38
                            model: [root.loc("widgets.gallery.sort_name"), root.loc("widgets.gallery.sort_status"), root.loc("widgets.gallery.sort_platform")]
                            currentIndex: root.gallerySort
                            contentItem: Text {
                                text: root.loc("widgets.gallery.sort_label") + " " + gallerySortBox.displayText
                                color: root.ink
                                font.pixelSize: 12
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            onUserActivated: function(idx) { root.gallerySort = idx; }
                            onActivated: function(idx) { root.gallerySort = idx; }
                        }
                    }

                    // ---- Widget instances data (no legacy list UI; gallery below is the only list) ----
                    // compat-refs: widgets.instances.create_button widgets.common.duplicate
                    Text { visible: false; text: root.loc("widgets.instances.create_button") + root.loc("widgets.common.duplicate") }
                    Connections {
                        ignoreUnknownSignals: true
                        target: (typeof api !== "undefined") ? api : null
                        function onWidgetInstancesChanged() { root.refreshWidgetInstances(); }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 12
                        color: "#111827"
                        border.width: 1
                        border.color: cardEdge
                        visible: root.showCreateWidget
                        implicitHeight: createCol.implicitHeight + 16
                        ColumnLayout {
                            id: createCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 8
                            Text { text: root.loc("widgets.instances.new_title"); color: ink; font.pixelSize: 15; font.bold: true }
                            StyledComboBox {
                                id: newTypeBox
                                Layout.fillWidth: true
                                model: (root.widgetTypeList || []).map(function(t) { return (t.icon || "") + " " + (t.name || t.type_id); })
                                onUserActivated: function(idx) {
                                    var t = (root.widgetTypeList || [])[idx];
                                    if (t) root.newInstanceType = t.type_id;
                                }
                                onActivated: function(idx) {
                                    var t2 = (root.widgetTypeList || [])[idx];
                                    if (t2) root.newInstanceType = t2.type_id;
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                color: muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                text: {
                                    var t = (root.widgetTypeList || []).filter(function(x) { return x.type_id === root.newInstanceType; })[0];
                                    return t ? (t.description || "") : "";
                                }
                            }
                            TextField {
                                id: newNameField
                                Layout.fillWidth: true
                                placeholderText: root.loc("widgets.instances.name_placeholder")
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: "#0b0f17"; border.width: 1; border.color: cardEdge }
                                onTextChanged: root.newInstanceName = text
                            }
                            RowLayout {
                                spacing: 8
                                PillButton {
                                    text: root.loc("widgets.common.create")
                                    onClicked: {
                                        var nm = (root.newInstanceName || "").trim();
                                        if (!nm) nm = root.newInstanceType;
                                        var nid = "";
                                        if (api) nid = api.createWidgetInstance(root.newInstanceType, nm);
                                        root.newInstanceName = "";
                                        newNameField.text = "";
                                         root.showCreateWidget = false;
                                         root.refreshWidgetInstances();
                                         if (nid) {
                                            var created = null;
                                            var list = root.widgetInstanceList || [];
                                            for (var ci = 0; ci < list.length; ++ci) {
                                                if (list[ci].id === nid) { created = list[ci]; break; }
                                            }
                                            root.editWidgetInstance(created || {id: nid, type_id: root.newInstanceType, name: nm});
                                        } else {
                                            console.warn("createWidgetInstance returned empty id; not opening editor");
                                        }
                                    }
                                }
                                PillButton {
                                    text: root.loc("widgets.common.cancel")
                                    onClicked: root.showCreateWidget = false
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 12
                        color: "#111827"
                        border.width: 1
                        border.color: cardEdge
                        visible: typeof tunnelApi !== "undefined" && tunnelApi !== null
                        implicitHeight: tunnelPanel.implicitHeight + 16

                        ColumnLayout {
                            id: tunnelPanel
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            StyledCheckBox {
                                text: tunnelApi ? tunnelApi.tunnelEnabledLabel : ""
                                checked: tunnelApi ? tunnelApi.tunnelEnabled : false
                                onToggled: if (tunnelApi) tunnelApi.setTunnelEnabled(checked)
                            }

                            Text {
                                Layout.fillWidth: true
                                text: tunnelApi ? tunnelApi.tunnelHelpText : ""
                                color: muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: tunnelApi && tunnelApi.tunnelEnabled
                                text: tunnelApi ? tunnelApi.tunnelStatusText : ""
                                color: ink
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                     ScrollView {
                        id: galleryScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: 420
                        Layout.minimumHeight: 200
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        CheremshaResponsiveCardGrid {
                        width: galleryScroll.availableWidth
                        // Readable cards first: 270px minimum + 14px gaps.
                        // 6 cols wide desktop → 2 cols narrow.
                        columns: Math.max(2, Math.floor((width + 14) / 284))
                        columnSpacing: 14
                        rowSpacing: 14

                        Repeater {
                            model: root.galleryFilteredTypes()
                            delegate: CheremshaSourceCard {
                                        id: gcard
                                        required property var modelData
                                        property var wtype: modelData.wtype
                                        property var instance: modelData.instance
                                        property var pageRoot: root
                                        property string wstatus: modelData.instance
                                            ? (modelData.instance.enabled ? "active" : "disabled")
                                            : "active"
                                        property bool _copied: false
                                        property string dupText: root.loc("widgets.common.duplicate")
                                        property string delText: root.loc("widgets.common.delete")
                                        // Raise above neighbour cards while the dropdown is open.
                                        z: cardMenu.visible ? 100 : 0
                                        // Fallback widgets (no instance yet) render with defaults = active.
                                        property bool cardOn: wstatus === "active"

                                        title: ((instance && instance.name) || (wtype && (wtype.name || wtype.type_id))) || ""
                                        description: (wtype && wtype.description) || ""
                                        iconSource: Qt.resolvedUrl("../assets/" + ((wtype && wtype.icon_svg) || "icons/web_multichat.svg"))
                                        accentColor: (wtype && wtype.accent) || "#8b5cf6"
                                        statusText: cardOn ? root.loc("widgets.gallery.enabled") : root.loc("widgets.gallery.disabled")
                                        statusColor: cardOn ? "#22c55e" : muted
                                        statusDotColor: cardOn ? "#22c55e" : "#6b7280"
                                        url: galleryCardUrl()
                                        previewBadgeText: (root.galleryPlatforms(wtype).join(" · ") || "all")
                                        previewBadgeColor: platBadgeColor()
                                        openButtonText: root.loc("widgets.gallery.open")
                                        copyButtonText: _copied ? root.loc("widgets.gallery.copied") : root.loc("widgets.gallery.copy_url")
                                        showMenuButton: true
                                        showToggle: true
                                        toggleOn: cardOn
                                        toggleTipText: root.loc("widgets.gallery.toggle")
                                        clickEnabled: true
                                        openIconOnly: true
                                        accentFlow: true
                                        descriptionMinHeight: 34
                                        onCopyClicked: {
                                            var iid = gcard.ensureInstId();
                                            if (iid && typeof api !== "undefined" && api) api.copyWidgetInstanceUrl(iid);
                                            gcard._copied = true;
                                            copiedTimer.restart();
                                        }
                                        onOpenClicked: {
                                            var pid = gcard.ensureInstId();
                                            if (pid && typeof api !== "undefined" && api) api.openWidgetInstanceUrl(pid);
                                        }
                                        onToggleClicked: {
                                            var tid = gcard.ensureInstId();
                                            if (tid && typeof api !== "undefined" && api) {
                                                api.setWidgetInstanceEnabled(tid, !gcard.cardOn);
                                                gcard.pageRoot.refreshWidgetInstances();
                                            }
                                        }
                                        onMenuClicked: cardMenu.visible ? cardMenu.close() : cardMenu.open()
                                        onCardClicked: {
                                            if (cardMenu.visible) { cardMenu.close(); return; }
                                            gcard.openEditor();
                                        }
                                        previewContent: pickPreview()

                                        // ---- per-type preview data (presentation layer only;
                                        // the generic card never sees widget types) ----
                                        property var previewSpec: selectPreviewSpec()
                                        function platBadgeColor() {
                                            var plats = root.galleryPlatforms(wtype);
                                            var first = (plats && plats.length) ? plats[0] : "all";
                                            var m = {tiktok: "#67e8f9", twitch: "#a970ff", youtube: "#f87171", kick: "#6ee7a0"};
                                            return m[first] || "#8b95a5";
                                        }
                                        function selectPreviewSpec() {
                                            var t = (wtype && wtype.type_id) || "";
                                            switch (t) {
                                            case "activity":
                                                return {kind: "feed", rows: [
                                                    {icon: "web_event_subscribe", label: "Підписка", user: "luna", time: "2 хв"},
                                                    {icon: "web_event_donation", label: "Донат $5", user: "darkness", time: "5 хв"},
                                                    {icon: "web_event_gift", label: "Подарунок", user: "sakura", time: "9 хв"},
                                                    {icon: "web_event_raid", label: "Рейд ×42", user: "void", time: "12 хв"}]};
                                            case "top_gifters":
                                                return {kind: "feed", rows: [
                                                    {icon: "web_event_gift", label: "sakura", user: "320 монет", time: "топ-1"},
                                                    {icon: "web_event_gift", label: "luna", user: "210 монет", time: "топ-2"},
                                                    {icon: "web_event_gift", label: "void", user: "98 монет", time: "топ-3"}]};
                                            case "top_likers":
                                                return {kind: "feed", rows: [
                                                    {icon: "heart", label: "luna", user: "12,4 тис.", time: "топ-1"},
                                                    {icon: "heart", label: "darkness", user: "9,1 тис.", time: "топ-2"},
                                                    {icon: "heart", label: "sakura", user: "7,8 тис.", time: "топ-3"}]};
                                            case "live_leaderboard":
                                                return {kind: "feed", rows: [
                                                    {icon: "web_trophy", label: "luna", user: "12 400", time: "#1"},
                                                    {icon: "web_trophy", label: "darkness", user: "9 870", time: "#2"},
                                                    {icon: "web_trophy", label: "void", user: "7 310", time: "#3"}]};
                                            case "king_of_live":
                                                return {kind: "feed", rows: [
                                                    {icon: "web_crown", label: "luna", user: "42 дні", time: "#1"},
                                                    {icon: "web_crown", label: "mira", user: "18 днів", time: "#2"},
                                                    {icon: "web_crown", label: "void", user: "9 днів", time: "#3"}]};
                                            case "chat":
                                                return {kind: "chat", rows: [
                                                    {platform: "twitch", html: "<b><font color=\"#a970ff\">luna</font></b> <font color=\"#c3cddc\">Крутий стрім!</font>"},
                                                    {platform: "youtube", html: "<b><font color=\"#f87171\">darkness</font></b> <font color=\"#c3cddc\">Всім привіт!</font>"},
                                                    {platform: "tiktok", html: "<b><font color=\"#67e8f9\">sakura</font></b> <font color=\"#c3cddc\">love it!</font>"}]};
                                            case "online":
                                                return {kind: "stats", cols: [
                                                    {value: "01:24", label: "Онлайн", frac: 0.85, color: "#22d3ee"},
                                                    {value: "1 247", label: "Глядачі", frac: 0.6, color: "#8b5cf6"},
                                                    {value: "892", label: "Підписники", frac: 0.4, color: "#10b981"}]};
                                            case "stream_goal":
                                                return {kind: "stats", cols: [
                                                    {value: "6 800", label: "Зібрано", frac: 0.68, color: "#34d399"},
                                                    {value: "10 000", label: "Ціль", frac: 1.0, color: "#3a4356"}]};
                                            case "battle_royale":
                                                return {kind: "battle"};
                                            case "actions":
                                                return {kind: "emblem", caption: "3 активні алерти", progress: -1};
                                            case "stream_pet":
                                                return {kind: "emblem", caption: "Рівень 12 · Ситий", progress: 0.7};
                                            case "community_world":
                                                return {kind: "emblem", caption: "1 240 мешканців", progress: -1};
                                            case "social_rotator":
                                                return {kind: "emblem", caption: "TikTok / Twitch · 15 с", progress: -1};
                                            case "webcam_frame":
                                                return {kind: "emblem", caption: "1080p · CAM 1", progress: -1};
                                            case "signal_system":
                                                return {kind: "emblem", caption: "Канал чистий · 12 мс", progress: -1};
                                            case "music":
                                                return {kind: "emblem", caption: "Саундтрек стріму", progress: 0.35};
                                            default:
                                                return {kind: "emblem", caption: "", progress: -1};
                                            }
                                        }
                                        function pickPreview() {
                                            var k = (previewSpec && previewSpec.kind) || "emblem";
                                            if (k === "feed") return pvFeed;
                                            if (k === "chat") return pvChat;
                                            if (k === "stats") return pvStats;
                                            if (k === "battle") return pvBattle;
                                            return pvEmblem;
                                        }
                                        property Component pvFeed: Component {
                                            WidgetFeedPreview { rows: previewSpec.rows }
                                        }
                                        property Component pvChat: Component {
                                            WidgetChatPreview { rows: previewSpec.rows }
                                        }
                                        property Component pvStats: Component {
                                            WidgetStatsPreview { cols: previewSpec.cols }
                                        }
                                        property Component pvEmblem: Component {
                                            WidgetEmblemPreview {
                                                iconSource: gcard.iconSource
                                                caption: previewSpec.caption || ""
                                                progress: (previewSpec.progress !== undefined) ? previewSpec.progress : -1
                                            }
                                        }
                                        property Component pvBattle: Component {
                                            WidgetBattlePreview {}
                                        }

                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 250
                                        Layout.fillHeight: true

                                        function instId() {
                                            if (instance && instance.id) return instance.id;
                                            return firstInstId();
                                        }
                                        function firstInstId() {
                                            var tid = (wtype && wtype.type_id) || "";
                                            var lst = pageRoot.widgetInstanceList || [];
                                            for (var i = 0; i < lst.length; ++i)
                                                if (lst[i].type_id === tid) return lst[i].id;
                                            return "";
                                        }
                                        // Non-creating lookup for display bindings (never
                                        // creates an instance as a side effect).
                                        function viewId() {
                                            if (instance && instance.id) return instance.id;
                                            return firstInstId();
                                        }
                                        function galleryCardUrl() {
                                            var id = viewId();
                                            if (!id || typeof api === "undefined" || !api) return "";
                                            return api.widgetInstanceUrl(id) || "";
                                        }
                                        function ensureInstId() {
                                            if (instance && instance.id) return instance.id;
                                            var existing = firstInstId();
                                            if (existing) return existing;
                                            if (typeof api === "undefined" || !api) return "";
                                            var nid = api.createWidgetInstance(
                                                (wtype && wtype.type_id) || "",
                                                (wtype && wtype.name) || ((wtype && wtype.type_id) || ""));
                                            pageRoot.refreshWidgetInstances();
                                            return nid || "";
                                        }
                                        function openEditor() {
                                            var iid = ensureInstId();
                                            if (!iid) return;
                                            var lst = pageRoot.widgetInstanceList || [];
                                            for (var i = 0; i < lst.length; ++i) {
                                                if (lst[i].id === iid) { pageRoot.editWidgetInstance(lst[i]); return; }
                                            }
                                        }
                                        Timer {
                                            id: copiedTimer
                                            interval: 1500; repeat: false
                                            onTriggered: gcard._copied = false
                                        }
                            // Inline dropdown (stays in delegate scope, unlike Popup
                            // which reparents to Overlay and loses the file scope).
                            // Anchors can't target the kebab (not a sibling), so
                            // place under it when opening.
                            Rectangle {
                                id: cardMenu
                                visible: false
                                width: 202
                                height: menuCol.implicitHeight + 12
                                radius: 10; color: "#0d1320"
                                border.width: 1; border.color: "#2b3b55"
                                z: 50
                                function open() {
                                    var p = gcard.menuButton.mapToItem(gcard, 0, 0);
                                    x = p.x + gcard.menuButton.width - width;
                                    y = p.y + gcard.menuButton.height + 4;
                                    visible = true;
                                }
                                            function close() { visible = false; }
                                            function toggle() { visible = !visible; }
                                            ColumnLayout {
                                                id: menuCol
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 2
                                                Rectangle {
                                                    Layout.fillWidth: true; implicitHeight: 34; radius: 8
                                                    color: dupMa.pressed ? "#253d62" : (dupMa.containsMouse ? "#1d2f4d" : "transparent")
                                                    Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                                    RowLayout {
                                                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                                        spacing: 8
                                                        Image { source: Qt.resolvedUrl("../assets/icons/web_copy.svg"); Layout.preferredWidth: 14; Layout.preferredHeight: 14; Layout.alignment: Qt.AlignVCenter }
                                                        Text { text: gcard.dupText; color: ink; font.pixelSize: 12; Layout.fillWidth: true }
                                                    }
                                                    MouseArea {
                                                        id: dupMa
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            var iid = gcard.ensureInstId();
                                                            if (iid && typeof api !== "undefined" && api) api.duplicateWidgetInstance(iid);
                                                            gcard.pageRoot.refreshWidgetInstances();
                                                            cardMenu.close();
                                                        }
                                                    }
                                                }
                                                Rectangle {
                                                    // Fallback widgets have nothing stored to delete yet.
                                                    visible: gcard.instance && gcard.instance.id
                                                    Layout.fillWidth: true; implicitHeight: 34; radius: 8
                                                    color: delMa.pressed ? "#541515" : (delMa.containsMouse ? "#3b1111" : "transparent")
                                                    Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                                    RowLayout {
                                                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                                        spacing: 8
                                                        Image { source: Qt.resolvedUrl("../assets/icons/web_trash.svg"); Layout.preferredWidth: 14; Layout.preferredHeight: 14; Layout.alignment: Qt.AlignVCenter }
                                                        Text { text: gcard.delText; color: "#ef4444"; font.pixelSize: 12; Layout.fillWidth: true }
                                                    }
                                                    MouseArea {
                                                        id: delMa
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            var did = gcard.instId();
                                                            if (did && typeof api !== "undefined" && api) {
                                                                api.deleteWidgetInstance(did);
                                                                if (gcard.pageRoot.editingInstanceId === did) gcard.pageRoot.clearEditingInstance();
                                                                gcard.pageRoot.refreshWidgetInstances();
                                                            }
                                                            cardMenu.close();
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                        }

                         Rectangle {
                             id: createNewTile
                             Layout.fillWidth: true
                             Layout.minimumWidth: 250
                             Layout.fillHeight: true
                             implicitHeight: 300
                             radius: 14
                             property bool hovered: createNewMa.containsMouse
                             transformOrigin: Item.Center
                             color: hovered ? "#101827" : "transparent"
                             border.width: 1
                             border.color: hovered ? "#7c3aed" : "#334155"
                             Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
                             Behavior on border.color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
                            ColumnLayout {
                                anchors.centerIn: parent
                                width: parent.width - 32
                                spacing: 6
                                Image {
                                    Layout.alignment: Qt.AlignHCenter
                                    source: Qt.resolvedUrl("../assets/icons/web_plus.svg")
                                    Layout.preferredWidth: 26
                                    Layout.preferredHeight: 26
                                }
                                Text { Layout.alignment: Qt.AlignHCenter; horizontalAlignment: Text.AlignHCenter; text: root.loc("widgets.gallery.create_new"); color: ink; font.pixelSize: 12; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { Layout.alignment: Qt.AlignHCenter; horizontalAlignment: Text.AlignHCenter; text: root.loc("widgets.gallery.create_new_sub"); color: muted; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            }
                             MouseArea { id: createNewMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { root.refreshWidgetInstances(); root.showCreateWidget = true; } }
                         }
                    }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.galleryFilteredTypes().length === 0
                        text: root.loc("widgets.gallery.empty")
                        color: muted; font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                    }

                    }
            }

            Item {
                id: layoutBrowserCard
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                implicitHeight: layoutBrowserColumn.implicitHeight
                visible: root.layoutsOnly && root.layoutViewMode === "list"

                ColumnLayout {
                    id: layoutBrowserColumn
                    anchors.fill: parent
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 50
                            Layout.preferredHeight: 50
                            radius: 13
                            color: "#21104f"
                            border.width: 1
                            border.color: "#5b35b6"
                            Image {
                                anchors.centerIn: parent
                                width: 28
                                height: 28
                                source: Qt.resolvedUrl("../assets/icons/web_layout.svg")
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 3
                            Text {
                                Layout.minimumWidth: 0
                                text: root.loc("ui.nav_layouts")
                                color: ink
                                font.pixelSize: 25
                                font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.loc("widgets.layouts.description")
                                color: muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                elide: Text.ElideRight
                            }
                        }

                        LayoutPrimaryButton {
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            text: root.loc("widgets.layouts.create")
                            iconName: "web_plus.svg"
                            onClicked: root.createLayoutAndOpen()
                        }
                    }

                    GridLayout {
                        id: layoutStatsGrid
                        Layout.fillWidth: true
                        columns: width > 720 ? 3 : 1
                        columnSpacing: 10
                        rowSpacing: 8

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 140
                            Layout.preferredHeight: 58
                            radius: 10
                            color: "#101827"
                            border.width: 1
                            border.color: cardEdge
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 10
                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 9
                                    color: "#24104f"
                                    Image { anchors.centerIn: parent; width: 18; height: 18; source: Qt.resolvedUrl("../assets/icons/web_layout.svg") }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text { text: root.layoutDocList.length; color: ink; font.pixelSize: 16; font.bold: true }
                                    Text { text: root.loc("widgets.layouts.stat_layouts"); color: muted; font.pixelSize: 10 }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 140
                            Layout.preferredHeight: 58
                            radius: 10
                            color: "#101827"
                            border.width: 1
                            border.color: cardEdge
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 10
                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 9
                                    color: "#0b3048"
                                    Image { anchors.centerIn: parent; width: 18; height: 18; source: Qt.resolvedUrl("../assets/icons/web_layers.svg") }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text { text: root.layoutWidgetTotal(); color: ink; font.pixelSize: 16; font.bold: true }
                                    Text { text: root.loc("widgets.layouts.stat_widgets"); color: muted; font.pixelSize: 10 }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 140
                            Layout.preferredHeight: 58
                            radius: 10
                            color: "#101827"
                            border.width: 1
                            border.color: cardEdge
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 10
                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 9
                                    color: "#10352f"
                                    Rectangle { anchors.centerIn: parent; width: 12; height: 12; radius: 6; color: "#34d399" }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text { text: root.layoutActiveTotal(); color: ink; font.pixelSize: 16; font.bold: true }
                                    Text { text: root.loc("widgets.layouts.stat_active"); color: muted; font.pixelSize: 10 }
                                }
                            }
                        }
                    }

                    Item {
                        id: layoutGridHost
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: layoutBrowserColumn.width
                        Layout.alignment: Qt.AlignTop
                        implicitHeight: layoutBrowserGrid.implicitHeight
                        Layout.preferredHeight: implicitHeight
                        visible: (root.layoutDocList || []).length > 0

                        Grid {
                            id: layoutBrowserGrid
                            width: layoutGridHost.width
                            columns: {
                                var availableWidth = Math.max(0, width);
                                if (availableWidth >= 1500) return 4;
                                if (availableWidth >= 1200) return 3;
                                if (availableWidth >= 850) return 2;
                                return 1;
                            }
                            columnSpacing: 14
                            rowSpacing: 14
                            property real cardWidth: Math.min(
                                420,
                                Math.max(280, (width - ((columns - 1) * columnSpacing)) / columns)
                            )

                            Repeater {
                                // Delegates are siblings in Grid; hide only the zero-size
                                // generator so it cannot participate in positioning.
                                visible: false
                                model: (root.layoutDocList || []).concat([{__create: true}])
                                delegate: Rectangle {
                                id: layoutCard
                                required property var modelData
                                property var layoutModel: modelData
                                property bool isCreateCard: !!(modelData && modelData.__create)
                                property bool hovered: layoutCardHover.hovered
                                width: layoutBrowserGrid.cardWidth
                                height: 386
                                radius: 12
                                color: isCreateCard
                                    ? (hovered ? "#111b2e" : "#0c1422")
                                    : (hovered ? "#121c2e" : "#0f1726")
                                border.width: 1
                                border.color: isCreateCard
                                    ? (hovered ? "#7451c7" : "#33445f")
                                    : (hovered ? "#7451c7" : "#26344b")
                                Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                                Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }

                                HoverHandler { id: layoutCardHover }

                                ColumnLayout {
                                    visible: !layoutCard.isCreateCard
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 10

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 9

                                        Rectangle {
                                            Layout.preferredWidth: 38
                                            Layout.preferredHeight: 38
                                            radius: 10
                                            color: hovered ? "#3d1c93" : "#2b146d"
                                            border.width: 1
                                            border.color: hovered ? "#a78bfa" : "#6336c5"
                                            Image { anchors.centerIn: parent; width: 21; height: 21; source: Qt.resolvedUrl("../assets/icons/web_layout.svg") }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            Text {
                                                Layout.fillWidth: true
                                                text: layoutModel.name || root.loc("widgets.layouts.untitled")
                                                color: ink
                                                font.pixelSize: 15
                                                font.bold: true
                                                elide: Text.ElideRight
                                            }
                                            RowLayout {
                                                visible: layoutModel.id === root.activeLayoutId
                                                spacing: 5
                                                Rectangle { width: 7; height: 7; radius: 4; color: "#34d399" }
                                                Text { text: root.loc("widgets.layouts.active_status"); color: "#5eead4"; font.pixelSize: 10 }
                                            }
                                        }

                                        Button {
                                            implicitWidth: 31
                                            implicitHeight: 31
                                            padding: 0
                                            hoverEnabled: true
                                            focusPolicy: Qt.NoFocus
                                            onClicked: layoutCardMenu.popup()
                                            contentItem: Image {
                                                source: Qt.resolvedUrl("../assets/icons/web_more.svg")
                                                width: 16
                                                height: 16
                                                anchors.centerIn: parent
                                                fillMode: Image.PreserveAspectFit
                                            }
                                            background: Rectangle {
                                                radius: 8
                                                color: parent.hovered ? "#1e2b42" : "#121d30"
                                                border.width: 1
                                                border.color: parent.hovered ? "#52617a" : "#26344b"
                                            }
                                        }

                                        Menu {
                                            id: layoutCardMenu
                                            MenuItem {
                                                text: root.loc("widgets.common.duplicate")
                                                onTriggered: {
                                                    if (api) {
                                                        var duplicateId = api.duplicateLayout(layoutModel.id);
                                                        if (duplicateId) root.openLayoutEditor(duplicateId);
                                                    }
                                                }
                                            }
                                            MenuSeparator {}
                                            MenuItem {
                                                text: root.loc("widgets.common.delete")
                                                enabled: (root.layoutDocList || []).length > 1
                                                onTriggered: {
                                                    if (api && api.deleteLayout(layoutModel.id)) root.refreshLayouts();
                                                }
                                            }
                                        }
                                    }

                                    Item {
                                        id: layoutPreviewFrame
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 178
                                        clip: true

                                        Rectangle {
                                            anchors.fill: parent
                                            radius: 12
                                            color: "#080d18"
                                            border.width: 1
                                            border.color: hovered ? "#344c70" : "#1c2b41"
                                        }

                                        Item {
                                            id: layoutPreviewCanvas
                                            property real documentWidth: Math.max(1, Number(layoutModel.width || 1920))
                                            property real documentHeight: Math.max(1, Number(layoutModel.height || 1080))
                                            property real previewScale: Math.min((layoutPreviewFrame.width - 18) / documentWidth, (layoutPreviewFrame.height - 18) / documentHeight)
                                            width: documentWidth * previewScale
                                            height: documentHeight * previewScale
                                            anchors.centerIn: parent
                                            clip: true

                                            Rectangle {
                                                anchors.fill: parent
                                                radius: 8
                                                color: "#0c1322"
                                                border.width: 1
                                                border.color: hovered ? "#5b4a9a" : "#26344b"
                                                gradient: Gradient {
                                                    GradientStop { position: 0.0; color: "#111a2d" }
                                                    GradientStop { position: 1.0; color: "#090f1c" }
                                                }
                                            }

                                            Repeater {
                                                model: layoutModel.widgets || []
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    required property int index
                                                    x: Number(modelData.x || 0) * layoutPreviewCanvas.previewScale
                                                    y: Number(modelData.y || 0) * layoutPreviewCanvas.previewScale
                                                    width: Math.max(16, Number(modelData.width || 320) * layoutPreviewCanvas.previewScale)
                                                    height: Math.max(12, Number(modelData.height || 180) * layoutPreviewCanvas.previewScale)
                                                    radius: 4
                                                    color: "#111827cc"
                                                    border.width: 1
                                                    border.color: root.layoutPreviewAccent(index)
                                                    z: Number(modelData.z_index || index)
                                                    clip: true
                                                    Text {
                                                        anchors.fill: parent
                                                        anchors.margins: 4
                                                        text: root.layoutPreviewLabel(modelData.type)
                                                        color: "#dbeafe"
                                                        font.pixelSize: Math.max(7, Math.min(11, parent.height * 0.18))
                                                        elide: Text.ElideRight
                                                        verticalAlignment: Text.AlignVCenter
                                                        visible: parent.width > 40 && parent.height > 18
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 30
                                            radius: 7
                                            color: "#111c2e"
                                            border.width: 1
                                            border.color: "#1f3048"
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                spacing: 6
                                                Image { Layout.preferredWidth: 14; Layout.preferredHeight: 14; source: Qt.resolvedUrl("../assets/icons/web_layout.svg") }
                                                Text { Layout.fillWidth: true; text: (layoutModel.width || 0) + " × " + (layoutModel.height || 0); color: inkSecondary; font.pixelSize: 11 }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 30
                                            radius: 7
                                            color: "#111c2e"
                                            border.width: 1
                                            border.color: "#1f3048"
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                spacing: 6
                                                Image { Layout.preferredWidth: 14; Layout.preferredHeight: 14; source: Qt.resolvedUrl("../assets/icons/web_layers.svg") }
                                                Text { Layout.fillWidth: true; text: (layoutModel.widgets || []).length + " " + root.loc("widgets.layouts.widgets"); color: inkSecondary; font.pixelSize: 11; elide: Text.ElideRight }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 31
                                        radius: 7
                                        color: "#0c1423"
                                        border.width: 1
                                        border.color: "#1e2d44"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 8
                                            anchors.rightMargin: 5
                                            spacing: 6
                                            Image { Layout.preferredWidth: 14; Layout.preferredHeight: 14; source: Qt.resolvedUrl("../assets/icons/web_globe.svg") }
                                            Text {
                                                Layout.fillWidth: true
                                                text: api ? api.layoutOverlayUrl(layoutModel.id) : ""
                                                color: muted
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }

                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Layout.alignment: Qt.AlignBottom
                                        Layout.fillHeight: true
                                        Item { Layout.fillWidth: true }
                                        LayoutCardButton {
                                            text: root.layoutCopiedId === layoutModel.id ? root.loc("widgets.gallery.copied") : root.loc("widgets.common.copy_url")
                                            iconName: "web_copy.svg"
                                            primary: true
                                            onClicked: {
                                                if (api) {
                                                    api.copyLayoutOverlayUrl(layoutModel.id);
                                                    root.layoutCopiedId = layoutModel.id;
                                                }
                                            }
                                        }
                                        LayoutCardButton {
                                            text: root.loc("widgets.common.edit")
                                            iconName: "edit.svg"
                                            onClicked: root.openLayoutEditor(layoutModel.id)
                                        }
                                    }
                                }

                                ColumnLayout {
                                    visible: layoutCard.isCreateCard
                                    anchors.centerIn: parent
                                    width: parent.width - 36
                                    spacing: 10
                                    Rectangle {
                                        Layout.alignment: Qt.AlignHCenter
                                        Layout.preferredWidth: 56
                                        Layout.preferredHeight: 56
                                        radius: 28
                                        color: "#1a1733"
                                        border.width: 1
                                        border.color: "#6d4ac1"
                                        Image { anchors.centerIn: parent; width: 26; height: 26; source: Qt.resolvedUrl("../assets/icons/web_plus.svg") }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: root.loc("widgets.layouts.create_card_title")
                                        color: ink
                                        font.pixelSize: 15
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: root.loc("widgets.layouts.create_card_hint")
                                        color: muted
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }

                                MouseArea {
                                    visible: layoutCard.isCreateCard
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.createLayoutAndOpen()
                                }
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        implicitHeight: 260
                        visible: (root.layoutDocList || []).length === 0
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 420)
                            spacing: 10
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 58
                                Layout.preferredHeight: 58
                                radius: 16
                                color: "#21104f"
                                border.width: 1
                                border.color: "#5b35b6"
                                Image { anchors.centerIn: parent; width: 29; height: 29; source: Qt.resolvedUrl("../assets/icons/web_layout.svg") }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.loc("widgets.layouts.empty_title")
                                color: ink
                                font.pixelSize: 17
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.loc("widgets.layouts.empty_hint")
                                color: muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            LayoutPrimaryButton {
                                Layout.alignment: Qt.AlignHCenter
                                text: root.loc("widgets.layouts.create")
                                iconName: "web_plus.svg"
                                onClicked: root.createLayoutAndOpen()
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: layoutEditorCard
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 680
                radius: 0
                color: "transparent"
                border.width: 0
                visible: root.layoutsOnly && root.layoutViewMode !== "list" && root.widgetMode === "layout"
                implicitHeight: layoutEditorColumn.implicitHeight

                ColumnLayout {
                    id: layoutEditorColumn
                    anchors.fill: parent
                    spacing: 10

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
                        radius: 10
                        color: "#0d1320"
                        border.width: 1
                        border.color: cardEdge

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 6

                            EditorIconButton {
                                iconName: "web_back.svg"
                                toolTipText: root.loc("widgets.common.back")
                                onClicked: {
                                    if (root.layoutsOnly) root.showLayoutList();
                                    else root.widgetMode = "grid";
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 36
                                Layout.preferredHeight: 36
                                radius: 9
                                color: "#21104f"
                                border.width: 1
                                border.color: "#5b35b6"
                                Image {
                                    anchors.centerIn: parent
                                    width: 19
                                    height: 19
                                    source: Qt.resolvedUrl("../assets/icons/web_layout.svg")
                                }
                            }

                            TextField {
                                id: layoutNameField
                                Layout.preferredWidth: 205
                                Layout.preferredHeight: 34
                                placeholderText: root.loc("widgets.layouts.name_placeholder")
                                Binding {
                                    target: layoutNameField
                                    property: "text"
                                    value: root.layoutDoc.name || ""
                                    when: !layoutNameField.activeFocus
                                }
                                color: ink
                                font.pixelSize: 14
                                font.bold: true
                                leftPadding: 8
                                rightPadding: 8
                                background: Rectangle {
                                    radius: 7
                                    color: layoutNameField.activeFocus ? fieldBg : "transparent"
                                    border.width: layoutNameField.activeFocus ? 1 : 0
                                    border.color: accent
                                }
                                onEditingFinished: {
                                    var nm = text.trim();
                                    if (nm && nm !== (root.layoutDoc.name || "") && api) {
                                        if (api.renameLayout(root.activeLayoutId, nm)) {
                                            root._inspectorUpdating = true;
                                            root.layoutDoc = Object.assign({}, root.layoutDoc, {name: nm});
                                            root._inspectorUpdating = false;
                                            root.saveLayoutEditor();
                                            root.refreshLayouts();
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                spacing: 5
                                Image {
                                    Layout.preferredWidth: 14
                                    Layout.preferredHeight: 14
                                    source: Qt.resolvedUrl("../assets/icons/" + (root.layoutSaveSucceeded ? "check.svg" : "x.svg"))
                                }
                                Text {
                                    text: root.layoutSaveSucceeded ? "Збережено" : "Не збережено"
                                    color: root.layoutSaveSucceeded ? muted : "#fca5a5"
                                    font.pixelSize: 11
                                }
                            }

                            Item { Layout.fillWidth: true }

                            StyledComboBox {
                                id: layoutSwitchBox
                                Layout.preferredWidth: 150
                                Layout.preferredHeight: 34
                                model: (root.layoutDocList || []).map(function(l) { return l.name || l.id; })
                                currentIndex: {
                                    var all = root.layoutDocList || [];
                                    for (var si = 0; si < all.length; ++si) {
                                        if (all[si].id === root.activeLayoutId) return si;
                                    }
                                    return all.length ? 0 : -1;
                                }
                                onUserActivated: function(idx) { root.switchLayoutByIndex(idx); }
                                onActivated: function(idx) { root.switchLayoutByIndex(idx); }
                            }

                            EditorIconButton {
                                iconName: "web_plus.svg"
                                toolTipText: root.loc("widgets.layouts.new")
                                onClicked: {
                                    if (api) {
                                        var nid = api.createLayout("");
                                        root.loadLayoutEditor(nid || undefined);
                                        try { api.setActiveLayoutId(root.activeLayoutId); } catch (e) {}
                                    }
                                }
                            }
                            EditorIconButton {
                                iconName: "copy.svg"
                                toolTipText: root.loc("widgets.common.duplicate")
                                onClicked: {
                                    if (api) {
                                        var did = api.duplicateLayout(root.activeLayoutId);
                                        if (did) {
                                            root.loadLayoutEditor(did);
                                            try { api.setActiveLayoutId(root.activeLayoutId); } catch (e2) {}
                                        }
                                    }
                                }
                            }
                            EditorIconButton {
                                iconName: "web_trash.svg"
                                toolTipText: root.loc("widgets.common.delete")
                                enabled: (root.layoutDocList || []).length > 1
                                onClicked: {
                                    if (api && api.deleteLayout(root.activeLayoutId)) {
                                        if (root.layoutsOnly) root.showLayoutList();
                                        else root.loadLayoutEditor();
                                    }
                                }
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 24; color: cardEdge }

                            EditorIconButton {
                                iconName: "editor_undo.svg"
                                toolTipText: "Скасувати"
                                enabled: (root._undoStack || []).length > 0
                                onClicked: root.undo()
                            }
                            EditorIconButton {
                                iconName: "editor_redo.svg"
                                toolTipText: "Повторити"
                                enabled: (root._redoStack || []).length > 0
                                onClicked: root.redo()
                            }

                            LayoutCardButton {
                                text: "Показати preview"
                                iconName: "open-external.svg"
                                implicitHeight: 34
                                onClicked: {
                                    root.saveLayoutEditor();
                                    if (api) api.previewLayout(root.activeLayoutId);
                                }
                            }
                            LayoutPrimaryButton {
                                text: "Зберегти"
                                iconName: "check.svg"
                                implicitHeight: 34
                                onClicked: {
                                    if (root.saveLayoutEditor() && root.layoutsOnly)
                                        root.showLayoutList();
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 400
                        Layout.preferredHeight: 560
                        spacing: 12

                        // Left panel: Widget library
                        Rectangle {
                            Layout.preferredWidth: 250
                            Layout.fillHeight: true
                            radius: 10
                            color: "#0d1320"
                            border.width: 1
                            border.color: cardEdge

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Додати віджет"; color: ink; font.pixelSize: 14; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: root.filteredLayoutWidgetTypes().length; color: muted; font.pixelSize: 11 }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Перетягніть на полотно або натисніть +"
                                    color: muted
                                    font.pixelSize: 10
                                    wrapMode: Text.Wrap
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    radius: 7
                                    color: fieldBg
                                    border.width: 1
                                    border.color: librarySearchField.activeFocus ? accent : cardEdge
                                    Image {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 9
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 15
                                        height: 15
                                        source: Qt.resolvedUrl("../assets/icons/web_search.svg")
                                    }
                                    TextField {
                                        id: librarySearchField
                                        anchors.fill: parent
                                        leftPadding: 32
                                        rightPadding: 8
                                        placeholderText: "Пошук віджетів"
                                        text: root.layoutLibrarySearch
                                        color: ink
                                        font.pixelSize: 12
                                        background: Item {}
                                        onTextChanged: root.layoutLibrarySearch = text
                                    }
                                }

                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true

                                    ColumnLayout {
                                        width: parent.width
                                        spacing: 4

                                        Repeater {
                                            model: root.filteredLayoutWidgetTypes()
                                            delegate: Rectangle {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                implicitHeight: 42
                                                radius: 7
                                                color: libMouseArea.pressed ? "#162033" : (libMouseArea.containsMouse ? "#1e293b" : "#111726")
                                                border.width: 1
                                                border.color: libMouseArea.containsMouse ? "#38bdf8" : "#1e293b"

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 8
                                                    anchors.rightMargin: 6
                                                    spacing: 6
                                                    z: 2

                                                    Rectangle {
                                                        Layout.preferredWidth: 28
                                                        Layout.preferredHeight: 28
                                                        radius: 6
                                                        color: "#182235"
                                                        Image {
                                                            anchors.centerIn: parent
                                                            width: 16
                                                            height: 16
                                                            source: Qt.resolvedUrl("../assets/icons/" + (modelData.iconName || "web_layout.svg"))
                                                        }
                                                    }
                                                    Text {
                                                        text: modelData.label
                                                        color: libMouseArea.containsMouse ? "#ffffff" : root.ink
                                                        font.pixelSize: 12
                                                        font.weight: Font.Medium
                                                        Layout.fillWidth: true
                                                        elide: Text.ElideRight
                                                    }
                                                    EditorIconButton {
                                                        iconName: "web_plus.svg"
                                                        toolTipText: "Додати віджет"
                                                        implicitWidth: 28
                                                        implicitHeight: 28
                                                        onClicked: root.addLayoutWidget(modelData.type, modelData.label)
                                                    }
                                                }

                                                MouseArea {
                                                    id: libMouseArea
                                                    anchors.fill: parent
                                                    z: 1
                                                    hoverEnabled: true
                                                    cursorShape: pressed ? Qt.DragCopyCursor : Qt.PointingHandCursor
                                                    preventStealing: true

                                                    property bool isDraggingLib: false

                                                    onPressed: function(mouse) {
                                                        isDraggingLib = false;
                                                    }

                                                    onPositionChanged: function(mouse) {
                                                        if (!pressed) return;
                                                        if (!isDraggingLib) {
                                                            isDraggingLib = true;
                                                            root._dragLibType = modelData.type;
                                                            root._dragLibLabel = modelData.label;
                                                        }
                                                    }

                                                    onReleased: function(mouse) {
                                                        if (isDraggingLib && root._dragLibType) {
                                                            var pt = mapToItem(layoutCanvas, mouse.x, mouse.y);
                                                            if (pt.x >= 0 && pt.x <= layoutCanvas.width && pt.y >= 0 && pt.y <= layoutCanvas.height) {
                                                                var dropCanvasX = Math.round(pt.x / layoutCanvas.editorScale);
                                                                var dropCanvasY = Math.round(pt.y / layoutCanvas.editorScale);
                                                                root.addLayoutWidget(root._dragLibType, root._dragLibLabel, dropCanvasX, dropCanvasY);
                                                            }
                                                            root._dragLibType = "";
                                                            root._dragLibLabel = "";
                                                        }
                                                        isDraggingLib = false;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Center: Canvas Viewport
                        Item {
                            id: layoutCanvasViewport
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Rectangle {
                                anchors.top: parent.top
                                anchors.right: parent.right
                                anchors.margins: 8
                                width: canvasControlsRow.implicitWidth + 12
                                height: 38
                                radius: 8
                                color: "#101722"
                                border.width: 1
                                border.color: cardEdge
                                z: 200

                                RowLayout {
                                    id: canvasControlsRow
                                    anchors.centerIn: parent
                                    spacing: 2
                                    EditorIconButton {
                                        iconName: "editor_zoom_out.svg"
                                        toolTipText: "Зменшити масштаб"
                                        implicitWidth: 28
                                        implicitHeight: 28
                                        enabled: root.layoutCanvasZoom > 0.5
                                        onClicked: root.setLayoutCanvasZoom(root.layoutCanvasZoom - 0.1)
                                    }
                                    Text {
                                        Layout.preferredWidth: 42
                                        text: Math.round(root.layoutCanvasZoom * 100) + "%"
                                        color: inkSecondary
                                        font.pixelSize: 11
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                    EditorIconButton {
                                        iconName: "editor_zoom_in.svg"
                                        toolTipText: "Збільшити масштаб"
                                        implicitWidth: 28
                                        implicitHeight: 28
                                        enabled: root.layoutCanvasZoom < 2.0
                                        onClicked: root.setLayoutCanvasZoom(root.layoutCanvasZoom + 0.1)
                                    }
                                    LayoutCardButton {
                                        text: "Вписати"
                                        iconName: "editor_fit.svg"
                                        implicitHeight: 28
                                        onClicked: root.layoutCanvasZoom = 1.0
                                    }
                                    LayoutCardButton {
                                        text: "Сітка"
                                        iconName: "editor_grid.svg"
                                        primary: root.layoutCanvasGridVisible
                                        implicitHeight: 28
                                        onClicked: root.layoutCanvasGridVisible = !root.layoutCanvasGridVisible
                                    }
                                }
                            }

                            Rectangle {
                                id: layoutCanvas
                                anchors.centerIn: parent
                                property real documentWidth: Number(root.layoutDoc.width || 1920)
                                property real documentHeight: Number(root.layoutDoc.height || 1080)
                                property real aspect: documentWidth / Math.max(1, documentHeight)
                                property real fitScale: Math.min((parent.width - 20) / Math.max(1, documentWidth), (parent.height - 20) / Math.max(1, documentHeight))
                                property real editorScale: fitScale * root.layoutCanvasZoom
                                property int selectedIndex: root.selectedLayoutWidget

                                width: documentWidth * editorScale
                                height: documentHeight * editorScale
                                color: "#06080d"
                                border.width: 1
                                border.color: "#334155"
                                clip: false
                                focus: true

                                // Snapping calculation for moving
                                function calculateMoveSnapping(widgetIdx, candX, candY, w, h) {
                                    var tolerance = 8 / layoutCanvas.editorScale;
                                    var docW = layoutCanvas.documentWidth;
                                    var docH = layoutCanvas.documentHeight;

                                    var vGuides = [0, docW / 2, docW];
                                    var hGuides = [0, docH / 2, docH];

                                    var widgets = root.layoutDoc.widgets || [];
                                    for (var i = 0; i < widgets.length; ++i) {
                                        if (i === widgetIdx) continue;
                                        var o = widgets[i];
                                        var ox = Number(o.x || 0);
                                        var oy = Number(o.y || 0);
                                        var ow = Number(o.width || 320);
                                        var oh = Number(o.height || 180);

                                        vGuides.push(ox);
                                        vGuides.push(ox + ow / 2);
                                        vGuides.push(ox + ow);

                                        hGuides.push(oy);
                                        hGuides.push(oy + oh / 2);
                                        hGuides.push(oy + oh);
                                    }

                                    var testX = [
                                        {val: candX, offset: 0},
                                        {val: candX + w / 2, offset: w / 2},
                                        {val: candX + w, offset: w}
                                    ];
                                    var testY = [
                                        {val: candY, offset: 0},
                                        {val: candY + h / 2, offset: h / 2},
                                        {val: candY + h, offset: h}
                                    ];

                                    var snappedX = candX;
                                    var snappedY = candY;
                                    var matchedGuides = [];
                                    var bestDx = tolerance + 1;
                                    var bestDy = tolerance + 1;

                                    for (var vi = 0; vi < vGuides.length; ++vi) {
                                        var gv = vGuides[vi];
                                        for (var ti = 0; ti < testX.length; ++ti) {
                                            var diffX = Math.abs(testX[ti].val - gv);
                                            if (diffX < tolerance && diffX < bestDx) {
                                                bestDx = diffX;
                                                snappedX = gv - testX[ti].offset;
                                                matchedGuides = matchedGuides.filter(function(g) { return g.axis !== "v"; });
                                                matchedGuides.push({axis: "v", pos: gv});
                                            }
                                        }
                                    }

                                    for (var hi = 0; hi < hGuides.length; ++hi) {
                                        var gh = hGuides[hi];
                                        for (var tj = 0; tj < testY.length; ++tj) {
                                            var diffY = Math.abs(testY[tj].val - gh);
                                            if (diffY < tolerance && diffY < bestDy) {
                                                bestDy = diffY;
                                                snappedY = gh - testY[tj].offset;
                                                matchedGuides = matchedGuides.filter(function(g) { return g.axis !== "h"; });
                                                matchedGuides.push({axis: "h", pos: gh});
                                            }
                                        }
                                    }

                                    return {x: snappedX, y: snappedY, guides: matchedGuides};
                                }

                                // Snapping calculation for resizing
                                function calculateResizeSnapping(widgetIdx, edgeX, edgeY, candX, candY, candW, candH) {
                                    var tolerance = 8 / layoutCanvas.editorScale;
                                    var docW = layoutCanvas.documentWidth;
                                    var docH = layoutCanvas.documentHeight;

                                    var vGuides = [0, docW / 2, docW];
                                    var hGuides = [0, docH / 2, docH];

                                    var widgets = root.layoutDoc.widgets || [];
                                    for (var i = 0; i < widgets.length; ++i) {
                                        if (i === widgetIdx) continue;
                                        var o = widgets[i];
                                        var ox = Number(o.x || 0);
                                        var oy = Number(o.y || 0);
                                        var ow = Number(o.width || 320);
                                        var oh = Number(o.height || 180);

                                        vGuides.push(ox);
                                        vGuides.push(ox + ow / 2);
                                        vGuides.push(ox + ow);

                                        hGuides.push(oy);
                                        hGuides.push(oy + oh / 2);
                                        hGuides.push(oy + oh);
                                    }

                                    var nextX = candX;
                                    var nextY = candY;
                                    var nextW = candW;
                                    var nextH = candH;
                                    var matchedGuides = [];

                                    if (edgeX === -1) {
                                        var bestDx = tolerance + 1;
                                        for (var vi = 0; vi < vGuides.length; ++vi) {
                                            var diff = Math.abs(candX - vGuides[vi]);
                                            if (diff < tolerance && diff < bestDx) {
                                                bestDx = diff;
                                                var rightEdge = candX + candW;
                                                nextX = vGuides[vi];
                                                nextW = Math.max(32, rightEdge - nextX);
                                                matchedGuides.push({axis: "v", pos: vGuides[vi]});
                                            }
                                        }
                                    } else if (edgeX === 1) {
                                        var bestDx = tolerance + 1;
                                        var curRight = candX + candW;
                                        for (var vi = 0; vi < vGuides.length; ++vi) {
                                            var diff = Math.abs(curRight - vGuides[vi]);
                                            if (diff < tolerance && diff < bestDx) {
                                                bestDx = diff;
                                                nextW = Math.max(32, vGuides[vi] - candX);
                                                matchedGuides.push({axis: "v", pos: vGuides[vi]});
                                            }
                                        }
                                    }

                                    if (edgeY === -1) {
                                        var bestDy = tolerance + 1;
                                        for (var hi = 0; hi < hGuides.length; ++hi) {
                                            var diff = Math.abs(candY - hGuides[hi]);
                                            if (diff < tolerance && diff < bestDy) {
                                                bestDy = diff;
                                                var bottomEdge = candY + candH;
                                                nextY = hGuides[hi];
                                                nextH = Math.max(24, bottomEdge - nextY);
                                                matchedGuides.push({axis: "h", pos: hGuides[hi]});
                                            }
                                        }
                                    } else if (edgeY === 1) {
                                        var bestDy = tolerance + 1;
                                        var curBottom = candY + candH;
                                        for (var hi = 0; hi < hGuides.length; ++hi) {
                                            var diff = Math.abs(curBottom - hGuides[hi]);
                                            if (diff < tolerance && diff < bestDy) {
                                                bestDy = diff;
                                                nextH = Math.max(24, hGuides[hi] - candY);
                                                matchedGuides.push({axis: "h", pos: hGuides[hi]});
                                            }
                                        }
                                    }

                                    return {x: nextX, y: nextY, w: nextW, h: nextH, guides: matchedGuides};
                                }

                                // Grid is document-space UI: it repaints only when dimensions, zoom, or visibility change.
                                Repeater {
                                    model: root.layoutCanvasGridVisible ? Math.max(0, Math.floor(layoutCanvas.documentWidth / 100) - 1) : 0
                                    delegate: Rectangle {
                                        required property int index
                                        x: (index + 1) * 100 * layoutCanvas.editorScale
                                        width: 1
                                        height: layoutCanvas.height
                                        color: root.canvasGrid
                                        opacity: 0.75
                                        z: -2
                                    }
                                }
                                Repeater {
                                    model: root.layoutCanvasGridVisible ? Math.max(0, Math.floor(layoutCanvas.documentHeight / 100) - 1) : 0
                                    delegate: Rectangle {
                                        required property int index
                                        y: (index + 1) * 100 * layoutCanvas.editorScale
                                        width: layoutCanvas.width
                                        height: 1
                                        color: root.canvasGrid
                                        opacity: 0.75
                                        z: -2
                                    }
                                }

                                // Canvas background click
                                MouseArea {
                                    anchors.fill: parent
                                    z: -1
                                    onClicked: {
                                        layoutCanvas.forceActiveFocus();
                                        root.selectedLayoutWidget = -1;
                                    }
                                }

                                // Keyboard shortcuts
                                Keys.onPressed: function(event) {
                                    var isCtrl = (event.modifiers & Qt.ControlModifier) !== 0;
                                    var isShift = (event.modifiers & Qt.ShiftModifier) !== 0;

                                    if (isCtrl && (event.key === Qt.Key_Z)) {
                                        if (isShift) root.redo();
                                        else root.undo();
                                        event.accepted = true;
                                        return;
                                    }
                                    if (isCtrl && (event.key === Qt.Key_Y)) {
                                        root.redo();
                                        event.accepted = true;
                                        return;
                                    }
                                    if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
                                        root.removeSelectedLayoutWidget();
                                        event.accepted = true;
                                        return;
                                    }

                                    var step = isShift ? 10 : 1;
                                    if (event.key === Qt.Key_Left) { root.nudgeSelected(-step, 0); event.accepted = true; }
                                    else if (event.key === Qt.Key_Right) { root.nudgeSelected(step, 0); event.accepted = true; }
                                    else if (event.key === Qt.Key_Up) { root.nudgeSelected(0, -step); event.accepted = true; }
                                    else if (event.key === Qt.Key_Down) { root.nudgeSelected(0, step); event.accepted = true; }
                                }

                                // Snapping visual guide lines overlay
                                Canvas {
                                    id: snapGuideCanvas
                                    anchors.fill: parent
                                    z: 100
                                    visible: (root._snapGuides || []).length > 0
                                    onPaint: {
                                        var ctx = getContext("2d");
                                        ctx.clearRect(0, 0, width, height);
                                        var guides = root._snapGuides || [];
                                        if (!guides.length) return;

                                        ctx.save();
                                        ctx.strokeStyle = "#14b8a6";
                                        ctx.lineWidth = 1.5;
                                        ctx.setLineDash([4, 4]);
                                        var s = layoutCanvas.editorScale;

                                        for (var i = 0; i < guides.length; ++i) {
                                            var g = guides[i];
                                            ctx.beginPath();
                                            if (g.axis === "v") {
                                                var sx = Math.round(g.pos * s);
                                                ctx.moveTo(sx, 0);
                                                ctx.lineTo(sx, height);
                                            } else if (g.axis === "h") {
                                                var sy = Math.round(g.pos * s);
                                                ctx.moveTo(0, sy);
                                                ctx.lineTo(width, sy);
                                            }
                                            ctx.stroke();
                                        }
                                        ctx.restore();
                                    }
                                    Connections {
                                        target: root
                                        function on_SnapGuidesChanged() {
                                            snapGuideCanvas.requestPaint();
                                        }
                                    }
                                }

                                // Widget delegates
                                Repeater {
                                    model: root.layoutDoc.widgets || []
                                    delegate: Item {
                                        required property var modelData
                                        required property int index
                                        id: layoutWidget

                                        property bool isSelected: index === root.selectedLayoutWidget
                                        property real localX: Number(modelData.x || 0)
                                        property real localY: Number(modelData.y || 0)
                                        property real localW: Math.max(32, Number(modelData.width || 320))
                                        property real localH: Math.max(24, Number(modelData.height || 180))

                                        // Store resize starting values
                                        property real _resStartLocalX: 0
                                        property real _resStartLocalY: 0
                                        property real _resStartLocalW: 0
                                        property real _resStartLocalH: 0
                                        property real _resStartAspect: 16/9

                                        x: localX * layoutCanvas.editorScale
                                        y: localY * layoutCanvas.editorScale
                                        width: localW * layoutCanvas.editorScale
                                        height: localH * layoutCanvas.editorScale
                                        z: isSelected ? 50 : index
                                        visible: modelData.visible !== false

                                        // Keep local interactive geometry in sync when model updates and not dragging
                                        Connections {
                                            target: root
                                            function onLayoutDocChanged() {
                                                if (root._editorState === "idle" && modelData) {
                                                    layoutWidget.localX = Number(modelData.x || 0);
                                                    layoutWidget.localY = Number(modelData.y || 0);
                                                    layoutWidget.localW = Math.max(32, Number(modelData.width || 320));
                                                    layoutWidget.localH = Math.max(24, Number(modelData.height || 180));
                                                }
                                            }
                                        }

                                        function beginResize(edgeX, edgeY) {
                                            root.selectedLayoutWidget = index;
                                            layoutCanvas.forceActiveFocus();
                                            root._pushUndo();
                                            root._editorState = "resizing";

                                            _resStartLocalX = localX;
                                            _resStartLocalY = localY;
                                            _resStartLocalW = localW;
                                            _resStartLocalH = localH;
                                            _resStartAspect = _resStartLocalW / Math.max(1, _resStartLocalH);
                                        }

                                        function resizeWith(edgeX, edgeY, dx, dy, shiftHeld, altHeld) {
                                            var rawX = _resStartLocalX;
                                            var rawY = _resStartLocalY;
                                            var rawW = _resStartLocalW;
                                            var rawH = _resStartLocalH;

                                            if (edgeX === -1) {
                                                rawX = _resStartLocalX + dx;
                                                rawW = _resStartLocalW - dx;
                                            } else if (edgeX === 1) {
                                                rawW = _resStartLocalW + dx;
                                            }

                                            if (edgeY === -1) {
                                                rawY = _resStartLocalY + dy;
                                                rawH = _resStartLocalH - dy;
                                            } else if (edgeY === 1) {
                                                rawH = _resStartLocalH + dy;
                                            }

                                            var minW = 32;
                                            var minH = 24;

                                            // Aspect ratio lock (Shift on corner handles)
                                            var isCorner = (edgeX !== 0 && edgeY !== 0);
                                            if (isCorner && shiftHeld) {
                                                var scaleW = rawW / _resStartLocalW;
                                                var scaleH = rawH / _resStartLocalH;
                                                var scale = Math.max(scaleW, scaleH);

                                                rawW = Math.max(minW, _resStartLocalW * scale);
                                                rawH = rawW / _resStartAspect;

                                                if (edgeX === -1) {
                                                    rawX = _resStartLocalX + _resStartLocalW - rawW;
                                                }
                                                if (edgeY === -1) {
                                                    rawY = _resStartLocalY + _resStartLocalH - rawH;
                                                }
                                            } else {
                                                // Free resize min constraints
                                                if (rawW < minW) {
                                                    if (edgeX === -1) rawX = _resStartLocalX + _resStartLocalW - minW;
                                                    rawW = minW;
                                                }
                                                if (rawH < minH) {
                                                    if (edgeY === -1) rawY = _resStartLocalY + _resStartLocalH - minH;
                                                    rawH = minH;
                                                }

                                                // Snapping for resize
                                                if (!altHeld) {
                                                    var snapRes = layoutCanvas.calculateResizeSnapping(index, edgeX, edgeY, rawX, rawY, rawW, rawH);
                                                    rawX = snapRes.x;
                                                    rawY = snapRes.y;
                                                    rawW = snapRes.w;
                                                    rawH = snapRes.h;
                                                    root._snapGuides = snapRes.guides;
                                                } else {
                                                    root._snapGuides = [];
                                                }
                                            }

                                            layoutWidget.localX = rawX;
                                            layoutWidget.localY = rawY;
                                            layoutWidget.localW = rawW;
                                            layoutWidget.localH = rawH;
                                        }

                                        function finishResize() {
                                            root._editorState = "idle";
                                            root._snapGuides = [];
                                            root.commitWidgetGeometry(index, Math.round(layoutWidget.localX), Math.round(layoutWidget.localY), Math.round(layoutWidget.localW), Math.round(layoutWidget.localH));
                                        }

                                        // Widget background box
                                        Rectangle {
                                            anchors.fill: parent
                                            radius: 4
                                            color: layoutWidget.isSelected ? "#1e3a5f" : (widgetBodyArea.containsMouse ? "#1b283d" : "#141c2c")
                                            border.width: layoutWidget.isSelected ? 2 : 1
                                            border.color: layoutWidget.isSelected ? "#5eead4" : (widgetBodyArea.containsMouse ? "#4a5d7c" : "#2d3b52")

                                            // Content preview inside widget
                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 2

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    Image {
                                                        Layout.preferredWidth: 14
                                                        Layout.preferredHeight: 14
                                                        source: {
                                                            var info = root.widgetTypeInfo(modelData.type);
                                                            return Qt.resolvedUrl("../assets/icons/" + (info.iconName || "web_layout.svg"));
                                                        }
                                                    }
                                                    Text {
                                                        text: {
                                                            var info = root.widgetTypeInfo(modelData.type);
                                                            return info.label || modelData.type || "Віджет";
                                                        }
                                                        color: layoutWidget.isSelected ? "#5eead4" : root.ink
                                                        font.pixelSize: Math.max(10, Math.min(13, layoutWidget.height * 0.2))
                                                        font.bold: true
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }
                                                    Image {
                                                        Layout.preferredWidth: 13
                                                        Layout.preferredHeight: 13
                                                        source: Qt.resolvedUrl("../assets/icons/editor_lock.svg")
                                                        visible: modelData.locked
                                                    }
                                                }

                                                Text {
                                                    text: Math.round(layoutWidget.localW) + " × " + Math.round(layoutWidget.localH)
                                                    color: "#64748b"
                                                    font.pixelSize: Math.max(9, Math.min(11, layoutWidget.height * 0.15))
                                                    visible: layoutWidget.height > 35
                                                }

                                                Item { Layout.fillHeight: true }
                                            }
                                        }

                                        // Move & Selection MouseArea on widget body
                                        MouseArea {
                                            id: widgetBodyArea
                                            anchors.fill: parent
                                            z: 1
                                            enabled: true
                                            hoverEnabled: true
                                            cursorShape: layoutWidget.isSelected ? Qt.SizeAllCursor : Qt.ArrowCursor
                                            preventStealing: true

                                            property real pressOffsetCanvasX: 0
                                            property real pressOffsetCanvasY: 0
                                            property bool isMoving: false

                                            onPressed: function(mouse) {
                                                root.selectedLayoutWidget = index;
                                                layoutCanvas.forceActiveFocus();
                                                var pt = mapToItem(layoutCanvas, mouse.x, mouse.y);
                                                var curCanvasX = pt.x / layoutCanvas.editorScale;
                                                var curCanvasY = pt.y / layoutCanvas.editorScale;
                                                pressOffsetCanvasX = curCanvasX - layoutWidget.localX;
                                                pressOffsetCanvasY = curCanvasY - layoutWidget.localY;
                                                isMoving = false;
                                                mouse.accepted = true;
                                            }

                                            onPositionChanged: function(mouse) {
                                                if (!pressed || modelData.locked) return;
                                                var pt = mapToItem(layoutCanvas, mouse.x, mouse.y);
                                                var curCanvasX = pt.x / layoutCanvas.editorScale;
                                                var curCanvasY = pt.y / layoutCanvas.editorScale;

                                                var targetX = curCanvasX - pressOffsetCanvasX;
                                                var targetY = curCanvasY - pressOffsetCanvasY;

                                                if (!isMoving) {
                                                    var diff = Math.abs(targetX - layoutWidget.localX) + Math.abs(targetY - layoutWidget.localY);
                                                    if (diff > 1) {
                                                        isMoving = true;
                                                        root._pushUndo();
                                                        root._editorState = "moving";
                                                    } else {
                                                        return;
                                                    }
                                                }

                                                var altHeld = (mouse.modifiers & Qt.AltModifier) !== 0;
                                                if (!altHeld) {
                                                    var snapResult = layoutCanvas.calculateMoveSnapping(index, targetX, targetY, layoutWidget.localW, layoutWidget.localH);
                                                    targetX = snapResult.x;
                                                    targetY = snapResult.y;
                                                    root._snapGuides = snapResult.guides;
                                                } else {
                                                    root._snapGuides = [];
                                                }

                                                layoutWidget.localX = targetX;
                                                layoutWidget.localY = targetY;
                                                mouse.accepted = true;
                                            }

                                            onReleased: function(mouse) {
                                                if (isMoving) {
                                                    isMoving = false;
                                                    root._editorState = "idle";
                                                    root._snapGuides = [];
                                                    root.commitWidgetGeometry(index, Math.round(layoutWidget.localX), Math.round(layoutWidget.localY), Math.round(layoutWidget.localW), Math.round(layoutWidget.localH));
                                                }
                                                mouse.accepted = true;
                                            }
                                        }

                                        // 8 Resize Handles (only visible when selected and not locked)
                                        ResizeHandle { anchors.horizontalCenter: parent.left; anchors.verticalCenter: parent.top; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: -1; edgeY: -1; resizeCursor: Qt.SizeFDiagCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.top; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: 0; edgeY: -1; resizeCursor: Qt.SizeVerCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.right; anchors.verticalCenter: parent.top; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: 1; edgeY: -1; resizeCursor: Qt.SizeBDiagCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.left; anchors.verticalCenter: parent.verticalCenter; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: -1; edgeY: 0; resizeCursor: Qt.SizeHorCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: 1; edgeY: 0; resizeCursor: Qt.SizeHorCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.left; anchors.verticalCenter: parent.bottom; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: -1; edgeY: 1; resizeCursor: Qt.SizeBDiagCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.bottom; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: 0; edgeY: 1; resizeCursor: Qt.SizeVerCursor }
                                        ResizeHandle { anchors.horizontalCenter: parent.right; anchors.verticalCenter: parent.bottom; visible: layoutWidget.isSelected && !modelData.locked; targetItem: layoutWidget; edgeX: 1; edgeY: 1; resizeCursor: Qt.SizeFDiagCursor }
                                    }
                                }
                            }
                        }

                        // Right panel: Active widgets list
                        Rectangle {
                            Layout.preferredWidth: 230
                            Layout.fillHeight: true
                            radius: 10
                            color: "#0d1320"
                            border.width: 1
                            border.color: cardEdge

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Шари"; color: ink; font.pixelSize: 14; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: (root.layoutDoc.widgets || []).length; color: muted; font.pixelSize: 11 }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Порядок віджетів"
                                    color: muted
                                    font.pixelSize: 10
                                }

                                ListView {
                                    id: activeLayoutWidgets
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 5
                                    model: root.layoutDoc.widgets || []

                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        width: activeLayoutWidgets.width
                                        height: 44
                                        radius: 7
                                        color: index === root.selectedLayoutWidget ? "#134e4a" : (itemHover.hovered ? "#1b2537" : "#141c2c")
                                        border.width: index === root.selectedLayoutWidget ? 1 : 0
                                        border.color: "#5eead4"

                                        HoverHandler { id: itemHover }

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 6
                                            spacing: 4

                                            Image {
                                                Layout.preferredWidth: 16
                                                Layout.preferredHeight: 16
                                                source: {
                                                    var info = root.widgetTypeInfo(modelData.type);
                                                    return Qt.resolvedUrl("../assets/icons/" + (info.iconName || "web_layout.svg"));
                                                }
                                                opacity: modelData.visible === false ? 0.4 : 1.0
                                            }
                                            Text {
                                                text: {
                                                    var info = root.widgetTypeInfo(modelData.type);
                                                    return info.label || modelData.type;
                                                }
                                                color: modelData.visible === false ? muted : ink
                                                font.pixelSize: 11
                                                font.weight: index === root.selectedLayoutWidget ? Font.Medium : Font.Normal
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            EditorIconButton {
                                                iconName: "chevron-up.svg"
                                                toolTipText: "Підняти шар"
                                                implicitWidth: 24
                                                implicitHeight: 24
                                                enabled: index > 0
                                                onClicked: root.moveWidgetLayer(index, index - 1)
                                            }
                                            EditorIconButton {
                                                iconName: "chevron-down.svg"
                                                toolTipText: "Опустити шар"
                                                implicitWidth: 24
                                                implicitHeight: 24
                                                enabled: index < (root.layoutDoc.widgets || []).length - 1
                                                onClicked: root.moveWidgetLayer(index, index + 1)
                                            }
                                            EditorIconButton {
                                                iconName: modelData.locked ? "editor_lock.svg" : "editor_unlock.svg"
                                                toolTipText: modelData.locked ? "Розблокувати" : "Заблокувати"
                                                implicitWidth: 24
                                                implicitHeight: 24
                                                active: modelData.locked
                                                onClicked: root.toggleWidgetLock(index)
                                            }
                                            EditorIconButton {
                                                iconName: modelData.visible === false ? "editor_eye_off.svg" : "editor_eye.svg"
                                                toolTipText: modelData.visible === false ? "Показати" : "Сховати"
                                                implicitWidth: 24
                                                implicitHeight: 24
                                                onClicked: root.toggleWidgetVisibility(index)
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            z: -1
                                            onClicked: {
                                                root.selectedLayoutWidget = index;
                                                layoutCanvas.forceActiveFocus();
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: !(root.layoutDoc.widgets || []).length
                                    Layout.fillWidth: true
                                    text: "Додайте віджет з панелі зліва"
                                    color: muted
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    // Bottom Panel: Canvas Settings & Widget Inspector
                    Rectangle {
                        Layout.fillWidth: true
                        radius: 10
                        color: "#0d1320"
                        border.width: 1
                        border.color: cardEdge
                        implicitHeight: layoutProperties.implicitHeight + 16

                        ColumnLayout {
                            id: layoutProperties
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text { text: "Полотно"; color: ink; font.pixelSize: 12; font.bold: true }
                                StyledComboBox {
                                    Layout.preferredWidth: 240
                                    model: ["1920 × 1080 · Горизонталь", "1080 × 1920 · TikTok вертикаль", "1080 × 1080 · Квадрат", "1280 × 720 · HD", "Вручну"]
                                    currentIndex: root.canvasPresetIndex
                                    onUserActivated: function(index) { root.selectCanvasPreset(index); }
                                }
                                Text { visible: root.canvasPresetIndex === 4; text: "W:"; color: muted; font.pixelSize: 11 }
                                StyledSpinBox {
                                    visible: root.canvasPresetIndex === 4
                                    Layout.preferredWidth: 84
                                    from: 320; to: 10000
                                    value: Number(root.layoutDoc.width || 1920)
                                    onValueModified: {
                                        if (value !== Number(root.layoutDoc.width || 1920)) {
                                            root.applyLayoutPreset(value, Number(root.layoutDoc.height || 1080), "Custom");
                                        }
                                    }
                                }
                                Text { visible: root.canvasPresetIndex === 4; text: "H:"; color: muted; font.pixelSize: 11 }
                                StyledSpinBox {
                                    visible: root.canvasPresetIndex === 4
                                    Layout.preferredWidth: 84
                                    from: 180; to: 10000
                                    value: Number(root.layoutDoc.height || 1080)
                                    onValueModified: {
                                        if (value !== Number(root.layoutDoc.height || 1080)) {
                                            root.applyLayoutPreset(Number(root.layoutDoc.width || 1920), value, "Custom");
                                        }
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                EditorIconButton {
                                    iconName: "web_trash.svg"
                                    toolTipText: "Видалити віджет"
                                    enabled: root.selectedLayoutItem() !== null
                                    onClicked: root.removeSelectedLayoutWidget()
                                }
                            }

                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: cardEdge }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Image {
                                    visible: root.selectedLayoutItem() !== null
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    source: {
                                        var item = root.selectedLayoutItem();
                                        var info = item ? root.widgetTypeInfo(item.type) : null;
                                        return Qt.resolvedUrl("../assets/icons/" + ((info && info.iconName) || "web_layout.svg"));
                                    }
                                }
                                Text {
                                    text: {
                                        var item = root.selectedLayoutItem();
                                        if (!item) return "Виберіть віджет для редагування";
                                        var info = root.widgetTypeInfo(item.type);
                                        return info.label || item.type;
                                    }
                                    color: root.selectedLayoutItem() ? "#5eead4" : muted
                                    font.pixelSize: 12
                                    font.bold: root.selectedLayoutItem() !== null
                                }

                                Item { Layout.fillWidth: true }

                                RowLayout {
                                    visible: root.selectedLayoutItem() !== null
                                    spacing: 5

                                    Text { text: "X"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutXSpin
                                        Layout.preferredWidth: 86
                                        from: -5000; to: 10000
                                        Binding {
                                            target: layoutXSpin
                                            property: "value"
                                            value: root.selectedLayoutItem() ? Number(root.selectedLayoutItem().x || 0) : 0
                                            when: !layoutXSpin.activeFocus
                                        }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().x || 0)) {
                                                root.updateLayoutItem("x", value);
                                            }
                                        }
                                    }

                                    Text { text: "Y"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutYSpin
                                        Layout.preferredWidth: 86
                                        from: -5000; to: 10000
                                        Binding {
                                            target: layoutYSpin
                                            property: "value"
                                            value: root.selectedLayoutItem() ? Number(root.selectedLayoutItem().y || 0) : 0
                                            when: !layoutYSpin.activeFocus
                                        }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().y || 0)) {
                                                root.updateLayoutItem("y", value);
                                            }
                                        }
                                    }

                                    Text { text: "W"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutWSpin
                                        Layout.preferredWidth: 86
                                        from: 1; to: 10000
                                        Binding {
                                            target: layoutWSpin
                                            property: "value"
                                            value: root.selectedLayoutItem() ? Number(root.selectedLayoutItem().width || 320) : 320
                                            when: !layoutWSpin.activeFocus
                                        }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().width || 320)) {
                                                root.updateLayoutItem("width", value);
                                            }
                                        }
                                    }

                                    Text { text: "H"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutHSpin
                                        Layout.preferredWidth: 86
                                        from: 1; to: 10000
                                        Binding {
                                            target: layoutHSpin
                                            property: "value"
                                            value: root.selectedLayoutItem() ? Number(root.selectedLayoutItem().height || 180) : 180
                                            when: !layoutHSpin.activeFocus
                                        }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().height || 180)) {
                                                root.updateLayoutItem("height", value);
                                            }
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                visible: root.selectedLayoutItem() !== null
                                Layout.fillWidth: true
                                spacing: 8
                                Text { text: root.loc("widgets.layouts.instance"); color: muted; font.pixelSize: 12 }
                                StyledComboBox {
                                    id: layoutInstBox
                                    Layout.preferredWidth: 240
                                    model: root.layoutWidgetInstanceOptions(
                                        root.selectedLayoutItem() ? root.selectedLayoutItem().type : "").map(
                                        function(o) { return o.label; })
                                    currentIndex: root.layoutWidgetInstanceIndex()
                                    onUserActivated: function(idx) { root.applyLayoutWidgetInstance(idx); }
                                    onActivated: function(idx) { root.applyLayoutWidgetInstance(idx); }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    color: muted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    text: {
                                        var iid = root.selectedLayoutWidgetInstanceId();
                                        return iid ? ("by-id: " + iid.slice(0, 8) + "…") : "";
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        radius: 9
                        color: "#0d1320"
                        border.width: 1
                        border.color: cardEdge

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 6
                            spacing: 8
                            Image {
                                Layout.preferredWidth: 15
                                Layout.preferredHeight: 15
                                source: Qt.resolvedUrl("../assets/icons/web_layout.svg")
                            }
                            Text { text: "Layout URL"; color: muted; font.pixelSize: 11; font.bold: true }
                            TextField {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                readOnly: true
                                selectByMouse: true
                                color: inkSecondary
                                font.pixelSize: 11
                                text: api ? api.layoutOverlayUrl(root.activeLayoutId || "default") : ""
                                background: Rectangle { radius: 6; color: fieldBg }
                            }
                            EditorIconButton {
                                iconName: "copy.svg"
                                toolTipText: "Скопіювати URL"
                                implicitWidth: 28
                                implicitHeight: 28
                                onClicked: if (api) api.copyLayoutOverlayUrl(root.activeLayoutId || "default")
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 12
                color: "#0e2a26"
                border.width: 1
                border.color: "#14b8a6"
                visible: root.editingInstanceId !== "" && root.widgetMode !== "grid" && root.widgetMode !== "layout" && !root.universalEditorActive
                implicitHeight: editingBanner.implicitHeight + 16
                ColumnLayout {
                    id: editingBanner
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 4
                    Text {
                        Layout.fillWidth: true
                        color: "#5eead4"
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                        text: root.loc("widgets.instances.editing_title") + " " + (
                            root.editingInstanceName || root.editingInstanceId)
                    }
                    Text {
                        Layout.fillWidth: true
                        color: inkSecondary
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        text: root.loc("widgets.instances.editing_hint")
                    }
                    RowLayout {
                        spacing: 8
                        PillButton {
                            text: root.loc("widgets.common.back")
                            pillFontSize: 11
                            onClicked: root.widgetMode = "grid"
                        }
                        PillButton {
                            text: root.loc("widgets.common.copy_url")
                            pillFontSize: 11
                            onClicked: { if (api) api.copyWidgetInstanceUrl(root.editingInstanceId); }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "chat" && !root.universalEditorActive
                implicitHeight: editChatHeader.implicitHeight + 20

                ColumnLayout {
                    id: editChatHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Chat overlay"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.chatOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyChatOverlayUrl(); })
                        }

                        PillButton {
                            text: "Зберегти й застосувати"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "actions" && !root.universalEditorActive
                implicitHeight: editActionsHeader.implicitHeight + 20

                ColumnLayout {
                    id: editActionsHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Actions overlay"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.actionsOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyActionsOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewActionsOverlay()
                        }

                        PillButton {
                            text: "Зберегти й застосувати"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "online" && !root.universalEditorActive
                implicitHeight: editOnlineHeader.implicitHeight + 20

                ColumnLayout {
                    id: editOnlineHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Online overlay"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.onlineOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyOnlineOverlayUrl(); })
                        }

                        PillButton {
                            text: "Зберегти й застосувати"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: (root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") && !root.universalEditorActive
                implicitHeight: editTopLikersHeader.implicitHeight + 20

                ColumnLayout {
                    id: editTopLikersHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: root.widgetMode === "top_gifters" ? "Top GIFters (TikTok)" : "Top Likers (TikTok)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(root.widgetMode === "top_gifters" ? api.topGiftersOverlayUrlValue : api.topLikersOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() {
                                if (!api) return;
                                if (root.widgetMode === "top_gifters") api.copyTopGiftersOverlayUrl();
                                else api.copyTopLikersOverlayUrl();
                            })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: {
                                if (!api) return;
                                if (root.widgetMode === "top_gifters") api.previewTopGiftersOverlay();
                                else api.previewTopLikersOverlay();
                            }
                        }

                        PillButton {
                            text: "Зберегти й застосувати"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "king_of_live" && !root.universalEditorActive
                implicitHeight: editKingHeader.implicitHeight + 20

                ColumnLayout {
                    id: editKingHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "King of the Live (TikTok)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.kingOfLiveOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyKingOfLiveOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewKingOfLiveOverlay()
                        }

                        PillButton {
                            text: "Зберегти й застосувати"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "stream_pet" && !root.universalEditorActive
                implicitHeight: editStreamPetHeader.implicitHeight + 20

                ColumnLayout {
                    id: editStreamPetHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "StreamPet (Тамагочі)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.streamPetOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyStreamPetOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewStreamPetOverlay()
                        }

                        PillButton {
                            text: "Зберегти"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "community_world" && !root.universalEditorActive
                implicitHeight: editCommunityWorldHeader.implicitHeight + 20

                ColumnLayout {
                    id: editCommunityWorldHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Community World (Село)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.communityWorldOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyCommunityWorldOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewCommunityWorldOverlay()
                        }

                        PillButton {
                            text: "Зберегти"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "battle_royale" && !root.universalEditorActive
                implicitHeight: editBattleHeader.implicitHeight + 20

                ColumnLayout {
                    id: editBattleHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Battle Royale (TikTok)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.battleRoyaleOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyBattleRoyaleOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewBattleRoyaleOverlay()
                        }

                        PillButton {
                            text: "Зберегти"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "stream_goal" && !root.universalEditorActive
                implicitHeight: editStreamGoalHeader.implicitHeight + 20

                ColumnLayout {
                    id: editStreamGoalHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: root.loc("widgets.stream_goal.title")
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.streamGoalOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: root.loc("widgets.common.copy_url")
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyStreamGoalOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewStreamGoalOverlay()
                        }

                        PillButton {
                            text: root.loc("widgets.common.save")
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: root.loc("widgets.common.back")
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "live_leaderboard" && !root.universalEditorActive
                implicitHeight: editLiveLeaderboardHeader.implicitHeight + 20

                ColumnLayout {
                    id: editLiveLeaderboardHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Live Leaderboard (Живий рейтинг)"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.liveLeaderboardOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyLiveLeaderboardOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewLiveLeaderboardOverlay()
                        }

                        PillButton {
                            text: "Зберегти"
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "social_rotator" && !root.universalEditorActive
                implicitHeight: editSocialRotatorHeader.implicitHeight + 20

                ColumnLayout {
                    id: editSocialRotatorHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: root.loc("widgets.social_rotator.title")
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.socialRotatorOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: root.loc("widgets.common.copy_url")
                            onClicked: root.copyEditorUrl(function() { if (api) api.copySocialRotatorOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewSocialRotatorOverlay()
                        }

                        PillButton {
                            text: root.loc("widgets.common.save")
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: root.loc("widgets.common.back")
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "webcam_frame" && !root.universalEditorActive
                implicitHeight: editWebcamFrameHeader.implicitHeight + 20

                ColumnLayout {
                    id: editWebcamFrameHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: root.loc("widgets.webcam_frame.title")
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.webcamFrameOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: root.loc("widgets.common.copy_url")
                            onClicked: root.copyEditorUrl(function() { if (api) api.copyWebcamFrameOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewWebcamFrameOverlay()
                        }

                        PillButton {
                            text: root.loc("widgets.common.save")
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: root.loc("widgets.common.back")
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "signal_system" && !root.universalEditorActive
                implicitHeight: editSignalSystemHeader.implicitHeight + 20

                ColumnLayout {
                    id: editSignalSystemHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: root.loc("widgets.signal_system.edit_header")
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            selectByMouse: true
                            color: ink
                            font.pixelSize: 12
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            text: api ? root.editorUrlValue(api.signalSystemOverlayUrlValue) : ""
                        }

                        PillButton {
                            text: root.loc("widgets.common.copy_url")
                            onClicked: root.copyEditorUrl(function() { if (api) api.copySignalSystemOverlayUrl(); })
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewSignalSystemOverlay()
                        }

                        PillButton {
                            text: root.loc("widgets.common.save")
                            enabled: root._canSaveCurrentWidget
                            onClicked: root._saveAndApplyCurrentWidget()
                        }

                        PillButton {
                            text: root.loc("widgets.common.back")
                            onClicked: root.widgetMode = "grid"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode !== "grid" && root.widgetMode !== "layout" && !root.universalEditorActive

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    contentWidth: availableWidth
                    background: Item {}

                    ColumnLayout {
                        width: Math.max(1, parent.width - 24)
                        spacing: 10

                        ColumnLayout {
                            id: chatSettings
                            visible: root.widgetMode === "chat"
                            Layout.fillWidth: true
                            spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "К-сть повідомлень"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: maxItems
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "max_items"
                                hostDefault: 12
                                from: 1
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: fontSize
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "font_size_px"
                                hostDefault: 18
                                from: 8
                                to: 96
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Іконки платформ"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: showPlatformIcon
                                checked: root.cfg ? !!root.cfg.show_platform_icon : true
                                onClicked: {
                                    if (root.cfg === null) return;
                                    root.cfg.show_platform_icon = checked;
                                    root._save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Авто-приховування (сек)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: fadeSeconds
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "fade_seconds"
                                hostDefault: 0
                                from: 0
                                to: 600
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон віджета"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: widgetBgSw
                                checked: root.cfg ? !!root.cfg.widget_bg_enabled : false
                                onClicked: {
                                    if (root.cfg === null) return;
                                    root.cfg.widget_bg_enabled = checked;
                                    root._save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.widget_bg_enabled
                            Text { text: "Колір фону"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _widgetBgColor
                                border.width: 1
                                border.color: cardEdge
                                opacity: _widgetBgAlpha
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                focusPolicy: Qt.NoFocus
                                onClicked: widgetBgColorDlg.open()
                            }
                            StyledSlider {
                                id: widgetBgAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _widgetBgAlpha
                                onMoved: {
                                    if (root.cfg === null) return;
                                    _widgetBgAlpha = value;
                                    root.cfg.widget_bg_rgba = _rgbaString(_widgetBgColor, _widgetBgAlpha);
                                    root._save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.widget_bg_enabled
                            Text { text: "Заокруглення фону (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: widgetBgRadius
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "widget_bg_radius_px"
                                hostDefault: 14
                                from: 0
                                to: 60
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.widget_bg_enabled
                            Text { text: "Внутрішній відступ (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: widgetBgPadding
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "widget_bg_padding_px"
                                hostDefault: 10
                                from: 0
                                to: 48
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон повідомлень"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: bubbleBgSw
                                checked: root.cfg ? !!root.cfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (root.cfg === null) return;
                                    root.cfg.bubble_bg_enabled = checked;
                                    root._save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.bubble_bg_enabled
                            Text { text: "Фон бульбашки"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _bubbleColor
                                border.width: 1
                                border.color: cardEdge
                                opacity: _bubbleAlpha
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                focusPolicy: Qt.NoFocus
                                onClicked: bubbleColorDlg.open()
                            }
                            StyledSlider {
                                id: bubbleAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _bubbleAlpha
                                onMoved: {
                                    if (root.cfg === null) return;
                                    _bubbleAlpha = value;
                                    root.cfg.bubble_bg_rgba = _rgbaString(_bubbleColor, _bubbleAlpha);
                                    root._save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.bubble_bg_enabled
                            Text { text: "Заокруглення (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: bubbleRadius
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "bubble_radius_px"
                                hostDefault: 10
                                from: 0
                                to: 60
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір ніку"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: usernameColorMode
                                model: ["Авто", "Колір платформи", "Свій колір"]
                                Layout.fillWidth: true
                                onUserActivated: {
                                    if (root._loadingCfg || root.cfg === null) return;
                                    root.cfg.username_color_mode = (currentIndex === 1) ? "platform" : ((currentIndex === 2) ? "custom" : "auto");
                                    root._save();
                                }
                                Component.onCompleted: {
                                    if (!root.cfg) return;
                                    var raw = root.cfg.username_color_mode || "auto";
                                    currentIndex = (raw === "platform") ? 1 : ((raw === "custom") ? 2 : 0);
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.username_color_mode === "custom"
                            Text { text: "Свій колір ніку"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _usernameCustomColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                focusPolicy: Qt.NoFocus
                                onClicked: usernameColorDlg.open()
                            }
                            Text {
                                text: root.cfg ? (root.cfg.username_color_custom || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір тексту"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: root.cfg ? (root.cfg.text_color || "#e5e7eb") : "#e5e7eb"
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                focusPolicy: Qt.NoFocus
                                onClicked: textColorDlg.open()
                            }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.cfg ? (root.cfg.text_color || "") : ""
                                onEditingFinished: {
                                    if (root.cfg === null) return;
                                    root.cfg.text_color = text;
                                    root._save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Тінь тексту"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: textShadowSw
                                checked: root.cfg ? !!root.cfg.text_shadow_enabled : false
                                onClicked: {
                                    if (root.cfg === null) return;
                                    root.cfg.text_shadow_enabled = checked;
                                    root._save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.text_shadow_enabled
                            Text { text: "Колір тіні"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _textShadowColor
                                border.width: 1
                                border.color: cardEdge
                                opacity: _textShadowAlpha
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                focusPolicy: Qt.NoFocus
                                onClicked: textShadowColorDlg.open()
                            }
                            StyledSlider {
                                id: shadowAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _textShadowAlpha
                                onMoved: {
                                    if (root.cfg === null) return;
                                    _textShadowAlpha = value;
                                    root.cfg.text_shadow_rgba = _rgbaString(_textShadowColor, _textShadowAlpha);
                                    root._save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.text_shadow_enabled
                            Text { text: "Розмиття тіні"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: textShadowBlur
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "text_shadow_blur_px"
                                hostDefault: 4
                                from: 0
                                to: 24
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.text_shadow_enabled
                            Text { text: "Зміщення X"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: textShadowOffX
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "text_shadow_offset_x_px"
                                hostDefault: 0
                                from: -12
                                to: 12
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.chatCfgEpoch >= 0 && root.cfg && root.cfg.text_shadow_enabled
                            Text { text: "Зміщення Y"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                id: textShadowOffY
                                syncGroup: "chat"
                                hostMap: root.cfg
                                hostKey: "text_shadow_offset_y_px"
                                hostDefault: 1
                                from: -12
                                to: 12
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: fontFamily
                                Layout.fillWidth: true
                                editable: true
                                model: api ? api.systemFontFamilies() : []
                                onUserActivated: {
                                    if (root._loadingCfg || root.cfg === null) return;
                                    root.cfg.font_family = currentText;
                                    root._save();
                                }
                                onAccepted: {
                                    if (root._loadingCfg || root.cfg === null) return;
                                    root.cfg.font_family = editText || currentText;
                                    root._save();
                                }
                                Component.onCompleted: {
                                    if (!root.cfg) return;
                                    var ff = (root.cfg.font_family || "").trim();
                                    var i = model.indexOf(ff);
                                    if (i >= 0) currentIndex = i;
                                    else {
                                        currentIndex = -1;
                                        editText = ff || "Segoe UI";
                                    }
                                }
                            }
                        }

                        } // chatSettings

                        ColumnLayout {
                            id: onlineSettings
                            visible: root.widgetMode === "online"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Online overlay — Налаштування"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Режим"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: onlineLayoutMode
                                Layout.fillWidth: true
                                model: [
                                    "З усіх площадок (іконки + сума)",
                                    "Окремо по кожній площадці"
                                ]
                                onUserActivated: {
                                    if (root._loadingOnlineCfg || root.onlineCfg === null) return;
                                    root.onlineCfg.layout_mode = (currentIndex === 1) ? "per_platform" : "combined";
                                    root._saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!root.onlineCfg) { currentIndex = 0; return; }
                                    var m = String(root.onlineCfg.layout_mode || "combined").toLowerCase();
                                    currentIndex = (m === "per_platform") ? 1 : 0;
                                }
                            }
                        }

                        Text { text: "Площадки"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Twitch"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.platform_twitch_enabled : true
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.platform_twitch_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "TikTok"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.platform_tiktok_enabled : true
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.platform_tiktok_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "YouTube"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.platform_youtube_enabled : true
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.platform_youtube_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Kick"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.platform_kick_enabled : true
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.platform_kick_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "Для YouTube показується кількість унікальних учасників чату за сесію."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: onlineFontFamily
                                Layout.fillWidth: true
                                editable: true
                                model: api ? api.systemFontFamilies() : []
                                onUserActivated: {
                                    if (root._loadingOnlineCfg || root.onlineCfg === null) return;
                                    root.onlineCfg.font_family = currentText;
                                    root._saveOnline();
                                }
                                onAccepted: {
                                    if (root._loadingOnlineCfg || root.onlineCfg === null) return;
                                    root.onlineCfg.font_family = editText || currentText;
                                    root._saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!root.onlineCfg) return;
                                    var ff = (root.onlineCfg.font_family || "").trim();
                                    var i = model.indexOf(ff);
                                    if (i >= 0) currentIndex = i;
                                    else {
                                        currentIndex = -1;
                                        editText = ff || "Segoe UI";
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "font_size_px"
                                hostDefault: 36
                                from: 8
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал між рядками"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "font_line_spacing_px"
                                hostDefault: 0
                                from: 0
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал між літерами"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "font_letter_spacing_px"
                                hostDefault: 0
                                from: -200
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Тінь тексту"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Увімкнути тінь"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.text_shadow_enabled : false
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.text_shadow_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.onlineCfgEpoch >= 0 && root.onlineCfg && root.onlineCfg.text_shadow_enabled
                            Text { text: "Колір тіні"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _onlineTextShadowColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: onlineTextShadowDlg.open()
                            }
                            Text {
                                text: root.onlineCfg ? (root.onlineCfg.text_shadow_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Текст"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір тексту"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _onlineTextColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: onlineTextColorDlg.open()
                            }
                            Text {
                                text: root.onlineCfg ? (root.onlineCfg.text_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Контур шрифту"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Увімкнути контур"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.font_border_enabled : false
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.font_border_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.onlineCfgEpoch >= 0 && root.onlineCfg && root.onlineCfg.font_border_enabled
                            Text { text: "Колір контуру"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _onlineBorderColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: onlineBorderDlg.open()
                            }
                            Text {
                                text: root.onlineCfg ? (root.onlineCfg.font_border_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Ефекти тексту"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ефект"; color: muted; Layout.preferredWidth: 220 }
                            StyledComboBox {
                                id: onlineTextEffect
                                Layout.fillWidth: true
                                model: ["Немає", "Glow", "Neon", "Rainbow", "The Aurora", "Fire"]
                                onUserActivated: {
                                    if (root._loadingOnlineCfg || root.onlineCfg === null) return;
                                    root.onlineCfg.text_effect =
                                        (currentIndex === 1) ? "glow"
                                        : (currentIndex === 2) ? "neon"
                                        : (currentIndex === 3) ? "rainbow"
                                        : (currentIndex === 4) ? "aurora"
                                        : (currentIndex === 5) ? "fire"
                                        : "none";
                                    root._saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!root.onlineCfg) { currentIndex = 0; return; }
                                    var raw = String(root.onlineCfg.text_effect || "none").trim().toLowerCase();
                                    currentIndex =
                                        (raw === "glow") ? 1
                                        : (raw === "neon") ? 2
                                        : (raw === "rainbow") ? 3
                                        : (raw === "aurora") ? 4
                                        : (raw === "fire") ? 5
                                        : 0;
                                }
                            }
                        }

                        Text { text: "Іконки"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір іконки (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "platform_icon_size_px"
                                hostDefault: 28
                                from: 16
                                to: 128
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Відступ іконки — число (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "icon_number_gap_px"
                                hostDefault: 12
                                from: 0
                                to: 80
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Тло блоку"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон-підкладка"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.onlineCfg ? !!root.onlineCfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.bubble_bg_enabled = checked;
                                    root._saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.onlineCfgEpoch >= 0 && root.onlineCfg && root.onlineCfg.bubble_bg_enabled
                            Text { text: "Непрозорість фону"; color: muted; Layout.preferredWidth: 220 }
                            StyledSlider {
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: (root.onlineCfg && root.onlineCfg.bubble_bg_alpha !== undefined) ? root.onlineCfg.bubble_bg_alpha : 0.45
                                onMoved: {
                                    if (root.onlineCfg === null) return;
                                    root.onlineCfg.bubble_bg_alpha = value;
                                    root._saveOnline();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.onlineCfgEpoch >= 0 && root.onlineCfg && root.onlineCfg.bubble_bg_enabled
                            Text { text: "Радіус кутів (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "online"
                                hostMap: root.onlineCfg
                                hostKey: "bubble_radius_px"
                                hostDefault: 14
                                from: 0
                                to: 60
                            }
                            Item { Layout.fillWidth: true }
                        }

                        } // onlineSettings

                        ColumnLayout {
                            id: topLikersSettings
                            visible: root.widgetMode === "top_likers" || root.widgetMode === "top_gifters"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Top Likers — Налаштування"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: tlFontFamily
                                Layout.fillWidth: true
                                editable: true
                                model: api ? api.systemFontFamilies() : []
                                onUserActivated: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.font_family = currentText;
                                    root._saveTierOverlay();
                                }
                                onAccepted: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.font_family = editText || currentText;
                                    root._saveTierOverlay();
                                }
                                Component.onCompleted: {
                                    if (!root.tierOverlayCfg) return;
                                    var ff = (root.tierOverlayCfg.font_family || "").trim();
                                    var i = model.indexOf(ff);
                                    if (i >= 0) currentIndex = i;
                                    else { currentIndex = -1; editText = ff || "Segoe UI"; }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту (нік)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "font_size_px"
                                hostDefault: 22
                                from: 8; to: 120
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал рядків (нік)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "font_line_spacing_px"
                                hostDefault: 4
                                from: 0; to: 80
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал літер"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "font_letter_spacing_px"
                                hostDefault: 0
                                from: -20; to: 40
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір ніку"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlUsernameColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlUsernameDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.color_username || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.widgetMode === "top_gifters" ? "Колір монет" : "Колір лайків"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlPointsColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlPointsDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.color_points || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір рангу"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlRankColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlRankDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.color_rank || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Показувати тінь панелі"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.bg_shadow_enabled : false
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.bg_shadow_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір тіні панелі"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlPanelShadowColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlPanelShadowDlg.open() }
                            }
                            StyledSpinBox {
                                id: tlPanelShadowAlphaSb
                                from: 0; to: 100
                                value: {
                                    void root.topLikersCfgEpoch;
                                    void root.topGiftersCfgEpoch;
                                    return Math.round(_tlPanelShadowAlpha * 100);
                                }
                                onValueChanged: {
                                    if (root._tierOverlayLoading || root.tierOverlayCfg === null) return;
                                    _tlPanelShadowAlpha = value / 100.0;
                                    root.tierOverlayCfg.bg_shadow_color = _rgbaString(_tlPanelShadowColor, _tlPanelShadowAlpha);
                                    root._saveTierOverlay();
                                }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.bg_shadow_color || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Показувати ранг"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_rank : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.show_rank = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.widgetMode === "top_gifters" ? "Показувати монети" : "Показувати лайки"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_likes : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.show_likes = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "RTL (справа наліво)"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.rtl : false
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.rtl = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Корона для 1-го"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_top1_crown : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.show_top1_crown = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Медалі топ-3"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_top3_medal : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.show_top3_medal = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.widgetMode === "top_gifters" ? "Значок монети біля числа" : "Серце біля лайків"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_heart : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.show_heart = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір серця (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "heart_size_px"
                                hostDefault: 14
                                from: 8; to: 48
                                enabled: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_heart : false
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Плавна пульсація серця"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                enabled: root.tierOverlayCfg ? !!root.tierOverlayCfg.show_heart : false
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.heart_animated : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.heart_animated = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Текстові ефекти"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ефект ніку"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: tlTextFx
                                Layout.fillWidth: true
                                textRole: "label"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { label: "Без ефекту"; value: "none" }
                                    ListElement { label: "Веселка"; value: "rainbow" }
                                    ListElement { label: "Полярне сяйво"; value: "aurora" }
                                    ListElement { label: "Кіберпанк"; value: "cyberpunk" }
                                    ListElement { label: "Вогонь"; value: "fire" }
                                    ListElement { label: "Лід"; value: "ice" }
                                    ListElement { label: "Холод"; value: "cold" }
                                    ListElement { label: "Мороз"; value: "freeze" }
                                    ListElement { label: "Потужний"; value: "strong" }
                                }
                                onUserActivated: function (index) {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.text_effect_username = tlTextFx.model.get(index).value;
                                    root._saveTierOverlay();
                                }
                                Component.onCompleted: {
                                    if (!root.tierOverlayCfg) {
                                        currentIndex = 0;
                                        return;
                                    }
                                    var raw = String(root.tierOverlayCfg.text_effect_username || "none").toLowerCase();
                                    for (var ti = 0; ti < tlTextFx.count; ++ti) {
                                        if (tlTextFx.model.get(ti).value === raw) {
                                            currentIndex = ti;
                                            return;
                                        }
                                    }
                                    currentIndex = 0;
                                }
                            }
                        }

                        Text { text: "Хвиля"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Анімація хвилі"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.wave_enabled : false
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.wave_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Швидкість хвилі"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: tlWaveSpd
                                Layout.fillWidth: true
                                textRole: "label"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { label: "Повільно"; value: "slow" }
                                    ListElement { label: "Звичайна"; value: "normal" }
                                    ListElement { label: "Швидко"; value: "fast" }
                                }
                                onUserActivated: function (index) {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.wave_speed = tlWaveSpd.model.get(index).value;
                                    root._saveTierOverlay();
                                }
                                Component.onCompleted: {
                                    if (!root.tierOverlayCfg) {
                                        currentIndex = 1;
                                        return;
                                    }
                                    var raw = String(root.tierOverlayCfg.wave_speed || "normal").toLowerCase();
                                    for (var wi = 0; wi < tlWaveSpd.count; ++wi) {
                                        if (tlWaveSpd.model.get(wi).value === raw) {
                                            currentIndex = wi;
                                            return;
                                        }
                                    }
                                    currentIndex = 1;
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Контур шрифту"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Увімкнути контур"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.font_border_enabled : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.font_border_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір контуру"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlBorderColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlBorderDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.font_border_color || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "Тінь тексту"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Тінь ніку"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.username_text_shadow_enabled : false
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.username_text_shadow_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Колір тіні ніку"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlUsernameShadowColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlUsernameShadowDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.username_text_shadow_color || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.widgetMode === "top_gifters" ? "Тінь числа монет" : "Тінь лайків"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.likes_text_shadow_enabled : false
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.likes_text_shadow_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.widgetMode === "top_gifters" ? "Колір тіні числа монет" : "Колір тіні лайків"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlLikesShadowColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlLikesShadowDlg.open() }
                            }
                            TextField {
                                Layout.fillWidth: true
                                readOnly: true
                                color: ink
                                font.pixelSize: 12
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.tierOverlayCfg ? (root.tierOverlayCfg.likes_text_shadow_color || "") : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "Список лідерів"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Порядок у списку"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: tlLeaderSort
                                Layout.fillWidth: true
                                model: root.widgetMode === "top_gifters"
                                    ? ["Монети: спадання", "Монети: зростання", "Ім'я: А–Я"]
                                    : ["Лайки: спадання", "Лайки: зростання", "Ім'я: А–Я"]
                                onUserActivated: {
                                    if (root.tierOverlayCfg === null) return;
                                    var index = currentIndex;
                                    if (index === 0) root.tierOverlayCfg.leader_sort = "likes_desc";
                                    else if (index === 1) root.tierOverlayCfg.leader_sort = "likes_asc";
                                    else root.tierOverlayCfg.leader_sort = "name_asc";
                                    root._saveTierOverlay();
                                }
                                Component.onCompleted: {
                                    if (!root.tierOverlayCfg) { currentIndex = 0; return; }
                                    var r = String(root.tierOverlayCfg.leader_sort || "likes_desc").toLowerCase();
                                    if (r === "likes_asc") currentIndex = 1;
                                    else if (r === "name_asc") currentIndex = 2;
                                    else currentIndex = 0;
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Кількість у топі"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "top_count"
                                hostDefault: 8
                                from: 1; to: 10
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Аватар (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "avatar_size_px"
                                hostDefault: 48
                                from: 24; to: 120
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Відступ між рядками"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "row_gap_px"
                                hostDefault: 10
                                from: 0; to: 40
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Панель списку"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон панелі"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: root.tierOverlayCfg ? !!root.tierOverlayCfg.list_bg_enabled : true
                                onClicked: {
                                    if (root.tierOverlayCfg === null) return;
                                    root.tierOverlayCfg.list_bg_enabled = checked;
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон (rgba)"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 28; height: 28; radius: 6; color: _tlListBgColor; border.width: 1; border.color: cardEdge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tlListBgDlg.open() }
                            }
                            StyledSpinBox {
                                id: tlListBgAlphaSb
                                from: 0; to: 100
                                value: {
                                    void root.topLikersCfgEpoch;
                                    void root.topGiftersCfgEpoch;
                                    return Math.round(_tlListBgAlpha * 100);
                                }
                                onValueChanged: {
                                    if (root._tierOverlayLoading || root.tierOverlayCfg === null) return;
                                    _tlListBgAlpha = value / 100.0;
                                    root.tierOverlayCfg.list_bg_rgba = _rgbaString(_tlListBgColor, _tlListBgAlpha);
                                    root._saveTierOverlay();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Радіус панелі (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "list_radius_px"
                                hostDefault: 12
                                from: 0; to: 40
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал прокрутки (с)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "tier"
                                hostMap: root.tierOverlayCfg
                                hostKey: "list_scroll_interval_sec"
                                hostDefault: 0
                                from: 0; to: 600
                            }
                            Text {
                                text: "0 — вимк. N>0: N с зверху → вниз → нагору → знову N с (завжди рух, не залежить від кількості лідерів)."
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                        }

                        } // topLikersSettings

                        ColumnLayout {
                            id: kingOfLiveSettings
                            visible: root.widgetMode === "king_of_live"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "King of the Live — стиль і пороги"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Пресет"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: kingPreset
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { text: "Imperial Gold"; value: "imperial_gold" }
                                    ListElement { text: "Cyber King"; value: "cyber_king" }
                                    ListElement { text: "Dark Overlord"; value: "dark_overlord" }
                                    ListElement { text: "Minimalist"; value: "minimalist" }
                                }
                                onUserActivated: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    var v = model.get(index).value;
                                    if (v) { root.kingCfg.preset = v; root._saveKing(); }
                                }
                                Component.onCompleted: {
                                    if (!root.kingCfg) return;
                                    var p = String(root.kingCfg.preset || "imperial_gold").toLowerCase();
                                    for (var i = 0; i < count; ++i) {
                                        if (model.get(i).value === p) { currentIndex = i; return; }
                                    }
                                    currentIndex = 0;
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Заголовок"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.kingCfg ? (root.kingCfg.title_text || "") : ""
                                onEditingFinished: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.title_text = text;
                                    root._saveKing();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Поріг небезпеки (% від рекорду)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "danger_threshold_pct"
                                hostDefault: 90
                                from: 50; to: 99
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Показувати смугу «до корони»"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: root.kingCfg ? !!root.kingCfg.show_gap_strip : true
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.show_gap_strip = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір аватара (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "avatar_size_px"
                                hostDefault: 120
                                from: 64; to: 220
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: kingFontFamily
                                Layout.fillWidth: true
                                editable: true
                                model: api ? api.systemFontFamilies() : []
                                onUserActivated: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.font_family = currentText;
                                    root._saveKing();
                                }
                                onAccepted: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.font_family = editText || currentText;
                                    root._saveKing();
                                }
                                Component.onCompleted: {
                                    if (!root.kingCfg) return;
                                    var ff = (root.kingCfg.font_family || "").trim();
                                    var i = model.indexOf(ff);
                                    if (i >= 0) currentIndex = i;
                                    else { currentIndex = -1; editText = ff || "Segoe UI"; }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Блюр фону за карткою (px, 0 = вимкнено)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "backdrop_blur_px"
                                hostDefault: 0
                                from: 0; to: 48
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Блюр «бабла» за блоком (px, 0 = вимкнено)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "backdrop_bubble_blur_px"
                                hostDefault: 0
                                from: 0; to: 48
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Яскравість променів (фон, %)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "rays_intensity_pct"
                                hostDefault: 130
                                from: 40; to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір тексту (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "text_scale_pct"
                                hostDefault: 100
                                from: 70; to: 160
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтенсивність анімацій (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "king"
                                hostMap: root.kingCfg
                                hostKey: "anim_intensity_pct"
                                hostDefault: 100
                                from: 25; to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Анімації"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Рух аватарки"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_avatar_motion !== false && root.kingCfg.anim_avatar_motion !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_avatar_motion = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Корона (левітація)"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_crown_float !== false && root.kingCfg.anim_crown_float !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_crown_float = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Золоті промені (фон)"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_rays_spin !== false && root.kingCfg.anim_rays_spin !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_rays_spin = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Монети / пил (знизу)"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_coins_fall !== false && root.kingCfg.anim_coins_fall !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_coins_fall = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Пульсація числа 💎"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_gem_pulse !== false && root.kingCfg.anim_gem_pulse !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_gem_pulse = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Мерехтіння заголовка"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_title_shimmer !== false && root.kingCfg.anim_title_shimmer !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_title_shimmer = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Феєрверки при вході короля"; color: muted; Layout.preferredWidth: 160 }
                            StyledCheckBox {
                                checked: !root.kingCfg || (root.kingCfg.anim_fireworks_on_presence !== false && root.kingCfg.anim_fireworks_on_presence !== 0)
                                onClicked: {
                                    if (root._loadingKingCfg || root.kingCfg === null) return;
                                    root.kingCfg.anim_fireworks_on_presence = checked;
                                    root._saveKing();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "Топ береться з локальної БД подарунків (усі стріми). Небезпека трону — коли хтось у цьому ефірі набирає відсоток від рекорду короля."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        } // kingOfLiveSettings

                        ColumnLayout {
                            id: battleRoyaleSettings
                            visible: root.widgetMode === "battle_royale"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Battle Royale — правила та керування"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            PillButton {
                                text: "Старт (топ-2 GIFters)"
                                onClicked: { if (api) api.battleRoyaleStartFromLeaders(); }
                            }
                            PillButton {
                                text: "Стоп битви"
                                onClicked: { if (api) api.battleRoyaleStop(); }
                            }
                            Text {
                                color: muted
                                text: api ? ("Фаза: " + api.battleRoyalePhase()) : ""
                            }
                            Item { Layout.fillWidth: true }
                        }

                        StyledCheckBox {
                            id: battleHideWhenIdleChk
                            text: "Порожній оверлей, коли битви немає"
                            checked: !root.battleCfg || root.battleCfg.hide_when_idle !== false
                            onCheckedChanged: {
                                if (root._loadingBattleCfg || !root.battleCfg) return;
                                root.battleCfg.hide_when_idle = battleHideWhenIdleChk.checked;
                                root._saveBattle();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "HP старт"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "max_hp"
                                hostDefault: 1000
                                from: 100; to: 10000; stepSize: 50
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Тривалість (с)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "round_duration_s"
                                hostDefault: 120
                                from: 30; to: 600; stepSize: 10
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Крит (діаманти)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "crit_threshold_diamonds"
                                hostDefault: 500
                                from: 50; to: 50000; stepSize: 50
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Авто-поріг (кожен)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "auto_threshold_each"
                                hostDefault: 100
                                from: 1; to: 10000; stepSize: 10
                            }
                            StyledCheckBox {
                                id: battleAutoArmChk
                                text: "Авто-старт"
                                checked: !root.battleCfg || root.battleCfg.auto_arm_enabled !== false
                                onCheckedChanged: {
                                    if (root._loadingBattleCfg || !root.battleCfg) return;
                                    root.battleCfg.auto_arm_enabled = battleAutoArmChk.checked;
                                    root._saveBattle();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Подарунків на бійця"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "gifts_per_fighter"
                                hostDefault: 3
                                from: 1; to: 6; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "battle"
                                hostMap: root.battleCfg
                                hostKey: "base_font_size_px"
                                hostDefault: 14
                                from: 10; to: 32; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "На старті кожному бійцю випадкові подарунки з каталогу. Будь-хто може підтримати бійця, надіславши один із його подарунків (іконки на картці). Інші подарунки під час бою не рахуються."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        } // battleRoyaleSettings

                        ColumnLayout {
                            id: streamPetSettings
                            visible: root.widgetMode === "stream_pet"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "StreamPet — енергія та вигляд"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "Пресет пета"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Стиль"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: streamPetPreset
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { text: "Classic Gold"; value: "classic_gold" }
                                    ListElement { text: "Cyber Purple"; value: "cyber_purple" }
                                    ListElement { text: "Cotton Candy"; value: "cotton_candy" }
                                    ListElement { text: "Forest Fox"; value: "forest_fox" }
                                    ListElement { text: "Midnight Shadow"; value: "midnight_shadow" }
                                    ListElement { text: "Sunset Shiba"; value: "sunset_shiba" }
                                    ListElement { text: "Custom (свій)"; value: "custom" }
                                }
                                onUserActivated: {
                                    if (root._loadingStreamPetCfg || root.streamPetCfg === null) return;
                                    var v = model.get(index).value;
                                    if (v) root._applyStreamPetPreset(v);
                                }
                                Component.onCompleted: {
                                    if (!root.streamPetCfg) return;
                                    var p = String(root.streamPetCfg.preset || "classic_gold").toLowerCase();
                                    for (var i = 0; i < count; ++i) {
                                        if (model.get(i).value === p) { currentIndex = i; return; }
                                    }
                                    currentIndex = 0;
                                }
                            }
                        }

                        StyledCheckBox {
                            text: "Нашийник"
                            checked: !root.streamPetCfg || root.streamPetCfg.collar_enabled !== false
                            onCheckedChanged: {
                                if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                root.streamPetCfg.collar_enabled = checked;
                                root.streamPetCfg.preset = "custom";
                                root._saveStreamPet();
                            }
                        }

                        StyledCheckBox {
                            text: "Рум'янці на щоках"
                            checked: !root.streamPetCfg || root.streamPetCfg.blush_enabled !== false
                            onCheckedChanged: {
                                if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                root.streamPetCfg.blush_enabled = checked;
                                root.streamPetCfg.preset = "custom";
                                root._saveStreamPet();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root._streamPetCustom
                            Text { text: "Колір тіла"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle { width: 26; height: 26; radius: 8; color: _spBodyColor; border.width: 1; border.color: cardEdge }
                            PillButton { text: "Вибрати"; onClicked: spBodyColorDlg.open() }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root._streamPetCustom
                            Text { text: "Колір вух"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle { width: 26; height: 26; radius: 8; color: _spEarColor; border.width: 1; border.color: cardEdge }
                            PillButton { text: "Вибрати"; onClicked: spEarColorDlg.open() }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root._streamPetCustom
                            Text { text: "Колір нашийника"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle { width: 26; height: 26; radius: 8; color: _spCollarColor; border.width: 1; border.color: cardEdge }
                            PillButton { text: "Вибрати"; onClicked: spCollarColorDlg.open() }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root._streamPetCustom
                            Text { text: "Фон хмарки"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle { width: 26; height: 26; radius: 8; color: _spBubbleBgColor; border.width: 1; border.color: cardEdge }
                            PillButton { text: "Вибрати"; onClicked: spBubbleBgColorDlg.open() }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Масштаб пета (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "pet_scale_pct"
                                hostDefault: 100
                                from: 50; to: 200; stepSize: 5
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Енергія та поведінка"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        StyledCheckBox {
                            text: "Увімкнено"
                            checked: !root.streamPetCfg || !!root.streamPetCfg.enabled
                            onCheckedChanged: {
                                if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                root.streamPetCfg.enabled = checked;
                                root._saveStreamPet();
                            }
                        }

                        StyledCheckBox {
                            text: "Показувати шкалу енергії"
                            checked: !root.streamPetCfg || root.streamPetCfg.show_energy_bar !== false
                            onCheckedChanged: {
                                if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                root.streamPetCfg.show_energy_bar = checked;
                                root._saveStreamPet();
                            }
                        }

                        StyledCheckBox {
                            text: "Еволюція за енергією (рівні 1–3)"
                            checked: !root.streamPetCfg || root.streamPetCfg.evolution_enabled !== false
                            onCheckedChanged: {
                                if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                root.streamPetCfg.evolution_enabled = checked;
                                root._saveStreamPet();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Макс. довжина фрази"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "bubble_max_chars"
                                hostDefault: 110
                                from: 40; to: 200; stepSize: 10
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "VIP-бонус L3 (с)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "level3_vip_interval_sec"
                                hostDefault: 180
                                from: 30; to: 3600; stepSize: 30
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Енергія після еволюції (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "post_evolution_energy"
                                hostDefault: 50
                                from: 31; to: 100
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Дискотека L3 (мс)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "disco_duration_ms"
                                hostDefault: 5000
                                from: 1000; to: 30000; stepSize: 500
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Початкова енергія (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "initial_energy"
                                hostDefault: 70
                                from: 0; to: 100
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Спад енергії / 2 хв (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "decay_per_2min"
                                hostDefault: 1
                                from: 0; to: 10
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Авто-сон (с)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "sleep_idle_sec"
                                hostDefault: 900
                                from: 60; to: 3600; stepSize: 60
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт хмарки"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.streamPetCfg ? (root.streamPetCfg.bubble_font_family || "Press Start 2P") : "Press Start 2P"
                                onEditingFinished: {
                                    if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                    root.streamPetCfg.bubble_font_family = text;
                                    root._saveStreamPet();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_pet"
                                hostMap: root.streamPetCfg
                                hostKey: "bubble_font_size_px"
                                hostDefault: 20
                                from: 12; to: 48; stepSize: 2
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "URL спрайта (опц.)"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.streamPetCfg ? (root.streamPetCfg.pet_sprite_url || "") : ""
                                placeholderText: "https://..."
                                onEditingFinished: {
                                    if (root._loadingStreamPetCfg || !root.streamPetCfg) return;
                                    root.streamPetCfg.pet_sprite_url = text;
                                    root._saveStreamPet();
                                }
                            }
                        }

                        Text {
                            text: "Команди в чаті: !sleep — сон, !wake / !прокинься — пробудити. Реакції на подарунки, follow і спам працюють на всіх платформах."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        } // streamPetSettings

                        ColumnLayout {
                            id: communityWorldSettings
                            visible: root.widgetMode === "community_world"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Community World — спільне село"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "Село росте разом із ком’юніті: фолови будують хати, лайки наповнюють криницю, шери — міст, а подарунки відкривають вежі та замок. Квести оновлюються наживо."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        StyledCheckBox {
                            text: "Увімкнено"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.enabled !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.enabled = checked;
                                root._saveCommunityWorld();
                            }
                        }

                        StyledCheckBox {
                            text: "Тихий режим (без анімацій святкувань)"
                            checked: !!root.communityWorldCfg && root.communityWorldCfg.quiet_mode
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.quiet_mode = checked;
                                root._saveCommunityWorld();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Тема світу"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwTheme
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "pixel"; text: "Pixel" }
                                    ListElement { value: "fantasy"; text: "Fantasy" }
                                    ListElement { value: "cyber"; text: "Cyber" }
                                    ListElement { value: "ukrainian"; text: "Українське село" }
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    var v = cwTheme.currentIndex >= 0 ? cwTheme.model.get(cwTheme.currentIndex).value : "ukrainian";
                                    root.communityWorldCfg.theme = v;
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розкладка"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwLayout
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "full"; text: "Повна (широкий екран)" }
                                    ListElement { value: "compact"; text: "Компактна (вертикальний стрим)" }
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    var v = cwLayout.currentIndex >= 0 ? cwLayout.model.get(cwLayout.currentIndex).value : "full";
                                    root.communityWorldCfg.layout_mode = v;
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Активні квести (4 слоти)"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Квест 1"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwQ1
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "likes"; text: "Лайки" }
                                    ListElement { value: "shares"; text: "Шери" }
                                    ListElement { value: "gifts"; text: "Койни" }
                                    ListElement { value: "follows"; text: "Фолови" }
                                    ListElement { value: "none"; text: "Вимкнено" }
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    root.communityWorldCfg.quest1_type = cwQ1.currentIndex >= 0 ? cwQ1.model.get(cwQ1.currentIndex).value : "likes";
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Квест 2"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwQ2
                                Layout.fillWidth: true
                                model: cwQ1.model
                                textRole: "text"
                                valueRole: "value"
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    root.communityWorldCfg.quest2_type = cwQ2.currentIndex >= 0 ? cwQ2.model.get(cwQ2.currentIndex).value : "shares";
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Квест 3"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwQ3
                                Layout.fillWidth: true
                                model: cwQ1.model
                                textRole: "text"
                                valueRole: "value"
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    root.communityWorldCfg.quest3_type = cwQ3.currentIndex >= 0 ? cwQ3.model.get(cwQ3.currentIndex).value : "gifts";
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Квест 4"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: cwQ4
                                Layout.fillWidth: true
                                model: cwQ1.model
                                textRole: "text"
                                valueRole: "value"
                                onCurrentIndexChanged: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    root.communityWorldCfg.quest4_type = cwQ4.currentIndex >= 0 ? cwQ4.model.get(cwQ4.currentIndex).value : "follows";
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ціль: лайки"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "quest_likes_target"
                                hostDefault: 5000
                                from: 100; to: 100000000; stepSize: 500
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ціль: шери"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "quest_shares_target"
                                hostDefault: 50
                                from: 5; to: 100000; stepSize: 5
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ціль: койни"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "quest_gifts_target"
                                hostDefault: 1000
                                from: 50; to: 100000000; stepSize: 50
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Ціль: фолови"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "quest_follows_target"
                                hostDefault: 100
                                from: 5; to: 100000; stepSize: 5
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Досвід (XP) за активність"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: фол"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_follow"
                                hostDefault: 40
                                from: 0; to: 1000; stepSize: 5
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: приєднання"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_join"
                                hostDefault: 5
                                from: 0; to: 1000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: повідомлення"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_chat"
                                hostDefault: 2
                                from: 0; to: 1000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: лайки (за 10)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_like_per_10"
                                hostDefault: 2
                                from: 0; to: 1000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: шер"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_share"
                                hostDefault: 25
                                from: 0; to: 1000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: койни (за 10)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_gift_coin_per_10"
                                hostDefault: 1
                                from: 0; to: 1000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "XP: перемога в батлі"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "xp_battle_win"
                                hostDefault: 150
                                from: 0; to: 10000; stepSize: 10
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Показ на екрані"
                            color: ink
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        StyledCheckBox {
                            text: "Рівень і смужка досвіду"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_level !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_level = checked;
                                root._saveCommunityWorld();
                            }
                        }
                        StyledCheckBox {
                            text: "Дошка квестів"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_quests !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_quests = checked;
                                root._saveCommunityWorld();
                            }
                        }
                        StyledCheckBox {
                            text: "Стрічка подій"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_recognition !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_recognition = checked;
                                root._saveCommunityWorld();
                            }
                        }
                        StyledCheckBox {
                            text: "Паспорти глядачів"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_passports !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_passports = checked;
                                root._saveCommunityWorld();
                            }
                        }
                        StyledCheckBox {
                            text: "Будівлі села"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_buildings !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_buildings = checked;
                                root._saveCommunityWorld();
                            }
                        }
                        StyledCheckBox {
                            text: "Старійшини (усі стріми)"
                            checked: !root.communityWorldCfg || root.communityWorldCfg.show_elders !== false
                            onCheckedChanged: {
                                if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                root.communityWorldCfg.show_elders = checked;
                                root._saveCommunityWorld();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Масштаб (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "scale_pct"
                                hostDefault: 100
                                from: 40; to: 200; stepSize: 5
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту (px)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "community_world"
                                hostMap: root.communityWorldCfg
                                hostKey: "font_size_px"
                                hostDefault: 16
                                from: 8; to: 120; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Шрифт"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.communityWorldCfg ? (root.communityWorldCfg.font_family || "Segoe UI") : "Segoe UI"
                                onEditingFinished: {
                                    if (root._loadingCommunityWorldCfg || !root.communityWorldCfg) return;
                                    root.communityWorldCfg.font_family = text;
                                    root._saveCommunityWorld();
                                }
                            }
                        }

                        Text {
                            text: "Будівлі відкриваються автоматично: криниця після 500 лайків, міст після 25 шерів, монумент після 500 койнів, замок — рівень 6."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        } // communityWorldSettings

                        ColumnLayout {
                            id: streamGoalSettings
                            visible: root.widgetMode === "stream_goal"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: root.loc("widgets.stream_goal.settings_title")
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Text {
                            text: root.loc("widgets.stream_goal.settings_blurb")
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        StyledCheckBox {
                            text: root.loc("widgets.common.enabled")
                            checked: !root.streamGoalCfg || root.streamGoalCfg.enabled !== false
                            onCheckedChanged: {
                                if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                root.streamGoalCfg.enabled = checked;
                                root._saveStreamGoal();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.goal_type"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: sgGoalType
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: sgGoalTypeModel
                                }
                                Component.onCompleted: root._rebuildStreamGoalComboModels(sgGoalTypeModel, sgGoalType, sgSkinModel, sgSkin, sgAnimIntensityModel, sgAnimIntensity, sgResetBehaviorModel, sgResetBehavior)
                                onCurrentIndexChanged: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    var v = sgGoalType.currentIndex >= 0 ? sgGoalType.model.get(sgGoalType.currentIndex).value : "followers";
                                    root.streamGoalCfg.goal_type = v;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        Connections {
                            target: (typeof navApi !== "undefined" && navApi) ? navApi : null
                            function onRefreshCounterChanged() {
                                root._rebuildStreamGoalComboModels(sgGoalTypeModel, sgGoalType, sgSkinModel, sgSkin, sgAnimIntensityModel, sgAnimIntensity, sgResetBehaviorModel, sgResetBehavior)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.title"); color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.streamGoalCfg ? (root.streamGoalCfg.title || "") : "GOAL"
                                onEditingFinished: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    root.streamGoalCfg.title = text;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.subtitle"); color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.streamGoalCfg ? (root.streamGoalCfg.subtitle || "") : ""
                                onEditingFinished: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    root.streamGoalCfg.subtitle = text;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.current"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_goal"
                                hostMap: root.streamGoalCfg
                                hostKey: "current_value"
                                hostDefault: 0
                                from: 0; to: 10000000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.target"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_goal"
                                hostMap: root.streamGoalCfg
                                hostKey: "target_value"
                                hostDefault: 10000
                                from: 1; to: 10000000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.skin"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: sgSkin
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: sgSkinModel
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    var v = sgSkin.currentIndex >= 0 ? sgSkin.model.get(sgSkin.currentIndex).value : "digital_core";
                                    root.streamGoalCfg.skin = v;
                                    var skinAccents = {
                                        "digital_core": "#00ffff",
                                        "boss": "#ff3355",
                                        "reactor": "#39ff88",
                                        "rocket": "#ff6600",
                                        "vault": "#88ff00",
                                        "tower": "#ff00aa",
                                        "creature": "#ff66cc"
                                    };
                                    var stock = {
                                        "#00ffff": true, "#ff3355": true, "#39ff88": true,
                                        "#ff6600": true, "#88ff00": true, "#ff00aa": true, "#ff66cc": true
                                    };
                                    var cur = String(root.streamGoalCfg.accent_color || "").toLowerCase();
                                    if (!cur || stock[cur])
                                        root.streamGoalCfg.accent_color = skinAccents[v] || "#00ffff";
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.accent"); color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 13
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: root.streamGoalCfg ? (root.streamGoalCfg.accent_color || "#00ffff") : "#00ffff"
                                onEditingFinished: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    root.streamGoalCfg.accent_color = text;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("widgets.common.scale_percent"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_goal"
                                hostMap: root.streamGoalCfg
                                hostKey: "scale_percent"
                                hostDefault: 100
                                from: 40; to: 250; stepSize: 5
                            }
                            Text {
                                text: root.loc("stream_goal.ui.scale_hint")
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.anim_intensity"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: sgAnimIntensity
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: sgAnimIntensityModel
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    var v = sgAnimIntensity.currentIndex >= 0 ? sgAnimIntensity.model.get(sgAnimIntensity.currentIndex).value : "medium";
                                    root.streamGoalCfg.animation_intensity = v;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        StyledCheckBox {
                            text: root.loc("stream_goal.ui.enable_combo")
                            checked: !root.streamGoalCfg || root.streamGoalCfg.enable_combo !== false
                            onCheckedChanged: {
                                if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                root.streamGoalCfg.enable_combo = checked;
                                root._saveStreamGoal();
                            }
                        }

                        StyledCheckBox {
                            text: root.loc("stream_goal.ui.enable_milestones")
                            checked: !root.streamGoalCfg || root.streamGoalCfg.enable_milestones !== false
                            onCheckedChanged: {
                                if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                root.streamGoalCfg.enable_milestones = checked;
                                root._saveStreamGoal();
                            }
                        }

                        StyledCheckBox {
                            text: root.loc("stream_goal.ui.enable_particles")
                            checked: !root.streamGoalCfg || root.streamGoalCfg.enable_particles !== false
                            onCheckedChanged: {
                                if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                root.streamGoalCfg.enable_particles = checked;
                                root._saveStreamGoal();
                            }
                        }

                        StyledCheckBox {
                            text: root.loc("stream_goal.ui.enable_glitch")
                            checked: !root.streamGoalCfg || root.streamGoalCfg.enable_glitch !== false
                            onCheckedChanged: {
                                if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                root.streamGoalCfg.enable_glitch = checked;
                                root._saveStreamGoal();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.reset_behavior"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: sgResetBehavior
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: sgResetBehaviorModel
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingStreamGoalCfg || !root.streamGoalCfg) return;
                                    var v = sgResetBehavior.currentIndex >= 0 ? sgResetBehavior.model.get(sgResetBehavior.currentIndex).value : "after_completion";
                                    root.streamGoalCfg.reset_behavior = v;
                                    root._saveStreamGoal();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("stream_goal.ui.next_target"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "stream_goal"
                                hostMap: root.streamGoalCfg
                                hostKey: "next_target_value"
                                hostDefault: 25000
                                from: 1; to: 50000000; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        } // streamGoalSettings

                        ColumnLayout {
                            id: liveLeaderboardSettings
                            visible: root.widgetMode === "live_leaderboard"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Live Leaderboard — Живий рейтинг"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "Один датасет, кілька broadcast-сцен. TikTok події оновлюють рейтинг; ротація сцен керується таймлайном (не подіями)."
                            color: muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        StyledCheckBox {
                            text: "Увімкнено"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enabled !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enabled = checked;
                                root._saveLiveLeaderboard();
                            }
                        }

                        Text {
                            text: "ДЖЕРЕЛА РЕЙТИНГУ"
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        StyledCheckBox {
                            text: "Топ лайкерів (Likers)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_likers !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_likers = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Топ донорів (Gifters)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_gifters !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_gifters = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Топ шерів (Sharers)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_sharers !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_sharers = checked;
                                if (checked) root._ensureLiveLeaderboardSourceInSequence("sharers");
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Топ коментаторів (Commenters)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_commenters !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_commenters = checked;
                                if (checked) root._ensureLiveLeaderboardSourceInSequence("commenters");
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Топ контриб'юторів (Contributors)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_contributors !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_contributors = checked;
                                if (checked) root._ensureLiveLeaderboardSourceInSequence("contributors");
                                root._saveLiveLeaderboard();
                            }
                        }

                        Text {
                            text: "СЦЕНИ"
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        StyledCheckBox {
                            text: "Зал слави (Hall of Fame)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_hall_of_fame !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_hall_of_fame = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Арена (Arena)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_arena !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_arena = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Енергомережа (Energy Network)"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_energy_network !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_energy_network = checked;
                                root._saveLiveLeaderboard();
                            }
                        }

                        Text {
                            text: "ПОСЛІДОВНІСТЬ РОТАЦІЇ"
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        Repeater {
                            model: root.liveLeaderboardCfg && root.liveLeaderboardCfg.sequence ? root.liveLeaderboardCfg.sequence.length : 0
                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                property int stepIndex: index
                                property var step: root.liveLeaderboardCfg.sequence[index]

                                Text {
                                    Layout.fillWidth: true
                                    color: ink
                                    font.pixelSize: 12
                                    text: (step ? (String(step.source_id || "") + " / " + String(step.scene_id || "")) : "") +
                                          " — " + (step ? Number(step.duration_sec || 8) : 8) + "s"
                                    elide: Text.ElideRight
                                }

                                SpinBox {
                                    from: 1; to: 120
                                    value: step ? Math.max(1, Math.min(120, Number(step.duration_sec || 8))) : 8
                                    editable: true
                                    onValueModified: {
                                        if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                        root.liveLeaderboardCfg.sequence[stepIndex].duration_sec = value;
                                        root._saveLiveLeaderboard();
                                    }
                                }

                                PillButton {
                                    text: "↑"
                                    enabled: stepIndex > 0
                                    onClicked: {
                                        if (!root.liveLeaderboardCfg || !root.liveLeaderboardCfg.sequence) return;
                                        var arr = root.liveLeaderboardCfg.sequence.slice();
                                        var tmp = arr[stepIndex - 1];
                                        arr[stepIndex - 1] = arr[stepIndex];
                                        arr[stepIndex] = tmp;
                                        root.liveLeaderboardCfg.sequence = arr;
                                        root._saveLiveLeaderboard();
                                    }
                                }
                                PillButton {
                                    text: "↓"
                                    enabled: root.liveLeaderboardCfg && stepIndex < root.liveLeaderboardCfg.sequence.length - 1
                                    onClicked: {
                                        if (!root.liveLeaderboardCfg || !root.liveLeaderboardCfg.sequence) return;
                                        var arr = root.liveLeaderboardCfg.sequence.slice();
                                        var tmp = arr[stepIndex + 1];
                                        arr[stepIndex + 1] = arr[stepIndex];
                                        arr[stepIndex] = tmp;
                                        root.liveLeaderboardCfg.sequence = arr;
                                        root._saveLiveLeaderboard();
                                    }
                                }
                                PillButton {
                                    text: "✕"
                                    onClicked: {
                                        if (!root.liveLeaderboardCfg || !root.liveLeaderboardCfg.sequence) return;
                                        if (root.liveLeaderboardCfg.sequence.length <= 1) return;
                                        var arr = root.liveLeaderboardCfg.sequence.slice();
                                        arr.splice(stepIndex, 1);
                                        root.liveLeaderboardCfg.sequence = arr;
                                        root._saveLiveLeaderboard();
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            StyledComboBox {
                                id: llAddSource
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "likers"; text: "Лайкери" }
                                    ListElement { value: "gifters"; text: "Донори" }
                                    ListElement { value: "sharers"; text: "Шери" }
                                    ListElement { value: "commenters"; text: "Коментатори" }
                                    ListElement { value: "contributors"; text: "Контриб'ютори" }
                                }
                            }
                            StyledComboBox {
                                id: llAddScene
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "hall_of_fame"; text: "Зал слави" }
                                    ListElement { value: "arena"; text: "Арена" }
                                    ListElement { value: "energy_network"; text: "Енергомережа" }
                                }
                            }
                            PillButton {
                                text: "Додати сцену"
                                onClicked: {
                                    if (!root.liveLeaderboardCfg) return;
                                    var src = llAddSource.currentIndex >= 0 ? llAddSource.model.get(llAddSource.currentIndex).value : "likers";
                                    var scn = llAddScene.currentIndex >= 0 ? llAddScene.model.get(llAddScene.currentIndex).value : "hall_of_fame";
                                    var arr = (root.liveLeaderboardCfg.sequence || []).slice();
                                    arr.push({ source_id: src, scene_id: scn, duration_sec: 8 });
                                    root.liveLeaderboardCfg.sequence = arr;
                                    root._saveLiveLeaderboard();
                                }
                            }
                        }

                        Text {
                            text: "НАЛАШТУВАННЯ РЕЙТИНГУ"
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Топ N"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "live_leaderboard"
                                hostMap: root.liveLeaderboardCfg
                                hostKey: "top_n"
                                hostDefault: 10
                                from: 1; to: 10; stepSize: 1
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Період"; color: muted; Layout.preferredWidth: 160 }
                            Text {
                                text: "Цей стрім"
                                color: ink
                                font.pixelSize: 13
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            text: "АНІМАЦІЯ"
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Перехід"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: llTransition
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "glitch_morph"; text: "Glitch Morph" }
                                    ListElement { value: "digital_dissolve"; text: "Digital Dissolve" }
                                    ListElement { value: "scan"; text: "Scan" }
                                    ListElement { value: "fade"; text: "Fade" }
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                    var v = llTransition.currentIndex >= 0 ? llTransition.model.get(llTransition.currentIndex).value : "glitch_morph";
                                    root.liveLeaderboardCfg.transition = v;
                                    root._saveLiveLeaderboard();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтенсивність"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: llAnimIntensity
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    ListElement { value: "low"; text: "Низька" }
                                    ListElement { value: "medium"; text: "Середня" }
                                    ListElement { value: "high"; text: "Висока" }
                                }
                                onCurrentIndexChanged: {
                                    if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                    var v = llAnimIntensity.currentIndex >= 0 ? llAnimIntensity.model.get(llAnimIntensity.currentIndex).value : "medium";
                                    root.liveLeaderboardCfg.animation_intensity = v;
                                    root._saveLiveLeaderboard();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Масштаб (%)"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "live_leaderboard"
                                hostMap: root.liveLeaderboardCfg
                                hostKey: "scale_percent"
                                hostDefault: 100
                                from: 40; to: 250; stepSize: 5
                            }
                            Text {
                                text: "Масштаб елементів у межах віджета (не zoom за край)"
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                        }

                        StyledCheckBox {
                            text: "Анімація зміни рангу"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_rank_change_anim !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_rank_change_anim = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "Частинки"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_particles !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_particles = checked;
                                root._saveLiveLeaderboard();
                            }
                        }
                        StyledCheckBox {
                            text: "CRT-ефекти"
                            checked: !root.liveLeaderboardCfg || root.liveLeaderboardCfg.enable_crt !== false
                            onCheckedChanged: {
                                if (root._loadingLiveLeaderboardCfg || !root.liveLeaderboardCfg) return;
                                root.liveLeaderboardCfg.enable_crt = checked;
                                root._saveLiveLeaderboard();
                            }
                        }

                        } // liveLeaderboardSettings

                        ColumnLayout {
                            id: socialRotatorSettings
                            visible: root.widgetMode === "social_rotator"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: root.loc("widgets.social_rotator.settings_title")
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        StyledCheckBox {
                            text: root.loc("widgets.common.enabled")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.enabled !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.enabled = checked;
                                root._saveSocialRotator();
                            }
                        }

                        Text {
                            text: root.loc("social_rotator.ui.platforms")
                            color: ink
                            font.pixelSize: 13
                            font.bold: true
                        }

                        Repeater {
                            model: root.socialRotatorCfg && root.socialRotatorCfg.platforms ? root.socialRotatorCfg.platforms.length : 0
                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                property int pIndex: index
                                property var prow: root.socialRotatorCfg.platforms[index]

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Text {
                                        text: String(pIndex + 1).padStart(2, "0")
                                        color: muted
                                        font.pixelSize: 12
                                        Layout.preferredWidth: 28
                                    }
                                    Text {
                                        text: (prow && prow.platform) ? String(prow.platform).toUpperCase() : "?"
                                        color: ink
                                        font.pixelSize: 13
                                        font.bold: true
                                        Layout.preferredWidth: 100
                                    }
                                    StyledCheckBox {
                                        text: root.loc("widgets.common.on")
                                        checked: !prow || prow.enabled !== false
                                        onCheckedChanged: {
                                            if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                            root.socialRotatorCfg.platforms[pIndex].enabled = checked;
                                            root._saveSocialRotator();
                                        }
                                    }
                                    PillButton {
                                        text: "↑"
                                        enabled: pIndex > 0
                                        onClicked: root._srMovePlatform(pIndex, -1)
                                    }
                                    PillButton {
                                        text: "↓"
                                        enabled: root.socialRotatorCfg && pIndex < root.socialRotatorCfg.platforms.length - 1
                                        onClicked: root._srMovePlatform(pIndex, 1)
                                    }
                                    PillButton {
                                        text: root.loc("widgets.common.remove")
                                        onClicked: root._srRemovePlatform(pIndex)
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Text { text: root.loc("widgets.common.username"); color: muted; Layout.preferredWidth: 80 }
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        font.pixelSize: 12
                                        text: prow ? (prow.username || "") : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onEditingFinished: {
                                            if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                            root.socialRotatorCfg.platforms[pIndex].username = text;
                                            root._saveSocialRotator();
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Text { text: root.loc("social_rotator.ui.url_override"); color: muted; Layout.preferredWidth: 80 }
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        font.pixelSize: 12
                                        text: prow ? (prow.url || "") : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onEditingFinished: {
                                            if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                            root.socialRotatorCfg.platforms[pIndex].url = text;
                                            root._saveSocialRotator();
                                        }
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            StyledComboBox {
                                id: srAddPlatform
                                Layout.preferredWidth: 160
                                model: ListModel {
                                    ListElement { text: "Twitch"; value: "twitch" }
                                    ListElement { text: "YouTube"; value: "youtube" }
                                    ListElement { text: "Kick"; value: "kick" }
                                    ListElement { text: "Telegram"; value: "telegram" }
                                    ListElement { text: "TikTok"; value: "tiktok" }
                                    ListElement { text: "Instagram"; value: "instagram" }
                                    ListElement { text: "Discord"; value: "discord" }
                                    ListElement { text: "X"; value: "x" }
                                    ListElement { text: "Facebook"; value: "facebook" }
                                }
                                textRole: "text"
                                Component.onCompleted: currentIndex = 0
                            }
                            PillButton {
                                text: root.loc("social_rotator.ui.add_platform")
                                onClicked: {
                                    var v = "twitch";
                                    if (srAddPlatform.currentIndex >= 0)
                                        v = srAddPlatform.model.get(srAddPlatform.currentIndex).value;
                                    root._srAddPlatform(v);
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("social_rotator.ui.rotation_ms"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "social_rotator"
                                hostMap: root.socialRotatorCfg
                                hostKey: "rotation_interval_ms"
                                hostDefault: 8000
                                from: 1000; to: 120000; stepSize: 1000
                            }
                        }
                        Text {
                            text: root.loc("social_rotator.ui.rotation_hint")
                            color: muted
                            font.pixelSize: 11
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("social_rotator.ui.transition"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: srTransition
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: srTransitionModel
                                }
                                Component.onCompleted: root._rebuildSocialRotatorComboModels(srTransitionModel, srTransition, srThemeModel, srTheme)
                                onCurrentIndexChanged: {
                                    if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                    var v = srTransition.currentIndex >= 0
                                        ? srTransition.model.get(srTransition.currentIndex).value
                                        : "glitch_morph";
                                    root.socialRotatorCfg.transition = v;
                                    root._saveSocialRotator();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("widgets.common.theme"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: srTheme
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: srThemeModel
                                }
                                Component.onCompleted: root._rebuildSocialRotatorComboModels(srTransitionModel, srTransition, srThemeModel, srTheme)
                                onCurrentIndexChanged: {
                                    if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                    var v = srTheme.currentIndex >= 0
                                        ? srTheme.model.get(srTheme.currentIndex).value
                                        : "neon_cyber";
                                    root.socialRotatorCfg.theme = v;
                                    root._saveSocialRotator();
                                }
                            }
                        }

                        Connections {
                            target: (typeof navApi !== "undefined" && navApi) ? navApi : null
                            function onRefreshCounterChanged() {
                                root._rebuildSocialRotatorComboModels(srTransitionModel, srTransition, srThemeModel, srTheme)
                            }
                        }

                        Text { text: root.loc("social_rotator.ui.display"); color: ink; font.pixelSize: 13; font.bold: true }

                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.show_url")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_url !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_url = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.show_secondary")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_secondary_platforms !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_secondary_platforms = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.show_countdown")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_countdown !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_countdown = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.glow")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.enable_glow !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.enable_glow = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.particles")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.enable_particles !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.enable_particles = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.crt")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.enable_crt !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.enable_crt = checked;
                                root._saveSocialRotator();
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("social_rotator.ui.bg_opacity"); color: muted; Layout.preferredWidth: 160 }
                            StyledSlider {
                                Layout.fillWidth: true
                                from: 0
                                to: 100
                                stepSize: 1
                                value: root.socialRotatorCfg && root.socialRotatorCfg.background_opacity_percent !== undefined
                                    ? root.socialRotatorCfg.background_opacity_percent
                                    : 85
                                onMoved: {
                                    if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                    root.socialRotatorCfg.background_opacity_percent = Math.round(value);
                                    root._saveSocialRotator();
                                }
                            }
                            Text {
                                text: (root.socialRotatorCfg && root.socialRotatorCfg.background_opacity_percent !== undefined
                                    ? Math.round(root.socialRotatorCfg.background_opacity_percent)
                                    : 85) + "%"
                                color: ink
                                Layout.preferredWidth: 40
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        Text { text: root.loc("social_rotator.ui.stats_strip"); color: ink; font.pixelSize: 13; font.bold: true }

                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.stat.latest_follower")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_latest_follower !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_latest_follower = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.stat.latest_donation")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_latest_donation !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_latest_donation = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.stat.stream_time")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_stream_time !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_stream_time = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.stat.top_donator")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_top_donator !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_top_donator = checked;
                                root._saveSocialRotator();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("social_rotator.ui.stat.online")
                            checked: !root.socialRotatorCfg || root.socialRotatorCfg.show_online !== false
                            onCheckedChanged: {
                                if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                root.socialRotatorCfg.show_online = checked;
                                root._saveSocialRotator();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("social_rotator.ui.coin_rate"); color: muted; Layout.preferredWidth: 180 }
                            TextField {
                                Layout.preferredWidth: 100
                                color: ink
                                font.pixelSize: 12
                                text: root.socialRotatorCfg ? String(root.socialRotatorCfg.tiktok_coin_to_value_rate) : "1"
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                onEditingFinished: {
                                    if (root._loadingSocialRotatorCfg || !root.socialRotatorCfg) return;
                                    var n = parseFloat(text);
                                    if (isNaN(n) || n < 0) n = 1.0;
                                    root.socialRotatorCfg.tiktok_coin_to_value_rate = n;
                                    root._saveSocialRotator();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("widgets.common.scale_percent"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "social_rotator"
                                hostMap: root.socialRotatorCfg
                                hostKey: "scale_percent"
                                hostDefault: 100
                                from: 40; to: 250; stepSize: 5
                            }
                        }

                        } // socialRotatorSettings

                        ColumnLayout {
                            id: webcamFrameSettings
                            visible: root.widgetMode === "webcam_frame"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: root.loc("widgets.webcam_frame.settings_title")
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Text {
                            text: root.loc("widgets.webcam_frame.settings_blurb")
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        StyledCheckBox {
                            text: root.loc("widgets.common.enabled")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enabled !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enabled = checked;
                                root._saveWebcamFrame();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("widgets.common.theme"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: wfTheme
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: wfThemeModel
                                }
                                Component.onCompleted: root._rebuildWebcamFrameComboModels(wfThemeModel, wfTheme, wfIntensityModel, wfIntensity, wfFrameStyleModel, wfFrameStyle)
                                onCurrentIndexChanged: {
                                    if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                    var v = wfTheme.currentIndex >= 0
                                        ? wfTheme.model.get(wfTheme.currentIndex).value
                                        : "neon_cyber";
                                    root.webcamFrameCfg.theme = v;
                                    root._saveWebcamFrame();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("webcam_frame.ui.intensity_label"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: wfIntensity
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: wfIntensityModel
                                }
                                Component.onCompleted: root._rebuildWebcamFrameComboModels(wfThemeModel, wfTheme, wfIntensityModel, wfIntensity, wfFrameStyleModel, wfFrameStyle)
                                onCurrentIndexChanged: {
                                    if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                    var v = wfIntensity.currentIndex >= 0
                                        ? wfIntensity.model.get(wfIntensity.currentIndex).value
                                        : "medium";
                                    root.webcamFrameCfg.intensity = v;
                                    root._saveWebcamFrame();
                                }
                            }
                        }

                        Connections {
                            target: (typeof navApi !== "undefined" && navApi) ? navApi : null
                            function onRefreshCounterChanged() {
                                root._rebuildWebcamFrameComboModels(wfThemeModel, wfTheme, wfIntensityModel, wfIntensity, wfFrameStyleModel, wfFrameStyle)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("webcam_frame.ui.frame_style_label"); color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: wfFrameStyle
                                Layout.fillWidth: true
                                textRole: "text"
                                valueRole: "value"
                                model: ListModel {
                                    id: wfFrameStyleModel
                                }
                                Component.onCompleted: root._rebuildWebcamFrameComboModels(wfThemeModel, wfTheme, wfIntensityModel, wfIntensity, wfFrameStyleModel, wfFrameStyle)
                                onCurrentIndexChanged: {
                                    if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                    var v = wfFrameStyle.currentIndex >= 0
                                        ? wfFrameStyle.model.get(wfFrameStyle.currentIndex).value
                                        : "primary";
                                    root.webcamFrameCfg.frame_style = v;
                                    root._saveWebcamFrame();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("webcam_frame.ui.cam_label"); color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                font.pixelSize: 12
                                maximumLength: 24
                                text: root.webcamFrameCfg ? (root.webcamFrameCfg.cam_label || "") : ""
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                onEditingFinished: {
                                    if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                    root.webcamFrameCfg.cam_label = text;
                                    root._saveWebcamFrame();
                                }
                            }
                        }

                        Text { text: root.loc("webcam_frame.ui.effects"); color: ink; font.pixelSize: 13; font.bold: true }

                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.energy_flow")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_energy_flow !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_energy_flow = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.breathing_glow")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_breathing_glow !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_breathing_glow = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.light_sweep")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_light_sweep !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_light_sweep = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.micro_glitch")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_micro_glitch !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_micro_glitch = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.sparks")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_sparks !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_sparks = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.crt")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_crt !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_crt = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.status_indicator")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_status_indicator !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_status_indicator = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.boot_animation")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_boot_animation !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_boot_animation = checked;
                                root._saveWebcamFrame();
                            }
                        }
                        StyledCheckBox {
                            text: root.loc("webcam_frame.ui.shutdown_animation")
                            checked: !root.webcamFrameCfg || root.webcamFrameCfg.enable_shutdown_animation !== false
                            onCheckedChanged: {
                                if (root._loadingWebcamFrameCfg || !root.webcamFrameCfg) return;
                                root.webcamFrameCfg.enable_shutdown_animation = checked;
                                root._saveWebcamFrame();
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: root.loc("widgets.common.scale_percent"); color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "webcam_frame"
                                hostMap: root.webcamFrameCfg
                                hostKey: "scale_percent"
                                hostDefault: 100
                                from: 40; to: 250; stepSize: 5
                            }
                        }

                        } // webcamFrameSettings

                        ColumnLayout {
                            id: signalSystemSettings
                            visible: root.widgetMode === "signal_system"
                            Layout.fillWidth: true
                            spacing: 12

                            Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

Text {
                                 text: root.loc("widgets.signal_system.settings_title")
                                 color: ink
                                 font.pixelSize: 16
                                 font.bold: true
                                 Layout.fillWidth: true
                             }

StyledCheckBox {
                                 text: root.loc("widgets.common.enabled")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             RowLayout {
                                 Layout.fillWidth: true
                                 spacing: 10
                                 Text { text: root.loc("signal_system.ui.theme"); color: muted; Layout.preferredWidth: 200 }
                                 StyledComboBox {
                                     id: ssTheme
                                     Layout.fillWidth: true
                                     textRole: "text"
                                     valueRole: "value"
                                     model: ListModel {
                                         id: ssThemeModel
                                     }
                                     Component.onCompleted: root._rebuildSignalSystemComboModels(ssThemeModel, ssTheme)
                                     onCurrentIndexChanged: {
                                         if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                         var v = ssTheme.currentIndex >= 0
                                             ? ssTheme.model.get(ssTheme.currentIndex).value
                                             : "neon_cyber";
                                         root.signalSystemCfg.theme = v;
                                        root._saveSignalSystem();
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.title"); color: muted; Layout.preferredWidth: 200 }
                                TextField {
                                    Layout.fillWidth: true
                                    color: ink
                                    font.pixelSize: 12
                                    placeholderText: root.loc("signal_system.goal.system")
                                    text: root.signalSystemCfg ? (root.signalSystemCfg.custom_title || "") : ""
                                    background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                    onEditingFinished: {
                                        if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                        root.signalSystemCfg.custom_title = text;
                                        root._saveSignalSystem();
                                    }
                                }
                            }

                            Text { text: root.loc("signal_system.ui.perimeter") + " / " + root.loc("widgets.common.enabled"); color: ink; font.pixelSize: 13; font.bold: true }

                            StyledCheckBox {
                                text: root.loc("signal_system.ui.perimeter")
                                checked: !root.signalSystemCfg || root.signalSystemCfg.perimeter_enabled !== false
                                onCheckedChanged: {
                                    if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                    root.signalSystemCfg.perimeter_enabled = checked;
                                    root._saveSignalSystem();
                                }
                            }

StyledCheckBox {
                                 text: root.loc("signal_system.ui.particles")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.particles_enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.particles_enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             StyledCheckBox {
                                 text: root.loc("signal_system.ui.glitch")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.glitch_enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.glitch_enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             StyledCheckBox {
                                 text: root.loc("signal_system.ui.sound")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.sound_enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.sound_enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             RowLayout {
                                 Layout.fillWidth: true
                                 spacing: 10
                                 Text { text: root.loc("signal_system.ui.opacity_idle"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "idle_opacity_pct"
                                    hostDefault: 35
                                    from: 0; to: 100; stepSize: 5
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.opacity_active"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "active_opacity_pct"
                                    hostDefault: 100
                                    from: 50; to: 100; stepSize: 5
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.min_gift_coins"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "min_gift_coins_for_event"
                                    hostDefault: 100
                                    from: 1; to: 10000; stepSize: 10
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.cooldown"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "cooldown_ms"
                                    hostDefault: 3000
                                    from: 500; to: 15000; stepSize: 500
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.scale"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "scale_percent"
                                    hostDefault: 100
                                    from: 40; to: 250; stepSize: 5
                                }
                                Text {
                                    text: root.loc("signal_system.ui.scale_hint")
                                    color: muted
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: root.loc("signal_system.ui.core_vertical"); color: muted; Layout.preferredWidth: 200 }
                                VarMapSpinBox {
                                    syncGroup: "signal_system"
                                    hostMap: root.signalSystemCfg
                                    hostKey: "core_vertical_pct"
                                    hostDefault: 50
                                    from: 20; to: 80; stepSize: 1
                                }
                                Text {
                                    text: root.loc("signal_system.ui.core_vertical_hint")
                                    color: muted
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }

                            Text { text: root.loc("signal_system.ui.perimeter") + " / " + root.loc("widgets.common.enabled") + ": " + root.loc("signal_system.goal.activity"); color: ink; font.pixelSize: 13; font.bold: true }

                            StyledCheckBox {
                                text: root.loc("signal_system.goal.milestone") + " " + root.loc("widgets.common.enabled")
                                checked: !root.signalSystemCfg || root.signalSystemCfg.milestones_enabled !== false
                                onCheckedChanged: {
                                    if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                    root.signalSystemCfg.milestones_enabled = checked;
                                    root._saveSignalSystem();
                                }
                            }

                            StyledCheckBox {
                                text: root.loc("signal_system.goal.surge") + " " + root.loc("widgets.common.enabled")
                                checked: !root.signalSystemCfg || root.signalSystemCfg.activity_surge_enabled !== false
                                onCheckedChanged: {
                                    if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                    root.signalSystemCfg.activity_surge_enabled = checked;
                                    root._saveSignalSystem();
                                }
                            }

                            StyledCheckBox {
                                 text: root.loc("signal_system.goal.ai") + " " + root.loc("widgets.common.enabled")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.ai_observations_enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.ai_observations_enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             StyledCheckBox {
                                 text: root.loc("signal_system.goal.anomaly") + " " + root.loc("widgets.common.enabled")
                                 checked: !root.signalSystemCfg || root.signalSystemCfg.unknown_signals_enabled !== false
                                 onCheckedChanged: {
                                     if (root._loadingSignalSystemCfg || !root.signalSystemCfg) return;
                                     root.signalSystemCfg.unknown_signals_enabled = checked;
                                     root._saveSignalSystem();
                                 }
                             }

                             Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                             Text { text: root.loc("signal_system.goal.test"); color: ink; font.pixelSize: 13; font.bold: true }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 8

                                PillButton {
                                    text: "⚡ " + root.loc("signal_system.goal.test") + ": " + root.loc("signal_system.goal.gifts")
                                    onClicked: if (api) api.triggerSignalSystemTest("big_gift")
                                }

                                PillButton {
                                    text: "🎯 " + root.loc("signal_system.goal.test") + ": " + root.loc("signal_system.goal.milestone")
                                    onClicked: if (api) api.triggerSignalSystemTest("milestone")
                                }

                                PillButton {
                                    text: "🔥 " + root.loc("signal_system.goal.test") + ": " + root.loc("signal_system.goal.surge")
                                    onClicked: if (api) api.triggerSignalSystemTest("activity_surge")
                                }

                                PillButton {
                                    text: "🧠 " + root.loc("signal_system.goal.test") + ": " + root.loc("signal_system.goal.ai")
                                    onClicked: if (api) api.triggerSignalSystemTest("ai_observation")
                                }

                                PillButton {
                                    text: "👁️ " + root.loc("signal_system.goal.test") + ": " + root.loc("signal_system.goal.anomaly")
                                    onClicked: if (api) api.triggerSignalSystemTest("unknown_signal")
                                }
                            }
                        } // signalSystemSettings

                        ColumnLayout {
                            id: actionsSettings
                            visible: root.widgetMode === "actions"
                            Layout.fillWidth: true
                            spacing: 10

                        Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }

                        Text {
                            text: "Actions overlay — Налаштування"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font"; color: muted; Layout.preferredWidth: 160 }
                            StyledComboBox {
                                id: actionsFontFamily
                                Layout.fillWidth: true
                                editable: true
                                model: api ? api.systemFontFamilies() : []
                                onUserActivated: {
                                    if (root._loadingActionsCfg || root.actionsCfg === null) return;
                                    root.actionsCfg.font_family = currentText;
                                    root._saveActions();
                                }
                                onAccepted: {
                                    if (root._loadingActionsCfg || root.actionsCfg === null) return;
                                    root.actionsCfg.font_family = editText || currentText;
                                    root._saveActions();
                                }
                                Component.onCompleted: {
                                    if (!root.actionsCfg) return;
                                    var ff = (root.actionsCfg.font_family || "").trim();
                                    var i = model.indexOf(ff);
                                    if (i >= 0) currentIndex = i;
                                    else {
                                        currentIndex = -1;
                                        editText = ff || "Segoe UI";
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font size"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "font_size_px"
                                hostDefault: 40
                                from: 8
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font line spacing"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "font_line_spacing_px"
                                hostDefault: 0
                                from: 0
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font letter spacing"; color: muted; Layout.preferredWidth: 160 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "font_letter_spacing_px"
                                hostDefault: 0
                                from: -200
                                to: 200
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Font Effects"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Wave Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.wave_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.wave_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Move Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.move_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.move_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable 3D Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.effect_3d_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.effect_3d_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Wiggle Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.wiggle_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.wiggle_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Text Shadow"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Text Shadow"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.text_shadow_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.text_shadow_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && root.actionsCfg.text_shadow_enabled
                            Text { text: "Shadow Color"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _actionsTextShadowColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: actionsTextShadowDlg.open()
                            }
                            Text {
                                text: root.actionsCfg ? (root.actionsCfg.text_shadow_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Text"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Text Color"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _actionsTextColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: actionsTextColorDlg.open()
                            }
                            Text {
                                text: root.actionsCfg ? (root.actionsCfg.text_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Font Border"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Font Border"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.font_border_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.font_border_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && root.actionsCfg.font_border_enabled
                            Text { text: "Border Color"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _actionsBorderColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: actionsBorderDlg.open()
                            }
                            Text {
                                text: root.actionsCfg ? (root.actionsCfg.font_border_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        Text { text: "Username"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Custom Color"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.username_custom_color_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.username_custom_color_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && root.actionsCfg.username_custom_color_enabled
                            Text { text: "Custom Color"; color: muted; Layout.preferredWidth: 220 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _actionsCustomColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            PillButton {
                                text: "Вибрати колір"
                                onClicked: actionsCustomColorDlg.open()
                            }
                            Text {
                                text: root.actionsCfg ? (root.actionsCfg.username_custom_color || "") : ""
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Username Text Effect"; color: muted; Layout.preferredWidth: 220 }
                            StyledComboBox {
                                id: actionsUsernameEffect
                                Layout.fillWidth: true
                                model: ["None", "Rainbow", "The Aurora", "Neon", "Fire"]
                                onUserActivated: {
                                    if (root._loadingActionsCfg || root.actionsCfg === null) return;
                                    root.actionsCfg.username_text_effect =
                                        (currentIndex === 1) ? "rainbow"
                                        : (currentIndex === 2) ? "aurora"
                                        : (currentIndex === 3) ? "neon"
                                        : (currentIndex === 4) ? "fire"
                                        : "none";
                                    root._saveActions();
                                }
                                Component.onCompleted: {
                                    if (!root.actionsCfg) { currentIndex = 0; return; }
                                    var raw = (root.actionsCfg.username_text_effect || "none").trim().toLowerCase();
                                    currentIndex =
                                        (raw === "rainbow") ? 1
                                        : (raw === "aurora") ? 2
                                        : (raw === "neon") ? 3
                                        : (raw === "fire") ? 4
                                        : 0;
                                }
                            }
                        }

                        Text { text: "Size"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Picture Size"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "picture_size_px"
                                hostDefault: 65
                                from: 1
                                to: 512
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Username Size"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "username_size_px"
                                hostDefault: 65
                                from: 1
                                to: 512
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Відстань між ніком і текстом (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "name_text_gap_px"
                                hostDefault: 8
                                from: 0
                                to: 80
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Options"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Bubble background"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.bubble_bg_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && root.actionsCfg.bubble_bg_enabled
                            Text { text: "Bubble opacity"; color: muted; Layout.preferredWidth: 220 }
                            StyledSlider {
                                id: bubbleOpacitySlider
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: (root.actionsCfg && root.actionsCfg.bubble_bg_alpha !== undefined) ? root.actionsCfg.bubble_bg_alpha : 0.55
                                onMoved: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.bubble_bg_alpha = value;
                                    root._saveActions();
                                }
                                // Nested map mutations don't notify; re-read after epoch bumps.
                                Connections {
                                    target: root
                                    function onActionsCfgEpochChanged() {
                                        if (!root.actionsCfg) return;
                                        var a = root.actionsCfg.bubble_bg_alpha;
                                        if (a === undefined || a === null) return;
                                        bubbleOpacitySlider.value = a;
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && root.actionsCfg.bubble_bg_enabled
                            Text { text: "Bubble radius (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "bubble_radius_px"
                                hostDefault: 16
                                from: 0
                                to: 60
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Auto-hide (sec)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "auto_hide_seconds"
                                hostDefault: 0
                                from: 0
                                to: 600
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Show Profile Picture"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.show_profile_picture : true
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.show_profile_picture = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Show Gift Picture"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.show_gift_picture : true
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.show_gift_picture = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text {
                                text: "Show streaming platform icon"
                                color: muted
                                Layout.preferredWidth: 220
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 220
                            }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.show_action_platform_icon : true
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.show_action_platform_icon = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && !!root.actionsCfg.show_action_platform_icon
                            Text {
                                text: "Platform icon flip (slow start, sharp finish)"
                                color: muted
                                Layout.preferredWidth: 220
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 220
                            }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.platform_icon_flip_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.platform_icon_flip_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: root.actionsCfgEpoch >= 0 && root.actionsCfg && !!root.actionsCfg.show_action_platform_icon
                            Text { text: "Platform icon size (px)"; color: muted; Layout.preferredWidth: 220 }
                            VarMapSpinBox {
                                syncGroup: "actions"
                                hostMap: root.actionsCfg
                                hostKey: "platform_icon_size_px"
                                hostDefault: 40
                                from: 16
                                to: 128
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Single Text Line"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.single_text_line : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.single_text_line = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text {
                                text: "Parallel popups (random free spot)"
                                color: muted
                                Layout.preferredWidth: 220
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 220
                            }
                            Switch {
                                checked: root.actionsCfg ? !!root.actionsCfg.parallel_popups_enabled : false
                                onClicked: {
                                    if (root.actionsCfg === null) return;
                                    root.actionsCfg.parallel_popups_enabled = checked;
                                    root._saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        } // actionsSettings
                    }
                }
            }

            function reloadAllWidgetConfigs() {
                if (!api) return;
                function _clearWidgetCfgLoadingLocks() {
                    root._loadingCfg = false;
                    root._loadingActionsCfg = false;
                    root._loadingOnlineCfg = false;
                    root._loadingTopLikersCfg = false;
                    root._loadingTopGiftersCfg = false;
                    root._loadingKingCfg = false;
                    root._loadingBattleCfg = false;
                    root._loadingStreamPetCfg = false;
                    root._loadingCommunityWorldCfg = false;
                    root._loadingStreamGoalCfg = false;
                    root._loadingLiveLeaderboardCfg = false;
                    root._loadingSocialRotatorCfg = false;
                    root._loadingWebcamFrameCfg = false;
                    root._loadingSignalSystemCfg = false;
                }
                try {
                // This handler lives on the Loader's inner ColumnLayout, not on root Item:
                // bare `cfg = …` would not assign root.cfg, so _save() would always see root.cfg === null.
                root._loadingCfg = true;
                root._loadingActionsCfg = true;
                root._loadingOnlineCfg = true;
                root._loadingTopLikersCfg = true;
                root._loadingTopGiftersCfg = true;
                root._loadingKingCfg = true;
                root._loadingBattleCfg = true;
                root._loadingStreamPetCfg = true;
                root._loadingCommunityWorldCfg = true;
                root._loadingStreamGoalCfg = true;
                root._loadingLiveLeaderboardCfg = true;
                root._loadingSocialRotatorCfg = true;
                root._loadingWebcamFrameCfg = true;
                root._loadingSignalSystemCfg = true;

                var obj = api.loadChatConfigMap();
                if (!obj || typeof obj !== "object")
                    obj = {};
                root.cfg = root._ensureDefaults(root._detachCfgMap(obj));
                root.chatCfgEpoch += 1;
                // Initialize derived UI state for pickers.
                var p = root._parseRgba(root.cfg.bubble_bg_rgba);
                root._bubbleColor = p.c;
                root._bubbleAlpha = p.a;
                bubbleAlpha.value = root._bubbleAlpha;
                root._usernameCustomColor = root.cfg.username_color_custom || "#93c5fd";
                var sp = root._parseRgba(root.cfg.text_shadow_rgba || "rgba(0,0,0,0.65)");
                root._textShadowColor = sp.c;
                root._textShadowAlpha = sp.a;
                shadowAlpha.value = root._textShadowAlpha;
                var wp = root._parseRgba(root.cfg.widget_bg_rgba || "rgba(10,12,18,0.45)");
                root._widgetBgColor = wp.c;
                root._widgetBgAlpha = wp.a;
                widgetBgAlpha.value = root._widgetBgAlpha;
                root._syncChatCombosFromCfg();

                var aobj = api.loadActionsConfigMap();
                if (!aobj || typeof aobj !== "object")
                    aobj = {};
                root.actionsCfg = root._ensureActionsDefaults(root._detachCfgMap(aobj));
                root.actionsCfgEpoch += 1;
                root._actionsTextShadowColor = root.actionsCfg.text_shadow_color || "#000000";
                root._actionsBorderColor = root.actionsCfg.font_border_color || "#242424";
                root._actionsCustomColor = root.actionsCfg.username_custom_color || "#32c3a6";
                root._actionsTextColor = root.actionsCfg.text_color || "#e5e7eb";
                root._syncActionsCombosFromCfg();

                var oobj = api.loadOnlineOverlayConfigMap();
                if (!oobj || typeof oobj !== "object")
                    oobj = {};
                root.onlineCfg = root._ensureOnlineDefaults(root._detachCfgMap(oobj));
                root.onlineCfgEpoch += 1;
                root._onlineTextShadowColor = root.onlineCfg.text_shadow_color || "#000000";
                root._onlineBorderColor = root.onlineCfg.font_border_color || "#242424";
                root._onlineTextColor = root.onlineCfg.text_color || "#e5e7eb";
                root._syncOnlineCombosFromCfg();

                var tobj = api.loadTopLikersOverlayConfigMap();
                if (!tobj || typeof tobj !== "object")
                    tobj = {};
                root.topLikersCfg = root._ensureTopLikersDefaults(root._detachTierOverlayCfgMap(tobj));
                root._tlUsernameColor = root.topLikersCfg.color_username || "#c4b5fd";
                root._tlPointsColor = root.topLikersCfg.color_points || "#f4f4f5";
                root._tlRankColor = root.topLikersCfg.color_rank || "#d9d9d9";
                root._tlBorderColor = root.topLikersCfg.font_border_color || "#242424";
                root._tlUsernameShadowColor = root._tlColorFromCfg(root.topLikersCfg.username_text_shadow_color);
                root._tlLikesShadowColor = root._tlColorFromCfg(root.topLikersCfg.likes_text_shadow_color);
                var bsp = root._parseRgba(root.topLikersCfg.bg_shadow_color || "rgba(33,33,33,0.4)");
                root._tlPanelShadowColor = bsp.c;
                root._tlPanelShadowAlpha = bsp.a;
                var tlp = root._parseRgba(root.topLikersCfg.list_bg_rgba || "rgba(18,20,28,0.72)");
                root._tlListBgColor = tlp.c;
                root._tlListBgAlpha = tlp.a;
                if (typeof tlListBgAlphaSb !== "undefined")
                    tlListBgAlphaSb.value = Math.round(root._tlListBgAlpha * 100);
                if (typeof tlPanelShadowAlphaSb !== "undefined")
                    tlPanelShadowAlphaSb.value = Math.round(root._tlPanelShadowAlpha * 100);
                if (typeof tlFontFamily !== "undefined" && root.topLikersCfg) {
                    var tff = (root.topLikersCfg.font_family || "").trim();
                    var ti = tlFontFamily.model.indexOf(tff);
                    if (ti >= 0) tlFontFamily.currentIndex = ti;
                    else { tlFontFamily.currentIndex = -1; tlFontFamily.editText = tff || "Segoe UI"; }
                }
                if (typeof tlTextFx !== "undefined" && root.topLikersCfg) {
                    var tx = String(root.topLikersCfg.text_effect_username || "none").toLowerCase();
                    var foundFx = false;
                    for (var tj = 0; tj < tlTextFx.count; ++tj) {
                        if (tlTextFx.model.get(tj).value === tx) {
                            tlTextFx.currentIndex = tj;
                            foundFx = true;
                            break;
                        }
                    }
                    if (!foundFx)
                        tlTextFx.currentIndex = 0;
                }
                if (typeof tlWaveSpd !== "undefined" && root.topLikersCfg) {
                    var ws = String(root.topLikersCfg.wave_speed || "normal").toLowerCase();
                    var foundWs = false;
                    for (var wj = 0; wj < tlWaveSpd.count; ++wj) {
                        if (tlWaveSpd.model.get(wj).value === ws) {
                            tlWaveSpd.currentIndex = wj;
                            foundWs = true;
                            break;
                        }
                    }
                    if (!foundWs)
                        tlWaveSpd.currentIndex = 1;
                }
                if (typeof tlLeaderSort !== "undefined" && root.topLikersCfg) {
                    var r2 = String(root.topLikersCfg.leader_sort || "likes_desc").toLowerCase();
                    if (r2 === "likes_asc") tlLeaderSort.currentIndex = 1;
                    else if (r2 === "name_asc") tlLeaderSort.currentIndex = 2;
                    else tlLeaderSort.currentIndex = 0;
                }
                var tgobj = api.loadTopGiftersOverlayConfigMap();
                if (!tgobj || typeof tgobj !== "object")
                    tgobj = {};
                root.topGiftersCfg = root._ensureTopLikersDefaults(root._detachTierOverlayCfgMap(tgobj));
                var kgobj = api.loadKingOfLiveOverlayConfigMap();
                if (!kgobj || typeof kgobj !== "object")
                    kgobj = {};
                root.kingCfg = JSON.parse(JSON.stringify(kgobj));
                var bgobj = api.loadBattleRoyaleOverlayConfigMap();
                if (!bgobj || typeof bgobj !== "object")
                    bgobj = {};
                root.battleCfg = JSON.parse(JSON.stringify(bgobj));
                root.battleCfgEpoch += 1;
                var spobj = api.loadStreamPetOverlayConfigMap();
                if (!spobj || typeof spobj !== "object")
                    spobj = {};
                root.streamPetCfg = JSON.parse(JSON.stringify(spobj));
                root.streamPetCfgEpoch += 1;
                var cwobj = api.loadCommunityWorldOverlayConfigMap();
                if (!cwobj || typeof cwobj !== "object")
                    cwobj = {};
                root.communityWorldCfg = JSON.parse(JSON.stringify(cwobj));
                root.communityWorldCfgEpoch += 1;
                var sgobj = api.loadStreamGoalOverlayConfigMap();
                if (!sgobj || typeof sgobj !== "object")
                    sgobj = {};
                root.streamGoalCfg = JSON.parse(JSON.stringify(sgobj));
                root.streamGoalCfgEpoch += 1;
                if (root.streamGoalCfg) {
                    var sgIndexFor = function(mdl, val) {
                        for (var sgi = 0; sgi < mdl.count; ++sgi) {
                            if (mdl.get(sgi).value === val) return sgi;
                        }
                        return 0;
                    };
                    if (typeof sgGoalType !== "undefined")
                        sgGoalType.currentIndex = sgIndexFor(sgGoalType.model, root.streamGoalCfg.goal_type || "followers");
                    if (typeof sgSkin !== "undefined")
                        sgSkin.currentIndex = sgIndexFor(sgSkin.model, root.streamGoalCfg.skin || "digital_core");
                    if (typeof sgAnimIntensity !== "undefined")
                        sgAnimIntensity.currentIndex = sgIndexFor(sgAnimIntensity.model, root.streamGoalCfg.animation_intensity || "medium");
                    if (typeof sgResetBehavior !== "undefined")
                        sgResetBehavior.currentIndex = sgIndexFor(sgResetBehavior.model, root.streamGoalCfg.reset_behavior || "after_completion");
                }
                var llobj = api.loadLiveLeaderboardOverlayConfigMap();
                if (!llobj || typeof llobj !== "object")
                    llobj = {};
                root.liveLeaderboardCfg = JSON.parse(JSON.stringify(llobj));
                root.liveLeaderboardCfgEpoch += 1;
                if (root.liveLeaderboardCfg) {
                    if (!root.liveLeaderboardCfg.sequence)
                        root.liveLeaderboardCfg.sequence = [];
                    var llIndexFor = function(mdl, val) {
                        for (var lli = 0; lli < mdl.count; ++lli) {
                            if (mdl.get(lli).value === val) return lli;
                        }
                        return 0;
                    };
                    if (typeof llTransition !== "undefined")
                        llTransition.currentIndex = llIndexFor(llTransition.model, root.liveLeaderboardCfg.transition || "glitch_morph");
                    if (typeof llAnimIntensity !== "undefined")
                        llAnimIntensity.currentIndex = llIndexFor(llAnimIntensity.model, root.liveLeaderboardCfg.animation_intensity || "medium");
                }
                var srobj = api.loadSocialRotatorOverlayConfigMap();
                if (!srobj || typeof srobj !== "object")
                    srobj = {};
                root.socialRotatorCfg = JSON.parse(JSON.stringify(srobj));
                root.socialRotatorCfgEpoch += 1;
                if (root.socialRotatorCfg) {
                    if (!root.socialRotatorCfg.platforms)
                        root.socialRotatorCfg.platforms = [];
                    var srIndexFor = function(mdl, val) {
                        for (var sri = 0; sri < mdl.count; ++sri) {
                            if (mdl.get(sri).value === val) return sri;
                        }
                        return 0;
                    };
                    if (typeof srTransition !== "undefined")
                        srTransition.currentIndex = srIndexFor(srTransition.model, root.socialRotatorCfg.transition || "glitch_morph");
                    if (typeof srTheme !== "undefined")
                        srTheme.currentIndex = srIndexFor(srTheme.model, root.socialRotatorCfg.theme || "neon_cyber");
                }
                if (typeof sgGoalTypeModel !== "undefined")
                    root._rebuildStreamGoalComboModels(sgGoalTypeModel, sgGoalType, sgSkinModel, sgSkin, sgAnimIntensityModel, sgAnimIntensity, sgResetBehaviorModel, sgResetBehavior);
                if (typeof srTransitionModel !== "undefined")
                    root._rebuildSocialRotatorComboModels(srTransitionModel, srTransition, srThemeModel, srTheme);
                var wfobj = api.loadWebcamFrameOverlayConfigMap();
                if (!wfobj || typeof wfobj !== "object")
                    wfobj = {};
                root.webcamFrameCfg = JSON.parse(JSON.stringify(wfobj));
                root.webcamFrameCfgEpoch += 1;
                if (typeof wfThemeModel !== "undefined")
                    root._rebuildWebcamFrameComboModels(wfThemeModel, wfTheme, wfIntensityModel, wfIntensity, wfFrameStyleModel, wfFrameStyle);
                var ssobj = api.loadSignalSystemOverlayConfigMap();
                if (!ssobj || typeof ssobj !== "object")
                    ssobj = {};
                root.signalSystemCfg = JSON.parse(JSON.stringify(ssobj));
                root.signalSystemCfgEpoch += 1;
                if (typeof ssThemeModel !== "undefined")
                    root._rebuildSignalSystemComboModels(ssThemeModel, ssTheme);
                if (root.communityWorldCfg) {
                    var cwIndexFor = function(mdl, val) {
                        for (var ci = 0; ci < mdl.count; ++ci) {
                            if (mdl.get(ci).value === val) return ci;
                        }
                        return 0;
                    };
                    if (typeof cwTheme !== "undefined")
                        cwTheme.currentIndex = cwIndexFor(cwTheme.model, root.communityWorldCfg.theme || "ukrainian");
                    if (typeof cwLayout !== "undefined")
                        cwLayout.currentIndex = cwIndexFor(cwLayout.model, root.communityWorldCfg.layout_mode || "full");
                    if (typeof cwQ1 !== "undefined")
                        cwQ1.currentIndex = cwIndexFor(cwQ1.model, root.communityWorldCfg.quest1_type || "likes");
                    if (typeof cwQ2 !== "undefined")
                        cwQ2.currentIndex = cwIndexFor(cwQ2.model, root.communityWorldCfg.quest2_type || "shares");
                    if (typeof cwQ3 !== "undefined")
                        cwQ3.currentIndex = cwIndexFor(cwQ3.model, root.communityWorldCfg.quest3_type || "gifts");
                    if (typeof cwQ4 !== "undefined")
                        cwQ4.currentIndex = cwIndexFor(cwQ4.model, root.communityWorldCfg.quest4_type || "follows");
                }
                root._spBodyColor = root.streamPetCfg.pet_body_color || "#fbbf24";
                root._spEarColor = root.streamPetCfg.pet_ear_color || "#f59e0b";
                root._spCollarColor = root.streamPetCfg.collar_color || "#ef4444";
                root._spBubbleBgColor = root.streamPetCfg.bubble_bg_color || "#ffffff";
                if (typeof streamPetPreset !== "undefined" && root.streamPetCfg) {
                    var spp = String(root.streamPetCfg.preset || "classic_gold").toLowerCase();
                    for (var spi = 0; spi < streamPetPreset.count; ++spi) {
                        if (streamPetPreset.model.get(spi).value === spp) {
                            streamPetPreset.currentIndex = spi;
                            break;
                        }
                    }
                }
                overlayCfgInitGuardTimer.restart();
                _clearWidgetCfgLoadingLocks();
                } catch (e) {
                    console.warn("WidgetsView: settings init failed:", e);
                    _clearWidgetCfgLoadingLocks();
                }
            }

            Component.onCompleted: reloadAllWidgetConfigs()
        }
    }

    ColorDialog {
        id: bubbleColorDlg
        title: "Bubble background color"
        selectedColor: _bubbleColor
        onAccepted: {
            if (root.cfg === null) return;
            _bubbleColor = selectedColor;
            root.cfg.bubble_bg_rgba = _rgbaString(_bubbleColor, _bubbleAlpha);
            root._save();
        }
    }

    ColorDialog {
        id: widgetBgColorDlg
        title: "Widget background color"
        selectedColor: _widgetBgColor
        onAccepted: {
            if (root.cfg === null) return;
            _widgetBgColor = selectedColor;
            root.cfg.widget_bg_rgba = _rgbaString(_widgetBgColor, _widgetBgAlpha);
            root._save();
        }
    }

    ColorDialog {
        id: usernameColorDlg
        title: "Username color"
        selectedColor: _usernameCustomColor
        onAccepted: {
            if (root.cfg === null) return;
            _usernameCustomColor = selectedColor;
            root.cfg.username_color_custom = _colorToHex(_usernameCustomColor);
            root._save();
        }
    }

    ColorDialog {
        id: textColorDlg
        title: "Text color"
        selectedColor: root.cfg ? (root.cfg.text_color || "#e5e7eb") : "#e5e7eb"
        onAccepted: {
            if (root.cfg === null) return;
            root.cfg.text_color = _colorToHex(selectedColor);
            root._save();
        }
    }

    ColorDialog {
        id: textShadowColorDlg
        title: "Text shadow color"
        selectedColor: _textShadowColor
        onAccepted: {
            if (root.cfg === null) return;
            _textShadowColor = selectedColor;
            root.cfg.text_shadow_rgba = _rgbaString(_textShadowColor, _textShadowAlpha);
            root._save();
        }
    }

    ColorDialog {
        id: actionsTextShadowDlg
        title: "Actions: text shadow color"
        selectedColor: _actionsTextShadowColor
        onAccepted: {
            if (root.actionsCfg === null) return;
            _actionsTextShadowColor = selectedColor;
            root.actionsCfg.text_shadow_color = _colorToHex(selectedColor);
            root._saveActions();
        }
    }

    ColorDialog {
        id: actionsTextColorDlg
        title: "Actions: text color"
        selectedColor: _actionsTextColor
        onAccepted: {
            if (root.actionsCfg === null) return;
            _actionsTextColor = selectedColor;
            root.actionsCfg.text_color = _colorToHex(selectedColor);
            root._saveActions();
        }
    }

    ColorDialog {
        id: actionsBorderDlg
        title: "Actions: border color"
        selectedColor: _actionsBorderColor
        onAccepted: {
            if (root.actionsCfg === null) return;
            _actionsBorderColor = selectedColor;
            root.actionsCfg.font_border_color = _colorToHex(selectedColor);
            root._saveActions();
        }
    }

    ColorDialog {
        id: actionsCustomColorDlg
        title: "Actions: username custom color"
        selectedColor: _actionsCustomColor
        onAccepted: {
            if (root.actionsCfg === null) return;
            _actionsCustomColor = selectedColor;
            root.actionsCfg.username_custom_color = _colorToHex(selectedColor);
            root._saveActions();
        }
    }

    ColorDialog {
        id: onlineTextShadowDlg
        title: "Online: колір тіні"
        selectedColor: _onlineTextShadowColor
        onAccepted: {
            if (root.onlineCfg === null) return;
            _onlineTextShadowColor = selectedColor;
            root.onlineCfg.text_shadow_color = _colorToHex(selectedColor);
            root._saveOnline();
        }
    }

    ColorDialog {
        id: onlineTextColorDlg
        title: "Online: колір тексту"
        selectedColor: _onlineTextColor
        onAccepted: {
            if (root.onlineCfg === null) return;
            _onlineTextColor = selectedColor;
            root.onlineCfg.text_color = _colorToHex(selectedColor);
            root._saveOnline();
        }
    }

    ColorDialog {
        id: onlineBorderDlg
        title: "Online: колір контуру"
        selectedColor: _onlineBorderColor
        onAccepted: {
            if (root.onlineCfg === null) return;
            _onlineBorderColor = selectedColor;
            root.onlineCfg.font_border_color = _colorToHex(selectedColor);
            root._saveOnline();
        }
    }

    ColorDialog {
        id: tlUsernameDlg
        title: "Top Likers: колір ніку"
        selectedColor: _tlUsernameColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlUsernameColor = selectedColor;
            root.tierOverlayCfg.color_username = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlPointsDlg
        title: "Top Likers: колір лайків"
        selectedColor: _tlPointsColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlPointsColor = selectedColor;
            root.tierOverlayCfg.color_points = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlRankDlg
        title: "Top Likers: колір рангу"
        selectedColor: _tlRankColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlRankColor = selectedColor;
            root.tierOverlayCfg.color_rank = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlBorderDlg
        title: "Top Likers: колір контуру"
        selectedColor: _tlBorderColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlBorderColor = selectedColor;
            root.tierOverlayCfg.font_border_color = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlListBgDlg
        title: "Top Likers: колір фону панелі"
        selectedColor: _tlListBgColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlListBgColor = selectedColor;
            root.tierOverlayCfg.list_bg_rgba = _rgbaString(_tlListBgColor, _tlListBgAlpha);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlPanelShadowDlg
        title: "Top Likers: колір тіні панелі"
        selectedColor: _tlPanelShadowColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlPanelShadowColor = selectedColor;
            root.tierOverlayCfg.bg_shadow_color = _rgbaString(_tlPanelShadowColor, _tlPanelShadowAlpha);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlUsernameShadowDlg
        title: "Top Likers: тінь ніку"
        selectedColor: _tlUsernameShadowColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlUsernameShadowColor = selectedColor;
            root.tierOverlayCfg.username_text_shadow_color = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: tlLikesShadowDlg
        title: "Top Likers: тінь лайків"
        selectedColor: _tlLikesShadowColor
        onAccepted: {
            if (root.tierOverlayCfg === null) return;
            _tlLikesShadowColor = selectedColor;
            root.tierOverlayCfg.likes_text_shadow_color = _colorToHex(selectedColor);
            root._saveTierOverlay();
        }
    }

    ColorDialog {
        id: spBodyColorDlg
        title: "StreamPet: колір тіла"
        selectedColor: _spBodyColor
        onAccepted: {
            if (root.streamPetCfg === null) return;
            _spBodyColor = selectedColor;
            root.streamPetCfg.pet_body_color = _colorToHex(selectedColor);
            root.streamPetCfg.preset = "custom";
            root._saveStreamPet();
        }
    }

    ColorDialog {
        id: spEarColorDlg
        title: "StreamPet: колір вух"
        selectedColor: _spEarColor
        onAccepted: {
            if (root.streamPetCfg === null) return;
            _spEarColor = selectedColor;
            root.streamPetCfg.pet_ear_color = _colorToHex(selectedColor);
            root.streamPetCfg.preset = "custom";
            root._saveStreamPet();
        }
    }

    ColorDialog {
        id: spCollarColorDlg
        title: "StreamPet: колір нашийника"
        selectedColor: _spCollarColor
        onAccepted: {
            if (root.streamPetCfg === null) return;
            _spCollarColor = selectedColor;
            root.streamPetCfg.collar_color = _colorToHex(selectedColor);
            root.streamPetCfg.preset = "custom";
            root._saveStreamPet();
        }
    }

    ColorDialog {
        id: spBubbleBgColorDlg
        title: "StreamPet: фон хмарки"
        selectedColor: _spBubbleBgColor
        onAccepted: {
            if (root.streamPetCfg === null) return;
            _spBubbleBgColor = selectedColor;
            root.streamPetCfg.bubble_bg_color = _colorToHex(selectedColor);
            root.streamPetCfg.preset = "custom";
            root._saveStreamPet();
        }
    }
}
