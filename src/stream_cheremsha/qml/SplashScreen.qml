import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 640
    height: 360
    color: "#0a0b0e"
    radius: 18
    clip: true

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: root.radius - 1
        color: "#0a0b0e"
        border.width: 1
        border.color: "#2a3142"
    }

    Image {
        id: splash
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        smooth: true
        mipmap: true
        source: Qt.resolvedUrl("../assets/splash_screen.png")
    }

    Rectangle {
        anchors.fill: parent
        color: "#0a0b0e"
        opacity: 0.20
    }

    Rectangle {
        id: loadingPill
        anchors.left: parent.left
        anchors.leftMargin: 18
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        radius: 14
        color: "#0b0f18"
        opacity: 0.72
        border.width: 1
        border.color: "#2a3142"

        width: 170
        height: 44

        Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

        Item {
            id: content
            anchors.fill: parent
            anchors.margins: 10

            Row {
                id: row
                anchors.centerIn: parent
                spacing: 10

                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: "#93c5fd"
                    opacity: 0.9
                }

                Text {
                    text: "Loading…"
                    color: "#f1f5f9"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    verticalAlignment: Text.AlignVCenter
                    style: Text.Outline
                    styleColor: "#000000"
                }
            }
        }
    }

}
