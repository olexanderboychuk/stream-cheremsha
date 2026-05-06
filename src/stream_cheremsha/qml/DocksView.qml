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

    Loader {
        id: apiGate
        anchors.fill: parent
        active: typeof dockApi !== "undefined" && dockApi !== null
        sourceComponent: gatedUi
    }

    Text {
        anchors.centerIn: parent
        visible: !apiGate.active
        text: "Docks API is not available yet."
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
                implicitHeight: head.implicitHeight + 20

                ColumnLayout {
                    id: head
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "Доки"
                        color: ink
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "OBS Dock / Browser panel URL"
                        color: muted
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: cardBase
                border.width: 1
                border.color: cardEdge
                implicitHeight: body.implicitHeight + 20

                ColumnLayout {
                    id: body
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "MultiChat (read-only)"
                        color: ink
                        font.pixelSize: 16
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
                            text: dockApi ? dockApi.multichatDockUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (dockApi) dockApi.copyMultichatDockUrl()
                        }

                        PillButton {
                            text: "Назад"
                            onClicked: if (typeof navApi !== "undefined" && navApi) navApi.goHome()
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
                implicitHeight: actBody.implicitHeight + 20

                ColumnLayout {
                    id: actBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "Активність"
                        color: ink
                        font.pixelSize: 16
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
                            text: dockApi ? dockApi.activityDockUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (dockApi) dockApi.copyActivityDockUrl()
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
                implicitHeight: onlineBody.implicitHeight + 20

                ColumnLayout {
                    id: onlineBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "Онлайн"
                        color: ink
                        font.pixelSize: 16
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
                            text: dockApi ? dockApi.onlineDockUrlValue : ""
                        }

                        PillButton {
                            text: "Скопіювати URL"
                            onClicked: if (dockApi) dockApi.copyOnlineDockUrl()
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}

