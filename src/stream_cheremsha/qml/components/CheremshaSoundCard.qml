import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string soundId: ""
    property string soundName: "AIRHORN"
    property var peaks: []
    property double durationSec: 1.2
    property string hotkey: "F2"
    property bool playing: false
    property double progress: 0.0
    property double cooldownLeft: 0.0
    property bool broken: false

    signal playRequested()
    signal stopRequested()
    signal hotkeyClicked()
    signal editRequested()
    signal duplicateRequested()
    signal removeRequested()
    signal retryRequested()
    signal relinkRequested()

    implicitWidth: 260
    implicitHeight: 170
    radius: 12
    color: root.playing ? "#171326" : "#121620"
    border.width: 1
    // Focus outline (a11y): cyan ring when the card is the tab-focus target.
    border.color: root.activeFocus ? "#06b6d4"
        : (root.playing ? "#8b5cf6" : (root.broken ? "#7f1d1d" : "#2a3142"))
    Behavior on border.color { ColorAnimation { duration: 140 } }

    Accessible.role: Accessible.Button
    Accessible.name: root.soundName + " " + (root.hotkey !== "" ? root.hotkey : "")
    activeFocusOnTab: true
    Keys.onReturnPressed: if (!root.broken) root.playRequested()
    Keys.onSpacePressed: if (!root.broken) root.playRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        // Top row: name + category tag + menu
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: root.soundName
                color: "#e8eaed"
                font.pixelSize: 15
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            // Category tag (small pill)
            Rectangle {
                visible: false // Will be set by parent via property binding if needed
                radius: 4
                color: "#241b3a"
                border.width: 1
                border.color: "#8b5cf6"
                Text {
                    anchors.centerIn: parent
                    text: "Реакції"
                    color: "#c4b5fd"
                    font.pixelSize: 9
                    padding: 2
                }
            }
            // Three-dot menu button
            Rectangle {
                id: menuBtn
                Layout.preferredWidth: 26
                Layout.preferredHeight: 26
                radius: 6
                color: cardMenu.visible || menuMa.containsMouse ? "#1c2434" : "transparent"
                border.width: 1
                border.color: cardMenu.visible ? "#3b4458" : "transparent"
                Image {
                    anchors.centerIn: parent
                    width: 14
                    height: 14
                    source: Qt.resolvedUrl("../../assets/icons/web_more.svg")
                }
                MouseArea {
                    id: menuMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: cardMenu.visible ? cardMenu.close() : cardMenu.popup()
                }
            }
        }

        // Waveform visualization (static peaks + progress fill)
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.broken ? 20 : 48
            Repeater {
                id: peaksRep
                model: (root.peaks && root.peaks.length > 0) ? root.peaks : [0.2, 0.5, 0.3, 0.6, 0.4]
                delegate: Rectangle {
                    width: (parent.width - (peaksRep.count - 1) * 2) / Math.max(1, peaksRep.count)
                    height: Math.max(3, modelData * parent.height)
                    anchors.bottom: parent.bottom
                    radius: 1
                    color: (index / Math.max(1, peaksRep.count)) < root.progress ? "#06b6d4" : "#3b4458"
                }
            }
        }

        // Broken state message
        Text {
            Layout.fillWidth: true
            visible: root.broken
            text: "Аудіо недоступне — файл не знайдено"
            color: "#f87171"
            font.pixelSize: 12
        }

        // Bottom row: hotkey keycap + duration + play button
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            // Keyboard keycap style hotkey badge (using CheremshaKeycap)
            Item {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 26
                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    color: "#1c2434"
                    border.width: 1
                    border.color: "#3b4458"
                    Text {
                        anchors.centerIn: parent
                        text: root.hotkey === "" ? "—" : root.hotkey
                        color: "#e8eaed"
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.hotkeyClicked()
                }
            }
            // Duration display
            Text {
                text: root.durationSec.toFixed(1) + "s"
                color: "#8b95a5"
                font.pixelSize: 12
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            // Circular play button with hover glow
            Button {
                id: playBtn
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                enabled: !root.broken
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                contentItem: Image {
                    source: Qt.resolvedUrl("../../assets/icons/" + (root.playing ? "stop.svg" : "play.svg"))
                    width: 14
                    height: 14
                    anchors.centerIn: parent
                }
                background: Rectangle {
                    radius: 18 // Circular
                    color: playBtn.hovered && playBtn.enabled ? "#263246" : "#1c2434"
                    border.width: 1
                    border.color: root.playing ? "#8b5cf6" : "#3b4458"
                }
                onClicked: root.playing ? root.stopRequested() : root.playRequested()
            }
        }
    }

    Menu {
        id: cardMenu
        MenuItem {
            text: root.playing ? "Стоп" : "Відтворити"
            enabled: !root.broken
            onTriggered: root.playing ? root.stopRequested() : root.playRequested()
        }
        // Error-state actions (spec §45-46): re-check, relink to a new file, or remove.
        MenuItem {
            text: "Спробувати знову"
            visible: root.broken
            onTriggered: root.retryRequested()
        }
        MenuItem {
            text: "Змінити файл…"
            visible: root.broken
            onTriggered: root.relinkRequested()
        }
        MenuItem { text: "Хоткей…"; onTriggered: root.hotkeyClicked() }
        MenuItem { text: "Редагувати…"; onTriggered: root.editRequested() }
        MenuItem { text: "Дублювати"; onTriggered: root.duplicateRequested() }
        MenuSeparator {}
        MenuItem { text: "Видалити"; onTriggered: root.removeRequested() }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: cardMenu.popup()
    }
}
