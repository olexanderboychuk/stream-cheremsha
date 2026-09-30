import QtQuick
import QtQuick.Controls

// Category chip: default / hover / pressed / active(glow) / focus / disabled.
Button {
    id: root
    property bool active: false
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    font.pixelSize: 12
    font.weight: Font.Medium
    implicitHeight: 30
    implicitWidth: Math.max(52, chipText.implicitWidth + 28)

    contentItem: Text {
        id: chipText
        text: root.text
        color: !root.enabled ? "#4b5568" : (root.active ? "#ffffff" : (root.hovered ? "#e8ecf5" : "#9aa4b8"))
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 15
        color: !root.enabled ? "#0e1420"
            : root.active ? "#8b5cf6"
            : root.pressed ? "#232e45" : (root.hovered ? "#1a2233" : "#00101624")
        border.width: 1
        border.color: !root.enabled ? "#232c3f"
            : root.active ? "#a78bfa"
            : root.visualFocus ? "#22d3ee"
            : root.hovered ? "#4b5876" : "#2a3348"
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on border.color { ColorAnimation { duration: 130 } }
    }
    scale: root.pressed ? 0.96 : 1.0
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
}
