import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

ColumnLayout {
    id: root
    property string title: ""
    default property alias content: body.data

    spacing: 8

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 38
        radius: 10
        color: "#151b27"
        border.width: 1
        border.color: "#2a3142"

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 14
            text: root.title
            color: ConnTheme.ink
            font.pixelSize: 13
            font.weight: Font.DemiBold
            font.letterSpacing: 0.4
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: 12
        color: "#0c0f16"
        border.width: 1
        border.color: "#2a3142"
        clip: true

        Item {
            id: body
            anchors.fill: parent
            anchors.margins: 6
        }
    }
}
