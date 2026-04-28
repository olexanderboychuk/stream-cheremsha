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

    property var cfg: null
    property color _bubbleColor: "#0a0c12"
    property real _bubbleAlpha: 0.55
    property color _usernameCustomColor: "#93c5fd"

    function _ensureDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (obj.max_items === undefined) obj.max_items = 12;
        if (obj.font_size_px === undefined) obj.font_size_px = 18;
        if (obj.show_platform === undefined) obj.show_platform = true;
        if (obj.show_platform_icon === undefined) obj.show_platform_icon = true;
        if (obj.fade_seconds === undefined) obj.fade_seconds = 0;
        if (!obj.bubble_bg_rgba) obj.bubble_bg_rgba = "rgba(10,12,18,0.55)";
        if (obj.bubble_radius_px === undefined) obj.bubble_radius_px = 10;
        if (!obj.username_color_mode) obj.username_color_mode = "auto";
        if (!obj.username_color_custom) obj.username_color_custom = "#93c5fd";
        if (!obj.text_color) obj.text_color = "#e5e7eb";
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
                            text: api ? api.chatOverlayUrl() : ""
                        }

                        Button {
                            text: "Copy URL"
                            hoverEnabled: true
                            focusPolicy: Qt.NoFocus
                            onClicked: if (api) api.copyChatOverlayUrl()
                        }

                        Button {
                            text: "Закрити"
                            hoverEnabled: true
                            focusPolicy: Qt.NoFocus
                            onClicked: {
                                if (typeof widgetsWindow !== "undefined" && widgetsWindow) widgetsWindow.close();
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
                            Text { text: "max_items"; color: muted; Layout.preferredWidth: 160 }
                            SpinBox {
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
                            Text { text: "font_size_px"; color: muted; Layout.preferredWidth: 160 }
                            SpinBox {
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
                            Text { text: "show_platform"; color: muted; Layout.preferredWidth: 160 }
                            Switch {
                                id: showPlatform
                                checked: cfg ? !!cfg.show_platform : true
                                onClicked: {
                                    if (cfg === null) return;
                                    cfg.show_platform = checked;
                                    _save();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "show_platform_icon"; color: muted; Layout.preferredWidth: 160 }
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
                            Text { text: "fade_seconds"; color: muted; Layout.preferredWidth: 160 }
                            SpinBox {
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
                            Text { text: "bubble_bg_rgba"; color: muted; Layout.preferredWidth: 160 }
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
                            Button {
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
                            Text { text: "bubble_radius_px"; color: muted; Layout.preferredWidth: 160 }
                            SpinBox {
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
                            Text { text: "username_color_mode"; color: muted; Layout.preferredWidth: 160 }
                            ComboBox {
                                id: usernameColorMode
                                model: ["auto", "platform", "custom"]
                                Layout.fillWidth: true
                                onActivated: {
                                    if (cfg === null) return;
                                    cfg.username_color_mode = currentText;
                                    _save();
                                }
                                Component.onCompleted: {
                                    if (!cfg) return;
                                    var i = model.indexOf(cfg.username_color_mode || "auto");
                                    currentIndex = (i >= 0) ? i : 0;
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            visible: cfg && cfg.username_color_mode === "custom"
                            Text { text: "username_color_custom"; color: muted; Layout.preferredWidth: 160 }
                            Rectangle {
                                width: 26
                                height: 26
                                radius: 8
                                color: _usernameCustomColor
                                border.width: 1
                                border.color: cardEdge
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Button {
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
                            Text { text: "text_color"; color: muted; Layout.preferredWidth: 160 }
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
                            Text { text: "font_family"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: cfg ? (cfg.font_family || "") : ""
                                onEditingFinished: {
                                    if (cfg === null) return;
                                    cfg.font_family = text;
                                    _save();
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
}

