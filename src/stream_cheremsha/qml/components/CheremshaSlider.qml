import QtQuick
import QtQuick.Controls

// Cheremsha slider: dark track, purple fill, circular accent handle.
// States: default / hover (handle brightens) / pressed (handle enlarges) /
// focus (cyan ring) / disabled. Emits the standard valueChanged signal for
// EVERY change (drag, track click, wheel, keyboard) — parents must bind
// `value:` and react in onValueChanged, never onMoved (drag-only).
Slider {
    id: root
    property color fillColor: "#8b5cf6"
    from: 0.0
    to: 1.0
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    implicitHeight: 22

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 6
        radius: 3
        color: "#1c2434"
        border.width: 1
        border.color: root.visualFocus ? "#22d3ee" : "#232d42"
        Behavior on border.color { ColorAnimation { duration: 120 } }
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 3
            color: root.enabled ? root.fillColor : "#3b4458"
        }
    }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.pressed ? 17 : (root.hovered || root.visualFocus ? 15 : 13)
        height: width
        radius: width / 2
        color: !root.enabled ? "#3b4458" : (root.hovered || root.pressed || root.visualFocus ? "#c4b5fd" : "#a78bfa")
        border.width: 1
        border.color: "#6d28d9"
        Behavior on width { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
