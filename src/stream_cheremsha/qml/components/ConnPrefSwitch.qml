import QtQuick
import QtQuick.Controls

Switch {
    id: prefSw
    padding: 0
    implicitWidth: 44
    implicitHeight: 24
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    transformOrigin: Item.Right
    scale: prefSw.hovered ? 1.04 : 1.0
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

    indicator: Rectangle {
        width: prefSw.implicitWidth
        height: prefSw.implicitHeight
        radius: 12
        color: prefSw.checked ? "#3b1d7a" : "#1a2030"
        border.width: 1
        border.color: prefSw.checked ? "#8b5cf6" : "#334155"
        opacity: prefSw.enabled ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 3
            x: prefSw.checked ? (parent.width - width - 3) : 3
            color: prefSw.checked ? "#ede9fe" : "#64748b"
            border.width: 1
            border.color: prefSw.checked ? "#c4b5fd" : "#475569"
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Item {}
}
