import QtQuick
import QtQuick.Layouts

import components

Item {
    id: badge
    property string kind: "disabled" // connected | attention | error | disabled | live
    property string label: ""

    readonly property color _dot: {
        if (kind === "live") return "#ef4444"
        if (kind === "connected") return "#22c55e"
        if (kind === "attention") return "#eab308"
        if (kind === "error") return "#ef4444"
        return "#64748b"
    }
    readonly property color _fg: {
        if (kind === "live") return "#fca5a5"
        if (kind === "connected") return "#86efac"
        if (kind === "attention") return "#fde047"
        if (kind === "error") return "#fca5a5"
        return "#94a3b8"
    }
    readonly property color _bg: {
        if (kind === "live") return "#2a1414"
        if (kind === "connected") return "#0f2a1c"
        if (kind === "attention") return "#2a2410"
        if (kind === "error") return "#2a1414"
        return "#161b24"
    }
    readonly property color _bor: {
        if (kind === "live") return "#7f1d1d"
        if (kind === "connected") return "#1a3d2a"
        if (kind === "attention") return "#3d3518"
        if (kind === "error") return "#3d1c1c"
        return "#252b38"
    }

    implicitWidth: row.implicitWidth + 12
    implicitHeight: 22

    Rectangle {
        anchors.fill: parent
        radius: 999
        color: badge._bg
        border.width: 1
        border.color: badge._bor
    }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            width: 7
            height: 7
            radius: 4
            color: badge._dot
            Layout.alignment: Qt.AlignVCenter

            SequentialAnimation on opacity {
                running: badge.kind === "connected" || badge.kind === "live"
                loops: Animation.Infinite
                NumberAnimation { from: 1.0; to: 0.45; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.45; to: 1.0; duration: 900; easing.type: Easing.InOutSine }
            }
        }

        Text {
            text: badge.label
            color: badge._fg
            font.pixelSize: 11
            font.weight: Font.DemiBold
            Layout.alignment: Qt.AlignVCenter
        }
    }
}
