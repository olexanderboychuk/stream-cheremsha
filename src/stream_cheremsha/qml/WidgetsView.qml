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

    Rectangle { anchors.fill: parent; color: base }

    readonly property int titleBarH: 44

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
        focusPolicy: Qt.NoFocus
        font.pixelSize: 13
        implicitHeight: 34
        implicitWidth: 150

        function _stepBy(delta) {
            var next = sb.value + delta;
            if (next < sb.from) next = sb.from;
            if (next > sb.to) next = sb.to;
            sb.value = next;
        }

        contentItem: TextInput {
            text: sb.displayText
            color: root.ink
            selectionColor: "#334155"
            selectedTextColor: root.ink
            font.pixelSize: sb.font.pixelSize
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter
            readOnly: true
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
    property color _bubbleColor: "#0a0c12"
    property real _bubbleAlpha: 0.55
    property color _usernameCustomColor: "#93c5fd"
    property color _textShadowColor: "#000000"
    property real _textShadowAlpha: 0.65
    property color _widgetBgColor: "#0a0c12"
    property real _widgetBgAlpha: 0.45

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
        api.saveChatConfigJson(JSON.stringify(cfg));
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
                implicitHeight: headerCol.implicitHeight + 20

                ColumnLayout {
                    id: headerCol
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
                            id: urlField
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
                Layout.fillHeight: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    contentWidth: availableWidth
                    background: Item {}

                    ColumnLayout {
                        width: Math.max(1, parent.width - 24)
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
                                    cfg.widget_bg_padding_px = value;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
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
                            Text { text: "Заокруглення (px)"; color: muted; Layout.preferredWidth: 160 }
                            StyledSpinBox {
                                id: bubbleRadius
                                from: 0
                                to: 60
                                value: (cfg && cfg.bubble_radius_px !== undefined) ? cfg.bubble_radius_px : 10
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                onValueModified: {
                                    if (cfg === null) return;
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
                                model: [
                                    "Segoe UI",
                                    "Inter",
                                    "Roboto",
                                    "Arial",
                                    "Tahoma",
                                    "Verdana",
                                    "Noto Sans",
                                    "Ubuntu",
                                    "SF Pro Display"
                                ]
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
                    }
                }
            }

            Component.onCompleted: {
                if (!api) return;
                var raw = api.loadChatConfigJson();
                var obj = null;
                try { obj = JSON.parse(raw); } catch (e) { obj = {}; }
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
}

