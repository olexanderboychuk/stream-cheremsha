import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: "#080a0f"
    }

    BpSection {
        anchors.fill: parent
        anchors.margins: 10
        title: { if (!api) return "Platforms"; api.refreshCounter; return api.loc("ui.big_picture_platforms") }

        ScrollView {
            anchors.fill: parent
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            Item {
                width: parent.width
                implicitHeight: platforms.implicitHeight

                PlatformCardsPanel {
                    id: platforms
                    width: Math.min(parent.width, 420)
                    x: Math.max(0, (parent.width - width) / 2)
                    compact: true
                }
            }
        }
    }
}
