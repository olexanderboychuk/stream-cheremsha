import QtQuick

// Premium keycap: DEFAULT / HOVER / PRESSED / FOCUS / DISABLED + hotkey flash.
// Flash via flash() — called when a global hotkey fires.
Rectangle {
    id: root
    property string keyText: "F2"
    property bool empty: keyText === ""
    property bool flashActive: false
    signal clicked()

    implicitWidth: Math.max(40, label.implicitWidth + 18)
    implicitHeight: 28
    radius: 7
    color: !root.enabled ? "#10151f"
        : flashActive ? "#3b2a63"
        : keyMa.containsMouse ? "#232e45" : (empty ? "#141a26" : "#1a2233")
    border.width: 1
    border.color: !root.enabled ? "#232c3f"
        : flashActive ? "#a78bfa"
        : keyMa.containsMouse ? "#8b5cf6" : (empty ? "#2a3142" : "#3b4458")
    Behavior on color { ColorAnimation { duration: 130 } }
    Behavior on border.color { ColorAnimation { duration: 130 } }

    // subtle top highlight + bottom shadow for keycap depth
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 1
        height: 1
        radius: 6
        color: "#14ffffff"
    }
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 1
        height: 2
        radius: 6
        color: "#38000000"
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.empty ? "—" : root.keyText
        color: !root.enabled ? "#4b5568" : (flashActive ? "#ede9fe" : "#e8ecf5")
        font.pixelSize: 12
        font.weight: Font.DemiBold
        Behavior on color { ColorAnimation { duration: 130 } }
    }

    scale: keyMa.pressed ? 0.93 : 1.0
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    function flash() {
        flashActive = true;
        flashTimer.restart();
    }
    Timer {
        id: flashTimer
        interval: 450
        repeat: false
        onTriggered: root.flashActive = false
    }

    MouseArea {
        id: keyMa
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
