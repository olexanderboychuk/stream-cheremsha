import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Content-area empty state: connected to the grid, with drag drop-zone feedback.
Rectangle {
    id: root
    signal addRequested()
    property bool dragHover: false
    implicitWidth: 500
    implicitHeight: 260
    radius: 14
    color: dragHover ? "#161d33" : "#111728"
    border.width: 1
    border.color: dragHover ? "#8b5cf6" : "#26314a"
    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 10
        Item {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 56
            Layout.preferredHeight: 56
            Rectangle {
                anchors.fill: parent
                radius: 14
                color: "#8b5cf6"
                opacity: 0.14
            }
            Image {
                id: emptyIcon
                anchors.centerIn: parent
                source: Qt.resolvedUrl("../../assets/icons/web_music.svg")
                width: 28; height: 28
                scale: root.dragHover ? 1.06 : 1.0
                Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            }
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: spApi.strings.empty_title || "Soundpad порожній"
            color: "#e8ecf5"
            font.pixelSize: 19
            font.weight: Font.DemiBold
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: root.dragHover ? (spApi.strings.empty_drag || "Перетягніть файл сюди")
                                : (spApi.strings.empty_hint || "Додайте перший звук або перетягніть аудіофайл сюди")
            color: root.dragHover ? "#c4b5fd" : "#7f8aa3"
            font.pixelSize: 13
            font.weight: root.dragHover ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignHCenter
            Behavior on color { ColorAnimation { duration: 150 } }
        }
        Button {
            Layout.alignment: Qt.AlignHCenter
            text: spApi.strings.add_button || "+ Додати звук"
            hoverEnabled: true
            focusPolicy: Qt.TabFocus
            font.pixelSize: 13
            font.bold: true
            implicitWidth: 170
            implicitHeight: 38
            contentItem: Text {
                text: parent.text
                color: "white"
                font: parent.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 9
                gradient: Gradient {
                    GradientStop { position: 0.0; color: parent.hovered ? "#9d71f7" : "#8b5cf6" }
                    GradientStop { position: 1.0; color: parent.hovered ? "#8b5cf6" : "#7c3aed" }
                }
                border.width: 1
                border.color: parent.hovered ? "#a78bfa" : "#8b54f5"
            }
            onClicked: root.addRequested()
        }
    }
}
