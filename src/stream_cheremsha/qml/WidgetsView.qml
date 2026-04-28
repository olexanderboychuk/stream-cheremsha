import QtQuick
import QtQuick.Controls
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

    function _ensureDefaults(obj) {
        if (!obj) obj = {};
        if (obj.schema_version === undefined) obj.schema_version = 1;
        if (obj.max_items === undefined) obj.max_items = 12;
        if (obj.font_size_px === undefined) obj.font_size_px = 18;
        if (obj.show_platform === undefined) obj.show_platform = true;
        if (!obj.bg_rgba) obj.bg_rgba = "rgba(10,12,18,0.55)";
        if (!obj.author_color) obj.author_color = "#93c5fd";
        if (!obj.text_color) obj.text_color = "#e5e7eb";
        if (!obj.font_family) obj.font_family = "Segoe UI";
        return obj;
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
                            Text { text: "bg_rgba"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: cfg ? (cfg.bg_rgba || "") : ""
                                onEditingFinished: {
                                    if (cfg === null) return;
                                    cfg.bg_rgba = text;
                                    _save();
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "author_color"; color: muted; Layout.preferredWidth: 160 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                text: cfg ? (cfg.author_color || "") : ""
                                onEditingFinished: {
                                    if (cfg === null) return;
                                    cfg.author_color = text;
                                    _save();
                                }
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
            }
        }
    }
}

