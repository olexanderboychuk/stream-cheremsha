import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// CheremshaSourceCard — ONE reusable source card for the Docks and Widgets
// pages. Owns the shared Cheremsha card language: dark surface, accent wash,
// 44px icon tile, title/status header, description, preview container,
// display-only URL field, copy/open/menu actions, hover treatment.
//
// Consumers supply data + behavior; the component never hardcodes source
// types. Widget-specific UI (dropdown menus, timers, editors) stays in the
// consumer, anchored to the exposed menuButton alias when needed.
Item {
    id: card

    // ---- content ----
    property string title: ""
    property string description: ""
    property string iconSource: ""
    property color accentColor: "#8b5cf6"
    property string statusText: ""
    property color statusColor: "#8b95a5"
    property color statusDotColor: "#10b981"
    property string url: ""
    property int previewHeight: 96
    // Optional single-root content instantiated inside the preview container.
    // Null hides the preview block entirely (no gap left behind).
    property Component previewContent
    // Optional corner badge overlaid top-right of the preview
    // (e.g. widget platforms). Empty hides it.
    property string previewBadgeText: ""
    property color previewBadgeColor: "#c4b5fd"

    // ---- chrome options ----
    property bool showOpenButton: true
    // Compact 34px square open action (widget cards). False keeps the text
    // button (Docks cards).
    property bool openIconOnly: false
    property bool showMenuButton: false
    property bool showToggle: false
    property bool toggleOn: false
    property string toggleTipText: ""
    // Floor for the description block: keeps previews/URLs/actions aligned
    // across cards whose texts wrap differently. 0 disables (Docks).
    property real descriptionMinHeight: 0
    // Subtle living accent shimmer. Off by default (Docks stay static);
    // widgets enable it. One opacity property, no timers or shaders.
    property bool accentFlow: false
    property string copyButtonText: "Копіювати URL"
    property string openButtonText: "Відкрити"
    property string copyIconSource: Qt.resolvedUrl("../../assets/icons/web_copy.svg")
    property string openIconSource: Qt.resolvedUrl("../../assets/icons/web_open.svg")
    // Whole-card click (widget edit affordance). Disabled for Docks.
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

    // Content-driven height: anchored children do not propagate implicit
    // size, so derive it from the internal column.
    implicitHeight: cardBody.implicitHeight + 28

    Rectangle {
        id: cardBg
        anchors.fill: parent
        radius: 14
        color: clickMa.pressed ? "#121826" : (hoverMa.containsMouse ? "#151d2d" : "#121620")
        border.width: 1
        border.color: hoverMa.containsMouse ? mix("#3d4a63", card.accentColor, 0.3) : mix("#2a3142", card.accentColor, 0.16)
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

        // Below the action buttons so they keep click priority.
        MouseArea {
            id: clickMa
            anchors.fill: parent
            enabled: card.clickEnabled
            hoverEnabled: card.clickEnabled
            cursorShape: card.clickEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
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
            radius: 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: card.accentColor }
                GradientStop { position: 0.5; color: "transparent" }
            }
            opacity: hoverMa.containsMouse ? 0.1 : 0.07
            Behavior on opacity { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
        }

        // Living accent shimmer (widgets only): one opacity property on a
        // static gradient — no timers, shaders, blur, or per-frame JS.
        Rectangle {
            visible: card.accentFlow
            anchors.fill: parent
            radius: 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.55; color: card.accentColor }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.05
            SequentialAnimation on opacity {
                running: card.accentFlow && visible
                loops: Animation.Infinite
                NumberAnimation { from: 0.04; to: 0.09; duration: 2600; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.09; to: 0.04; duration: 2600; easing.type: Easing.InOutSine }
            }
        }

        ColumnLayout {
            id: cardBody
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

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
                    spacing: 3

                    Text {
                        text: card.title
                        color: "#e8eaed"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        maximumLineCount: 1
                        elide: Text.ElideRight
                    }

                    RowLayout {
                        visible: card.statusText !== ""
                        spacing: 6

                        Rectangle {
                            Layout.alignment: Qt.AlignVCenter
                            width: 7
                            height: 7
                            radius: 3.5
                            color: card.statusDotColor
                        }

                        Text {
                            text: card.statusText
                            color: card.statusColor
                            font.pixelSize: 11
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }
                }

                // Enable/disable switch (widgets). Hidden for Docks.
                Rectangle {
                    visible: card.showToggle
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 22
                    Layout.alignment: Qt.AlignVCenter
                    radius: 11
                    color: card.toggleOn ? (toggleMa.containsMouse ? "#22c55e" : "#16a34a") : (toggleMa.containsMouse ? "#4b5563" : "#374151")
                    border.width: 1
                    border.color: card.toggleOn ? "#22c55e" : (toggleMa.containsMouse ? "#64748b" : "#4b5563")
                    Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    ToolTip.visible: toggleMa.containsMouse
                    ToolTip.text: card.toggleTipText !== "" ? card.toggleTipText : (card.toggleOn ? "Увімкнено" : "Вимкнено")
                    Rectangle {
                        width: 16
                        height: 16
                        radius: 8
                        color: "white"
                        anchors.verticalCenter: parent.verticalCenter
                        x: card.toggleOn ? parent.width - width - 3 : 3
                        Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    }
                    MouseArea {
                        id: toggleMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: card.toggleClicked()
                    }
                }
            }

            Text {
                text: card.description
                color: "#9aa7bc"
                font.pixelSize: 13
                Layout.fillWidth: true
                Layout.minimumHeight: card.descriptionMinHeight
                wrapMode: Text.Wrap
                elide: Text.ElideRight
            }

            Item { Layout.fillHeight: true }

            Loader {
                id: previewLoader
                Layout.fillWidth: true
                Layout.preferredHeight: card.previewHeight
                visible: card.previewContent !== null && card.previewContent !== undefined
                active: visible
                sourceComponent: card.previewContent

                // Corner badge overlaid top-right of the preview content.
                // A Loader child (not a layout item) so it adds no height.
                // Raised above the dynamically loaded preview item.
                Rectangle {
                    visible: card.previewBadgeText !== ""
                    z: 5
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: 6
                    anchors.rightMargin: 6
                    implicitHeight: 20
                    implicitWidth: badgeLabel.implicitWidth + 14
                    radius: 10
                    color: "#1e1b4b"
                    border.width: 1
                    border.color: "#4c1d95"
                    Text {
                        id: badgeLabel
                        anchors.centerIn: parent
                        text: card.previewBadgeText
                        color: card.previewBadgeColor
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                radius: 8
                color: "#0c0f16"
                border.width: 1
                border.color: "#2a3142"

                Text {
                    text: card.url
                    color: "#9aa7bc"
                    font.pixelSize: 11
                    font.family: "monospace"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    elide: Text.ElideRight
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Button {
                    id: copyBtn
                    Layout.fillWidth: true
                    Layout.maximumWidth: 140
                    hoverEnabled: true
                    focusPolicy: Qt.NoFocus
                    font.pixelSize: 13
                    font.bold: true
                    contentItem: Row {
                        anchors.centerIn: parent
                        spacing: 6
                        Image {
                            source: card.copyIconSource
                            visible: card.copyIconSource !== ""
                            width: 14
                            height: 14
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: copyBtn.text
                            color: "white"
                            font: copyBtn.font
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            anchors.verticalCenter: parent.verticalCenter
                        }
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
                    text: card.copyButtonText
                    onClicked: card.copyClicked()
                }

                Button {
                    id: openBtn
                    visible: card.showOpenButton
                    Layout.fillWidth: !card.openIconOnly
                    Layout.maximumWidth: card.openIconOnly ? 34 : 100
                    Layout.preferredWidth: card.openIconOnly ? 34 : -1
                    Layout.preferredHeight: card.openIconOnly ? 32 : -1
                    Layout.alignment: Qt.AlignVCenter
                    hoverEnabled: true
                    focusPolicy: Qt.NoFocus
                    font.pixelSize: 13
                    ToolTip.visible: card.openIconOnly && openBtn.hovered
                    ToolTip.text: card.openButtonText
                    contentItem: card.openIconOnly ? openIconGlyph : openTextRow
                    Row {
                        id: openTextRow
                        visible: !card.openIconOnly
                        anchors.centerIn: parent
                        spacing: 6
                        Image {
                            source: card.openIconSource
                            visible: card.openIconSource !== ""
                            width: 14
                            height: 14
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: openBtn.text
                            color: "#b8c1cf"
                            font: openBtn.font
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    Image {
                        id: openIconGlyph
                        visible: card.openIconOnly
                        source: card.openIconSource
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
                    text: card.openButtonText
                    onClicked: card.openClicked()
                }

                Rectangle {
                    id: kebabBtn
                    visible: card.showMenuButton
                    Layout.preferredWidth: 34
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
                        onClicked: card.menuClicked()
                    }
                }
            }
        }
    }
}
