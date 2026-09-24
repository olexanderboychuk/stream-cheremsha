import QtQuick
import QtQuick.Controls
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
    // Inspector spin refs (registered by the spins themselves: ids inside
    // `Component { id: gatedUi }` are invisible from root scope).
    property var _spinX: null
    property var _spinY: null
    property var _spinW: null
    property var _spinH: null
    onLayoutDocChanged: root._syncInspectorSpins()
    onSelectedLayoutWidgetChanged: { root._syncInspectorSpins(); root.ensureLayoutWidgetInstance(); }
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
    // Centralized grid config (editor-only visualization, never exported).
    // gridEnabled === layoutCanvasGridVisible; snap follows layoutGridSnapEnabled.
    // Supported future sizes: 4 / 8 / 16 / 32.
    property int layoutGridSize: 16
    property bool layoutGridSnapEnabled: true
    // Editor camera pan in screen px, applied as canvas center offset.
    // Viewport-only: never touches widget x/y/width/height.
    property real layoutCanvasPanX: 0
    property real layoutCanvasPanY: 0
    Behavior on layoutCanvasZoom {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
    Behavior on layoutCanvasPanX {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
    Behavior on layoutCanvasPanY {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
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
        {type: "battle", label: "Battle", iconName: "web_swords.svg"},
        {type: "stream_pet", label: "Stream Pet", iconName: "web_paw.svg"},
        {type: "community_world", label: "Community World", iconName: "web_globe.svg"},
        {type: "stream_goal", label: "Stream Goal", iconName: "web_target.svg"},
        {type: "live_leaderboard", label: "Live Leaderboard", iconName: "web_trophy.svg"},
        {type: "live_leaderboard_simple", label: "Live Leaderboard Simple", iconName: "web_trophy.svg"},
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
            case "battle": return {w: 640, h: 220};
            case "stream_pet": return {w: 240, h: 240};
            case "community_world": return {w: 480, h: 320};
            case "stream_goal": return {w: 400, h: 160};
            case "live_leaderboard": return {w: 360, h: 280};
            case "live_leaderboard_simple": return {w: 300, h: 280};
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
        root.layoutCanvasZoom = Math.max(0.25, Math.min(3.0, Math.round(value * 20) / 20));
    }

    // Round a canvas-space coordinate to the configured grid step.
    // Zoom-independent: always operates in canvas coordinates.
    function snapCanvasToGrid(value) {
        var step = Math.max(1, Number(root.layoutGridSize || 16));
        return Math.round(Number(value) / step) * step;
    }

    function gridSnapActive() {
        return root.layoutCanvasGridVisible && root.layoutGridSnapEnabled;
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

    function refreshWidgetInstances() {
        try {
            if (typeof api === "undefined" || !api) return;
            if (api.widgetTypesJson) root.widgetTypeList = JSON.parse(api.widgetTypesJson());
            if (api.widgetInstancesJson) root.widgetInstanceList = JSON.parse(api.widgetInstancesJson());
        } catch (e) { console.warn("instances refresh failed:", e); }
    }

    // ---- New-widget modal (UI layer only; creation logic unchanged) ----
    // showCreateWidget drives createModal.opened via binding; never assign
    // createModal.opened directly (that would break the binding).
    function openCreateModal() {
        root.refreshWidgetInstances();
        if ((root.widgetTypeList || []).length > 0) {
            var stillThere = (root.widgetTypeList || []).filter(function (x) {
                return x.type_id === root.newInstanceType;
            }).length > 0;
            if (!stillThere) root.newInstanceType = root.widgetTypeList[0].type_id;
        }
        root.showCreateWidget = true;
    }
    function closeCreateModal() {
        root.showCreateWidget = false;
        root.newInstanceName = "";
    }
    function submitCreateWidget() {
        var nm = (root.newInstanceName || "").trim();
        if (!nm) nm = root.newInstanceType;
        var nid = "";
        if (typeof api !== "undefined" && api) nid = api.createWidgetInstance(root.newInstanceType, nm);
        root.newInstanceName = "";
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
    property string widgetMode: "grid" // grid | chat | actions | online | top_likers | top_gifters | king_of_live | battle_royale | battle | stream_pet | community_world | stream_goal | live_leaderboard | live_leaderboard_simple | social_rotator | webcam_frame | signal_system
    readonly property bool universalEditorActive: root.editingInstanceId !== "" && root.widgetMode !== "grid" && root.widgetMode !== "layout"

    function universalInstance() {
        var list = root.widgetInstanceList || [];
        for (var i = 0; i < list.length; ++i)
            if (list[i].id === root.editingInstanceId) return list[i];
        return null;
    }

    function _systemFontOptions(current) {
        var fams = [];
        try {
            if (typeof api !== "undefined" && api && typeof api.systemFontFamilies === "function")
                fams = api.systemFontFamilies() || [];
        } catch (e) {}
        if (!fams.length) fams = ["system-ui", "Segoe UI", "Arial", "Verdana", "Tahoma"];
        var cur = String(current || "").trim();
        if (cur && fams.indexOf(cur) < 0) fams = [cur].concat(fams);
        return fams;
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
        var bt = function(key) { return root.loc("widgets.battle." + key); };
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
        } else if (typeId === "battle") {
            general = [c(bt("battle_name"), "battle_name", "text", "BATTLE"), c(bt("best_of"), "best_of", "select", 3, {options: [1, 3, 5]}), c(bt("round_duration"), "round_duration_s", "number", 60, {minimum: 30, maximum: 300}), c(bt("countdown"), "countdown_s", "number", 5, {minimum: 1, maximum: 10}), c(bt("auto_start"), "auto_start", "toggle", true), c(bt("auto_threshold"), "auto_threshold_each", "number", 100, {minimum: 1, maximum: 10000}), c(bt("auto_window"), "auto_window_s", "number", 30, {minimum: 5, maximum: 120}), c(bt("auto_reset"), "auto_reset", "toggle", true)];
            appearance = [c(bt("theme"), "theme", "select", "cheremsha_neon", {options: ["cheremsha_neon", "cyber", "arcade", "minimal"]}), c(bt("layout_mode"), "layout_mode", "select", "normal", {options: ["normal", "compact"]}), c(bt("show_avatars"), "show_avatars", "toggle", true), c(bt("scale"), "scale_percent", "number", 100, {minimum: 40, maximum: 250}), c(bt("font_size"), "base_font_size_px", "number", 14, {minimum: 10, maximum: 32})];
            behavior = [c(bt("gift_multiplier"), "gift_multiplier", "number", 1.0, {minimum: 0.1, maximum: 10}), c(bt("combo_enabled"), "combo_enabled", "toggle", true), c(bt("combo_threshold"), "combo_threshold", "number", 5, {minimum: 2, maximum: 20}), c(bt("comeback_enabled"), "comeback_enabled", "toggle", true), c(bt("final_push"), "final_push_seconds", "number", 10, {minimum: 3, maximum: 30})];
            animation = [c(bt("event_animations"), "event_animations", "toggle", true), c(bt("animation_intensity"), "animation_intensity_pct", "number", 100, {minimum: 25, maximum: 200}), c(bt("show_badges"), "show_event_badges", "toggle", true), c(bt("show_winner"), "show_winner_screen", "toggle", true)];
            advanced = [c(bt("victory_display"), "victory_display_s", "number", 8, {minimum: 3, maximum: 15}), c(bt("hide_when_idle"), "hide_when_idle", "toggle", false), c(bt("font_family"), "font_family", "text", "Segoe UI"), c(bt("decision_layer"), "decision_layer_enabled", "toggle", false)];
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
            general = [c("Enabled", "enabled", "toggle", true), c("Top entries", "top_n", "number", 10, {minimum: 1, maximum: 10}), c("Rotation sequence", "sequence", "leaderboard_sequence", "")];
            appearance = [c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            behavior = [c("Likers", "enable_likers", "toggle", true), c("Gifters", "enable_gifters", "toggle", true), c("Sharers", "enable_sharers", "toggle", true), c("Commenters", "enable_commenters", "toggle", true), c("Contributors", "enable_contributors", "toggle", true), c("Leaders scene", "enable_hall_of_fame", "toggle", true), c("Top 3 scene", "enable_arena", "toggle", true), c("Overview scene", "enable_energy_network", "toggle", true)];
            animation = [c("Transition", "transition", "select", "glitch_morph", {options: ["glitch_morph", "digital_dissolve", "scan", "energy_burst", "slide", "fade"]}), c("Animation intensity", "animation_intensity", "select", "medium", {options: ["low", "medium", "high"]}), c("Rank change animation", "enable_rank_change_anim", "toggle", true), c("Particles", "enable_particles", "toggle", true), c("CRT effects", "enable_crt", "toggle", true)];
        } else if (typeId === "live_leaderboard_simple") {
            general = [c("Enabled", "enabled", "toggle", true), c("Top entries", "top_n", "number", 10, {minimum: 1, maximum: 10}), c("Show header", "show_header", "toggle", true), c("Show avatars", "show_avatars", "toggle", true), c("Rotation sequence", "sequence", "leaderboard_sequence", "")];
            appearance = [c("Theme", "theme", "select", "dark", {options: ["dark", "transparent", "light", "neon"]}), c("Background color", "background_color", "color", "#0b0e14"), c("Background opacity", "background_opacity", "slider", 0.72, {minimum: 0, maximum: 1}), c("Font", "font_family", "font", "system-ui", {options: root._systemFontOptions("system-ui")}), c("Font size", "font_size_px", "number", 15, {minimum: 8, maximum: 48}), c("Value format", "value_format", "select", "compact", {options: ["compact", "full", "short"]}), c("Rank style", "rank_style", "select", "medal", {options: ["medal", "number", "badge"]}), c("Accent color", "accent_color", "color", "#14b8a6"), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            behavior = [c("Likers", "enable_likers", "toggle", true), c("Gifters", "enable_gifters", "toggle", true), c("Sharers", "enable_sharers", "toggle", true), c("Commenters", "enable_commenters", "toggle", true), c("Contributors", "enable_contributors", "toggle", true), c("Leaders scene", "enable_hall_of_fame", "toggle", true), c("Top 3 scene", "enable_arena", "toggle", true), c("Overview scene", "enable_energy_network", "toggle", true)];
            animation = [c("Transition", "transition", "select", "fade", {options: ["fade", "slide", "digital_dissolve", "scan"]}), c("Animation intensity", "animation_intensity", "select", "low", {options: ["low", "medium", "high"]}), c("Rank change animation", "enable_rank_change_anim", "toggle", true), c("Username text effect", "text_effect_username", "select", "none", {options: ["none", "rainbow", "aurora", "fire", "ice", "cold", "freeze", "strong"]}), c("Wave animation", "wave_enabled", "toggle", false), c("Wave speed", "wave_speed", "select", "normal", {options: ["slow", "normal", "fast"]})];
        } else if (typeId === "social_rotator") {
            general = [c("Enabled", "enabled", "toggle", true), c("Platforms", "platforms", "social_platforms", "", {options: ["twitch", "youtube", "kick", "telegram", "tiktok", "instagram", "discord", "x", "facebook"]}), c("Rotation interval", "rotation_interval_ms", "number", 8000, {minimum: 1000, maximum: 120000})];
            appearance = [c("Transition", "transition", "select", "glitch_morph", {options: ["glitch_morph", "data_stream", "energy_burst", "scan", "pixel_dissolve", "fade"]}), c("Theme", "theme", "select", "neon_cyber", {options: ["neon_cyber", "synthwave", "toxic", "ice", "amber"]}), c("Background opacity", "background_opacity_percent", "slider", 85, {minimum: 0, maximum: 100}), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
            behavior = [c("Show URL", "show_url", "toggle", true), c("Secondary platforms", "show_secondary_platforms", "toggle", true), c("Countdown", "show_countdown", "toggle", true), c("Glow", "enable_glow", "toggle", true), c("Particles", "enable_particles", "toggle", true), c("CRT", "enable_crt", "toggle", true), c("Latest follower", "show_latest_follower", "toggle", true), c("Latest donation", "show_latest_donation", "toggle", true), c("Stream time", "show_stream_time", "toggle", true), c("Top donator", "show_top_donator", "toggle", true), c("Online count", "show_online", "toggle", true), c("TikTok coin rate", "tiktok_coin_to_value_rate", "text", 1.0)];
        } else if (typeId === "webcam_frame") {
            general = [c("Enabled", "enabled", "toggle", true), c("Theme", "theme", "select", "neon_cyber", {options: ["neon_cyber", "synthwave", "toxic", "ice", "amber", "critical", "aurora", "royal", "sakura", "mono"]}), c("Intensity", "intensity", "select", "medium", {options: ["low", "medium", "high"]}), c("Frame style", "frame_style", "select", "primary", {options: ["primary", "minimal", "tactical", "broadcast", "hologram", "anime", "fantasy", "glitch", "cosmic"]}), c("Camera label", "cam_label", "text", "CAM // 01"), c("Scale", "scale_percent", "number", 100, {minimum: 40, maximum: 250})];
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
        if (typeId === "live_leaderboard_simple") advanced = advanced.concat([c("Like weight", "weight_like", "number", 1, {minimum: 0, maximum: 100}), c("Gift weight", "weight_gift_coin", "number", 1, {minimum: 0, maximum: 100}), c("Share weight", "weight_share", "number", 1, {minimum: 0, maximum: 100}), c("Comment weight", "weight_comment", "number", 1, {minimum: 0, maximum: 100})]);
        if (typeId === "social_rotator") advanced = advanced.concat([c("Accent color", "accent_color", "color", "#14b8a6")]);
        if (typeId === "signal_system") advanced = advanced.concat([
            c("Font family", "font_family", "text", "Segoe UI"), c("Intensity multiplier", "intensity_multiplier", "number", 1, {minimum: 0, maximum: 10}), c("Primary accent", "primary_accent", "color", "#14b8a6"), c("Secondary accent", "secondary_accent", "color", "#a78bfa"),
            c("Frame detail level", "frame_detail_level", "number", 1, {minimum: 0, maximum: 10}), c("Particle density", "particle_density", "number", 1, {minimum: 0, maximum: 10}), c("Gift icon", "gift_icon_enabled", "toggle", true), c("Gift quantity", "show_gift_quantity", "toggle", true), c("Coin value", "show_coin_value", "toggle", true), c("Gift name", "show_gift_name", "toggle", true), c("Reduced motion", "reduced_motion", "toggle", false),
            c("Global cooldown", "global_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000}), c("AI cooldown", "ai_observation_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000}), c("AI max per hour", "ai_observation_max_per_hour", "number", 10, {minimum: 0, maximum: 1000}), c("Unknown signal cooldown", "unknown_signal_cooldown_ms", "number", 3000, {minimum: 0, maximum: 60000})
        ]);

        var _isBr = typeId === "battle_royale" || typeId === "battle";
        var _bl = function(key) { return typeId === "battle" ? bt(key) : bl(key); };
        if (general.length) sections.push(s(_isBr ? _bl("section_general") : "General", _isBr ? _bl("desc_general") : "Core settings for this widget instance.", general, "◇"));
        if (appearance.length) sections.push(s(_isBr ? _bl("section_appearance") : "Appearance", _isBr ? _bl("desc_appearance") : "Visual presentation and display options.", appearance, "✦"));
        if (behavior.length) sections.push(s(_isBr ? _bl("section_behavior") : "Gameplay / Behavior", _isBr ? _bl("desc_behavior") : "Rules, sources, timing, and widget behavior.", behavior, "≡"));
        if (animation.length) sections.push(s("Animation", "Motion and visual effect controls.", animation, "⌁"));
        if (advanced.length) sections.push(s(_isBr ? _bl("section_advanced") : "Advanced", _isBr ? _bl("desc_advanced") : "Technical settings for this widget.", advanced, "⚙", false));
        return sections;
    }

    function universalConfig() {
        if (root.widgetMode === "chat") return root.cfg;
        if (root.widgetMode === "actions") return root.actionsCfg;
        if (root.widgetMode === "online") return root.onlineCfg;
        if (root.widgetMode === "top_likers" || root.widgetMode === "top_gifters") return root.tierOverlayCfg;
        if (root.widgetMode === "king_of_live") return root.kingCfg;
        if (root.widgetMode === "battle_royale") return root.battleCfg;
        if (root.widgetMode === "battle") return root.battleCfg2;
        if (root.widgetMode === "stream_pet") return root.streamPetCfg;
        if (root.widgetMode === "community_world") return root.communityWorldCfg;
        if (root.widgetMode === "stream_goal") return root.streamGoalCfg;
        if (root.widgetMode === "live_leaderboard") return root.liveLeaderboardCfg;
        if (root.widgetMode === "live_leaderboard_simple") return root.liveLeaderboardSimpleCfg;
        if (root.widgetMode === "social_rotator") return root.socialRotatorCfg;
        if (root.widgetMode === "webcam_frame") return root.webcamFrameCfg;
        if (root.widgetMode === "signal_system") return root.signalSystemCfg;
        return null;
    }

    function _ensureSimpleSourceInSequence(sourceId) {
        if (!root.liveLeaderboardSimpleCfg) return;
        var arr = (root.liveLeaderboardSimpleCfg.sequence || []).slice();
        for (var i = 0; i < arr.length; ++i) {
            if (String((arr[i] && (arr[i].source_id || arr[i].source)) || "") === sourceId) return;
        }
        arr.push({source_id: sourceId, scene_id: "hall_of_fame", duration_sec: 8});
        root.liveLeaderboardSimpleCfg.sequence = arr;
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
        if (value === true) {
            var srcByToggle = {
                enable_likers: "likers",
                enable_gifters: "gifters",
                enable_sharers: "sharers",
                enable_commenters: "commenters",
                enable_contributors: "contributors"
            };
            if (srcByToggle[field]) {
                if (root.widgetMode === "live_leaderboard_simple")
                    root._ensureSimpleSourceInSequence(srcByToggle[field]);
                else if (root.widgetMode === "live_leaderboard")
                    root._ensureLiveLeaderboardSourceInSequence(srcByToggle[field]);
            }
        }
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

    function firstWidgetInstanceId(type) {
        var list = root.widgetInstanceList || [];
        for (var i = 0; i < list.length; ++i) {
            if (list[i].type_id === type) return list[i].id;
        }
        return "";
    }

    function layoutWidgetInstanceOptions(type) {
        var opts = [];
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
        if (!item) return -1;
        var opts = root.layoutWidgetInstanceOptions(item.type);
        var cur = item.widget_instance_id || "";
        for (var i = 0; i < opts.length; ++i) {
            if (opts[i].id === cur) return i;
        }
        return -1;
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
            // Self-heal legacy docs: z_index must mirror array position so
            // editor stacking and OBS export agree. No save triggered here;
            // the normalized doc persists on the next user edit.
            try {
                var zw = ((root.layoutDoc || {}).widgets || []).slice();
                root._renumberLayoutZ(zw);
                root._inspectorUpdating = true;
                root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: zw});
                root._inspectorUpdating = false;
            } catch (e2) {}
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
        root.layoutCanvasPanX = 0;
        root.layoutCanvasPanY = 0;
        root.layoutSaveSucceeded = true;
    }

    function selectedLayoutItem() {
        var items = root.layoutDoc.widgets || [];
        return (items.length && root.selectedLayoutWidget >= 0 && root.selectedLayoutWidget < items.length)
            ? items[root.selectedLayoutWidget] : null;
    }

    function ensureLayoutWidgetInstance() {
        var item = root.selectedLayoutItem();
        if (!item || (item.widget_instance_id || "")) return;
        var opts = root.layoutWidgetInstanceOptions(item.type);
        if (opts.length) root.updateLayoutItemStr("widget_instance_id", opts[0].id);
    }

    onWidgetInstanceListChanged: root.ensureLayoutWidgetInstance()

    // Explicit one-way sync of the X/Y/W/H inspector spins. Live Binding
    // elements race with stepping (resetting the value to 0 / stale data),
    // so spins are plain values synced here whenever the doc or selection
    // changes. Focused spin is skipped so typing is never disturbed.
    // NOTE: the whole editor UI lives inside `Component { id: gatedUi }`,
    // so spin ids are NOT visible from root scope. Spins register
    // themselves into _spinX/_spinY/_spinW/_spinH on completion.
    function _syncInspectorSpins() {
        var item = root.selectedLayoutItem();
        if (!item) return;
        if (root._spinX && !root._spinX.activeFocus) root._spinX.value = Number(item.x || 0);
        if (root._spinY && !root._spinY.activeFocus) root._spinY.value = Number(item.y || 0);
        if (root._spinW && !root._spinW.activeFocus) root._spinW.value = Number(item.width || 320);
        if (root._spinH && !root._spinH.activeFocus) root._spinH.value = Number(item.height || 180);
    }

    // Live mirror of canvas drag/resize into the X/Y/W/H spins. During a
    // drag only the delegate-local geometry changes (layoutDoc commits on
    // release), so without this the inspector numbers stay frozen while
    // the cursor moves. Model is untouched here; the release commit is
    // still the source of truth.
    function _syncInspectorLive(index, x, y, w, h) {
        if (index !== root.selectedLayoutWidget) return;
        if (root._spinX && !root._spinX.activeFocus) root._spinX.value = Math.round(x);
        if (root._spinY && !root._spinY.activeFocus) root._spinY.value = Math.round(y);
        if (root._spinW && !root._spinW.activeFocus) root._spinW.value = Math.max(1, Math.round(w));
        if (root._spinH && !root._spinH.activeFocus) root._spinH.value = Math.max(1, Math.round(h));
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
        if (posX !== undefined && root.gridSnapActive()) {
            targetX = root.snapCanvasToGrid(targetX);
            targetY = root.snapCanvasToGrid(targetY);
        }

        items.push({
            id: type + "-" + Date.now(),
            type: type,
            instance: "main",
            x: targetX,
            y: targetY,
            width: defaultW,
            height: defaultH,
            z_index: items.length,
            visible: true,
            locked: false,
            widget_instance_id: root.firstWidgetInstanceId(type)
        });
        root._renumberLayoutZ(items);
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
        root._renumberLayoutZ(items);
        root._inspectorUpdating = true;
        root.layoutDoc = Object.assign({}, root.layoutDoc, {widgets: items});
        root._inspectorUpdating = false;
        root.selectedLayoutWidget = items.length ? Math.min(removedIdx, items.length - 1) : -1;
        root.saveLayoutEditor();
    }

    // z_index always mirrors array position (back-to-front): array[0]
    // is the back layer, array[last] is the front layer. OBS export sorts
    // by z_index, the editor canvas stacks by array index, so keeping them
    // in sync is what keeps editor and output consistent.
    function _renumberLayoutZ(items) {
        for (var i = 0; i < items.length; ++i) {
            if (Number(items[i].z_index) !== i) {
                items[i] = Object.assign({}, items[i], {z_index: i});
            }
        }
        return items;
    }

    function moveWidgetLayer(fromIdx, toIdx) {
        var items = (root.layoutDoc.widgets || []).slice();
        if (fromIdx < 0 || fromIdx >= items.length || toIdx < 0 || toIdx >= items.length || fromIdx === toIdx) return;
        root._pushUndo();
        var moved = items.splice(fromIdx, 1)[0];
        items.splice(toIdx, 0, moved);
        root._renumberLayoutZ(items);
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
        if (index === 1) root.applyLayoutPreset(1080, 1920, root.loc("widgets.layouts.editor.preset_tiktok_name"));
        else if (index === 2) root.applyLayoutPreset(1080, 1080, root.loc("widgets.layouts.editor.preset_square_name"));
        else if (index === 3) root.applyLayoutPreset(1280, 720, root.loc("widgets.layouts.editor.preset_hd_name"));
        else if (index === 0) root.applyLayoutPreset(1920, 1080, root.loc("widgets.layouts.default_name"));
    }

    component EditorIconButton: Button {
        id: editorIconButton
        property string iconName: ""
        property string toolTipText: ""
        property bool active: false
        implicitWidth: 40
        implicitHeight: 40
        padding: 6
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Image {
            source: editorIconButton.iconName ? Qt.resolvedUrl("../assets/icons/" + editorIconButton.iconName) : ""
            fillMode: Image.PreserveAspectFit
            sourceSize.width: Math.max(1, Math.round(editorIconButton.availableWidth))
            sourceSize.height: Math.max(1, Math.round(editorIconButton.availableHeight))
            smooth: true
            mipmap: true
            opacity: editorIconButton.enabled ? 1.0 : 0.4
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
                width: 20
                height: 20
                sourceSize.width: 40
                sourceSize.height: 40
                smooth: true
                mipmap: true
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
        property string toolTipText: ""
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
                width: 18
                height: 18
                sourceSize.width: 36
                sourceSize.height: 36
                smooth: true
                mipmap: true
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
        ToolTip.visible: layoutCardButton.hovered && layoutCardButton.toolTipText !== ""
        ToolTip.text: layoutCardButton.toolTipText
        ToolTip.delay: 450
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
            // Assign + emit synchronously so the consumer's onValueModified
            // handler observes the fresh value before any resync can run.
            // (increase()/decrease() from JS do not reliably emit
            // valueModified, and a deferred emit races with focus loss.)
            var v = sb.value + delta;
            if (v < sb.from) v = sb.from;
            if (v > sb.to) v = sb.to;
            if (v === sb.value) return;
            sb.forceActiveFocus();
            sb.value = v;
            sb.valueModified();
        }

        contentItem: TextInput {
            id: sbInput
            // Keep the text strictly between the -/+ indicator buttons.
            // Without these margins the editor spans the full width, slides
            // under the buttons and even steals their edge clicks.
            anchors.fill: parent
            anchors.leftMargin: 37
            anchors.rightMargin: 37
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
                var v = sb.valueFromText(t, sb.locale);
                if (t.length && v !== undefined && v !== null && !isNaN(v)) {
                    if (v < sb.from) v = sb.from;
                    if (v > sb.to) v = sb.to;
                    if (v !== sb.value) {
                        sb.value = v;
                        sb.valueModified();
                    }
                }
                // Re-establish the live text binding. A direct `text = ...`
                // assignment freezes the editor: the field keeps showing a
                // stale number and the next focus loss parses it back,
                // reverting/committing a wrong value (e.g. X regressed after
                // touching W). The binding keeps the display in sync and
                // resets any invalid typed text to displayText.
                text = Qt.binding(function() { return sb.displayText; });
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
    property var cfg: null
    property var actionsCfg: null
    property bool _loadingActionsCfg: false
    // QVariant map mutations don't notify dependents; bump this whenever actions overlay cfg is saved.
    property int actionsCfgEpoch: 0

    property var onlineCfg: null
    property bool _loadingOnlineCfg: false
    property int onlineCfgEpoch: 0

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
    // battleCfg2 is the 1v1 battle (TikTok-gift race) config. It is instance-routed
    // through loadBattleOverlayConfigMap() / saveBattleOverlayConfigJson(), so it can
    // be saved per-instance when an instance is selected and falls back to the shared
    // overlay key otherwise (unlike battle_royale, whose config is always global).
    property var battleCfg2: null
    property int battleCfg2Epoch: 0
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
    property var liveLeaderboardSimpleCfg: null
    property bool _loadingLiveLeaderboardSimpleCfg: false
    property int liveLeaderboardSimpleCfgEpoch: 0
    property var socialRotatorCfg: null
    property bool _loadingSocialRotatorCfg: false
    property int socialRotatorCfgEpoch: 0
    property var webcamFrameCfg: null
    property bool _loadingWebcamFrameCfg: false
    property int webcamFrameCfgEpoch: 0
    property var tierOverlayCfg: null

    readonly property bool _tierOverlayLoading: (root.widgetMode === "top_gifters")
        ? root._loadingTopGiftersCfg
        : root._loadingTopLikersCfg

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
            (root.widgetMode === "battle" && root.battleCfg2 !== null) ||
            (root.widgetMode === "stream_pet" && root.streamPetCfg !== null) ||
            (root.widgetMode === "community_world" && root.communityWorldCfg !== null) ||
            (root.widgetMode === "stream_goal" && root.streamGoalCfg !== null) ||
            (root.widgetMode === "live_leaderboard" && root.liveLeaderboardCfg !== null) ||
            (root.widgetMode === "live_leaderboard_simple" && root.liveLeaderboardSimpleCfg !== null) ||
            (root.widgetMode === "social_rotator" && root.socialRotatorCfg !== null) ||
            (root.widgetMode === "webcam_frame" && root.webcamFrameCfg !== null) ||
            (root.widgetMode === "signal_system" && root.signalSystemCfg !== null)
        )

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
            root._saveTierOverlay();
        } else if (root.widgetMode === "king_of_live") {
            root._saveKing();
        } else if (root.widgetMode === "battle_royale") {
            root._saveBattle();
        } else if (root.widgetMode === "battle") {
            root._saveBattle2();
        } else if (root.widgetMode === "stream_pet") {
            root._saveStreamPet();
        } else if (root.widgetMode === "community_world") {
            root._saveCommunityWorld();
        } else if (root.widgetMode === "stream_goal") {
            root._saveStreamGoal();
        } else if (root.widgetMode === "live_leaderboard") {
            root._saveLiveLeaderboard();
        } else if (root.widgetMode === "live_leaderboard_simple") {
            root._saveLiveLeaderboardSimple();
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

    // NOTE: same scoping caveat as _rebuildWebcamFrameComboModels below - the sgXxx*/srXxx*
    // ids live inside the `gatedUi` Component, not on root, so they must be passed in explicitly
    // rather than bare-referenced here (bare references from root always silently no-op, which
    // used to leave every one of these combo boxes empty).
    // NOTE: this function lives on the root Item, but wfThemeModel/wfTheme/wfIntensityModel/
    // wfIntensity are ids declared inside the `gatedUi` Component (see the Loader below). QML id
    // scoping only flows outward (child components can see ancestor scope, never the reverse),
    // so those ids are NOT resolvable via bare reference from here - hence the explicit
    // parameters instead of `typeof wfThemeModel !== "undefined"` bare-id lookups, which always
    // evaluated to false and silently left the combo boxes empty.
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

    function _saveLiveLeaderboardSimple() {
        if (!api || root.liveLeaderboardSimpleCfg === null) return;
        root.liveLeaderboardSimpleCfgEpoch += 1;
        if (root.liveLeaderboardSimpleCfg.sequence)
            root.liveLeaderboardSimpleCfg.sequence_json = JSON.stringify(root.liveLeaderboardSimpleCfg.sequence);
        api.saveLiveLeaderboardSimpleConfigJson(JSON.stringify(root.liveLeaderboardSimpleCfg));
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

    function _saveBattle2() {
        if (!api || root.battleCfg2 === null) return;
        root.battleCfg2Epoch += 1;
        // battleCfg2 is a cloned plain JS object; JSON.stringify is reliable (ConfigMap/toVariant often is not).
        var txt = JSON.stringify(root.battleCfg2);
        if (!txt || txt === "{}")
            return;
        api.saveBattleOverlayConfigJson(txt);
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
                            MouseArea { id: createWidgetMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.openCreateModal() }
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

                    // New-widget creation lives in the CheremshaModal overlay
                    // at the root (createModal). Inline panel removed.

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
                                            case "live_leaderboard_simple":
                                                return {kind: "feed", rows: [
                                                    {icon: "web_trophy", label: "kriss", user: "12.4K", time: "#1"},
                                                    {icon: "web_trophy", label: "marta", user: "8.1K", time: "#2"},
                                                    {icon: "web_trophy", label: "denis", user: "6.7K", time: "#3"}]};
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
                                            case "battle":
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
                                            // Depend on overlayBaseUrl so the binding
                                            // re-evaluates once the overlay server is up
                                            // (same pattern as docks/layouts). Without
                                            // this, Slot-only calls evaluate once while
                                            // the base is still empty and stay "" forever.
                                            var _baseDep = (typeof api !== "undefined" && api) ? api.overlayBaseUrl : "";
                                            void _baseDep;
                                            var tid = (wtype && wtype.type_id) || "";
                                            var id = viewId();
                                            if (typeof api === "undefined" || !api) return "";
                                            if (id) return api.widgetInstanceUrl(id) || "";
                                            // No instance yet (fallback card): show the
                                            // type-level URL so every card displays its URL.
                                            if (tid && api.layoutWidgetPreviewUrl)
                                                return api.layoutWidgetPreviewUrl(tid, "main") || "";
                                            return "";
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
                             MouseArea { id: createNewMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.openCreateModal() }
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
                                                    z: modelData.z_index !== undefined ? Number(modelData.z_index) : index
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
                                                text: (api && api.overlayBaseUrl) ? api.layoutOverlayUrl(layoutModel.id) : ""
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
                                    text: root.layoutSaveSucceeded ? root.loc("widgets.layouts.editor.saved") : root.loc("widgets.layouts.editor.unsaved")
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
                                toolTipText: root.loc("widgets.layouts.editor.undo")
                                enabled: (root._undoStack || []).length > 0
                                onClicked: root.undo()
                            }
                            EditorIconButton {
                                iconName: "editor_redo.svg"
                                toolTipText: root.loc("widgets.layouts.editor.redo")
                                enabled: (root._redoStack || []).length > 0
                                onClicked: root.redo()
                            }

                            LayoutCardButton {
                                text: root.loc("widgets.layouts.editor.preview")
                                iconName: "open-external.svg"
                                implicitHeight: 34
                                onClicked: {
                                    root.saveLayoutEditor();
                                    if (api) api.previewLayout(root.activeLayoutId);
                                }
                            }
                            LayoutPrimaryButton {
                                text: root.loc("widgets.common.save")
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
                                    Text { text: root.loc("widgets.layouts.editor.add_widget"); color: ink; font.pixelSize: 14; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: root.filteredLayoutWidgetTypes().length; color: muted; font.pixelSize: 11 }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: root.loc("widgets.layouts.editor.add_widget_hint")
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
                                        placeholderText: root.loc("widgets.layouts.editor.search_ph")
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
                                                         toolTipText: root.loc("widgets.layouts.editor.add_widget")
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
                                        toolTipText: root.loc("widgets.layouts.editor.zoom_out")
                                        implicitWidth: 28
                                        implicitHeight: 28
                                        enabled: root.layoutCanvasZoom > 0.25
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
                                        toolTipText: root.loc("widgets.layouts.editor.zoom_in")
                                        implicitWidth: 28
                                        implicitHeight: 28
                                        enabled: root.layoutCanvasZoom < 3.0
                                        onClicked: root.setLayoutCanvasZoom(root.layoutCanvasZoom + 0.1)
                                    }
                                    LayoutCardButton {
                                        text: root.loc("widgets.layouts.editor.fit")
                                        iconName: "editor_fit.svg"
                                        implicitHeight: 28
                                        toolTipText: root.loc("widgets.layouts.editor.fit_tip")
                                        onClicked: layoutCanvas.fitToContent()
                                    }
                                    LayoutCardButton {
                                        text: root.loc("widgets.layouts.editor.grid") + (root.layoutCanvasGridVisible ? " ✓" : "")
                                        iconName: "editor_grid.svg"
                                        primary: root.layoutCanvasGridVisible
                                        implicitHeight: 28
                                        toolTipText: root.loc("widgets.layouts.editor.grid_tip")
                                        onClicked: root.layoutCanvasGridVisible = !root.layoutCanvasGridVisible
                                    }
                                }
                            }

                            Rectangle {
                                id: layoutCanvas
                                anchors.centerIn: parent
                                anchors.horizontalCenterOffset: root.layoutCanvasPanX
                                anchors.verticalCenterOffset: root.layoutCanvasPanY
                                property real documentWidth: Number(root.layoutDoc.width || 1920)
                                property real documentHeight: Number(root.layoutDoc.height || 1080)
                                property real aspect: documentWidth / Math.max(1, documentHeight)
                                property real fitScale: Math.max(0, Math.min((parent.width - 20) / Math.max(1, documentWidth), (parent.height - 20) / Math.max(1, documentHeight)))
                                property real editorScale: fitScale * root.layoutCanvasZoom
                                property int selectedIndex: root.selectedLayoutWidget

                                // Fit to Content: viewport-only zoom + camera pan.
                                // Never modifies widget x/y/width/height.
                                function fitToContent() {
                                    var widgets = root.layoutDoc.widgets || [];
                                    if (!widgets.length || !parent) {
                                        root.setLayoutCanvasZoom(1.0);
                                        root.layoutCanvasPanX = 0;
                                        root.layoutCanvasPanY = 0;
                                        return;
                                    }
                                    var minX = Infinity, minY = Infinity;
                                    var maxX = -Infinity, maxY = -Infinity;
                                    for (var i = 0; i < widgets.length; ++i) {
                                        var o = widgets[i];
                                        var ox = Number(o.x || 0);
                                        var oy = Number(o.y || 0);
                                        var ow = Math.max(1, Number(o.width || 320));
                                        var oh = Math.max(1, Number(o.height || 180));
                                        if (ox < minX) minX = ox;
                                        if (oy < minY) minY = oy;
                                        if (ox + ow > maxX) maxX = ox + ow;
                                        if (oy + oh > maxY) maxY = oy + oh;
                                    }
                                    if (!(isFinite(minX) && isFinite(minY) && isFinite(maxX) && isFinite(maxY))) {
                                        root.setLayoutCanvasZoom(1.0);
                                        root.layoutCanvasPanX = 0;
                                        root.layoutCanvasPanY = 0;
                                        return;
                                    }
                                    var pad = 40;
                                    var bboxX = minX - pad;
                                    var bboxY = minY - pad;
                                    var bboxW = Math.max(1, (maxX - minX) + pad * 2);
                                    var bboxH = Math.max(1, (maxY - minY) + pad * 2);
                                    var availW = Math.max(1, parent.width - 24);
                                    var availH = Math.max(1, parent.height - 24);
                                    var fs = layoutCanvas.fitScale || 1;
                                    // Zoom so the padded bbox fills the viewport.
                                    var need = Math.min(availW / Math.max(1, bboxW * fs), availH / Math.max(1, bboxH * fs));
                                    if (!isFinite(need) || need <= 0) need = 1.0;
                                    root.setLayoutCanvasZoom(need);
                                    // Center the bbox: canvas center + pan must place
                                    // bbox center at viewport center (closed form, no drift).
                                    var s = fs * root.layoutCanvasZoom;
                                    var canvasW = layoutCanvas.documentWidth * s;
                                    var canvasH = layoutCanvas.documentHeight * s;
                                    var bboxCx = bboxX + bboxW / 2;
                                    var bboxCy = bboxY + bboxH / 2;
                                    root.layoutCanvasPanX = canvasW / 2 - bboxCx * s;
                                    root.layoutCanvasPanY = canvasH / 2 - bboxCy * s;
                                }

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
                                    var guideHitX = false;
                                    var guideHitY = false;

                                    for (var vi = 0; vi < vGuides.length; ++vi) {
                                        var gv = vGuides[vi];
                                        for (var ti = 0; ti < testX.length; ++ti) {
                                            var diffX = Math.abs(testX[ti].val - gv);
                                            if (diffX < tolerance && diffX < bestDx) {
                                                bestDx = diffX;
                                                snappedX = gv - testX[ti].offset;
                                                guideHitX = true;
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
                                                guideHitY = true;
                                                matchedGuides = matchedGuides.filter(function(g) { return g.axis !== "h"; });
                                                matchedGuides.push({axis: "h", pos: gh});
                                            }
                                        }
                                    }

                                    // Grid snap in canvas coordinates (zoom-independent step).
                                    // Object guides take precedence when they match.
                                    if (root.gridSnapActive()) {
                                        if (!guideHitX) snappedX = root.snapCanvasToGrid(snappedX);
                                        if (!guideHitY) snappedY = root.snapCanvasToGrid(snappedY);
                                    }

                                    return {x: snappedX, y: snappedY, guides: matchedGuides};
                                }

                                // Grid snap for a size value, never below the minimum.
                                function snapGridSize(value, minimum) {
                                    var snapped = root.snapCanvasToGrid(value);
                                    if (snapped < minimum) snapped = Math.ceil(minimum / Math.max(1, Number(root.layoutGridSize || 16))) * Math.max(1, Number(root.layoutGridSize || 16));
                                    return snapped;
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
                                    var resizeGuideX = false;
                                    var resizeGuideY = false;

                                    if (edgeX === -1) {
                                        var bestDx = tolerance + 1;
                                        for (var vi = 0; vi < vGuides.length; ++vi) {
                                            var diff = Math.abs(candX - vGuides[vi]);
                                            if (diff < tolerance && diff < bestDx) {
                                                bestDx = diff;
                                                var rightEdge = candX + candW;
                                                nextX = vGuides[vi];
                                                nextW = Math.max(32, rightEdge - nextX);
                                                resizeGuideX = true;
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
                                                resizeGuideX = true;
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
                                                resizeGuideY = true;
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
                                                resizeGuideY = true;
                                                matchedGuides.push({axis: "h", pos: hGuides[hi]});
                                            }
                                        }
                                    }

                                    // Grid snap for resize in canvas coordinates.
                                    // Object guides take precedence; minimums are preserved.
                                    if (root.gridSnapActive()) {
                                        if (edgeX === -1 && !resizeGuideX) {
                                            var rsRight = nextX + nextW;
                                            nextX = root.snapCanvasToGrid(nextX);
                                            nextW = snapGridSize(rsRight - nextX, 32);
                                        } else if (edgeX === 1 && !resizeGuideX) {
                                            nextW = snapGridSize(nextW, 32);
                                        } else if (edgeX === 0 && !resizeGuideX) {
                                            nextW = snapGridSize(nextW, 32);
                                        }
                                        if (edgeY === -1 && !resizeGuideY) {
                                            var rsBottom = nextY + nextH;
                                            nextY = root.snapCanvasToGrid(nextY);
                                            nextH = snapGridSize(rsBottom - nextY, 24);
                                        } else if (edgeY === 1 && !resizeGuideY) {
                                            nextH = snapGridSize(nextH, 24);
                                        } else if (edgeY === 0 && !resizeGuideY) {
                                            nextH = snapGridSize(nextH, 24);
                                        }
                                    }

                                    return {x: nextX, y: nextY, w: nextW, h: nextH, guides: matchedGuides};
                                }

                                // Editor-only grid: canvas coordinate system, scales and
                                // pans together with the canvas. Never exported to
                                // preview / OBS output. Snap step stays fixed at
                                // layoutGridSize canvas px; only visibility adapts.
                                Canvas {
                                    id: editorGridCanvas
                                    anchors.fill: parent
                                    // z >= 0: negative z renders below the parent
                                    // Rectangle's opaque background. Declared before
                                    // the widget Repeater, so equal z stays below widgets.
                                    z: 0
                                    visible: root.layoutCanvasGridVisible
                                    // Explicit buffer size: never allocate a 0/negative
                                    // buffer during layout transients (unrecoverable).
                                    canvasSize: Qt.size(Math.max(1, Math.ceil(width)), Math.max(1, Math.ceil(height)))
                                    onPaint: {
                                        var ctx = getContext("2d");
                                        ctx.clearRect(0, 0, width, height);
                                        if (!root.layoutCanvasGridVisible) return;
                                        var step = Math.max(1, Number(root.layoutGridSize || 16));
                                        var s = layoutCanvas.editorScale;
                                        if (!(s > 0)) return;
                                        var minorPx = step * s;
                                        // Too dense: show major lines only.
                                        var showMinor = minorPx >= 6;
                                        var majorEvery = 5;
                                        var minorColor = "rgba(94, 234, 212, 0.13)";
                                        var majorColor = "rgba(94, 234, 212, 0.30)";
                                        var docW = layoutCanvas.documentWidth;
                                        var docH = layoutCanvas.documentHeight;
                                        var nX = Math.floor(docW / step);
                                        var nY = Math.floor(docH / step);
                                        ctx.lineWidth = 1;
                                        var i, sx, sy;
                                        if (showMinor) {
                                            ctx.strokeStyle = minorColor;
                                            ctx.beginPath();
                                            for (i = 1; i <= nX; ++i) {
                                                if (i % majorEvery === 0) continue;
                                                sx = Math.round(i * step * s) + 0.5;
                                                ctx.moveTo(sx, 0);
                                                ctx.lineTo(sx, height);
                                            }
                                            for (i = 1; i <= nY; ++i) {
                                                if (i % majorEvery === 0) continue;
                                                sy = Math.round(i * step * s) + 0.5;
                                                ctx.moveTo(0, sy);
                                                ctx.lineTo(width, sy);
                                            }
                                            ctx.stroke();
                                        }
                                        ctx.strokeStyle = majorColor;
                                        ctx.beginPath();
                                        for (i = majorEvery; i <= nX; i += majorEvery) {
                                            sx = Math.round(i * step * s) + 0.5;
                                            ctx.moveTo(sx, 0);
                                            ctx.lineTo(sx, height);
                                        }
                                        for (i = majorEvery; i <= nY; i += majorEvery) {
                                            sy = Math.round(i * step * s) + 0.5;
                                            ctx.moveTo(0, sy);
                                            ctx.lineTo(width, sy);
                                        }
                                        ctx.stroke();
                                        // Document border emphasis inside grid layer.
                                        ctx.strokeStyle = "#334155";
                                        ctx.strokeRect(0.5, 0.5, width - 1, height - 1);
                                    }
                                    Connections {
                                        target: root
                                        function onLayoutCanvasGridVisibleChanged() { editorGridCanvas.requestPaint(); }
                                        function onLayoutGridSizeChanged() { editorGridCanvas.requestPaint(); }
                                        function onLayoutCanvasZoomChanged() { editorGridCanvas.requestPaint(); }
                                        function onLayoutDocChanged() { editorGridCanvas.requestPaint(); }
                                    }
                                    Connections {
                                        target: layoutCanvas
                                        function onWidthChanged() { editorGridCanvas.requestPaint(); }
                                        function onHeightChanged() { editorGridCanvas.requestPaint(); }
                                        function onEditorScaleChanged() { editorGridCanvas.requestPaint(); }
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
                                            root._syncInspectorLive(index, rawX, rawY, rawW, rawH);
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
                                                root._syncInspectorLive(index, targetX, targetY, layoutWidget.localW, layoutWidget.localH);
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
                                    Text { text: root.loc("widgets.layouts.editor.layers"); color: ink; font.pixelSize: 14; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: (root.layoutDoc.widgets || []).length; color: muted; font.pixelSize: 11 }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: root.loc("widgets.layouts.editor.layers_hint")
                                    color: muted
                                    font.pixelSize: 10
                                }

                                ListView {
                                    id: activeLayoutWidgets
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 5
                                    // Front layer on top (Figma/Photoshop convention):
                                    // array order is back-to-front, so display reversed.
                                    model: (root.layoutDoc.widgets || []).slice().reverse()

                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        // Array position of this row (back-to-front order).
                                        property int realIndex: ((root.layoutDoc.widgets || []).length - 1) - index
                                        property int layerCount: (root.layoutDoc.widgets || []).length
                                        width: activeLayoutWidgets.width
                                        height: 44
                                        radius: 7
                                        color: realIndex === root.selectedLayoutWidget ? "#134e4a" : (itemHover.hovered ? "#1b2537" : "#141c2c")
                                        border.width: realIndex === root.selectedLayoutWidget ? 1 : 0
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
                                                font.weight: realIndex === root.selectedLayoutWidget ? Font.Medium : Font.Normal
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            EditorIconButton {
                                                iconName: "chevron-up.svg"
                                                toolTipText: root.loc("widgets.layouts.editor.layer_up")
                                                implicitWidth: 30
                                                implicitHeight: 30
                                                padding: 4
                                                enabled: realIndex < layerCount - 1
                                                onClicked: root.moveWidgetLayer(realIndex, realIndex + 1)
                                            }
                                            EditorIconButton {
                                                iconName: "chevron-down.svg"
                                                toolTipText: root.loc("widgets.layouts.editor.layer_down")
                                                implicitWidth: 30
                                                implicitHeight: 30
                                                padding: 4
                                                enabled: realIndex > 0
                                                onClicked: root.moveWidgetLayer(realIndex, realIndex - 1)
                                            }
                                            EditorIconButton {
                                                iconName: modelData.locked ? "editor_lock.svg" : "editor_unlock.svg"
                                                toolTipText: modelData.locked ? root.loc("widgets.layouts.editor.unlock") : root.loc("widgets.layouts.editor.lock")
                                                implicitWidth: 30
                                                implicitHeight: 30
                                                padding: 4
                                                active: modelData.locked
                                                onClicked: root.toggleWidgetLock(realIndex)
                                            }
                                            EditorIconButton {
                                                iconName: modelData.visible === false ? "editor_eye_off.svg" : "editor_eye.svg"
                                                toolTipText: modelData.visible === false ? root.loc("widgets.layouts.editor.show") : root.loc("widgets.layouts.editor.hide")
                                                implicitWidth: 30
                                                implicitHeight: 30
                                                padding: 4
                                                onClicked: root.toggleWidgetVisibility(realIndex)
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            z: -1
                                            onClicked: {
                                                root.selectedLayoutWidget = realIndex;
                                                layoutCanvas.forceActiveFocus();
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: !(root.layoutDoc.widgets || []).length
                                    Layout.fillWidth: true
                                    text: root.loc("widgets.layouts.editor.empty_layers")
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
                                Text { text: root.loc("widgets.layouts.editor.canvas"); color: ink; font.pixelSize: 12; font.bold: true }
                                StyledComboBox {
                                    Layout.preferredWidth: 240
                                    model: [root.loc("widgets.layouts.editor.preset_landscape"), root.loc("widgets.layouts.editor.preset_tiktok"), root.loc("widgets.layouts.editor.preset_square"), root.loc("widgets.layouts.editor.preset_hd"), root.loc("widgets.layouts.editor.preset_custom")]
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
                                    toolTipText: root.loc("widgets.layouts.editor.delete_widget")
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
                                        if (!item) return root.loc("widgets.layouts.editor.select_hint");
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
                                        Layout.preferredWidth: 124
                                        implicitWidth: 124
                                        from: -5000; to: 10000
                                        Component.onCompleted: { root._spinX = layoutXSpin; root._syncInspectorSpins(); }
                                        Component.onDestruction: { if (root._spinX === layoutXSpin) root._spinX = null; }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().x || 0)) {
                                                root.updateLayoutItem("x", value);
                                            }
                                        }
                                    }

                                    Text { text: "Y"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutYSpin
                                        Layout.preferredWidth: 124
                                        implicitWidth: 124
                                        from: -5000; to: 10000
                                        Component.onCompleted: { root._spinY = layoutYSpin; root._syncInspectorSpins(); }
                                        Component.onDestruction: { if (root._spinY === layoutYSpin) root._spinY = null; }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().y || 0)) {
                                                root.updateLayoutItem("y", value);
                                            }
                                        }
                                    }

                                    Text { text: "W"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutWSpin
                                        Layout.preferredWidth: 124
                                        implicitWidth: 124
                                        from: 1; to: 10000
                                        Component.onCompleted: { root._spinW = layoutWSpin; root._syncInspectorSpins(); }
                                        Component.onDestruction: { if (root._spinW === layoutWSpin) root._spinW = null; }
                                        onValueModified: {
                                            if (root.selectedLayoutItem() && value !== Number(root.selectedLayoutItem().width || 320)) {
                                                root.updateLayoutItem("width", value);
                                            }
                                        }
                                    }

                                    Text { text: "H"; color: muted; font.pixelSize: 11 }
                                    StyledSpinBox {
                                        id: layoutHSpin
                                        Layout.preferredWidth: 124
                                        implicitWidth: 124
                                        from: 1; to: 10000
                                        Component.onCompleted: { root._spinH = layoutHSpin; root._syncInspectorSpins(); }
                                        Component.onDestruction: { if (root._spinH === layoutHSpin) root._spinH = null; }
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
                                    displayText: {
                                        var idx = root.layoutWidgetInstanceIndex();
                                        if (idx >= 0) {
                                            var opts = root.layoutWidgetInstanceOptions(
                                                root.selectedLayoutItem() ? root.selectedLayoutItem().type : "");
                                            return opts[idx].label;
                                        }
                                        return root.loc("widgets.layouts.no_instance");
                                    }
                                    enabled: root.layoutWidgetInstanceOptions(
                                        root.selectedLayoutItem() ? root.selectedLayoutItem().type : "").length > 0
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
                                // Depends on api.overlayBaseUrl so the URL appears
                                // once the overlay server has started (Slot
                                // calls alone never re-evaluate the binding).
                                text: (api && api.overlayBaseUrl) ? api.layoutOverlayUrl(root.activeLayoutId || "default") : ""
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
                    root._loadingLiveLeaderboardSimpleCfg = false;
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
                root._loadingLiveLeaderboardSimpleCfg = true;
                root._loadingSocialRotatorCfg = true;
                root._loadingWebcamFrameCfg = true;
                root._loadingSignalSystemCfg = true;

                var obj = api.loadChatConfigMap();
                if (!obj || typeof obj !== "object")
                    obj = {};
                root.cfg = root._ensureDefaults(root._detachCfgMap(obj));
                root.chatCfgEpoch += 1;

                var aobj = api.loadActionsConfigMap();
                if (!aobj || typeof aobj !== "object")
                    aobj = {};
                root.actionsCfg = root._ensureActionsDefaults(root._detachCfgMap(aobj));
                root.actionsCfgEpoch += 1;

                var oobj = api.loadOnlineOverlayConfigMap();
                if (!oobj || typeof oobj !== "object")
                    oobj = {};
                root.onlineCfg = root._ensureOnlineDefaults(root._detachCfgMap(oobj));
                root.onlineCfgEpoch += 1;

                var tobj = api.loadTopLikersOverlayConfigMap();
                if (!tobj || typeof tobj !== "object")
                    tobj = {};
                root.topLikersCfg = root._ensureTopLikersDefaults(root._detachTierOverlayCfgMap(tobj));
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
                var b2obj = api.loadBattleOverlayConfigMap();
                if (!b2obj || typeof b2obj !== "object")
                    b2obj = {};
                root.battleCfg2 = JSON.parse(JSON.stringify(b2obj));
                root.battleCfg2Epoch += 1;
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
                var llobj = api.loadLiveLeaderboardOverlayConfigMap();
                if (!llobj || typeof llobj !== "object")
                    llobj = {};
                var llsobj = null;
                try {
                    if (typeof api.loadLiveLeaderboardSimpleConfigMap === "function")
                        llsobj = api.loadLiveLeaderboardSimpleConfigMap();
                } catch (e) { console.warn("live_leaderboard_simple load failed:", e); }
                if (!llsobj || typeof llsobj !== "object")
                    llsobj = {};
                root.liveLeaderboardSimpleCfg = JSON.parse(JSON.stringify(llsobj));
                root.liveLeaderboardSimpleCfgEpoch += 1;
                if (root.liveLeaderboardSimpleCfg && !root.liveLeaderboardSimpleCfg.sequence)
                    root.liveLeaderboardSimpleCfg.sequence = [];
                root.liveLeaderboardCfg = JSON.parse(JSON.stringify(llobj));
                root.liveLeaderboardCfgEpoch += 1;
                if (root.liveLeaderboardCfg && !root.liveLeaderboardCfg.sequence)
                    root.liveLeaderboardCfg.sequence = [];
                var srobj = api.loadSocialRotatorOverlayConfigMap();
                if (!srobj || typeof srobj !== "object")
                    srobj = {};
                root.socialRotatorCfg = JSON.parse(JSON.stringify(srobj));
                root.socialRotatorCfgEpoch += 1;
                if (root.socialRotatorCfg && !root.socialRotatorCfg.platforms)
                    root.socialRotatorCfg.platforms = [];
                var wfobj = api.loadWebcamFrameOverlayConfigMap();
                if (!wfobj || typeof wfobj !== "object")
                    wfobj = {};
                root.webcamFrameCfg = JSON.parse(JSON.stringify(wfobj));
                root.webcamFrameCfgEpoch += 1;
                var ssobj = api.loadSignalSystemOverlayConfigMap();
                if (!ssobj || typeof ssobj !== "object")
                    ssobj = {};
                root.signalSystemCfg = JSON.parse(JSON.stringify(ssobj));
                root.signalSystemCfgEpoch += 1;
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

    // ---- New-widget modal overlay (UI layer only) ----
    CheremshaModal {
        id: createModal
        anchors.fill: parent
        title: root.loc("widgets.instances.new_title")
        subtitle: root.loc("widgets.instances.new_subtitle")
        opened: root.showCreateWidget
        onCloseRequested: {
            root.showCreateWidget = false;
            root.closeCreateModal();
        }
        onOpenedChanged: {
            if (!opened && root.showCreateWidget) root.showCreateWidget = false;
        }

        body: Component {
            ColumnLayout {
                spacing: 0
                Text {
                    text: root.loc("widgets.instances.type_label")
                    color: root.inkMuted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                    Layout.fillWidth: true
                }
                Item { Layout.preferredHeight: 8 }
                StyledComboBox {
                    id: modalTypeBox
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    model: (root.widgetTypeList || []).map(function (t) {
                        return (t.name || t.type_id);
                    })
                    Component.onCompleted: modalTypeBox._syncToRoot()
                    function _syncToRoot() {
                        var list = root.widgetTypeList || [];
                        for (var i = 0; i < list.length; ++i) {
                            if (list[i].type_id === root.newInstanceType) {
                                modalTypeBox.currentIndex = i;
                                return;
                            }
                        }
                        if (list.length > 0) modalTypeBox.currentIndex = 0;
                    }
                    Connections {
                        target: createModal
                        function onOpenedChanged() {
                            if (createModal.opened) {
                                modalTypeBox._syncToRoot();
                                modalNameField.text = root.newInstanceName || "";
                                modalNameField.forceActiveFocus();
                            } else {
                                modalNameField.text = "";
                            }
                        }
                    }
                    onUserActivated: function (idx) {
                        var t = (root.widgetTypeList || [])[idx];
                        if (t) root.newInstanceType = t.type_id;
                    }
                    onActivated: function (idx) {
                        var t2 = (root.widgetTypeList || [])[idx];
                        if (t2) root.newInstanceType = t2.type_id;
                    }
                }
                Item { Layout.preferredHeight: 8 }
                Text {
                    Layout.fillWidth: true
                    color: root.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    text: {
                        var t = (root.widgetTypeList || []).filter(function (x) {
                            return x.type_id === root.newInstanceType;
                        })[0];
                        return t ? (t.description || "") : "";
                    }
                }
                Item { Layout.preferredHeight: 20 }
                Text {
                    text: root.loc("widgets.instances.name_label")
                    color: root.inkMuted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                    Layout.fillWidth: true
                }
                Item { Layout.preferredHeight: 8 }
                StyledTextField {
                    id: modalNameField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    leftPadding: 14
                    rightPadding: 14
                    placeholderText: root.loc("widgets.instances.name_placeholder")
                    onTextChanged: root.newInstanceName = text
                    Keys.onReturnPressed: {
                        if (root.newInstanceType !== "") root.submitCreateWidget();
                    }
                    Keys.onEnterPressed: {
                        if (root.newInstanceType !== "") root.submitCreateWidget();
                    }
                }
            }
        }

        footer: Component {
            RowLayout {
                spacing: 8
                Item { Layout.fillWidth: true }
                PillButton {
                    Layout.preferredHeight: 40
                    Layout.preferredWidth: 100
                    text: root.loc("widgets.common.cancel")
                    onClicked: {
                        root.showCreateWidget = false;
                        root.closeCreateModal();
                    }
                }
                PillButton {
                    id: createBtn
                    Layout.preferredHeight: 40
                    Layout.preferredWidth: 130
                    primary: true
                    text: root.loc("widgets.common.create")
                    enabled: (root.widgetTypeList || []).length > 0 && root.newInstanceType !== ""
                    opacity: enabled ? 1.0 : 0.45
                    onClicked: root.submitCreateWidget()
                }
            }
        }
    }
}
