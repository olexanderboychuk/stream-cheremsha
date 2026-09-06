import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// Cheremsha — Platforms control center (config left, analytics right)
Item {
    id: root
    anchors.fill: parent

    property bool platformCardsHidden: false
    Component.onCompleted: if (api) platformCardsHidden = api.platformCardsHiddenGet()
    onPlatformCardsHiddenChanged: if (api) api.platformCardsHiddenSet(platformCardsHidden)

    Rectangle {
        anchors.fill: parent
        color: ConnTheme.base
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0d111a" }
            GradientStop { position: 0.55; color: "#0b0e14" }
            GradientStop { position: 1.0; color: "#080a0f" }
        }
    }

    ColumnLayout {
        id: pageCol
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 12
        anchors.topMargin: 10
        anchors.bottomMargin: 6
        spacing: 8

        // ---- Compact page header ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 1
                Text {
                    text: {
                        if (!api) return "Платформи"
                        api.refreshCounter
                        return api.loc("connections.page_title")
                    }
                    color: ConnTheme.ink
                    font.pixelSize: 20
                    font.bold: true
                    font.letterSpacing: 0.15
                }
                Text {
                    text: {
                        if (!api) return ""
                        api.refreshCounter
                        return api.loc("connections.page_subtitle")
                    }
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: sysRow.implicitWidth + 16
                implicitHeight: 28
                radius: 999
                color: "#0f1f18"
                border.width: 1
                border.color: "#1a3d2a"

                RowLayout {
                    id: sysRow
                    anchors.centerIn: parent
                    spacing: 6
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: "#22c55e"
                        Layout.alignment: Qt.AlignVCenter
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation { from: 1.0; to: 0.4; duration: 1000; easing.type: Easing.InOutSine }
                            NumberAnimation { from: 0.4; to: 1.0; duration: 1000; easing.type: Easing.InOutSine }
                        }
                    }
                    Text {
                        text: {
                            if (!api) return ""
                            api.refreshCounter
                            return api.loc("connections.system_ok")
                        }
                        color: "#86efac"
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
            }

            Rectangle {
                Layout.alignment: Qt.AlignVCenter
                visible: analyticsSlot._anyPanelEnabled
                implicitWidth: liveRow.implicitWidth + 14
                implicitHeight: 28
                radius: 999
                color: "#2a1216"
                border.width: 1
                border.color: "#4a1d24"
                RowLayout {
                    id: liveRow
                    anchors.centerIn: parent
                    spacing: 5
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: "#ef4444"
                        Layout.alignment: Qt.AlignVCenter
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation { from: 1.0; to: 0.25; duration: 700 }
                            NumberAnimation { from: 0.25; to: 1.0; duration: 700 }
                        }
                    }
                    Text {
                        text: {
                            if (!api) return "LIVE"
                            api.refreshCounter
                            return api.loc("connections.live")
                        }
                        color: "#fca5a5"
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 0.8
                    }
                }
            }
        }

        // ---- Workspace ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                id: row
                anchors.fill: parent
                spacing: 0

                // LEFT: configuration ~38%
                Item {
                    id: leftPane
                    property real _targetW: Math.min(440, Math.max(300, row.width * 0.37))
                    property real _animW: root.platformCardsHidden ? 0 : _targetW
                    Layout.preferredWidth: _animW
                    Layout.minimumWidth: 0
                    Layout.maximumWidth: _animW
                    Layout.fillHeight: true
                    opacity: root.platformCardsHidden ? 0.0 : 1.0
                    clip: true
                    Behavior on _animW { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                    Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.rightMargin: 6
                        spacing: 6

                        Text {
                            text: {
                                if (!api) return ""
                                api.refreshCounter
                                return api.loc("connections.section_platforms")
                            }
                            color: ConnTheme.muted
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.7
                            font.capitalization: Font.AllUppercase
                        }

                        ScrollView {
                            id: leftScroll
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentWidth: availableWidth
                            background: Item {}
                            ScrollBar.vertical: ScrollBar {
                                width: 7
                                policy: ScrollBar.AsNeeded
                                background: Rectangle {
                                    implicitWidth: 7
                                    radius: 3
                                    color: "#0f1219"
                                }
                                contentItem: Rectangle {
                                    implicitWidth: 4
                                    radius: 2
                                    color: parent.pressed ? ConnTheme.neonCyan : (parent.hovered ? "#52607a" : "#3d4a60")
                                }
                            }

                            PlatformCardsPanel {
                                id: col
                                width: Math.max(1, leftScroll.availableWidth - 2)
                                compact: false
                                spacing: 8
                            }
                        }
                    }
                }

                // Divider + collapse
                Item {
                    id: splitter
                    Layout.preferredWidth: 24
                    Layout.fillHeight: true
                    visible: analyticsSlot._anyPanelEnabled || !root.platformCardsHidden

                    Rectangle {
                        id: splitLine
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 20
                        anchors.bottomMargin: 20
                        width: 1
                        color: splitHover.containsMouse ? "#3a455c" : "#1e2636"
                        Behavior on color { ColorAnimation { duration: 140 } }
                    }

                    MouseArea {
                        id: splitHover
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }

                    SideCollapseHandle {
                        anchors.centerIn: parent
                        collapsed: root.platformCardsHidden
                        accent: splitHover.containsMouse ? ConnTheme.neonViolet : "#52607a"
                        onToggled: root.platformCardsHidden = !root.platformCardsHidden
                    }
                }

                // RIGHT: analytics
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 6

                    Text {
                        text: {
                            if (!api) return ""
                            api.refreshCounter
                            return api.loc("connections.section_analytics")
                        }
                        color: ConnTheme.muted
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.7
                        font.capitalization: Font.AllUppercase
                    }

                    AnalyticsPanel {
                        id: analyticsSlot
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        fillHeight: false
                        alwaysVisible: false
                        footerReserve: {
                            if (!root.platformCardsHidden) return 0
                            if (!api) return 0
                            api.refreshCounter
                            return Math.max(0, api.footerHeightPx || 0)
                        }
                        _visibilityWide: root.platformCardsHidden || (row.width > (leftPane._animW + 160))
                    }

                    Rectangle {
                        visible: !analyticsSlot._anyPanelEnabled
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.maximumHeight: 220
                        Layout.alignment: Qt.AlignTop
                        radius: ConnTheme.cardRadius
                        color: ConnTheme.cardBase
                        border.width: 1
                        border.color: ConnTheme.cardEdge

                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            width: Math.min(320, parent.width - 40)

                            Rectangle {
                                width: 36
                                height: 36
                                radius: 18
                                anchors.horizontalCenter: parent.horizontalCenter
                                color: "#151b27"
                                border.width: 1
                                border.color: ConnTheme.cardEdge
                                Text {
                                    anchors.centerIn: parent
                                    text: "◎"
                                    color: ConnTheme.muted
                                    font.pixelSize: 16
                                    opacity: 0.7
                                }
                            }
                            Text {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: {
                                    if (!api) return ""
                                    api.refreshCounter
                                    return api.loc("connections.events_empty")
                                }
                                color: ConnTheme.ink
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                opacity: 0.85
                            }
                            Text {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.Wrap
                                text: {
                                    if (!api) return ""
                                    api.refreshCounter
                                    return api.loc("connections.analytics_empty")
                                }
                                color: ConnTheme.muted
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }
        }
    }
}
