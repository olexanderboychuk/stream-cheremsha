import QtQuick

Rectangle {
    id: root
    width: 640
    height: 360
    color: "#0a0b0e"
    radius: 18
    clip: true

    // Startup phase text, set from Python via l10n (splash.* keys).
    property string statusText: "Завантаження…"
    // 0.0–1.0 warm-up progress; -1 hides the bar (indeterminate state).
    property real progress: -1

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
        opacity: 0.88
        border.width: 1
        border.color: "#2a3142"

        width: 300
        height: 64

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Row {
                id: row
                spacing: 10

                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: "#14b8a6"
                    opacity: 0.95
                }

                Text {
                    text: root.statusText
                    color: "#f1f5f9"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    width: loadingPill.width - 52
                    style: Text.Outline
                    styleColor: "#000000"
                }
            }

            // App-styled progress track (teal accent #14b8a6, as in WidgetsView).
            Rectangle {
                id: track
                width: parent.width
                height: 6
                radius: 3
                color: "#1c2536"
                visible: root.progress >= 0
                clip: true

                Rectangle {
                    id: fill
                    height: parent.height
                    radius: parent.radius
                    width: parent.width * Math.min(1, Math.max(0, root.progress))
                    color: "#14b8a6"

                    Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                }
            }
        }
    }
}
