import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// PREMIUM sound card — performance-console surface, not a generic rectangle.
// Contract preserved: soundId/soundName/category/peaks/durationSec/hotkey/
// playing/broken/cooldownLeft/progress + play/stop/hotkey/edit/duplicate/
// remove/retry/relink signals.
Rectangle {
    id: root
    property string soundId: ""
    property string soundName: "AIRHORN"
    property string category: "Меми"
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
    signal menuOpened()

    implicitWidth: 260
    implicitHeight: 178
    radius: 11
    color: root.playing ? "#1a1530" : (hoverMa.containsMouse ? "#151b2a" : "#111728")
    border.width: 1
    border.color: root.activeFocus ? "#22d3ee"
        : root.playing ? "#8b5cf6"
        : root.broken ? "#7f1d1d"
        : hoverMa.containsMouse ? "#4b5876" : "#26314a"
    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    // accent glow: playing = visible, hover = faint
    Rectangle {
        anchors.fill: parent
        anchors.margins: -1
        radius: parent.radius + 1
        z: -1
        color: "transparent"
        border.width: 1
        border.color: root.playing ? "#558b5cf6" : (hoverMa.containsMouse ? "#2e8b5cf6" : "#00000000")
        Behavior on border.color { ColorAnimation { duration: 160 } }
    }
    // top accent hairline when playing
    Rectangle {
        visible: root.playing
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 1
        anchors.leftMargin: 11
        anchors.rightMargin: 11
        height: 2
        radius: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#8b5cf6" }
            GradientStop { position: 1.0; color: "#22d3ee" }
        }
    }

    // hover lift + press compress (GPU-cheap, no effects)
    transform: Translate { id: lift; y: hoverMa.containsMouse && !pressMa.pressed ? -2 : 0
        Behavior on y { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } } }
    scale: pressMa.pressed ? 0.985 : 1.0
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }

    Accessible.role: Accessible.Button
    Accessible.name: root.soundName + " " + (root.hotkey !== "" ? root.hotkey : "")
    activeFocusOnTab: true
    Keys.onReturnPressed: if (!root.broken) root.playRequested()
    Keys.onSpacePressed: if (!root.broken) root.playRequested()

    property bool menuOpen: false

    function openMenu() {
        root.menuOpen = true;
        root.menuOpened();
    }
    function closeMenu() { root.menuOpen = false; }

    function fmtDur(sec) {
        var s = Math.max(0, Math.floor(Number(sec) || 0));
        var m = Math.floor(s / 60);
        var r = s % 60;
        var ms = Math.floor((Number(sec) - s) * 10);
        if (m > 0) return "0" + m + ":" + (r < 10 ? "0" + r : r);
        return "0:0" + r;
    }
    function catColor(c) {
        switch (c) {
        case "Меми": return ["#2b1f4d", "#a78bfa"];
        case "Реакції": return ["#0f2b33", "#22d3ee"];
        case "Голоси": return ["#1f2b4d", "#7aa2ff"];
        case "Музика": return ["#2d1f4d", "#c084fc"];
        case "Ігри": return ["#3d2317", "#fb923c"];
        case "Alerts": return ["#3d1a24", "#f87171"];
        case "Атмосфера": return ["#17324a", "#38bdf8"];
        default: return ["#232d42", "#9aa4b8"];
        }
    }

    // Click-through layer FIRST (below content): controls on top (play
    // button, keycap, menu) receive their clicks; empty card areas fall
    // through here and toggle playback. Declaring it after the content
    // would steal every click from the controls above.
    MouseArea {
        id: pressMa
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: false
        onClicked: function (mouse) {
            if (mouse.button === Qt.RightButton) {
                root.menuOpen ? root.closeMenu() : root.openMenu();
                return;
            }
            if (root.menuOpen) { root.closeMenu(); return; }
            if (!root.broken) { root.playing ? root.stopRequested() : root.playRequested(); }
        }
        onPressAndHold: root.menuOpen ? root.closeMenu() : root.openMenu()
    }
    MouseArea {
        id: hoverMa
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        cursorShape: Qt.PointingHandCursor
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 0

        // — header: title + menu —
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: root.soundName.toUpperCase()
                    color: "#e8ecf5"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                RowLayout {
                    spacing: 6
                    Rectangle {
                        Layout.preferredWidth: Math.min(120, catLbl.implicitWidth + 14)
                        Layout.preferredHeight: 18
                        radius: 4
                        color: root.catColor(root.category)[0]
                        border.width: 1
                        border.color: "#55" + root.catColor(root.category)[1].slice(1)
                        Text {
                            id: catLbl
                            anchors.centerIn: parent
                            text: root.category
                            color: root.catColor(root.category)[1]
                            font.pixelSize: 10
                            font.weight: Font.Medium
                        }
                    }
                    RowLayout {
                        spacing: 4
                        visible: root.playing
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: "#22d3ee"
                            Layout.alignment: Qt.AlignVCenter
                            SequentialAnimation on opacity { running: root.playing; loops: Animation.Infinite
                                NumberAnimation { to: 0.35; duration: 550 }
                                NumberAnimation { to: 1.0; duration: 550 } }
                        }
                        Text { text: spApi.strings.card_playing || "PLAYING"; color: "#22d3ee"; font.pixelSize: 9; font.weight: Font.DemiBold }
                    }
                    Text {
                        visible: root.cooldownLeft > 0.05 && !root.playing
                        text: Number(root.cooldownLeft).toFixed(1) + "s"
                        color: "#fbbf24"
                        font.pixelSize: 10
                    }
                }
            }
            Rectangle {
                id: menuBtn
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                Layout.alignment: Qt.AlignTop
                radius: 7
                color: root.menuOpen || menuMa.containsMouse ? "#1c2434" : "transparent"
                border.width: 1
                border.color: root.menuOpen ? "#3b4458" : "transparent"
                opacity: hoverMa.containsMouse || root.menuOpen ? 1.0 : 0.55
                Behavior on opacity { NumberAnimation { duration: 140 } }
                Image {
                    anchors.centerIn: parent
                    width: 15; height: 15
                    source: Qt.resolvedUrl("../../assets/icons/web_more.svg")
                }
                MouseArea {
                    id: menuMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.menuOpen ? root.closeMenu() : root.openMenu()
                }
            }
        }

        Item { Layout.preferredHeight: 10 }

        // — waveform: meaningful band, progress fill + playhead —
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.broken ? 22 : 52
            Repeater {
                id: peaksRep
                model: (root.peaks && root.peaks.length > 0) ? root.peaks : [0.25, 0.5, 0.35, 0.65, 0.45, 0.7, 0.3, 0.55, 0.4, 0.6, 0.28, 0.5]
                delegate: Rectangle {
                    property bool filled: (index / Math.max(1, peaksRep.count)) < root.progress
                    width: Math.max(2, (parent.width - (peaksRep.count - 1) * 3) / Math.max(1, peaksRep.count))
                    x: index * (width + 3)
                    height: Math.max(3, modelData * parent.height)
                    anchors.bottom: parent.bottom
                    radius: 1.5
                    color: root.playing
                        ? (filled ? "#a78bfa" : "#888b5cf6")
                        : (filled ? "#22d3ee" : "#33405a")
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
            }
            // playhead
            Rectangle {
                visible: root.playing
                x: parent.width * Math.min(1, root.progress) - 1
                width: 2
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                radius: 1
                color: "#e8ecf5"
            }
            Text {
                visible: root.broken
                anchors.verticalCenter: parent.verticalCenter
                text: spApi.strings.file_missing || "Файл не знайдено"
                color: "#f87171"
                font.pixelSize: 11
            }
        }

        Item { Layout.preferredHeight: 10 }

        // — footer: keycap + duration … play —
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            CheremshaKeycap {
                id: cardKey
                keyText: root.hotkey
                Layout.alignment: Qt.AlignVCenter
                onClicked: root.hotkeyClicked()
            }
            Text {
                text: root.fmtDur(root.durationSec)
                color: "#7f8aa3"
                font.pixelSize: 11
                Layout.alignment: Qt.AlignVCenter
            }
            Item { Layout.fillWidth: true }
            CheremshaPlayButton {
                playing: root.playing
                enabled: !root.broken && !(root.cooldownLeft > 0.05 && !root.playing)
                opacity: hoverMa.containsMouse || root.playing ? 1.0 : 0.88
                Behavior on opacity { NumberAnimation { duration: 140 } }
                onClicked: root.playing ? root.stopRequested() : root.playRequested()
            }
        }
    }

    // global-hotkey flash: card accent pulse + keycap highlight
    function flashHotkey() {
        hotFlash.restart();
        cardKey.flash();
    }
    SequentialAnimation {
        id: hotFlash
        PropertyAnimation { target: root; property: "border.color"; to: "#c4b5fd"; duration: 90 }
        PauseAnimation { duration: 220 }
        PropertyAnimation { target: root; property: "border.color";
            to: root.playing ? "#8b5cf6" : "#26314a"; duration: 260 }
    }

    // Card dropdown — rendered in-scene (Menu.popup() does not reliably open
    // from inside Repeater delegates), full Cheremsha theme, no native look.
    component MenuRow: Rectangle {
        id: mrow
        property alias label: lbl.text
        property bool danger: false
        property bool rowEnabled: true
        signal clicked()
        implicitWidth: 198
        implicitHeight: 32
        radius: 7
        color: !mrow.rowEnabled ? "transparent"
            : rowMa.pressed ? "#2a1f4d"
            : (rowMa.containsMouse ? "#1c2434" : "transparent")
        border.width: 1
        border.color: rowMa.containsMouse && mrow.rowEnabled ? "#3b4458" : "transparent"
        Behavior on color { ColorAnimation { duration: 110 } }
        Text {
            id: lbl
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font.pixelSize: 13
            color: !mrow.rowEnabled ? "#4b5568"
                : mrow.danger ? (rowMa.containsMouse ? "#fca5a5" : "#f87171")
                : (rowMa.containsMouse ? "#ffffff" : "#c9d1e0")
        }
        MouseArea {
            id: rowMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: mrow.rowEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: if (mrow.rowEnabled) { root.closeMenu(); mrow.clicked(); }
        }
    }

    Rectangle {
        id: menuPanel
        visible: root.menuOpen
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 42
        anchors.rightMargin: 10
        width: 210
        height: menuCol.implicitHeight + 12
        radius: 11
        color: "#0e1420"
        border.width: 1
        border.color: "#2a3348"
        z: 50

        Column {
            id: menuCol
            anchors.fill: parent
            anchors.margins: 6
            spacing: 2
            MenuRow {
                label: root.playing ? (spApi.strings.menu_stop || "Стоп") : (spApi.strings.menu_play || "Відтворити")
                rowEnabled: !root.broken
                onClicked: root.playing ? root.stopRequested() : root.playRequested()
            }
            // Error-state actions: re-check, relink to a new file, or remove.
            MenuRow {
                label: spApi.strings.menu_retry || "Спробувати знову"
                visible: root.broken
                onClicked: root.retryRequested()
            }
            MenuRow {
                label: spApi.strings.menu_relink || "Змінити файл…"
                visible: root.broken
                onClicked: root.relinkRequested()
            }
            MenuRow { label: spApi.strings.menu_hotkey || "Хоткей…"; onClicked: root.hotkeyClicked() }
            MenuRow { label: spApi.strings.menu_edit || "Редагувати…"; onClicked: root.editRequested() }
            MenuRow { label: spApi.strings.menu_duplicate || "Дублювати"; onClicked: root.duplicateRequested() }
            Rectangle {
                width: 198
                height: 9
                color: "transparent"
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width - 16
                    height: 1
                    color: "#1e2942"
                }
            }
            MenuRow { label: spApi.strings.menu_remove || "Видалити"; danger: true; onClicked: root.removeRequested() }
        }
    }

    Keys.onEscapePressed: root.closeMenu()
}
