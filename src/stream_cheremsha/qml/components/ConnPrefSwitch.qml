import QtQuick
import QtQuick.Controls

Switch {
    id: prefSw
    padding: 0
    implicitWidth: 46
    implicitHeight: 24
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    transformOrigin: Item.Right
    scale: prefSw.hovered ? 1.06 : 1.0
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

    indicator: Rectangle {
        width: prefSw.implicitWidth
        height: prefSw.implicitHeight
        radius: 12
        color: prefSw.checked ? "#134e4a" : "#252d3d"
        border.width: 1
        border.color: prefSw.checked ? "#14b8a6" : "#3b4a63"
        opacity: prefSw.enabled ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 3
            x: prefSw.checked ? (parent.width - width - 3) : 3
            color: prefSw.checked ? "#e8eaed" : "#52607a"
            border.width: 1
            border.color: prefSw.checked ? "#cbd5e1" : "#3d4a60"
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Item {}
}
