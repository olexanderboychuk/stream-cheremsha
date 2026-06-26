import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// stream-cheremsha — connection cards (dark glass, brand headers, stream toggles)
Item {
    id: root
    anchors.fill: parent

    property bool platformCardsHidden: false

    readonly property int footerPad: root.platformCardsHidden ? 102 : 0

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    ScrollView {
        id: sc
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        background: Item {}

        ScrollBar.vertical: ScrollBar {
            width: 10
            policy: ScrollBar.AsNeeded
            background: Rectangle {
                implicitWidth: 10
                radius: 5
                color: "#0f1219"
                border.width: 1
                border.color: "#1e2430"
            }
            contentItem: Rectangle {
                implicitWidth: 6
                radius: 4
                color: parent.pressed ? "#0d9488" : (parent.hovered ? "#52607a" : "#3d4a60")
            }
        }

        Item {
            id: scInner
            width: root.width
            implicitHeight: root.platformCardsHidden
                ? Math.max(1, sc.availableHeight)
                : (Math.max(col.implicitHeight, analyticsSlot.implicitHeight) + 24)
            height: root.platformCardsHidden ? Math.max(1, sc.availableHeight) : implicitHeight
            readonly property int _viewportH: Math.max(1, sc.availableHeight - root.footerPad)

            states: [
                State {
                    name: "platformsHidden"
                    when: root.platformCardsHidden
                    PropertyChanges { target: scInner; height: scInner._viewportH; implicitHeight: scInner._viewportH }
                }
            ]

            RowLayout {
                id: row
                width: Math.max(1, scInner.width - 32)
                anchors {
                    top: parent.top
                    left: parent.left
                    topMargin: 10
                    leftMargin: 16
                    bottomMargin: 20
                }
                spacing: 14

                states: [
                    State {
                        name: "platformsHidden"
                        when: root.platformCardsHidden
                        AnchorChanges {
                            target: row
                            anchors.bottom: scInner.bottom
                        }
                        PropertyChanges {
                            target: row.anchors
                            bottomMargin: 10
                        }
                    }
                ]

                PlatformCardsPanel {
                    id: col
                    property real _targetW: Math.min(560, row.width)
                    property real _animW: root.platformCardsHidden ? 0 : _targetW
                    compact: false
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: _animW
                    Layout.minimumWidth: 0
                    Layout.maximumWidth: _animW
                    Layout.fillHeight: true
                    spacing: root.platformCardsHidden ? 0 : 12
                    opacity: root.platformCardsHidden ? 0.0 : 1.0
                    clip: true
                    Behavior on _animW { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
                    Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                }

                Item {
                    Layout.preferredWidth: 36
                    Layout.fillHeight: true
                    visible: analyticsSlot._anyPanelEnabled

                    SideCollapseHandle {
                        anchors.centerIn: parent
                        collapsed: root.platformCardsHidden
                        accent: "#52607a"
                        onToggled: root.platformCardsHidden = !root.platformCardsHidden
                    }
                }

                AnalyticsPanel {
                    id: analyticsSlot
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignTop
                    fillHeight: root.platformCardsHidden
                    alwaysVisible: false
                    footerReserve: {
                        if (!root.platformCardsHidden) return 0
                        if (!api) return 0
                        api.refreshCounter
                        return Math.max(0, api.footerHeightPx || 0)
                    }
                    Layout.bottomMargin: footerReserve
                    _visibilityWide: root.platformCardsHidden || (row.width > (col._animW + 180))
                }
            }
        }
    }
}
