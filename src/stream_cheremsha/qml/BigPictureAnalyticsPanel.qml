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
        title: { if (!api) return "Analytics"; api.refreshCounter; return api.loc("ui.big_picture_analytics") }

        AnalyticsPanel {
            anchors.fill: parent
            bigPictureMode: true
            alwaysVisible: true
            fillHeight: true
            footerReserve: 0
        }
    }
}
