import QtQuick
import QtQuick.Controls

// Cheremsha circular play/stop button — SVG only, no unicode glyphs.
// States: default / hover (purple accent) / pressed (compress) / playing / loading / disabled.
// `accented` highlights the button while its parent row is hovered, so the
// whole row reads as one interactive surface.
Button {
    id: root
    property bool playing: false
    property bool accented: false
    // Audio is being resolved/downloaded/cached — shows a spinner; clicking cancels.
    property bool loading: false
    property int diameter: 38
    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    focusPolicy: Qt.NoFocus

    contentItem: Item {
        Image {
            anchors.centerIn: parent
            source: Qt.resolvedUrl("../../assets/icons/" + (root.playing ? "stop_cyan.svg" : "play_cyan.svg"))
            width: root.playing ? 13 : 14
            height: root.playing ? 13 : 14
            anchors.horizontalCenterOffset: (!root.playing && !root.loading) ? 1 : 0
            visible: !root.loading
            opacity: root.enabled ? 1.0 : 0.4
        }
        Image {
            id: loadSpinner
            anchors.centerIn: parent
            width: 16; height: 16
            source: Qt.resolvedUrl("../../assets/icons/spinner.svg")
            visible: root.loading
            RotationAnimation {
                target: loadSpinner
                from: 0; to: 360
                duration: 900
                easing.type: Easing.Linear
                running: root.loading
            }
        }
    }
    background: Rectangle {
        radius: diameter / 2
        // Loading keeps the dark accent fill so the purple spinner stays visible.
        color: !root.enabled ? "#141a26"
            : root.playing ? "#8b5cf6"
            : root.pressed ? "#6d28d9"
            : (root.loading || root.hovered || root.accented) ? "#2a1f4d" : "#1a2233"
        border.width: 1
        border.color: !root.enabled ? "#232c3f"
            : root.playing ? "#c4b5fd"
            : (root.loading || root.hovered || root.accented) ? "#8b5cf6" : "#3b4458"
        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }
    scale: root.pressed ? 0.94 : (root.hovered ? 1.05 : 1.0)
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
}
