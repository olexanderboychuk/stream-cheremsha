import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// Cheremsha — Platforms control center (config left ~35%, analytics right ~65%)
Item {
    id: root
    anchors.fill: parent

    property bool platformCardsHidden: false
    Component.onCompleted: if (api) platformCardsHidden = api.platformCardsHiddenGet()
    onPlatformCardsHiddenChanged: if (api) api.platformCardsHiddenSet(platformCardsHidden)

    // Micro entrance transition, retriggered by MainWindow (enterPulse toggle)
    // on every cached navigation. GPU-cheap root opacity only, 120ms.
    property bool enterPulse: false
    onEnterPulseChanged: enterFade.restart()
    NumberAnimation {
        id: enterFade
        target: root
        property: "opacity"
        from: 0.97
        to: 1.0
        duration: 120
        easing.type: Easing.OutCubic
    }

    // Lightweight stream clock for the reference header (single 1s timer, text only).
    property int _streamSecs: 0
    function _fmtClock(s) {
        var h = Math.floor(s / 3600)
        var m = Math.floor((s % 3600) / 60)
        var ss = s % 60
        function p(n) { return (n < 10 ? "0" : "") + n }
        return p(h) + ":" + p(m) + ":" + p(ss)
    }
    Timer {
        id: streamClock
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            var anyOn = analyticsSlot ? analyticsSlot._anyPanelEnabled : false
            if (anyOn) root._streamSecs += 1
            else if (root._streamSecs !== 0) root._streamSecs = 0
        }
    }

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
        anchors.leftMargin: ConnTheme.pageOuter
        anchors.rightMargin: ConnTheme.pageOuter
        anchors.topMargin: 16
        anchors.bottomMargin: 12
        spacing: 12

        // ---- Dual page headers (left over platform column, right over analytics) ----
        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            spacing: 0

            // LEFT header — matches left pane width (gutter aligns with splitter)
            Item {
                id: leftHeader
                Layout.preferredWidth: leftPane._animW
                Layout.minimumWidth: 0
                Layout.maximumWidth: leftPane._animW
                Layout.preferredHeight: 52
                visible: !root.platformCardsHidden
                clip: true

                ColumnLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text {
                        text: {
                            if (!api) return "Підключення платформ"
                            api.refreshCounter
                            var v = api.loc("connections.page_title")
                            return v && v.length ? v : "Підключення платформ"
                        }
                        color: ConnTheme.ink
                        font.pixelSize: ConnTheme.titlePx
                        font.bold: true
                        font.letterSpacing: 0.1
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        text: {
                            if (!api) return ""
                            api.refreshCounter
                            return api.loc("connections.page_subtitle")
                        }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }

            // Splitter gutter alignment
            Item {
                Layout.preferredWidth: 20
                Layout.preferredHeight: 52
                visible: !root.platformCardsHidden
            }

            // RIGHT header
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    Text {
                        text: {
                            if (!api) return "Аналітика в реальному часі"
                            api.refreshCounter
                            var v = api.loc("connections.analytics_title")
                            if (!v || !v.length) v = api.loc("connections.section_analytics")
                            return v && v.length ? v : "Аналітика в реальному часі"
                        }
                        color: ConnTheme.ink
                        font.pixelSize: ConnTheme.titlePx
                        font.bold: true
                        font.letterSpacing: 0.1
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        text: {
                            if (!api) return ""
                            api.refreshCounter
                            return api.loc("connections.analytics_subtitle")
                        }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                // LIVE badge — compact rounded capsule, red accent
                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    visible: analyticsSlot._anyPanelEnabled
                    implicitWidth: liveRow.implicitWidth + 20
                    implicitHeight: 30
                    radius: 999
                    color: ConnTheme.liveBg
                    border.width: 1
                    border.color: ConnTheme.liveEdge
                    RowLayout {
                        id: liveRow
                        anchors.centerIn: parent
                        spacing: 7
                        Rectangle {
                            width: 7
                            height: 7
                            radius: 4
                            color: "#ef4444"
                            Layout.alignment: Qt.AlignVCenter
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { from: 1.0; to: 0.25; duration: 700 }
                                NumberAnimation { from: 0.25; to: 1.0; duration: 700 }
                            }
                        }
                        Text {
                            text: "LIVE"
                            color: ConnTheme.liveFg
                            font.pixelSize: 12
                            font.bold: true
                            font.letterSpacing: 0.8
                        }
                    }
                }

                // Stream duration — visually secondary
                ColumnLayout {
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 1
                    Text {
                        Layout.alignment: Qt.AlignRight
                        text: root._fmtClock(root._streamSecs)
                        color: ConnTheme.ink
                        font.pixelSize: 19
                        font.bold: true
                        font.family: "Consolas, Cascadia Mono, monospace"
                    }
                    Text {
                        Layout.alignment: Qt.AlignRight
                        text: {
                            if (!api) return "Час стріму"
                            api.refreshCounter
                            return api.loc("connections.stream_time")
                        }
                        color: ConnTheme.muted
                        font.pixelSize: 10
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

                // LEFT: configuration ~37% (wide enough for the summary toggle row)
                Item {
                    id: leftPane
                    property real _targetW: Math.min(460, Math.max(330, row.width * 0.37))
                    property real _animW: root.platformCardsHidden ? 0 : _targetW
                    Layout.preferredWidth: _animW
                    Layout.minimumWidth: 0
                    Layout.maximumWidth: _animW
                    Layout.fillHeight: true
                    opacity: root.platformCardsHidden ? 0.0 : 1.0
                    clip: true
                    Behavior on _animW { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                    Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

                    ScrollView {
                        id: leftScroll
                        anchors.fill: parent
                        // Right inset: breathing room between cards and divider.
                        anchors.rightMargin: 10
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
                            spacing: ConnTheme.cardGap
                        }
                    }
                }

                // Divider + collapse — 1px vertical divider with centered handle
                Item {
                    id: splitter
                    Layout.preferredWidth: 20
                    Layout.fillHeight: true
                    visible: true

                    Rectangle {
                        id: splitLine
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 8
                        anchors.bottomMargin: 8
                        width: 1
                        color: splitHover.containsMouse ? "#3a455c" : ConnTheme.divider
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

                // RIGHT: analytics (~65%)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    AnalyticsPanel {
                        id: analyticsSlot
                        anchors.fill: parent
                        // Left inset: breathing room between divider and content.
                        anchors.leftMargin: 10
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
                        anchors.fill: parent
                        anchors.leftMargin: 10
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
