import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// CheremshaServiceCard — ONE data-driven service card for the Donations
// page (and any future provider). Owns the shared Cheremsha card language
// from CheremshaSourceCard: dark surface, accent wash, 44px icon tile,
// compact status badge, optional Live/TTS toggles, single action button,
// hover treatment, subtle accent flow.
//
// Consumers supply data + behavior only; the component never hardcodes
// service types. Extra provider-specific UI stays in the consumer.
Item {
    id: card

    // ---- content (data-driven, no per-service conditionals) ----
    property string title: ""
    property string description: ""
    property string iconSource: ""
    property color accentColor: "#8b5cf6"
    property bool connected: false
    property string statusConnectedText: ""
    property string statusDisconnectedText: ""
    property string actionText: ""
    // Single primary action per card (e.g. "Налаштувати"). Always the
    // Cheremsha purple primary button, compact and left-aligned.
    property bool actionPrimary: true
    property string actionIconSource: ""
    property real actionWidth: 132
    // Subtle living accent shimmer (same treatment as widget cards).
    property bool accentFlow: true
    // Optional Live/TTS quick toggles (mirror of the detail-page toggles).
    property bool showToggles: false
    property bool liveOn: false
    property bool ttsOn: false
    property string liveLabel: "Live"
    property string ttsLabel: "TTS"
    // Floor for the description block: keeps toggle/action rows aligned
    // across cards whose texts wrap differently.
    property real descriptionMinHeight: 0

    signal actionClicked()
    signal cardClicked()
    signal liveToggled(bool on)
    signal ttsToggled(bool on)

    // Mix two colors in sRGB. Used to inherit a whisper of the accent
    // into the neutral border.
    function mix(a, b, t) {
        return Qt.rgba(
            a.r + (b.r - a.r) * t,
            a.g + (b.g - a.g) * t,
            a.b + (b.b - a.b) * t,
            a.a + (b.a - a.a) * t)
    }

    // Content-driven height: anchored children do not propagate implicit
    // size, so derive it from the internal column.
    implicitHeight: cardBody.implicitHeight + 28

    Rectangle {
        id: cardBg
        anchors.fill: parent
        radius: 12
        color: clickMa.pressed ? "#121826" : (hoverMa.containsMouse ? "#151d2d" : "#121620")
        border.width: 1
        border.color: hoverMa.containsMouse ? mix("#3d4a63", card.accentColor, 0.3) : mix("#2a3142", card.accentColor, 0.16)
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        // Below the action button so it keeps click priority.
        MouseArea {
            id: clickMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: card.cardClicked()
        }
        // Pure hover observer, never consumes clicks.
        MouseArea {
            id: hoverMa
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }

        // Subtle per-card accent identity: faint wash from the top,
        // corners matched so it never reads as glow.
        Rectangle {
            anchors.fill: parent
            radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: card.accentColor }
                GradientStop { position: 0.5; color: "transparent" }
            }
            opacity: 0
            Behavior on opacity { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
        }

        // Living accent shimmer: one opacity property on a static
        // gradient — no timers, shaders, blur, or per-frame JS.
        Rectangle {
            visible: false // BISECT-A
            anchors.fill: parent
            radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.55; color: card.accentColor }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.04
            SequentialAnimation on opacity {
                running: card.accentFlow && visible
                loops: Animation.Infinite
                NumberAnimation { from: 0.03; to: 0.06; duration: 2600; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.06; to: 0.03; duration: 2600; easing.type: Easing.InOutSine }
            }
        }

        ColumnLayout {
            id: cardBody
            anchors.fill: parent
            anchors.margins: 14
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Item {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    Layout.alignment: Qt.AlignVCenter

                    Rectangle {
                        anchors.fill: parent
                        radius: 9
                        color: card.accentColor
                        opacity: 0.15
                    }
                    Rectangle {
                        anchors.fill: parent
                        radius: 9
                        color: "transparent"
                        border.width: 1
                        border.color: card.accentColor
                        opacity: 0.5
                    }
                    Image {
                        anchors.centerIn: parent
                        source: card.iconSource
                        width: 22
                        height: 22
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 5

                    Text {
                        text: card.title
                        color: "#e8eaed"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        maximumLineCount: 1
                        elide: Text.ElideRight
                    }

                    ConnStatusBadge {
                        Layout.alignment: Qt.AlignLeft
                        kind: card.connected ? "connected" : "disabled"
                        label: card.connected ? card.statusConnectedText : card.statusDisconnectedText
                    }
                }
            }

            Text {
                text: card.description
                color: "#9aa7bc"
                font.pixelSize: 13
                Layout.fillWidth: true
                Layout.topMargin: 10
                Layout.minimumHeight: card.descriptionMinHeight
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            RowLayout {
                visible: card.showToggles
                Layout.fillWidth: true
                Layout.topMargin: 14
                spacing: 8

                Text {
                    text: card.liveLabel
                    color: "#9eb0c8"
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    Layout.alignment: Qt.AlignVCenter
                }
                ConnPrefSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: card.liveOn
                    onToggled: card.liveToggled(checked)
                }
                Text {
                    text: card.ttsLabel
                    color: "#9eb0c8"
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    Layout.leftMargin: 12
                    Layout.alignment: Qt.AlignVCenter
                }
                ConnPrefSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: card.ttsOn
                    onToggled: card.ttsToggled(checked)
                }
                Item { Layout.fillWidth: true }
            }

            Item { Layout.fillHeight: true }

            Button {
                id: actionBtn
                Layout.alignment: Qt.AlignLeft
                Layout.topMargin: 14
                Layout.preferredWidth: card.actionWidth
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                font.pixelSize: 13
                font.bold: true
                contentItem: Row {
                    anchors.centerIn: parent
                    spacing: 6
                    Image {
                        source: card.actionIconSource
                        visible: card.actionIconSource !== ""
                        width: 14
                        height: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: actionBtn.text
                        color: card.actionPrimary ? "white" : "#b8c1cf"
                        font: actionBtn.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                background: Rectangle {
                    radius: 8
                    color: card.actionPrimary ? "transparent" : (actionBtn.hovered ? "#141c2c" : "#0a0f19")
                    border.width: 1
                    border.color: card.actionPrimary
                        ? (actionBtn.pressed ? "#6d28d9" : (actionBtn.hovered ? "#a78bfa" : "#8b54f5"))
                        : (actionBtn.hovered ? "#3d4a63" : "#232d42")
                    Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }

                    Rectangle {
                        visible: card.actionPrimary
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: 7
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: actionBtn.pressed ? "#7c3aed" : (actionBtn.hovered ? "#9d71f7" : "#8b5cf6") }
                            GradientStop { position: 1.0; color: actionBtn.pressed ? "#6d28d9" : (actionBtn.hovered ? "#8b5cf6" : "#7c3aed") }
                        }
                    }
                }
                text: card.actionText
                onClicked: card.actionClicked()
            }
        }
    }
}
