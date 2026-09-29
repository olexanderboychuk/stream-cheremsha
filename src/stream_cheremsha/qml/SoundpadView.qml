import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import components

Item {
    id: root
    implicitWidth: 800
    implicitHeight: 900

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

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    readonly property color primaryPurple: "#8b5cf6"
    readonly property color secondaryCyan: "#06b6d4"

    // ---- State (stable contract names) ----
    property string selectedCategory: "Усі"
    property string query: ""
    property var categoryList: []
    property var _allItems: []

    property string pendingFileUrl: ""
    property string addHotkeyDraft: ""
    property bool showAddModal: false

    property string editingSoundId: ""
    property bool showEditModal: false
    property string editName: ""
    property string editCategory: "Custom"
    property double editVolume: 1.0
    property double editCooldown: 0.0
    property string editMode: "restart"
    property bool editEnabled: true

    property bool showHotkeyModal: false
    property string hotkeyTargetId: ""
    property string capturedCombo: ""
    property string conflictOwnerId: ""

    // Now-playing state (position/duration fed by spApi.nowPlayingChanged).
    property string nowPlayingId: ""
    property double npPosition: 0.0
    property double npDuration: 0.0

    ListModel { id: soundModel }

    function _matches(it) {
        if (root.selectedCategory !== "Усі" && it.category !== root.selectedCategory) return false;
        var q = String(root.query || "").trim().toLowerCase();
        if (q === "") return true;
        return (it.name || "").toLowerCase().indexOf(q) >= 0
            || (it.category || "").toLowerCase().indexOf(q) >= 0
            || (it.hotkey || "").toLowerCase().indexOf(q) >= 0;
    }

    function _cooldownLeftFor(it) {
        var cd = Number(it.cooldown_sec) || 0;
        if (!cd || !it.last_played_at) return 0.0;
        var lastMs = new Date(it.last_played_at).getTime();
        if (isNaN(lastMs)) return 0.0;
        return Math.max(0, (lastMs / 1000 + cd) - (Date.now() / 1000));
    }

    function _hasCategory(c) {
        for (var i = 0; i < root._allItems.length; ++i)
            if ((root._allItems[i].category || "") === c) return true;
        return false;
    }

    function _categories() {
        var defaults = ["Меми", "Реакції", "Голоси", "Музика", "Атмосфера", "Ігри", "Alerts", "Custom"];
        var out = [];
        for (var i = 0; i < defaults.length; ++i)
            if (root._hasCategory(defaults[i])) out.push(defaults[i]);
        var extra = {};
        for (var j = 0; j < root._allItems.length; ++j) {
            var c = root._allItems[j].category || "";
            if (c && defaults.indexOf(c) < 0 && !extra[c]) extra[c] = true;
        }
        var keys = Object.keys(extra).sort();
        for (var k = 0; k < keys.length; ++k) out.push(keys[k]);
        return ["Усі"].concat(out);
    }

    function refresh() {
        root._allItems = [];
        try { root._allItems = JSON.parse(spApi.soundsJson()); } catch (err) { root._allItems = []; }
        soundModel.clear();
        var npId = "";
        for (var i = 0; i < root._allItems.length; ++i) {
            var it = root._allItems[i];
            if (!root._matches(it)) continue;
            soundModel.append({
                id: it.id, name: it.name || "", category: it.category || "Custom",
                hotkey: it.hotkey || "", peaks: it.waveform_peaks || [],
                durationSec: Number(it.duration_sec) || 0.0, playing: !!it.playing,
                broken: !!it.broken, cooldownLeft: root._cooldownLeftFor(it)
            });
            if (it.playing && npId === "") npId = it.id;
        }
        root.nowPlayingId = npId;
        root.categoryList = root._categories();
        // One-shot expiry timers per cooling-down sound (no polling loops).
        cooldownTimers.clear();
        for (var j = 0; j < root._allItems.length; ++j) {
            var it2 = root._allItems[j];
            if (!it2.playing && (Number(it2.cooldown_sec) || 0) > 0) {
                var waitMs = root._cooldownLeftFor(it2) * 1000;
                if (waitMs > 50) cooldownTimers.append({ delayMs: Math.ceil(waitMs), tag: it2.id });
            }
        }
    }

    function _fmtTime(sec) {
        var s = Math.max(0, Math.floor(Number(sec) || 0));
        var m = Math.floor(s / 60);
        var r = s % 60;
        return (m < 10 ? "0" + m : String(m)) + ":" + (r < 10 ? "0" + r : String(r));
    }

    function _npName() {
        for (var i = 0; i < root._allItems.length; ++i)
            if (root._allItems[i].id === root.nowPlayingId) return root._allItems[i].name || "";
        return "";
    }

    function _soundNameById(sid) {
        for (var i = 0; i < root._allItems.length; ++i)
            if (root._allItems[i].id === sid) return root._allItems[i].name || sid;
        return sid;
    }

    function _stemFromUrl(u) {
        var s = String(u || "").replace(/^file:\/\//, "");
        var base = s.split("/").pop() || "";
        var dot = base.lastIndexOf(".");
        return dot > 0 ? base.slice(0, dot) : base;
    }

    function openAddModal(fileUrl) {
        root.pendingFileUrl = String(fileUrl || "");
        root.addHotkeyDraft = "";
        addNameField.text = root._stemFromUrl(root.pendingFileUrl);
        root.showAddModal = true;
    }

    function openEditModal(soundId) {
        for (var i = 0; i < root._allItems.length; ++i) {
            var it = root._allItems[i];
            if (it.id !== soundId) continue;
            root.editingSoundId = soundId;
            root.editName = it.name || "";
            root.editCategory = it.category || "Custom";
            root.editVolume = Number(it.volume) || 1.0;
            root.editCooldown = Number(it.cooldown_sec) || 0.0;
            root.editMode = it.playback_mode || "restart";
            root.editEnabled = it.enabled !== false;
            break;
        }
        root.showEditModal = true;
    }

    function _comboFromEvent(ev) {
        var main = "";
        if (ev.key >= Qt.Key_F1 && ev.key <= Qt.Key_F24) main = "F" + (ev.key - Qt.Key_F1 + 1);
        else if (ev.key >= Qt.Key_A && ev.key <= Qt.Key_Z) main = String.fromCharCode(ev.key).toUpperCase();
        else if (ev.key >= Qt.Key_0 && ev.key <= Qt.Key_9) main = String(ev.key - Qt.Key_0);
        else return "";
        var mods = "";
        if (ev.modifiers & Qt.ControlModifier) mods += "Ctrl+";
        if (ev.modifiers & Qt.AltModifier) mods += "Alt+";
        if (ev.modifiers & Qt.ShiftModifier) mods += "Shift+";
        return mods + main;
    }

    function _applyCapturedHotkey() {
        var res = spApi.assignHotkey(root.hotkeyTargetId, root.capturedCombo);
        if (res === "ok") {
            root.showHotkeyModal = false;
        } else if (String(res).indexOf("conflict:") === 0) {
            root.conflictOwnerId = String(res).slice(9);
        }
    }

    function _saveAddSound() {
        if (root.pendingFileUrl === "") {
            root.showAddModal = false;
            return;
        }
        var sid = spApi.addSound(root.pendingFileUrl, addNameField.text.trim(),
                                 addCatBox.currentText, root.addHotkeyDraft, addVolSlider.value);
        if (sid !== "") {
            root.showAddModal = false;
            root.pendingFileUrl = "";
            root.addHotkeyDraft = "";
            addErrText.visible = false;
        } else {
            addErrText.visible = true;
        }
    }

    function _saveEditSound() {
        var patch = {
            name: editNameField.text.trim(),
            category: editCatBox.currentText,
            volume: Number(editVolSlider.value),
            cooldown_sec: Number(editCooldownSpin.value),
            playback_mode: editModeBox.currentText,
            enabled: !!editEnabledCheck.checked
        };
        spApi.updateSoundJson(root.editingSoundId, JSON.stringify(patch));
        root.showEditModal = false;
    }

    // ---- Background (same gradient as DocksView) ----
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    // ---- Drag & drop import (spec §11) ----
    DropArea {
        anchors.fill: parent
        onDropped: function (drop) {
            var urls = [];
            if (drop.hasUrls) {
                for (var i = 0; i < drop.urls.length; ++i) urls.push(drop.urls[i].toString());
            }
            spApi.importDroppedUrls(JSON.stringify(urls));
        }
    }

    FileDialog {
        id: fileDialog
        title: "Оберіть аудіофайл"
        nameFilters: ["Аудіо (*.mp3 *.wav *.ogg)", "MP3 (*.mp3)", "WAV (*.wav)", "OGG (*.ogg)"]
        onAccepted: root.openAddModal(selectedFile.toString())
    }

    // ---- Page content (scrollable; now-playing bar stays fixed below) ----
    ScrollView {
        id: pageScroll
        anchors.fill: parent
        anchors.bottomMargin: 76
        clip: true
        contentWidth: availableWidth
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            id: pageCol
            width: pageScroll.availableWidth
            spacing: 14

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: "Soundpad"; color: root.ink; font.pixelSize: 24; font.bold: true }
                    Text {
                        text: "Миттєві звуки, хоткеї та аудіо-реакції для стріму"
                        color: root.muted
                        font.pixelSize: 13
                    }
                }
                Button {
                    id: addBtn
                    text: "+ Додати звук"
                    hoverEnabled: true
                    focusPolicy: Qt.NoFocus
                    onClicked: fileDialog.open()
                    background: Rectangle {
                        radius: 8
                        color: addBtn.hovered ? "#7c4fee" : root.primaryPurple
                    }
                }
            }

            // Category chips (filtered to categories present in the library)
            Flickable {
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                contentWidth: chipsRow.width + 20
                contentHeight: height
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Row {
                    id: chipsRow
                    spacing: 8
                    Repeater {
                        model: root.categoryList
                        delegate: Rectangle {
                            width: chipLabel.implicitWidth + 20
                            height: 26
                            radius: 13
                            color: root.selectedCategory === modelData ? "#241b3a" : root.cardBase
                            border.width: 1
                            border.color: root.selectedCategory === modelData ? root.primaryPurple : root.cardEdge
                            Text {
                                id: chipLabel
                                anchors.centerIn: parent
                                text: modelData
                                color: root.selectedCategory === modelData ? "#c4b5fd" : root.muted
                                font.pixelSize: 12
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { root.selectedCategory = modelData; root.refresh(); }
                            }
                        }
                    }
                }
            }

            // Search (local filter over name/category/hotkey)
            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Пошук звуків..."
                color: root.ink
                selectionColor: "#7c4fee"
                onTextChanged: { root.query = text; root.refresh(); }
                background: Rectangle {
                    radius: 8
                    color: root.fieldBg
                    border.width: 1
                    border.color: searchField.activeFocus ? root.primaryPurple : root.cardEdge
                }
            }

            // Grid / empty states
            CheremshaResponsiveCardGrid {
                Layout.fillWidth: true
                visible: soundModel.count > 0
                columns: root.width >= 1500 ? 5 : (root.width >= 1200 ? 4 : (root.width >= 900 ? 3 : 2))
                columnSpacing: 14
                rowSpacing: 14

                Repeater {
                    model: soundModel
                    delegate: CheremshaSoundCard {
                        id: sndCard
                        Layout.fillWidth: true
                        implicitHeight: 148
                        soundId: model.id
                        soundName: model.name
                        peaks: model.peaks
                        durationSec: model.durationSec
                        hotkey: model.hotkey
                        playing: model.playing
                        broken: model.broken
                        cooldownLeft: model.cooldownLeft
                        progress: (model.id === root.nowPlayingId && root.npDuration > 0)
                                   ? Math.min(1.0, root.npPosition / root.npDuration) : 0.0
                        onPlayRequested: spApi.playSound(sndCard.soundId)
                        onStopRequested: spApi.stopSound(sndCard.soundId)
                        onHotkeyClicked: {
                            root.hotkeyTargetId = sndCard.soundId;
                            root.capturedCombo = "";
                            root.conflictOwnerId = "";
                            root.showHotkeyModal = true;
                        }
                        onEditRequested: root.openEditModal(sndCard.soundId)
                        onDuplicateRequested: spApi.duplicateSound(sndCard.soundId)
                        onRemoveRequested: spApi.removeSound(sndCard.soundId)
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 300
                visible: root._allItems.length === 0
                spacing: 10
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Soundpad"
                    color: root.muted
                    font.pixelSize: 28
                    font.bold: true
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Додайте перший звук і прив'яжіть його до хоткею."
                    color: root.muted
                    font.pixelSize: 14
                }
                Button {
                    id: emptyAddBtn
                    Layout.alignment: Qt.AlignHCenter
                    text: "+ Додати звук"
                    hoverEnabled: true
                    focusPolicy: Qt.NoFocus
                    onClicked: fileDialog.open()
                    background: Rectangle { radius: 8; color: root.primaryPurple }
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Перетягніть аудіофайл сюди"
                    color: "#5b6472"
                    font.pixelSize: 12
                }
            }

            Text {
                Layout.fillWidth: true
                visible: root._allItems.length > 0 && soundModel.count === 0
                text: "Нічого не знайдено"
                color: root.muted
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    // ---- Now-playing bar (fixed bottom) ----
    Rectangle {
        id: npBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 12
        height: 56
        radius: 12
        color: "#0e1420"
        border.width: 1
        border.color: root.cardEdge

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            Text {
                text: root.nowPlayingId !== "" ? "NOW PLAYING" : "No sound playing"
                color: root.nowPlayingId !== "" ? root.secondaryCyan : root.muted
                font.pixelSize: 10
                font.bold: true
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                visible: root.nowPlayingId !== ""
                text: root._npName()
                color: root.ink
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.maximumWidth: 200
                Layout.alignment: Qt.AlignVCenter
            }
            Rectangle { // progress track (bound to nowPlayingChanged, no polling)
                visible: root.nowPlayingId !== ""
                Layout.fillWidth: true
                Layout.preferredHeight: 4
                radius: 2
                color: "#1c2434"
                Rectangle {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width * (root.npDuration > 0 ? Math.min(1.0, root.npPosition / root.npDuration) : 0)
                    height: parent.height
                    radius: 2
                    color: root.secondaryCyan
                }
            }
            Text {
                visible: root.nowPlayingId !== ""
                text: root._fmtTime(root.npPosition) + "/" + root._fmtTime(root.npDuration)
                color: root.muted
                font.pixelSize: 11
                Layout.alignment: Qt.AlignVCenter
            }

            ComboBox {
                id: outBox
                Layout.preferredWidth: 190
                model: JSON.parse(spApi.outputDevices())
                onActivated: spApi.setOutputDevice(currentText)
            }

            Slider {
                id: volSlider
                Layout.preferredWidth: 120
                from: 0.0
                to: 1.0
                value: 0.78
                onMoved: spApi.setGlobalVolume(value)
                onPressedChanged: if (pressed) spApi.setGlobalVolume(value)
            }
            Text {
                text: Math.round(volSlider.value * 100) + "%"
                color: root.muted
                font.pixelSize: 12
                Layout.alignment: Qt.AlignVCenter
            }

            CheckBox {
                id: monitorCheck
                text: "Monitor"
                checked: true
                onToggled: spApi.setMonitor(checked)
            }
            CheckBox {
                id: streamOutCheck
                text: "Stream Output"
                checked: true
                onToggled: spApi.setStreamOut(checked)
            }

            Button {
                id: npStopBtn
                visible: root.nowPlayingId !== ""
                text: "STOP"
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                onClicked: spApi.stopSound(root.nowPlayingId)
                background: Rectangle { radius: 6; color: "#1c2434"; border.width: 1; border.color: root.cardEdge }
            }
        }
    }

    // ---- One-shot cooldown expiry timers (rebuilt on each refresh) ----
    ListModel { id: cooldownTimers }
    Repeater {
        model: cooldownTimers
        delegate: Timer {
            interval: Math.max(50, model.delayMs)
            repeat: false
            running: true
            onTriggered: root.refresh()
        }
    }

    // ---- Add-sound modal (spec §9/§10) ----
    CheremshaModal {
        id: addModal
        anchors.fill: parent
        title: "Додати звук"
        subtitle: root._stemFromUrl(root.pendingFileUrl) || ""
        opened: root.showAddModal
        onCloseRequested: { root.showAddModal = false; }

        body: Component {
            ColumnLayout {
                spacing: 8
                Text { text: "Назва"; color: root.muted; font.pixelSize: 12; Layout.fillWidth: true }
                TextField {
                    id: addNameField
                    Layout.fillWidth: true
                    placeholderText: "Airhorn"
                    color: root.ink
                    background: Rectangle { radius: 8; color: root.fieldBg; border.width: 1; border.color: root.cardEdge }
                }
                Text { text: "Категорія"; color: root.muted; font.pixelSize: 12; Layout.fillWidth: true }
                ComboBox {
                    id: addCatBox
                    Layout.fillWidth: true
                    model: ["Меми", "Реакції", "Голоси", "Музика", "Атмосфера", "Ігри", "Alerts", "Custom"]
                }
                RowLayout {
                    spacing: 10
                    Text { text: "Об'єм"; color: root.muted; font.pixelSize: 12 }
                    Slider {
                        id: addVolSlider
                        Layout.fillWidth: true
                        from: 0.0
                        to: 1.0
                        value: 1.0
                    }
                    Text { text: Math.round(addVolSlider.value * 100) + "%"; color: root.muted; font.pixelSize: 12 }
                }
                RowLayout {
                    spacing: 10
                    Text { text: "Хоткей (необов'язково)"; color: root.muted; font.pixelSize: 12 }
                    CheremshaKeycap {
                        keyText: root.addHotkeyDraft
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.addHotkeyDraft !== "") root.addHotkeyDraft = "";
                                else addCaptureZone.forceActiveFocus();
                            }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }

                // Invisible focus target that captures the next key press.
                Item {
                    id: addCaptureZone
                    Layout.fillWidth: true
                    Layout.preferredHeight: 8
                    Keys.onPressed: function (event) {
                        if (event.key === Qt.Key_Escape) {
                            event.accepted = true; // keep the modal open, just drop capture focus
                            addCaptureZone.activeFocus = false;
                            return;
                        }
                        var combo = root._comboFromEvent(event);
                        if (combo !== "") {
                            event.accepted = true;
                            root.addHotkeyDraft = combo;
                        }
                    }
                }
                Text {
                    id: addErrText
                    visible: false
                    text: "Файл відхилено (формат або розмір)"
                    color: "#f87171"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                }
            }
        }

        footer: Component {
            RowLayout {
                spacing: 10
                Item { Layout.fillWidth: true }
                Button {
                    text: "Скасувати"
                    onClicked: addModal.closeRequested()
                    background: Rectangle { radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge }
                }
                Button {
                    id: addSaveBtn
                    text: "Додати"
                    onClicked: root._saveAddSound()
                    background: Rectangle { radius: 8; color: root.primaryPurple }
                }
            }
        }
    }

    // ---- Edit-sound modal (spec §42 menu → Редагувати) ----
    CheremshaModal {
        id: editModal
        anchors.fill: parent
        title: "Редагувати звук"
        opened: root.showEditModal
        onCloseRequested: { root.showEditModal = false; }

        body: Component {
            ColumnLayout {
                spacing: 8
                Text { text: "Назва"; color: root.muted; font.pixelSize: 12; Layout.fillWidth: true }
                TextField {
                    id: editNameField
                    Layout.fillWidth: true
                    color: root.ink
                    background: Rectangle { radius: 8; color: root.fieldBg; border.width: 1; border.color: root.cardEdge }
                }
                Text { text: "Категорія"; color: root.muted; font.pixelSize: 12; Layout.fillWidth: true }
                ComboBox {
                    id: editCatBox
                    Layout.fillWidth: true
                    model: ["Меми", "Реакції", "Голоси", "Музика", "Атмосфера", "Ігри", "Alerts", "Custom"]
                }
                RowLayout {
                    spacing: 10
                    Text { text: "Об'єм"; color: root.muted; font.pixelSize: 12 }
                    Slider { id: editVolSlider; Layout.fillWidth: true; from: 0.0; to: 1.0 }
                    Text { text: Math.round(editVolSlider.value * 100) + "%"; color: root.muted; font.pixelSize: 12 }
                }
                RowLayout {
                    spacing: 10
                    Text { text: "Кулдаун, с"; color: root.muted; font.pixelSize: 12 }
                    SpinBox { id: editCooldownSpin; Layout.preferredWidth: 90; from: 0; to: 300; stepSize: 1 }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    spacing: 10
                    Text { text: "Режим відтворення"; color: root.muted; font.pixelSize: 12 }
                    ComboBox {
                        id: editModeBox
                        Layout.preferredWidth: 160
                        model: ["restart", "overlap", "replace", "queue"]
                    }
                    CheckBox {
                        id: editEnabledCheck
                        text: "Увімкнено"
                    }
                }
            }
        }

        footer: Component {
            RowLayout {
                spacing: 10
                Item { Layout.fillWidth: true }
                Button {
                    text: "Скасувати"
                    onClicked: editModal.closeRequested()
                    background: Rectangle { radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge }
                }
                Button {
                    id: editSaveBtn
                    text: "Зберегти"
                    onClicked: root._saveEditSound()
                    background: Rectangle { radius: 8; color: root.primaryPurple }
                }
            }
        }

        Connections {
            target: editModal
            function onOpenedChanged() {
                if (editModal.opened) {
                    editNameField.text = root.editName;
                    editCatBox.currentIndex = Math.max(0, editCatBox.model.indexOf(root.editCategory));
                    editVolSlider.value = root.editVolume;
                    editCooldownSpin.value = root.editCooldown;
                    editModeBox.currentIndex = Math.max(0, editModeBox.model.indexOf(root.editMode));
                    editEnabledCheck.checked = root.editEnabled;
                }
            }
        }
    }

    // ---- Hotkey capture modal (spec §7) ----
    CheremshaModal {
        id: hotkeyModal
        anchors.fill: parent
        title: "Призначити хоткей"
        subtitle: root._soundNameById(root.hotkeyTargetId) || ""
        opened: root.showHotkeyModal
        onCloseRequested: { root.showHotkeyModal = false; }

        body: Component {
            ColumnLayout {
                spacing: 12
                RowLayout {
                    spacing: 10
                    Text { text: "Натисніть комбінацію клавіш:"; color: root.muted; font.pixelSize: 13 }
                    CheremshaKeycap { keyText: root.capturedCombo }
                }

                // Invisible focus target that captures the next key press.
                Item {
                    id: captureZone
                    Layout.fillWidth: true
                    Layout.preferredHeight: 8
                    focus: hotkeyModal.opened && root.conflictOwnerId === ""
                    Keys.onPressed: function (event) {
                        if (event.key === Qt.Key_Escape) return; // modal handles Esc
                        var combo = root._comboFromEvent(event);
                        if (combo !== "") {
                            event.accepted = true;
                            root.capturedCombo = combo;
                            root.conflictOwnerId = "";
                            root._applyCapturedHotkey();
                        }
                    }
                }

                RowLayout {
                    visible: root.conflictOwnerId !== ""
                    spacing: 10
                    Text {
                        text: root.capturedCombo + " вже призначено: " + root._soundNameById(root.conflictOwnerId)
                        color: "#fbbf24"
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    visible: root.capturedCombo !== "" && root.conflictOwnerId === ""
                    spacing: 8
                    Text { text: "Призначено: " + root.capturedCombo; color: "#22c55e"; font.pixelSize: 13 }
                }

                RowLayout {
                    visible: root.conflictOwnerId !== ""
                    spacing: 10
                    Button {
                        id: replaceBtn
                        text: "Замінити"
                        onClicked: {
                            spApi.clearHotkey(root.conflictOwnerId);
                            var res = spApi.assignHotkey(root.hotkeyTargetId, root.capturedCombo);
                            if (res === "ok") root.showHotkeyModal = false;
                        }
                        background: Rectangle { radius: 8; color: root.primaryPurple }
                    }
                    Button {
                        text: "Скасувати"
                        onClicked: hotkeyModal.closeRequested()
                        background: Rectangle { radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge }
                    }
                }

                RowLayout {
                    spacing: 10
                    Item { Layout.fillWidth: true }
                    Button {
                        id: clearHkBtn
                        text: "Очистити"
                        onClicked: spApi.clearHotkey(root.hotkeyTargetId)
                        background: Rectangle { radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge }
                    }
                }
            }
        }

        Connections {
            target: hotkeyModal
            function onOpenedChanged() {
                if (hotkeyModal.opened) captureZone.forceActiveFocus();
            }
        }
    }

    // ---- spApi wiring ----
    Connections {
        target: spApi
        function onSoundsChanged() { root.refresh(); }
        function onImportNeeded(fileUrl) { root.openAddModal(String(fileUrl)); }
        function onNowPlayingChanged(id, position, duration) {
            if (id === root.nowPlayingId || root.nowPlayingId === "") {
                root.npPosition = Number(position) || 0.0;
                root.npDuration = Number(duration) || 0.0;
            }
        }
    }

    Component.onCompleted: {
        root.refresh();
        var st = null;
        try { st = JSON.parse(spApi.globalStateJson()); } catch (err) { st = null; }
        if (!st) return;
        if (typeof st.volume === "number") volSlider.value = st.volume;
        if (typeof st.monitor === "boolean") monitorCheck.checked = st.monitor;
        if (typeof st.stream_out === "boolean") streamOutCheck.checked = st.stream_out;
        if (typeof st.output_device === "string" && st.output_device !== "") {
            var idx = outBox.model.indexOf(st.output_device);
            if (idx >= 0) outBox.currentIndex = idx;
        }
    }
}
