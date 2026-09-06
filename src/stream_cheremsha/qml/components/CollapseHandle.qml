import QtQuick
import QtQuick.Controls

import components

Item {
    id: h
    property bool collapsed: false
    property color accent: ConnTheme.twBar
    signal toggled()

    implicitWidth: 26
    implicitHeight: 26

    readonly property color _bgRest: "#151b27"
    readonly property color _bgHover: "#1a2232"
    readonly property color _bgPress: "#212b40"

    Rectangle {
        id: pill
        anchors.fill: parent
        radius: 999
        border.width: 1
        border.color: tap.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
        color: tap.pressed ? h._bgPress : (tap.containsMouse ? h._bgHover : h._bgRest)
        scale: tap.pressed ? 0.96 : (tap.containsMouse ? 1.05 : 1.0)
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    Item {
        id: chev
        width: 14
        height: 10
        anchors.centerIn: parent
        rotation: h.collapsed ? 0 : 180
        transformOrigin: Item.Center
        Behavior on rotation { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        scale: tap.pressed ? 0.9 : 1.0
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

        Rectangle {
            width: 9
            height: 2
            radius: 1
            color: ConnTheme.ink
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.horizontalCenterOffset: -3
            rotation: 45
            antialiasing: true
        }
        Rectangle {
            width: 9
            height: 2
            radius: 1
            color: ConnTheme.ink
            anchors.verticalCenter: parent.verticalCenter
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.horizontalCenterOffset: 3
            rotation: -45
            antialiasing: true
        }
    }

    MouseArea {
        id: tap
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: h.toggled()
    }
}
