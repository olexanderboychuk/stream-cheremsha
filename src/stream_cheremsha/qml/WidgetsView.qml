import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Item {
    id: root
    implicitWidth: 720
    implicitHeight: 520

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
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
        }
    }

    readonly property int titleBarH: 44
    property string widgetMode: "grid" // grid | chat | actions | online

    component PillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property color colRest: "#1c2434"
        property color colHover: "#263246"
        property color colPress: "#303a50"
        property color borRest: root.cardEdge
        property color borHover: "#3b4458"
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: pillFontSize
        transformOrigin: Item.Center
        scale: pillCtl.hovered ? 1.02 : 1.0
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        contentItem: Text {
            text: pillCtl.text
            color: root.ink
            font.pixelSize: pillCtl.pillFontSize
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
        background: Rectangle {
            radius: 8
            color: pillCtl.pressed ? pillCtl.colPress : (pillCtl.hovered ? pillCtl.colHover : pillCtl.colRest)
            border.width: 1
            border.color: pillCtl.hovered ? pillCtl.borHover : pillCtl.borRest
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    component StyledComboBox: ComboBox {
        id: cb
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: 13
        padding: 10
        contentItem: Text {
            text: cb.editable ? (cb.editText || "") : cb.displayText
            color: root.ink
            font.pixelSize: cb.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: root.fieldBg
            border.width: 1
            border.color: cb.hovered ? "#3b4458" : root.cardEdge
        }
        delegate: ItemDelegate {
            width: ListView.view ? ListView.view.width : implicitWidth
            contentItem: Text {
                text: cb.textRole ? (modelData[cb.textRole] || "") : (modelData || "")
                color: root.ink
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 6
                color: highlighted ? "#1a2232" : "#111827"
            }
        }
    }

    component StyledSpinBox: SpinBox {
        id: sb
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        editable: true
        font.pixelSize: 13
        implicitHeight: 34
        implicitWidth: 150

        // Qt Quick SpinBox may not expose increase()/decrease() to QML (not invokable in this build).
        function _stepBy(delta) {
            var next = sb.value + delta;
            if (next < sb.from) next = sb.from;
            if (next > sb.to) next = sb.to;
            sb.value = next;
        }

        contentItem: TextInput {
            id: sbInput
            text: sb.displayText
            color: root.ink
            selectionColor: "#334155"
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
                // Commit typed value (clamped by SpinBox + validator bounds).
                // If input is empty/invalid, restore current value text.
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
            radius: 8
            color: root.fieldBg
            border.width: 1
            border.color: sb.hovered ? "#3b4458" : root.cardEdge
        }

        down.indicator: Item {
            implicitWidth: 34
            implicitHeight: 34
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 0
            Rectangle {
                anchors.fill: parent
                radius: 8
                color: downMa.pressed ? "#303a50" : (downMa.containsMouse ? "#263246" : "#1c2434")
                border.width: 1
                border.color: downMa.containsMouse ? "#3b4458" : root.cardEdge
                Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
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
                    onClicked: sb._stepBy(-sb.stepSize)
                }
            }
        }

        up.indicator: Item {
            implicitWidth: 34
            implicitHeight: 34
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 0
            Rectangle {
                anchors.fill: parent
                radius: 8
                color: upMa.pressed ? "#303a50" : (upMa.containsMouse ? "#263246" : "#1c2434")
                border.width: 1
                border.color: upMa.containsMouse ? "#3b4458" : root.cardEdge
                Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
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
                    onClicked: sb._stepBy(sb.stepSize)
                }
            }
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
        if (obj.text_shadow_enabled === undefined) obj.text_shadow_enabled = false;
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
        if (!api || cfg === null) return;
        if (_loadingCfg) return;
        api.saveChatConfigJson(JSON.stringify(cfg));
    }

    property bool _loadingCfg: false

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
        if (!api || actionsCfg === null) return;
        if (_loadingActionsCfg) return;
        actionsCfgEpoch += 1;
        api.saveActionsConfigJson(JSON.stringify(actionsCfg));
    }

    function _ensureOnlineDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (!obj.layout_mode) obj.layout_mode = "combined";

        if (obj.platform_twitch_enabled === undefined) obj.platform_twitch_enabled = true;
        if (obj.platform_tiktok_enabled === undefined) obj.platform_tiktok_enabled = true;
        if (obj.platform_youtube_enabled === undefined) obj.platform_youtube_enabled = true;

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
        if (!api || onlineCfg === null) return;
        if (_loadingOnlineCfg) return;
        onlineCfgEpoch += 1;
        api.saveOnlineOverlayConfigJson(JSON.stringify(onlineCfg));
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
                        text: "Віджети"
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

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode === "grid"
                implicitHeight: gridCol.implicitHeight + 20

                ColumnLayout {
                    id: gridCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "Віджети"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Оберіть віджет і натисніть “Редагувати”."
                        color: muted
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: Math.max(1, Math.floor((width + 12) / 320))
                        columnSpacing: 12
                        rowSpacing: 12

                        component WidgetCard: Rectangle {
                            id: card
                            property string title: ""
                            property string urlText: ""
                            property var onCopy: null
                            property var onPlay: null
                            property var onEdit: null
                            Layout.fillWidth: true
                            Layout.minimumWidth: 280
                            radius: 14
                            color: fieldBg
                            border.width: 1
                            border.color: cardEdge
                            implicitHeight: c.implicitHeight + 18

                            ColumnLayout {
                                id: c
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 12
                                spacing: 8

                                Text {
                                    text: card.title
                                    color: ink
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.fillWidth: true
                                }

                                TextField {
                                    Layout.fillWidth: true
                                    readOnly: true
                                    selectByMouse: true
                                    color: ink
                                    font.pixelSize: 12
                                    background: Rectangle { radius: 8; color: "#0b0f17"; border.width: 1; border.color: cardEdge }
                                    text: card.urlText
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    PillButton {
                                        visible: !!card.onPlay
                                        text: "▶"
                                        pillFontSize: 12
                                        onClicked: if (card.onPlay) card.onPlay()
                                    }
                                    PillButton {
                                        text: "Скопіювати URL"
                                        onClicked: if (card.onCopy) card.onCopy()
                                    }
                                    Item { Layout.fillWidth: true }
                                    PillButton {
                                        text: "Редагувати"
                                        onClicked: if (card.onEdit) card.onEdit()
                                    }
                                }
                            }
                        }

                        WidgetCard {
                            title: "Chat overlay"
                            urlText: api ? api.chatOverlayUrlValue : ""
                            onCopy: function() { if (api) api.copyChatOverlayUrl(); }
                            onEdit: function() { root.widgetMode = "chat"; }
                        }

                        WidgetCard {
                            title: "Actions overlay"
                            urlText: api ? api.actionsOverlayUrlValue : ""
                            onCopy: function() { if (api) api.copyActionsOverlayUrl(); }
                            onPlay: function() { if (api) api.previewActionsOverlay(); }
                            onEdit: function() { root.widgetMode = "actions"; }
                        }

                        WidgetCard {
                            title: "Online overlay"
                            urlText: api ? api.onlineOverlayUrlValue : ""
                            onCopy: function() { if (api) api.copyOnlineOverlayUrl(); }
                            onEdit: function() { root.widgetMode = "online"; }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Item { Layout.fillWidth: true }
                        PillButton {
                            text: "Закрити"
                            onClicked: {
                                if (typeof navApi !== "undefined" && navApi) navApi.goHome();
                                else if (winApi) winApi.close();
                            }
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
                visible: root.widgetMode === "chat"
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
                            text: api ? api.chatOverlayUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (api) api.copyChatOverlayUrl()
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
                visible: root.widgetMode === "actions"
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
                            text: api ? api.actionsOverlayUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (api) api.copyActionsOverlayUrl()
                        }

                        PillButton {
                            text: "▶"
                            pillFontSize: 12
                            onClicked: if (api) api.previewActionsOverlay()
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
                visible: root.widgetMode === "online"
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
                            text: api ? api.onlineOverlayUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (api) api.copyOnlineOverlayUrl()
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
                Layout.fillHeight: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                visible: root.widgetMode !== "grid"

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
                            StyledSpinBox {
                                id: maxItems
                                from: 1
                                to: 200
                                value: (cfg && cfg.max_items) ? cfg.max_items : 12
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.max_items = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Розмір шрифту"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: fontSize
                                from: 8
                                to: 96
                                value: (cfg && cfg.font_size_px) ? cfg.font_size_px : 18
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.font_size_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Іконки платформ"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: showPlatformIcon
                                checked: cfg ? !!cfg.show_platform_icon : true
                                onClicked: {
                                    if (cfg === null) return;
                                    cfg.show_platform_icon = checked;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Авто-приховування (сек)"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: fadeSeconds
                                from: 0
                                to: 600
                                value: (cfg && cfg.fade_seconds !== undefined) ? cfg.fade_seconds : 0
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.fade_seconds = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон віджета"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: widgetBgSw
                                checked: cfg ? !!cfg.widget_bg_enabled : false
                                onClicked: {
                                    if (cfg === null) return;
                                    cfg.widget_bg_enabled = checked;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.widget_bg_enabled
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
                            Slider {
                                id: widgetBgAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _widgetBgAlpha
                                onMoved: {
                                    if (cfg === null) return;
                                    _widgetBgAlpha = value;
                                    cfg.widget_bg_rgba = _rgbaString(_widgetBgColor, _widgetBgAlpha);
                                    _save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.widget_bg_enabled
                            Text { text: "Заокруглення фону (px)"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: widgetBgRadius
                                from: 0
                                to: 60
                                value: (cfg && cfg.widget_bg_radius_px !== undefined) ? cfg.widget_bg_radius_px : 14
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.widget_bg_radius_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.widget_bg_enabled
                            Text { text: "Внутрішній відступ (px)"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: widgetBgPadding
                                from: 0
                                to: 48
                                value: (cfg && cfg.widget_bg_padding_px !== undefined) ? cfg.widget_bg_padding_px : 10
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.widget_bg_padding_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон повідомлень"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: bubbleBgSw
                                checked: cfg ? !!cfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (cfg === null) return;
                                    cfg.bubble_bg_enabled = checked;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.bubble_bg_enabled
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
                            Slider {
                                id: bubbleAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _bubbleAlpha
                                onMoved: {
                                    if (cfg === null) return;
                                    _bubbleAlpha = value;
                                    cfg.bubble_bg_rgba = _rgbaString(_bubbleColor, _bubbleAlpha);
                                    _save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.bubble_bg_enabled
                            Text { text: "Заокруглення (px)"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: bubbleRadius
                                from: 0
                                to: 60
                                value: (cfg && cfg.bubble_radius_px !== undefined) ? cfg.bubble_radius_px : 10
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.bubble_radius_px = value;
                                    _save();
                                }
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
                                onActivated: {
                                    if (cfg === null) return;
                                    cfg.username_color_mode = (currentIndex === 1) ? "platform" : ((currentIndex === 2) ? "custom" : "auto");
                                    _save();
                                }
                                Component.onCompleted: {
                                    if (!cfg) return;
                                    var raw = cfg.username_color_mode || "auto";
                                    currentIndex = (raw === "platform") ? 1 : ((raw === "custom") ? 2 : 0);
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.username_color_mode === "custom"
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
                                text: cfg ? (cfg.username_color_custom || "") : ""
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
                                color: cfg ? (cfg.text_color || "#e5e7eb") : "#e5e7eb"
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
                                text: cfg ? (cfg.text_color || "") : ""
                                onEditingFinished: {
                                    if (cfg === null) return;
                                    cfg.text_color = text;
                                    _save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Тінь тексту"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: textShadowSw
                                checked: cfg ? !!cfg.text_shadow_enabled : false
                                onClicked: {
                                    if (cfg === null) return;
                                    cfg.text_shadow_enabled = checked;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.text_shadow_enabled
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
                            Slider {
                                id: shadowAlpha
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: _textShadowAlpha
                                onMoved: {
                                    if (cfg === null) return;
                                    _textShadowAlpha = value;
                                    cfg.text_shadow_rgba = _rgbaString(_textShadowColor, _textShadowAlpha);
                                    _save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.text_shadow_enabled
                            Text { text: "Розмиття тіні"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: textShadowBlur
                                from: 0
                                to: 24
                                value: (cfg && cfg.text_shadow_blur_px !== undefined) ? cfg.text_shadow_blur_px : 4
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.text_shadow_blur_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.text_shadow_enabled
                            Text { text: "Зміщення X"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: textShadowOffX
                                from: -12
                                to: 12
                                value: (cfg && cfg.text_shadow_offset_x_px !== undefined) ? cfg.text_shadow_offset_x_px : 0
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.text_shadow_offset_x_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.text_shadow_enabled
                            Text { text: "Зміщення Y"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: textShadowOffY
                                from: -12
                                to: 12
                                value: (cfg && cfg.text_shadow_offset_y_px !== undefined) ? cfg.text_shadow_offset_y_px : 1
                                onValueChanged: {
                                    if (_loadingCfg || cfg === null) return;
                                    cfg.text_shadow_offset_y_px = value;
                                    _save();
                                }
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
                                onActivated: {
                                    if (cfg === null) return;
                                    cfg.font_family = currentText;
                                    _save();
                                }
                                onAccepted: {
                                    if (cfg === null) return;
                                    cfg.font_family = editText || currentText;
                                    _save();
                                }
                                Component.onCompleted: {
                                    if (!cfg) return;
                                    var ff = (cfg.font_family || "").trim();
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
                                onActivated: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.layout_mode = (currentIndex === 1) ? "per_platform" : "combined";
                                    _saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!onlineCfg) { currentIndex = 0; return; }
                                    var m = String(onlineCfg.layout_mode || "combined").toLowerCase();
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
                                checked: onlineCfg ? !!onlineCfg.platform_twitch_enabled : true
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.platform_twitch_enabled = checked;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "TikTok"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: onlineCfg ? !!onlineCfg.platform_tiktok_enabled : true
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.platform_tiktok_enabled = checked;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "YouTube"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                checked: onlineCfg ? !!onlineCfg.platform_youtube_enabled : true
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.platform_youtube_enabled = checked;
                                    _saveOnline();
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
                                onActivated: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.font_family = currentText;
                                    _saveOnline();
                                }
                                onAccepted: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.font_family = editText || currentText;
                                    _saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!onlineCfg) return;
                                    var ff = (onlineCfg.font_family || "").trim();
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
                            StyledSpinBox {
                                from: 8
                                to: 200
                                value: (onlineCfg && onlineCfg.font_size_px !== undefined) ? onlineCfg.font_size_px : 36
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.font_size_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал між рядками"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                from: 0
                                to: 200
                                value: (onlineCfg && onlineCfg.font_line_spacing_px !== undefined) ? onlineCfg.font_line_spacing_px : 0
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.font_line_spacing_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Інтервал між літерами"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                from: -200
                                to: 200
                                value: (onlineCfg && onlineCfg.font_letter_spacing_px !== undefined) ? onlineCfg.font_letter_spacing_px : 0
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.font_letter_spacing_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Тінь тексту"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Увімкнути тінь"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: onlineCfg ? !!onlineCfg.text_shadow_enabled : false
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.text_shadow_enabled = checked;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: onlineCfg && onlineCfg.text_shadow_enabled
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
                                text: onlineCfg ? (onlineCfg.text_shadow_color || "") : ""
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
                                text: onlineCfg ? (onlineCfg.text_color || "") : ""
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
                                checked: onlineCfg ? !!onlineCfg.font_border_enabled : false
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.font_border_enabled = checked;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: onlineCfg && onlineCfg.font_border_enabled
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
                                text: onlineCfg ? (onlineCfg.font_border_color || "") : ""
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
                                onActivated: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.text_effect =
                                        (currentIndex === 1) ? "glow"
                                        : (currentIndex === 2) ? "neon"
                                        : (currentIndex === 3) ? "rainbow"
                                        : (currentIndex === 4) ? "aurora"
                                        : (currentIndex === 5) ? "fire"
                                        : "none";
                                    _saveOnline();
                                }
                                Component.onCompleted: {
                                    if (!onlineCfg) { currentIndex = 0; return; }
                                    var raw = String(onlineCfg.text_effect || "none").trim().toLowerCase();
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
                            StyledSpinBox {
                                from: 16
                                to: 128
                                value: (onlineCfg && onlineCfg.platform_icon_size_px !== undefined) ? onlineCfg.platform_icon_size_px : 28
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.platform_icon_size_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Відступ іконки — число (px)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 0
                                to: 80
                                value: (onlineCfg && onlineCfg.icon_number_gap_px !== undefined) ? onlineCfg.icon_number_gap_px : 12
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.icon_number_gap_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Тло блоку"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Фон-підкладка"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: onlineCfg ? !!onlineCfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.bubble_bg_enabled = checked;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: onlineCfg && onlineCfg.bubble_bg_enabled
                            Text { text: "Непрозорість фону"; color: muted; Layout.preferredWidth: 220 }
                            Slider {
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: (onlineCfg && onlineCfg.bubble_bg_alpha !== undefined) ? onlineCfg.bubble_bg_alpha : 0.45
                                onMoved: {
                                    if (onlineCfg === null) return;
                                    onlineCfg.bubble_bg_alpha = value;
                                    _saveOnline();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: onlineCfg && onlineCfg.bubble_bg_enabled
                            Text { text: "Радіус кутів (px)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 0
                                to: 60
                                value: (onlineCfg && onlineCfg.bubble_radius_px !== undefined) ? onlineCfg.bubble_radius_px : 14
                                onValueChanged: {
                                    if (_loadingOnlineCfg || onlineCfg === null) return;
                                    onlineCfg.bubble_radius_px = value;
                                    _saveOnline();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        } // onlineSettings

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
                                onActivated: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.font_family = currentText;
                                    _saveActions();
                                }
                                onAccepted: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.font_family = editText || currentText;
                                    _saveActions();
                                }
                                Component.onCompleted: {
                                    if (!actionsCfg) return;
                                    var ff = (actionsCfg.font_family || "").trim();
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
                            StyledSpinBox {
                                from: 8
                                to: 200
                                value: (actionsCfg && actionsCfg.font_size_px !== undefined) ? actionsCfg.font_size_px : 40
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.font_size_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font line spacing"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                from: 0
                                to: 200
                                value: (actionsCfg && actionsCfg.font_line_spacing_px !== undefined) ? actionsCfg.font_line_spacing_px : 0
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.font_line_spacing_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Font letter spacing"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                from: -200
                                to: 200
                                value: (actionsCfg && actionsCfg.font_letter_spacing_px !== undefined) ? actionsCfg.font_letter_spacing_px : 0
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.font_letter_spacing_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Font Effects"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Wave Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.wave_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.wave_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Move Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.move_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.move_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable 3D Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.effect_3d_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.effect_3d_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Enable Wiggle Effect"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.wiggle_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.wiggle_enabled = checked;
                                    _saveActions();
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
                                checked: actionsCfg ? !!actionsCfg.text_shadow_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.text_shadow_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfg && actionsCfg.text_shadow_enabled
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
                                text: actionsCfg ? (actionsCfg.text_shadow_color || "") : ""
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
                                text: actionsCfg ? (actionsCfg.text_color || "") : ""
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
                                checked: actionsCfg ? !!actionsCfg.font_border_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.font_border_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfg && actionsCfg.font_border_enabled
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
                                text: actionsCfg ? (actionsCfg.font_border_color || "") : ""
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
                                checked: actionsCfg ? !!actionsCfg.username_custom_color_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.username_custom_color_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfg && actionsCfg.username_custom_color_enabled
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
                                text: actionsCfg ? (actionsCfg.username_custom_color || "") : ""
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
                                onActivated: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.username_text_effect =
                                        (currentIndex === 1) ? "rainbow"
                                        : (currentIndex === 2) ? "aurora"
                                        : (currentIndex === 3) ? "neon"
                                        : (currentIndex === 4) ? "fire"
                                        : "none";
                                    _saveActions();
                                }
                                Component.onCompleted: {
                                    if (!actionsCfg) { currentIndex = 0; return; }
                                    var raw = (actionsCfg.username_text_effect || "none").trim().toLowerCase();
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
                            StyledSpinBox {
                                from: 1
                                to: 512
                                value: (actionsCfg && actionsCfg.picture_size_px !== undefined) ? actionsCfg.picture_size_px : 65
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null)
                                        return;
                                    actionsCfg.picture_size_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Username Size"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 1
                                to: 512
                                value: (actionsCfg && actionsCfg.username_size_px !== undefined) ? actionsCfg.username_size_px : 65
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null)
                                        return;
                                    actionsCfg.username_size_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Відстань між ніком і текстом (px)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 0
                                to: 80
                                value: (actionsCfg && actionsCfg.name_text_gap_px !== undefined) ? actionsCfg.name_text_gap_px : 8
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.name_text_gap_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Text { text: "Options"; color: ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Bubble background"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.bubble_bg_enabled : true
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.bubble_bg_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfg && actionsCfg.bubble_bg_enabled
                            Text { text: "Bubble opacity"; color: muted; Layout.preferredWidth: 220 }
                            Slider {
                                Layout.fillWidth: true
                                from: 0.0
                                to: 1.0
                                stepSize: 0.01
                                value: (actionsCfg && actionsCfg.bubble_bg_alpha !== undefined) ? actionsCfg.bubble_bg_alpha : 0.55
                                onMoved: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.bubble_bg_alpha = value;
                                    _saveActions();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfg && actionsCfg.bubble_bg_enabled
                            Text { text: "Bubble radius (px)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 0
                                to: 60
                                value: (actionsCfg && actionsCfg.bubble_radius_px !== undefined) ? actionsCfg.bubble_radius_px : 16
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.bubble_radius_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Auto-hide (sec)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 0
                                to: 600
                                value: (actionsCfg && actionsCfg.auto_hide_seconds !== undefined) ? actionsCfg.auto_hide_seconds : 0
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null) return;
                                    actionsCfg.auto_hide_seconds = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Show Profile Picture"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.show_profile_picture : true
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.show_profile_picture = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Show Gift Picture"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.show_gift_picture : true
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.show_gift_picture = checked;
                                    _saveActions();
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
                                checked: actionsCfg ? !!actionsCfg.show_action_platform_icon : true
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.show_action_platform_icon = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfgEpoch >= 0 && actionsCfg && !!actionsCfg.show_action_platform_icon
                            Text {
                                text: "Platform icon flip (slow start, sharp finish)"
                                color: muted
                                Layout.preferredWidth: 220
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 220
                            }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.platform_icon_flip_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.platform_icon_flip_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: actionsCfgEpoch >= 0 && actionsCfg && !!actionsCfg.show_action_platform_icon
                            Text { text: "Platform icon size (px)"; color: muted; Layout.preferredWidth: 220 }
                            StyledSpinBox {
                                from: 16
                                to: 128
                                value: (actionsCfg && actionsCfg.platform_icon_size_px !== undefined) ? actionsCfg.platform_icon_size_px : 40
                                onValueChanged: {
                                    if (_loadingActionsCfg || actionsCfg === null)
                                        return;
                                    actionsCfg.platform_icon_size_px = value;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Single Text Line"; color: muted; Layout.preferredWidth: 220 }
                            Switch {
                                checked: actionsCfg ? !!actionsCfg.single_text_line : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.single_text_line = checked;
                                    _saveActions();
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
                                checked: actionsCfg ? !!actionsCfg.parallel_popups_enabled : false
                                onClicked: {
                                    if (actionsCfg === null) return;
                                    actionsCfg.parallel_popups_enabled = checked;
                                    _saveActions();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        } // actionsSettings
                    }
                }
            }

            Component.onCompleted: {
                if (!api) return;
                var obj = api.loadChatConfigMap();
                if (!obj || typeof obj !== "object")
                    obj = {};
                _loadingCfg = true;
                cfg = _ensureDefaults(obj);
                // Initialize derived UI state for pickers.
                var p = _parseRgba(cfg.bubble_bg_rgba);
                _bubbleColor = p.c;
                _bubbleAlpha = p.a;
                bubbleAlpha.value = _bubbleAlpha;
                _usernameCustomColor = cfg.username_color_custom || "#93c5fd";
                var sp = _parseRgba(cfg.text_shadow_rgba || "rgba(0,0,0,0.65)");
                _textShadowColor = sp.c;
                _textShadowAlpha = sp.a;
                shadowAlpha.value = _textShadowAlpha;
                var wp = _parseRgba(cfg.widget_bg_rgba || "rgba(10,12,18,0.45)");
                _widgetBgColor = wp.c;
                _widgetBgAlpha = wp.a;
                widgetBgAlpha.value = _widgetBgAlpha;

                var aobj = api.loadActionsConfigMap();
                if (!aobj || typeof aobj !== "object")
                    aobj = {};
                _loadingActionsCfg = true;
                actionsCfg = _ensureActionsDefaults(aobj);
                _actionsTextShadowColor = actionsCfg.text_shadow_color || "#000000";
                _actionsBorderColor = actionsCfg.font_border_color || "#242424";
                _actionsCustomColor = actionsCfg.username_custom_color || "#32c3a6";
                _actionsTextColor = actionsCfg.text_color || "#e5e7eb";

                var oobj = api.loadOnlineOverlayConfigMap();
                if (!oobj || typeof oobj !== "object")
                    oobj = {};
                _loadingOnlineCfg = true;
                onlineCfg = _ensureOnlineDefaults(oobj);
                _onlineTextShadowColor = onlineCfg.text_shadow_color || "#000000";
                _onlineBorderColor = onlineCfg.font_border_color || "#242424";
                _onlineTextColor = onlineCfg.text_color || "#e5e7eb";
                overlayCfgInitGuardTimer.restart();
            }
        }
    }

    ColorDialog {
        id: bubbleColorDlg
        title: "Bubble background color"
        selectedColor: _bubbleColor
        onAccepted: {
            if (cfg === null) return;
            _bubbleColor = selectedColor;
            cfg.bubble_bg_rgba = _rgbaString(_bubbleColor, _bubbleAlpha);
            _save();
        }
    }

    ColorDialog {
        id: widgetBgColorDlg
        title: "Widget background color"
        selectedColor: _widgetBgColor
        onAccepted: {
            if (cfg === null) return;
            _widgetBgColor = selectedColor;
            cfg.widget_bg_rgba = _rgbaString(_widgetBgColor, _widgetBgAlpha);
            _save();
        }
    }

    ColorDialog {
        id: usernameColorDlg
        title: "Username color"
        selectedColor: _usernameCustomColor
        onAccepted: {
            if (cfg === null) return;
            _usernameCustomColor = selectedColor;
            cfg.username_color_custom = _colorToHex(_usernameCustomColor);
            _save();
        }
    }

    ColorDialog {
        id: textColorDlg
        title: "Text color"
        selectedColor: cfg ? (cfg.text_color || "#e5e7eb") : "#e5e7eb"
        onAccepted: {
            if (cfg === null) return;
            cfg.text_color = _colorToHex(selectedColor);
            _save();
        }
    }

    ColorDialog {
        id: textShadowColorDlg
        title: "Text shadow color"
        selectedColor: _textShadowColor
        onAccepted: {
            if (cfg === null) return;
            _textShadowColor = selectedColor;
            cfg.text_shadow_rgba = _rgbaString(_textShadowColor, _textShadowAlpha);
            _save();
        }
    }

    ColorDialog {
        id: actionsTextShadowDlg
        title: "Actions: text shadow color"
        selectedColor: _actionsTextShadowColor
        onAccepted: {
            if (actionsCfg === null) return;
            _actionsTextShadowColor = selectedColor;
            actionsCfg.text_shadow_color = _colorToHex(selectedColor);
            _saveActions();
        }
    }

    ColorDialog {
        id: actionsTextColorDlg
        title: "Actions: text color"
        selectedColor: _actionsTextColor
        onAccepted: {
            if (actionsCfg === null) return;
            _actionsTextColor = selectedColor;
            actionsCfg.text_color = _colorToHex(selectedColor);
            _saveActions();
        }
    }

    ColorDialog {
        id: actionsBorderDlg
        title: "Actions: border color"
        selectedColor: _actionsBorderColor
        onAccepted: {
            if (actionsCfg === null) return;
            _actionsBorderColor = selectedColor;
            actionsCfg.font_border_color = _colorToHex(selectedColor);
            _saveActions();
        }
    }

    ColorDialog {
        id: actionsCustomColorDlg
        title: "Actions: username custom color"
        selectedColor: _actionsCustomColor
        onAccepted: {
            if (actionsCfg === null) return;
            _actionsCustomColor = selectedColor;
            actionsCfg.username_custom_color = _colorToHex(selectedColor);
            _saveActions();
        }
    }

    ColorDialog {
        id: onlineTextShadowDlg
        title: "Online: колір тіні"
        selectedColor: _onlineTextShadowColor
        onAccepted: {
            if (onlineCfg === null) return;
            _onlineTextShadowColor = selectedColor;
            onlineCfg.text_shadow_color = _colorToHex(selectedColor);
            _saveOnline();
        }
    }

    ColorDialog {
        id: onlineTextColorDlg
        title: "Online: колір тексту"
        selectedColor: _onlineTextColor
        onAccepted: {
            if (onlineCfg === null) return;
            _onlineTextColor = selectedColor;
            onlineCfg.text_color = _colorToHex(selectedColor);
            _saveOnline();
        }
    }

    ColorDialog {
        id: onlineBorderDlg
        title: "Online: колір контуру"
        selectedColor: _onlineBorderColor
        onAccepted: {
            if (onlineCfg === null) return;
            _onlineBorderColor = selectedColor;
            onlineCfg.font_border_color = _colorToHex(selectedColor);
            _saveOnline();
        }
    }
}

