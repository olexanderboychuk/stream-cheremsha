import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// CheremshaWidgetRow — LIST-density sibling of CheremshaSourceCard for the
// Widgets gallery. Same card language (dark surface, accent wash, icon tile,
// title/status header, toggle, copy/open/menu actions, hover treatment) in a
// compact 72px row. No preview block and no URL field: list mode is density,
// the grid card remains the full-fidelity surface.
//
// Consumers supply data + behavior; the component never hardcodes widget
// types. Widget-specific UI (dropdown menus, timers, editors) stays in the
// consumer, anchored to the exposed menuButton alias when needed.
Item {
    id: row

    // ---- content (same names/semantics as CheremshaSourceCard) ----
    property string title: ""
    property string description: ""
    property string iconSource: ""
    property color accentColor: "#8b5cf6"
    property string statusText: ""
    property color statusColor: "#8b95a5"
    property color statusDotColor: "#10b981"
    property string platformBadgeText: ""
    property color platformBadgeColor: "#c4b5fd"

    // ---- chrome options ----
    property bool showToggle: false
    property bool toggleOn: false
    property string toggleTipText: ""
    property string copyButtonText: "Копіювати URL"
    property string openButtonText: "Відкрити"
    property string copyIconSource: Qt.resolvedUrl("../../assets/icons/web_copy.svg")
    property string openIconSource: Qt.resolvedUrl("../../assets/icons/web_open.svg")
    // Whole-row click (widget edit affordance).
    property bool clickEnabled: false

    signal copyClicked()
    signal openClicked()
    signal menuClicked()
    signal toggleClicked()
    signal cardClicked()

    // Anchor target for consumer-owned overlays (e.g. widget menu dropdown).
    property alias menuButton: kebabBtn

    // Mix two colors in sRGB. Used to inherit a whisper of the accent
    // into the neutral border.
    function mix(a, b, t) {
        return Qt.rgba(
            a.r + (b.r - a.r) * t,
            a.g + (b.g - a.g) * t,
            a.b + (b.b - a.b) * t,
            a.a + (b.a - a.a) * t)
    }

    implicitHeight: 72

    Rectangle {
        id: rowBg
        anchors.fill: parent
        radius: 14
        color: clickMa.pressed ? "#121826" : (hoverMa.containsMouse ? "#151d2d" : "#121620")
        border.width: 1
        border.color: hoverMa.containsMouse ? mix("#3d4a63", row.accentColor, 0.3) : mix("#2a3142", row.accentColor, 0.16)
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        // Below the action buttons so they keep click priority.
        MouseArea {
            id: clickMa
            anchors.fill: parent
            enabled: row.clickEnabled
            hoverEnabled: row.clickEnabled
            cursorShape: row.clickEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: row.cardClicked()
        }
        // Pure hover observer, never consumes clicks.
        MouseArea {
            id: hoverMa
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }

        // Subtle per-row accent identity: faint wash from the top,
        // corners matched so it never reads as glow.
        Rectangle {
            anchors.fill: parent
            radius: 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: row.accentColor }
                GradientStop { position: 0.5; color: "transparent" }
            }
            opacity: hoverMa.containsMouse ? 0.1 : 0.07
            Behavior on opacity { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: 12

            Item {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignVCenter

                Rectangle {
                    anchors.fill: parent
                    radius: 9
                    color: row.accentColor
                    opacity: 0.15
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 9
                    color: "transparent"
                    border.width: 1
                    border.color: row.accentColor
                    opacity: 0.5
                }
                Image {
                    anchors.centerIn: parent
                    source: row.iconSource
                    width: 20
                    height: 20
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 3

                Text {
                    text: row.title
                    color: "#e8eaed"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Rectangle {
                        visible: row.statusText !== ""
                        Layout.alignment: Qt.AlignVCenter
                        width: 7
                        height: 7
                        radius: 3.5
                        color: row.statusDotColor
                    }
                    Text {
                        visible: row.statusText !== ""
                        text: row.statusText
                        color: row.statusColor
                        font.pixelSize: 11
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        visible: row.description !== ""
                        text: "· " + row.description
                        color: "#9aa7bc"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        maximumLineCount: 1
                        elide: Text.ElideRight
                    }
                }
            }

            // Platform badge (same pill as the card preview corner badge).
            Rectangle {
                visible: row.platformBadgeText !== ""
                Layout.alignment: Qt.AlignVCenter
                implicitHeight: 20
                implicitWidth: badgeLabel.implicitWidth + 14
                radius: 10
                color: "#1e1b4b"
                border.width: 1
                border.color: "#4c1d95"
                Text {
                    id: badgeLabel
                    anchors.centerIn: parent
                    text: row.platformBadgeText
                    color: row.platformBadgeColor
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            // Enable/disable switch (same treatment as the card).
            Rectangle {
                visible: row.showToggle
                Layout.preferredWidth: 38
                Layout.preferredHeight: 22
                Layout.alignment: Qt.AlignVCenter
                radius: 11
                color: row.toggleOn ? (toggleMa.containsMouse ? "#22c55e" : "#16a34a") : (toggleMa.containsMouse ? "#4b5563" : "#374151")
                border.width: 1
                border.color: row.toggleOn ? "#22c55e" : (toggleMa.containsMouse ? "#64748b" : "#4b5563")
                Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                ToolTip.visible: toggleMa.containsMouse
                ToolTip.text: row.toggleTipText !== "" ? row.toggleTipText : (row.toggleOn ? "Увімкнено" : "Вимкнено")
                Rectangle {
                    width: 16
                    height: 16
                    radius: 8
                    color: "white"
                    anchors.verticalCenter: parent.verticalCenter
                    x: row.toggleOn ? parent.width - width - 3 : 3
                    Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                }
                MouseArea {
                    id: toggleMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: row.toggleClicked()
                }
            }

            // Copy URL — icon-only in list density, same purple gradient.
            Button {
                id: copyBtn
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignVCenter
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                ToolTip.visible: copyBtn.hovered
                ToolTip.text: row.copyButtonText
                contentItem: Image {
                    source: row.copyIconSource
                    width: 14
                    height: 14
                    anchors.centerIn: parent
                }
                background: Rectangle {
                    radius: 8
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: copyBtn.pressed ? "#7c3aed" : (copyBtn.hovered ? "#9d71f7" : "#8b5cf6") }
                        GradientStop { position: 1.0; color: copyBtn.pressed ? "#6d28d9" : (copyBtn.hovered ? "#8b5cf6" : "#7c3aed") }
                    }
                    border.width: 1
                    border.color: copyBtn.pressed ? "#6d28d9" : (copyBtn.hovered ? "#a78bfa" : "#8b54f5")
                    Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                }
                onClicked: row.copyClicked()
            }

            // Open — icon-only in list density, same outline treatment.
            Button {
                id: openBtn
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignVCenter
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                ToolTip.visible: openBtn.hovered
                ToolTip.text: row.openButtonText
                contentItem: Image {
                    source: row.openIconSource
                    width: 15
                    height: 15
                    anchors.centerIn: parent
                }
                background: Rectangle {
                    radius: 8
                    color: openBtn.hovered ? "#141c2c" : "#0a0f19"
                    border.width: 1
                    border.color: openBtn.hovered ? "#3d4a63" : "#232d42"
                    Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                    Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                }
                onClicked: row.openClicked()
            }

            Rectangle {
                id: kebabBtn
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignVCenter
                radius: 8
                color: kebabMa.pressed ? "#253d62" : (kebabMa.containsMouse ? "#24416b" : "#16233a")
                border.width: 1
                border.color: kebabMa.containsMouse ? "#42638f" : "#2b3b55"
                Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                Column {
                    anchors.centerIn: parent
                    spacing: 2
                    Repeater {
                        model: 3
                        Rectangle { width: 4; height: 4; radius: 2; color: "#e8eaed" }
                    }
                }
                MouseArea {
                    id: kebabMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: row.menuClicked()
                }
            }
        }
    }
}
