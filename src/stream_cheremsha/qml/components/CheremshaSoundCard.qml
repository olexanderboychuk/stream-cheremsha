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

    implicitWidth: 200
    implicitHeight: 148
    radius: 10
    color: root.playing ? "#171326" : "#121620"
    border.width: 1
    border.color: root.playing ? "#8b5cf6" : (root.broken ? "#7f1d1d" : "#2a3142")
    Behavior on border.color { ColorAnimation { duration: 140 } }

    Accessible.role: Accessible.Button
    Accessible.name: root.soundName + " " + (root.hotkey !== "" ? root.hotkey : "")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: root.soundName
                color: "#e8eaed"
                font.pixelSize: 14
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                visible: root.playing || root.cooldownLeft > 0
                text: root.playing ? "PLAYING" : ("COOLDOWN " + root.cooldownLeft.toFixed(1) + "s")
                color: "#06b6d4"
                font.pixelSize: 10
                font.bold: true
            }
        }

        // Waveform: static peaks + progress fill, no Canvas loop.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.broken ? 20 : 34
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

        Text {
            Layout.fillWidth: true
            visible: root.broken
            text: "Аудіо недоступне — файл не знайдено"
            color: "#f87171"
            font.pixelSize: 12
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Rectangle { // keycap inline (kept local to avoid extra import path issues)
                Layout.preferredWidth: 40
                Layout.preferredHeight: 24
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
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.hotkeyClicked()
                }
            }
            Text {
                text: root.durationSec.toFixed(1) + "s"
                color: "#8b95a5"
                font.pixelSize: 12
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            Rectangle { // three-dot menu (spec §42)
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
                    source: Qt.resolvedUrl("../assets/icons/web_more.svg")
                }
                MouseArea {
                    id: menuMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: cardMenu.visible ? cardMenu.close() : cardMenu.popup()
                }
            }

            Button {
                id: playBtn
                Layout.preferredWidth: 36
                Layout.preferredHeight: 28
                enabled: !root.broken
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                contentItem: Image {
                    source: Qt.resolvedUrl("../assets/icons/" + (root.playing ? "stop.svg" : "play.svg"))
                    width: 14
                    height: 14
                    anchors.centerIn: parent
                }
                background: Rectangle {
                    radius: 6
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
