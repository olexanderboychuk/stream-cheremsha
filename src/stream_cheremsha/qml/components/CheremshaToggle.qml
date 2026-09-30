import QtQuick
import QtQuick.Controls

// Compact Cheremsha toggle: label + sliding switch.
// States: checked/unchecked x hover/pressed/disabled.
Item {
    id: root
    property string label: ""
    property bool checked: false
    signal toggled(bool isOn)
    implicitWidth: row.implicitWidth
    implicitHeight: 26

    Row {
        id: row
        spacing: 8
        anchors.verticalCenter: parent.verticalCenter
        Text {
            text: root.label
            color: root.enabled ? "#9aa4b8" : "#4b5568"
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            id: track
            width: 36
            height: 20
            radius: 10
            anchors.verticalCenter: parent.verticalCenter
            color: !root.enabled ? "#141a26"
                : root.checked ? (togMa.containsMouse ? "#7c3aed" : "#8b5cf6") : (togMa.containsMouse ? "#2a3a56" : "#232d42")
            border.width: 1
            border.color: root.checked ? "#a78bfa" : "#3a4560"
            Behavior on color { ColorAnimation { duration: 130 } }
            Rectangle {
                y: 2
                x: root.checked ? 18 : 2
                width: 16
                height: 16
                radius: 8
                color: root.enabled ? "white" : "#5b6472"
                scale: togMa.pressed ? 0.88 : 1.0
                Behavior on x { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: 100 } }
            }
            MouseArea {
                id: togMa
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                enabled: root.enabled
                onClicked: { root.checked = !root.checked; root.toggled(root.checked); }            }
        }
        Text {
            text: root.checked ? "ON" : "OFF"
            color: root.checked ? "#a78bfa" : "#5b6472"
            font.pixelSize: 10
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
