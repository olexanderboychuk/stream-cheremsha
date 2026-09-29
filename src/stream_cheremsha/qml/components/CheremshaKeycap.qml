import QtQuick

Rectangle {
    id: root
    property string keyText: "F2"
    property bool empty: keyText === ""
    implicitWidth: Math.max(34, label.implicitWidth + 14)
    implicitHeight: 24
    radius: 6
    color: empty ? "#141a26" : "#1c2434"
    border.width: 1
    border.color: empty ? "#2a3142" : "#3b4458"

    Text {
        id: label
        anchors.centerIn: parent
        text: root.empty ? "—" : root.keyText
        color: "#e8eaed"
        font.pixelSize: 12
        font.bold: true
    }
}
