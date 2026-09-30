import QtQuick
import QtQuick.Controls

// Cheremsha circular play/stop button — SVG only, no unicode glyphs.
// States: default / hover (purple glow) / pressed (compress) / playing / disabled.
Button {
    id: root
    property bool playing: false
    property int diameter: 38
    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    focusPolicy: Qt.NoFocus

    contentItem: Image {
        source: Qt.resolvedUrl("../../assets/icons/" + (root.playing ? "stop.svg" : "play.svg"))
        width: root.playing ? 13 : 14
        height: root.playing ? 13 : 14
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: (!root.playing) ? 1 : 0
        opacity: root.enabled ? 1.0 : 0.4
    }
    background: Rectangle {
        radius: diameter / 2
        color: !root.enabled ? "#141a26"
            : root.playing ? "#8b5cf6"
            : root.pressed ? "#6d28d9"
            : root.hovered ? "#2a1f4d" : "#1a2233"
        border.width: 1
        border.color: !root.enabled ? "#232c3f"
            : root.playing ? "#c4b5fd"
            : root.hovered ? "#8b5cf6" : "#3b4458"
        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }
    scale: root.pressed ? 0.9 : (root.hovered ? 1.05 : 1.0)
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
}
