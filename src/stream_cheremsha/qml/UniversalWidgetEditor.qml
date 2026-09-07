pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    objectName: "universalEditorShell"
    property string instanceName: "Widget instance"
    property string instanceId: ""
    property string typeName: "Widget type"
    property string typeId: ""
    property string saveState: "saved" // saved | dirty | invalid
    property var sections: []
    readonly property color cardBase: "#10141a"
    readonly property color cardEdge: "#242b36"
    readonly property color cardEdgeStrong: "#2d3748"
    readonly property color ink: "#e8eaed"
    readonly property color accent: "#14b8a6"
    readonly property color accentHover: "#0d9488"
    readonly property color accentPress: "#0f766e"
    signal backRequested()
    signal saveRequested()
    signal resetRequested()
    signal copyRequested()
    signal settingChanged(string field, var value)

    component EditorButton: Button {
        id: buttonRoot
        property bool primary: false
        hoverEnabled: true
        implicitHeight: 36
        leftPadding: 14
        rightPadding: 14
        contentItem: Text {
            text: buttonRoot.text
            color: buttonRoot.primary ? "#041615" : root.ink
            font.pixelSize: 12
            font.weight: buttonRoot.primary ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 8
            color: !buttonRoot.enabled ? root.cardBase : (buttonRoot.pressed ? (buttonRoot.primary ? root.accentPress : root.cardEdgeStrong) : (buttonRoot.hovered ? (buttonRoot.primary ? root.accentHover : root.cardEdgeStrong) : (buttonRoot.primary ? root.accent : root.cardBase)))
            border.width: 1
            border.color: buttonRoot.primary && buttonRoot.enabled ? root.accentPress : (buttonRoot.hovered ? root.cardEdgeStrong : root.cardEdge)
            Behavior on color { ColorAnimation { duration: 160 } }
            Behavior on border.color { ColorAnimation { duration: 160 } }
        }
    }

    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0f172a" }
        GradientStop { position: 0.55; color: "#0b1220" }
        GradientStop { position: 1.0; color: "#070910" }
    }
    border.color: "#242b36"
    border.width: 1
    radius: 14

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Control {
            id: editorHeader
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            Layout.minimumHeight: 64
            Layout.maximumHeight: 64
            leftPadding: 32
            rightPadding: 32
            background: Rectangle {
                color: "#10141a"
                border.color: "#242b36"
            }
            contentItem: RowLayout {
                spacing: 16

                EditorButton {
                    text: "←  Віджети"
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 112
                    Layout.minimumWidth: 112
                    Layout.maximumWidth: 112
                    implicitHeight: 34
                    leftPadding: 12
                    rightPadding: 12
                    onClicked: root.backRequested()
                }

                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 1
                    Layout.minimumWidth: 1
                    Layout.maximumWidth: 1
                    Layout.preferredHeight: 26
                    Layout.minimumHeight: 26
                    Layout.maximumHeight: 26
                    color: "#202936"
                }

                ColumnLayout {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 3
                    Text {
                        Layout.fillWidth: true
                        text: root.instanceName
                        color: "#f3f4f6"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.typeName + " · Instance"
                        color: "#8b95a5"
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                }

                Text {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 160
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 190
                    text: root.saveState === "dirty" ? "●  Є незбережені зміни" : root.saveState === "invalid" ? "●  Перевірте поля" : "●  Усі зміни збережено"
                    color: root.saveState === "dirty" ? "#fbbf24" : root.saveState === "invalid" ? "#fb7185" : "#34d399"
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideRight
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 40
                anchors.rightMargin: 40
                anchors.topMargin: 28
                anchors.bottomMargin: 28
                spacing: 40

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 420
                    ScrollView {
                        anchors.fill: parent
                        clip: true
                        ColumnLayout {
                            width: Math.min(720, Math.max(420, parent.width - 20))
                            x: Math.max(0, (parent.width - width) / 2)
                            spacing: 0
                            Text { text: "SETTINGS"; color: "#5eead4"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.4; Layout.bottomMargin: 6 }
                            Text { text: "Only the capabilities provided by this widget type appear here."; color: "#8b95a5"; font.pixelSize: 11; Layout.bottomMargin: 20 }
                            Repeater {
                                model: root.sections
                                delegate: WidgetEditorSection {
                                    id: sectionDelegate
                                    required property var modelData
                                    title: modelData.title
                                    description: modelData.description || ""
                                    icon: modelData.icon || ""
                                    expanded: modelData.expanded !== false
                                    validationState: modelData.validationState || "normal"
                                    Layout.bottomMargin: 24
                                    Repeater {
                                        model: sectionDelegate.modelData.controls || []
                                        delegate: WidgetEditorControl {
                                            required property var modelData
                                            label: modelData.label
                                            description: modelData.description || ""
                                            type: modelData.type || "text"
                                            field: modelData.field || ""
                                             value: modelData.value
                                             options: modelData.options || []
                                             optionLabels: modelData.optionLabels || []
                                             minimum: modelData.minimum || 0
                                            maximum: modelData.maximum || 100
                                            wide: modelData.wide !== undefined ? modelData.wide : ["slider", "textarea", "url", "list", "repeater", "draggable", "file", "image"].indexOf(type) >= 0
                                            onChanged: function(field, value) { root.settingChanged(field, value); root.saveState = "dirty" }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: 360
                    Layout.minimumWidth: 300
                    Layout.maximumWidth: 440
                    spacing: 12
                    Text { text: "PREVIEW"; color: "#8b95a5"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                     Rectangle {
                         Layout.fillWidth: true
                         Layout.preferredHeight: 280
                         Layout.minimumHeight: 240
                         Layout.maximumHeight: 360
                         color: "#0d121a"
                         border.color: "#263241"
                         border.width: 1
                         radius: 12

                         ColumnLayout {
                             anchors.centerIn: parent
                             width: Math.min(parent.width - 48, 300)
                             spacing: 10

                             Rectangle {
                                 Layout.alignment: Qt.AlignHCenter
                                 implicitWidth: 58
                                 implicitHeight: 58
                                 radius: 18
                                 color: "#14b8a61f"
                                 border.color: "#14b8a655"
                                 border.width: 1
                                 Text {
                                     anchors.centerIn: parent
                                     text: "◫"
                                     color: root.accent
                                     font.pixelSize: 30
                                     font.weight: Font.DemiBold
                                 }
                             }

                             Text {
                                 Layout.fillWidth: true
                                 text: "Прев'ю віджета"
                                 color: root.ink
                                 font.pixelSize: 16
                                 font.weight: Font.DemiBold
                                 horizontalAlignment: Text.AlignHCenter
                             }

                             Text {
                                 Layout.fillWidth: true
                                 text: "Відкрити віджет у браузері"
                                 color: "#8b95a5"
                                 font.pixelSize: 11
                                 horizontalAlignment: Text.AlignHCenter
                                 wrapMode: Text.WordWrap
                             }

                             EditorButton {
                                 Layout.alignment: Qt.AlignHCenter
                                 primary: true
                                 text: "Показати прев'ю"
                                 implicitHeight: 40
                                 leftPadding: 20
                                 rightPadding: 20
                                 onClicked: if (api) api.openWidgetInstanceUrl(root.instanceId)
                             }
                         }
                     }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 58
            color: "#10141a"
            border.color: "#242b36"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 32; anchors.rightMargin: 32; spacing: 10
                Item { Layout.fillWidth: true }
                EditorButton { text: "Скинути"; onClicked: root.resetRequested() }
                EditorButton { text: "Скопіювати URL"; onClicked: root.copyRequested() }
                EditorButton { primary: true; text: "Зберегти й застосувати"; enabled: root.saveState !== "invalid"; leftPadding: 16; rightPadding: 16; onClicked: { root.saveRequested(); root.saveState = "saved" } }
            }
        }
    }
}
