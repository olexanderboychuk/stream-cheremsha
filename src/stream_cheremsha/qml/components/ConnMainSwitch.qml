import QtQuick
import QtQuick.Controls

Switch {
    id: mainSw
    padding: 0
    implicitWidth: 44
    implicitHeight: 24
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    transformOrigin: Item.Right
    scale: mainSw.hovered ? 1.04 : 1.0
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

    indicator: Rectangle {
        width: mainSw.implicitWidth
        height: mainSw.implicitHeight
        radius: 12
        color: mainSw.checked ? "#4c1d95" : "#1a2030"
        border.width: 1
        border.color: mainSw.checked ? "#a78bfa" : "#334155"
        opacity: mainSw.enabled ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 3
            x: mainSw.checked ? (parent.width - width - 3) : 3
            color: mainSw.checked ? "#f5f3ff" : "#64748b"
            border.width: 1
            border.color: mainSw.checked ? "#ddd6fe" : "#475569"
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Item {}
}
