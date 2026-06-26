import QtQuick
import QtQuick.Controls

import components

Item {
    id: sh
    property bool collapsed: false
    property color accent: ConnTheme.twBar
    signal toggled()

    implicitWidth: 26
    implicitHeight: 110

    Rectangle {
        anchors.fill: parent
        radius: 999
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.08)
        color: tap.pressed ? "#182033" : (tap.containsMouse ? "#1c263c" : "#151b27")
        scale: tap.pressed ? 0.98 : (tap.containsMouse ? 1.03 : 1.0)
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: 140 } }
    }

    Text {
        anchors.centerIn: parent
        text: sh.collapsed ? "❯" : "❮"
        color: ConnTheme.ink
        font.pixelSize: 18
        scale: tap.pressed ? 0.92 : 1.0
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        id: tap
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: sh.toggled()
    }
}
