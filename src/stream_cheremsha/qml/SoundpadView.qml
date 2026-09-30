import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// SOUNDPAD — premium streamer performance console.
// Composition: PageHeader / Toolbar / SoundGrid / NowPlayingBar.
// Backend contract unchanged (spApi slots/signals + refresh() logic).
Item {
    id: root
    implicitWidth: 800
    implicitHeight: 900

    property bool enterPulse: false
    onEnterPulseChanged: enterFade.restart()
    NumberAnimation {
        id: enterFade
        target: root
        property: "opacity"
        from: 0.97; to: 1.0; duration: 120
        easing.type: Easing.OutCubic
    }

    readonly property color base: "#080d18"
    readonly property color cardBase: "#101827"
    readonly property color cardEdge: "#26314a"
    readonly property color ink: "#e8ecf5"
    readonly property color muted: "#7f8aa3"
    readonly property color fieldBg: "#0c0f16"
    readonly property color primaryPurple: "#9b5cff"
    readonly property color secondaryCyan: "#20d7f5"

    // ---- State (stable contract names) ----
    // Internal sentinel for the "All categories" chip — never displayed raw;
    // the visible label comes from spApi.strings.category_all.
    readonly property string allCat: "__all__"
    property string selectedCategory: root.allCat
    property string query: ""
    property var categoryList: []
    property var _allItems: []
    property var _wasPlaying: ({})

    property string pendingFileUrl: ""
    property string addHotkeyDraft: ""
    property bool showAddModal: false
    property string suggestedName: ""
    property string addDraftName: ""
    property string addDraftCategory: "Меми"
    property double addDraftVolume: 1.0
    property string addDraftMode: "restart"
    property bool addListening: false
    property string addConflictOwner: ""
    property string addErrorMsg: ""
    property bool showLibraryModal: false

    property string relinkTargetId: ""

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

    property string nowPlayingId: ""
    property double npPosition: 0.0
    property double npDuration: 0.0
    property double globalVol: 0.78
    property var outputModel: []
    property int outputIndex: -1
    property bool dragHover: false

    ListModel { id: soundModel }

    function _matches(it) {
        if (root.selectedCategory !== root.allCat && it.category !== root.selectedCategory) return false;
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
        return [root.allCat].concat(out);
    }

    // Full grid rebuilds are expensive (JSON + model + delegates) and a
    // single press fires several (started/finished/API emits) synchronously
    // on the GUI thread BEFORE the audio task runs — each one delays audible
    // output 1:1. Coalesce bursts into one rebuild per 50ms window.
    property bool _refreshDirty: false
    function refresh() {
        if (refreshCoalescer.running) { root._refreshDirty = true; return; }
        root._refreshDirty = false;
        refreshCoalescer.start();
        root.refreshNow();
    }

    function refreshNow() {
        var prevPlaying = {};
        for (var p = 0; p < root._allItems.length; ++p)
            if (root._allItems[p].playing) prevPlaying[root._allItems[p].id] = true;
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
        cooldownTimers.clear();
        for (var j = 0; j < root._allItems.length; ++j) {
            var it2 = root._allItems[j];
            if (!it2.playing && (Number(it2.cooldown_sec) || 0) > 0) {
                var waitMs = root._cooldownLeftFor(it2) * 1000;
                if (waitMs > 50) cooldownTimers.append({ delayMs: Math.ceil(waitMs), tag: it2.id });
            }
        }
        // Global-hotkey feedback: newly playing cards flash even if window unfocused.
        for (var f = 0; f < root._allItems.length; ++f) {
            var it3 = root._allItems[f];
            if (it3.playing && !prevPlaying[it3.id]) {
                root._flashCard(it3.id);
                break;
            }
        }
    }

    function _flashCard(sid) {
        for (var i = 0; i < gridRepeater.count; ++i) {
            var item = gridRepeater.itemAt(i);
            if (item && item.soundId === sid) { item.flashHotkey(); break; }
        }
    }

    function closeOtherMenus(exceptId) {
        for (var i = 0; i < gridRepeater.count; ++i) {
            var item = gridRepeater.itemAt(i);
            if (item && item.soundId !== exceptId) item.menuOpen = false;
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
    function _npCategory() {
        for (var i = 0; i < root._allItems.length; ++i)
            if (root._allItems[i].id === root.nowPlayingId) return root._allItems[i].category || "";
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
        root.suggestedName = root._stemFromUrl(root.pendingFileUrl);
        root.addDraftName = root.suggestedName;
        root.addDraftCategory = "Меми";
        root.addDraftVolume = 1.0;
        root.addDraftMode = "restart";
        root.addListening = false;
        root.addConflictOwner = "";
        root.addErrorMsg = "";
        root.showAddModal = true;
    }

    function _relinkSound(fileUrl) {
        var sid = String(root.relinkTargetId || "");
        root.relinkTargetId = "";
        if (sid === "") return;
        var it = null;
        for (var i = 0; i < root._allItems.length; ++i) {
            if (root._allItems[i].id === sid) { it = root._allItems[i]; break; }
        }
        if (!it) return;
        var hk = it.hotkey || "";
        var newSid = spApi.addSound(String(fileUrl), it.name || "", it.category || "Custom",
                                    hk, Number(it.volume) || 1.0,
                                    it.playback_mode || "restart");
        if (newSid === "") return;
        spApi.removeSound(sid);
        if (hk !== "") spApi.assignHotkey(newSid, hk);
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

    // Live conflict check for the add-dialog draft (warn, don't block:
    // saving keeps the sound and drops the hotkey, like the backend).
    function _refreshAddConflict() {
        if (root.addHotkeyDraft === "") root.addConflictOwner = "";
        else root.addConflictOwner = String(spApi.hotkeyOwnerName(root.addHotkeyDraft) || "");
    }

    function _saveAddSound() {
        if (root.pendingFileUrl === "") {
            root.showAddModal = false;
            root.addListening = false;
            return;
        }
        var sid = spApi.addSound(root.pendingFileUrl, String(root.addDraftName).trim(),
                                 root.addDraftCategory, root.addHotkeyDraft,
                                 Number(root.addDraftVolume), root.addDraftMode);
        if (sid !== "") {
            root.showAddModal = false;
            root.addListening = false;
            root.pendingFileUrl = "";
            root.addHotkeyDraft = "";
            root.addConflictOwner = "";
            root.addErrorMsg = "";
        } else {
            root.addErrorMsg = spApi.strings.add_error_file || "Файл відхилено (формат або розмір)";
        }
    }

    function _saveEditSound() {
        var patch = {
            name: String(root.editName).trim(),
            category: root.editCategory,
            volume: Number(root.editVolume),
            cooldown_sec: Number(root.editCooldown),
            playback_mode: root.editMode,
            enabled: !!root.editEnabled
        };
        spApi.updateSoundJson(root.editingSoundId, JSON.stringify(patch));
        root.showEditModal = false;
    }

    function gridColumns() {
        if (root.width >= 1700) return 6;
        if (root.width >= 1400) return 5;
        if (root.width >= 1100) return 4;
        if (root.width >= 800) return 3;
        return 2;
    }

    // ---- Background ----
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b1120" }
            GradientStop { position: 0.55; color: "#080d18" }
            GradientStop { position: 1.0; color: "#060910" }
        }
    }

    DropArea {
        anchors.fill: parent
        onEntered: root.dragHover = true
        onExited: root.dragHover = false
        onDropped: function (drop) {
            root.dragHover = false;
            var urls = [];
            if (drop.hasUrls) {
                for (var i = 0; i < drop.urls.length; ++i) urls.push(drop.urls[i].toString());
            }
            spApi.importDroppedUrls(JSON.stringify(urls));
        }
    }

    // Native system picker via backend (same convention as actions API).
    function pickAndAdd() {
        var url = String(spApi.pickAudioFile() || "");
        if (url !== "") root.openAddModal(url);
    }

    function pickAndRelink() {
        var url = String(spApi.pickAudioFile() || "");
        if (url !== "") root._relinkSound(url);
    }

    // ============ PAGE COMPOSITION ============
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 22
        anchors.rightMargin: 22
        anchors.topMargin: 20
        anchors.bottomMargin: 0
        spacing: 0

        // ---- PageHeader ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            spacing: 12
            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                radius: 10
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#8b5cf6" }
                    GradientStop { position: 1.0; color: "#6d28d9" }
                }
                border.width: 1
                border.color: "#a78bfa"
                Image {
                    anchors.centerIn: parent
                    source: Qt.resolvedUrl("../assets/icons/web_music.svg")
                    width: 20; height: 20
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: spApi.strings.title || "Soundpad"; color: root.ink; font.pixelSize: 29; font.weight: Font.Bold }
                Text {
                    text: spApi.strings.subtitle || "Миттєві звуки, хоткеї та аудіо-реакції для стріму"
                    color: root.muted; font.pixelSize: 13
                }
            }
            // compact search with icon + focus ring
            Rectangle {
                Layout.preferredWidth: 250
                Layout.preferredHeight: 38
                radius: 9
                color: root.fieldBg
                border.width: 1
                border.color: headerSearchField.activeFocus ? root.primaryPurple : root.cardEdge
                Behavior on border.color { ColorAnimation { duration: 130 } }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Image { source: Qt.resolvedUrl("../assets/icons/web_search.svg"); width: 15; height: 15; opacity: 0.7 }
                    TextField {
                        id: headerSearchField
                        Layout.fillWidth: true
                        placeholderText: spApi.strings.search_ph || "Пошук звуків…"
                        placeholderTextColor: "#4b5568"
                        color: root.ink
                        selectionColor: "#7c4fee"
                        font.pixelSize: 13
                        onTextChanged: { root.query = text; root.refresh(); }
                        background: null
                    }
                }
            }
            // library (MyInstants) — secondary action, outline style
            Button {
                id: libraryBtn
                text: spApi.libraryStrings.button || "Бібліотека"
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 13
                implicitWidth: 140
                implicitHeight: 38
                contentItem: RowLayout {
                    spacing: 7
                    Image { source: Qt.resolvedUrl("../assets/icons/book.svg"); width: 15; height: 15 }
                    Text { text: libraryBtn.text; color: "#c7d2e5"; font: libraryBtn.font }
                }
                background: Rectangle {
                    radius: 9
                    color: libraryBtn.hovered ? "#141d30" : "transparent"
                    border.width: 1
                    border.color: libraryBtn.hovered ? "#7c3aed" : "#26314a"
                    Behavior on border.color { ColorAnimation { duration: 130 } }
                }
                scale: libraryBtn.pressed ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: 100 } }
                onClicked: { spApi.openLibrary(); root.showLibraryModal = true; }
            }
            // primary add
            Button {
                id: addBtn
                text: spApi.strings.add_button || "+ Додати звук"
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 13
                font.bold: true
                implicitWidth: 150
                implicitHeight: 38
                contentItem: Text {
                    text: addBtn.text; color: "white"; font: addBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: addBtn.pressed ? "#7c3aed" : (addBtn.hovered ? "#9d71f7" : root.primaryPurple) }
                        GradientStop { position: 1.0; color: addBtn.pressed ? "#6d28d9" : (addBtn.hovered ? "#8b5cf6" : "#7c3aed") }
                    }
                    border.width: 1
                    border.color: addBtn.hovered ? "#a78bfa" : "#8b54f5"
                }
                scale: addBtn.pressed ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: 100 } }
                onClicked: root.pickAndAdd()
            }
        }

        Item { Layout.preferredHeight: 18 }

        // ---- Toolbar: category chips + count ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            spacing: 10
            Flickable {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                contentWidth: chipsRow.width
                contentHeight: 32
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Row {
                    id: chipsRow
                    spacing: 8
                    Repeater {
                        model: root.categoryList
                        delegate: CheremshaCategoryChip {
                            text: modelData === root.allCat ? (spApi.strings.category_all || "Усі") : modelData
                            active: root.selectedCategory === modelData
                            onClicked: { root.selectedCategory = modelData; root.refresh(); }
                        }
                    }
                }
            }
            Text {
                visible: soundModel.count > 0
                text: (spApi.strings.count || "{n} звуків").replace("{n}", String(soundModel.count))
                color: "#5b6472"
                font.pixelSize: 12
            }
        }

        Item { Layout.preferredHeight: 16 }

        // ---- SoundGrid (primary visual, 70-80% attention) ----
        ScrollView {
            id: pageScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ColumnLayout {
                width: pageScroll.availableWidth
                spacing: 0

                CheremshaResponsiveCardGrid {
                    Layout.fillWidth: true
                    visible: soundModel.count > 0
                    columns: root.gridColumns()
                    columnSpacing: 16
                    rowSpacing: 16

                    Repeater {
                        id: gridRepeater
                        model: soundModel
                        delegate: CheremshaSoundCard {
                            id: sndCard
                            Layout.fillWidth: true
                            implicitHeight: 178
                            soundId: model.id
                            soundName: model.name
                            category: model.category
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
                            onMenuOpened: root.closeOtherMenus(sndCard.soundId)
                            onRetryRequested: root.refresh()
                            onRelinkRequested: {
                                root.relinkTargetId = sndCard.soundId;
                                root.pickAndRelink();
                            }
                        }
                    }
                }

                // content-area empty state (between toolbar and player, not app-centered)
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 320
                    visible: root._allItems.length === 0
                    SoundpadEmptyState {
                        anchors.centerIn: parent
                        width: 500
                        height: 260
                        dragHover: root.dragHover
                        onAddRequested: root.pickAndAdd()
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 40
                    visible: root._allItems.length > 0 && soundModel.count === 0
                    text: spApi.strings.no_results || "Нічого не знайдено"
                    color: root.muted
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                }

                Item { Layout.preferredHeight: 12 }
            }
        }

        Item { Layout.preferredHeight: 12 }

        // ---- NowPlayingBar ----
        SoundpadNowPlaying {
            Layout.fillWidth: true
            Layout.preferredHeight: 68
            Layout.bottomMargin: 14
            trackName: root._npName()
            trackCategory: root._npCategory()
            active: root.nowPlayingId !== ""
            position: root.npPosition
            duration: root.npDuration
            volume: root.globalVol
            outputModel: root.outputModel
            outputIndex: root.outputIndex
            onVolumeRequested: function (v) { root.globalVol = v; spApi.setGlobalVolume(v); }
            onOutputPicked: function (idx) {
                root.outputIndex = idx;
                if (idx >= 0 && idx < root.outputModel.length) spApi.setOutputDevice(root.outputModel[idx]);
            }
            onStopRequested: spApi.stopSound(root.nowPlayingId)
        }
    }

    // ---- Refresh coalescer (see refresh()) ----
    Timer {
        id: refreshCoalescer
        interval: 50
        repeat: false
        onTriggered: {
            if (root._refreshDirty) { root._refreshDirty = false; root.refreshNow(); }
        }
    }

    // ---- One-shot cooldown expiry timers ----
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

    // ---- Add-sound modal ----
    CheremshaModal {
        id: addModal
        anchors.fill: parent
        title: spApi.strings.add_title || "Додати звук"
        subtitle: (spApi.strings.add_subtitle || "Додайте звук до Soundpad · {name}")
                   .replace("{name}", root._stemFromUrl(root.pendingFileUrl) || "")
        opened: root.showAddModal
        onCloseRequested: { root.showAddModal = false; root.addListening = false; }

        body: Component {
            SoundpadAddDialog {
                draftName: root.addDraftName
                draftCategory: root.addDraftCategory
                draftVolume: root.addDraftVolume
                draftMode: root.addDraftMode
                hotkeyDraft: root.addHotkeyDraft
                listening: root.addListening
                conflictText: root.addConflictOwner
                errorMsg: root.addErrorMsg
                onNameChanged2: function (v) { root.addDraftName = v; }
                onCategoryChanged2: function (v) { root.addDraftCategory = v; }
                onVolumeChanged2: function (v) { root.addDraftVolume = v; }
                onModeChanged2: function (v) { root.addDraftMode = v; }
                onStartListening: {
                    root.addListening = true;
                    addCaptureZone.forceActiveFocus();
                }
                onClearHotkey: {
                    root.addHotkeyDraft = "";
                    root.addConflictOwner = "";
                    root.addListening = false;
                }
            }
        }

        footer: Component {
            RowLayout {
                spacing: 10
                Item { Layout.fillWidth: true }
                Button {
                    text: spApi.strings.cancel || "Скасувати"
                    hoverEnabled: true
                    focusPolicy: Qt.TabFocus
                    font.pixelSize: 13
                    implicitWidth: 120
                    implicitHeight: 38
                    contentItem: Text {
                        text: parent.text; color: "#b8c1cf"; font: parent.font
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9; color: parent.hovered ? "#141c2c" : "#0a0f19"
                        border.width: 1; border.color: parent.hovered ? "#4b5876" : "#232d42"
                    }
                    onClicked: addModal.closeRequested()
                }
                Button {
                    text: spApi.strings.add_title || "Додати звук"
                    hoverEnabled: true
                    focusPolicy: Qt.TabFocus
                    font.pixelSize: 13
                    font.bold: true
                    implicitWidth: 150
                    implicitHeight: 38
                    contentItem: Text {
                        text: parent.text; color: "white"; font: parent.font
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9; color: parent.hovered ? "#a37bff" : root.primaryPurple
                        border.width: 1; border.color: "#8b54f5"
                    }
                    onClicked: root._saveAddSound()
                }
            }
        }
    }

    // ---- Library modal (MyInstants) ----
    CheremshaModal {
        id: libraryModal
        anchors.fill: parent
        preferredWidth: 780
        title: spApi.libraryStrings.title || "Бібліотека звуків"
        subtitle: spApi.libraryStrings.subtitle || ""
        opened: root.showLibraryModal
        onCloseRequested: { root.showLibraryModal = false; spApi.stopPreview(); }

        body: Component {
            SoundpadLibraryPanel {}
        }
    }

    // Hotkey capture for the add dialog: active ONLY while the user
    // explicitly armed it (listening). Otherwise key presses are ignored.
    Item {
        id: addCaptureZone
        objectName: "addCaptureZone"
        width: 1; height: 1
        focus: root.addListening && root.showAddModal
        Keys.onPressed: function (event) {
            if (!root.addListening || !root.showAddModal) return;
            if (event.key === Qt.Key_Escape) {
                event.accepted = true;
                root.addListening = false;
                return;
            }
            var combo = root._comboFromEvent(event);
            if (combo !== "") {
                event.accepted = true;
                root.addHotkeyDraft = combo;
                root.addListening = false;
                root._refreshAddConflict();
            }
        }
    }

    // ---- Edit-sound modal (compact grouped, same language) ----
    CheremshaModal {
        id: editModal
        anchors.fill: parent
        title: spApi.strings.edit_title || "Редагувати звук"
        subtitle: root.editName || ""
        opened: root.showEditModal
        onCloseRequested: { root.showEditModal = false; }

        body: Component {
            ColumnLayout {
                spacing: 10
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 40
                    radius: 9; color: "#0c0f16"
                    border.width: 1
                    border.color: editNameField.activeFocus ? "#8b5cf6" : "#26314a"
                    TextField {
                        id: editNameField
                        anchors.fill: parent
                        anchors.leftMargin: 12; anchors.rightMargin: 12
                        text: root.editName
                        onTextChanged: root.editName = text
                        color: root.ink; font.pixelSize: 13
                        background: null
                    }
                }
                ComboBox {
                    id: editCatBox
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    model: ["Меми", "Реакції", "Голоси", "Музика", "Атмосфера", "Ігри", "Alerts", "Custom"]
                    currentIndex: Math.max(0, editCatBox.model.indexOf(root.editCategory))
                    onActivated: root.editCategory = currentText
                    font.pixelSize: 13
                    delegate: ItemDelegate {
                        width: ListView.view ? ListView.view.width : implicitWidth
                        contentItem: Text {
                            text: modelData
                            color: parent.highlighted ? "#ffffff" : "#c9d1e0"
                            font.pixelSize: 13
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 6
                            color: parent.highlighted ? "#8b5cf6" : (parent.hovered ? "#1c2434" : "transparent")
                        }
                        highlighted: editCatBox.highlightedIndex === index
                    }
                    contentItem: Text {
                        leftPadding: 12; rightPadding: 30
                        text: editCatBox.displayText; color: "#e8ecf5"; font: editCatBox.font
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9; color: "#0c0f16"
                        border.width: 1; border.color: editCatBox.hovered ? "#4b5876" : "#26314a"
                    }
                    indicator: Image {
                        x: editCatBox.width - width - 12; y: (editCatBox.height - height) / 2
                        source: Qt.resolvedUrl("../assets/icons/chevron-down.svg")
                        width: 14; height: 14
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 52
                    radius: 9; color: "#101827"
                    border.width: 1; border.color: "#1e2942"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 10
                        Text { text: spApi.strings.volume_label || "Гучність"; color: "#9aa4b8"; font.pixelSize: 12 }
                        CheremshaSlider {
                            id: editVolSlider
                            Layout.fillWidth: true
                            from: 0; to: 1; value: root.editVolume
                            onValueChanged: root.editVolume = value
                        }
                        Text { text: Math.round(editVolSlider.value * 100) + "%"; color: "#7f8aa3"; font.pixelSize: 12 }
                    }
                }
                RowLayout {
                    spacing: 10
                    Text { text: spApi.strings.cooldown_label || "Кулдаун, с"; color: "#9aa4b8"; font.pixelSize: 12 }
                    SpinBox {
                        id: cdSpin
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        from: 0
                        to: 300
                        stepSize: 1
                        editable: true
                        value: root.editCooldown
                        onValueChanged: root.editCooldown = Number(value)
                        font.pixelSize: 13
                        contentItem: TextInput {
                            z: 2
                            text: cdSpin.displayText
                            font: cdSpin.font
                            color: "#e8ecf5"
                            selectionColor: "#8b5cf6"
                            selectByMouse: true
                            horizontalAlignment: Qt.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            readOnly: !cdSpin.editable
                            validator: cdSpin.validator
                            inputMethodHints: Qt.ImhDigitsOnly
                        }
                        background: Rectangle {
                            radius: 9
                            color: "#0c0f16"
                            border.width: 1
                            border.color: cdSpin.activeFocus ? "#8b5cf6" : "#26314a"
                            Behavior on border.color { ColorAnimation { duration: 130 } }
                        }
                        up.indicator: Rectangle {
                            x: cdSpin.width - width - 4
                            y: 4
                            width: 30
                            height: cdSpin.height - 8
                            radius: 6
                            color: upHover.containsMouse ? "#232e45" : "transparent"
                            border.width: 1
                            border.color: upHover.containsMouse ? "#4b5876" : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Text { anchors.centerIn: parent; text: "+"; color: "#c9d1e0"; font.pixelSize: 16 }
                            MouseArea {
                                id: upHover
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                                cursorShape: Qt.PointingHandCursor
                            }
                        }
                        down.indicator: Rectangle {
                            x: 4
                            y: 4
                            width: 30
                            height: cdSpin.height - 8
                            radius: 6
                            color: downHover.containsMouse ? "#232e45" : "transparent"
                            border.width: 1
                            border.color: downHover.containsMouse ? "#4b5876" : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Text { anchors.centerIn: parent; text: "−"; color: "#c9d1e0"; font.pixelSize: 16 }
                            MouseArea {
                                id: downHover
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                                cursorShape: Qt.PointingHandCursor
                            }
                        }
                    }
                }
                Text { text: spApi.strings.mode_label || "Режим відтворення"; color: "#9aa4b8"; font.pixelSize: 12; Layout.fillWidth: true }
                ComboBox {
                    id: editModeBox
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    model: ["restart", "overlap", "replace", "queue", "hold"]
                    currentIndex: Math.max(0, editModeBox.model.indexOf(root.editMode))
                    onActivated: root.editMode = currentText
                    font.pixelSize: 13
                    contentItem: Text {
                        leftPadding: 12
                        rightPadding: 30
                        text: editModeBox.displayText
                        color: "#e8ecf5"
                        font: editModeBox.font
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    background: Rectangle {
                        radius: 9
                        color: "#0c0f16"
                        border.width: 1
                        border.color: editModeBox.hovered ? "#4b5876" : "#26314a"
                        Behavior on border.color { ColorAnimation { duration: 130 } }
                    }
                    indicator: Image {
                        x: editModeBox.width - width - 12
                        y: (editModeBox.height - height) / 2
                        source: Qt.resolvedUrl("../assets/icons/chevron-down.svg")
                        width: 14
                        height: 14
                    }
                    popup: Popup {
                        y: editModeBox.height + 4
                        width: editModeBox.width
                        background: Rectangle { radius: 9; color: "#0e1420"; border.width: 1; border.color: "#26314a" }
                        contentItem: ListView {
                            clip: true
                            implicitHeight: Math.min(220, contentHeight)
                            model: editModeBox.popup.visible ? editModeBox.delegateModel : null
                        }
                    }
                    delegate: ItemDelegate {
                        width: ListView.view ? ListView.view.width : implicitWidth
                        contentItem: Text {
                            text: modelData
                            color: parent.highlighted ? "#ffffff" : "#c9d1e0"
                            font.pixelSize: 13
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 6
                            color: parent.highlighted ? "#8b5cf6" : (parent.hovered ? "#1c2434" : "transparent")
                        }
                        highlighted: editModeBox.highlightedIndex === index
                    }
                }
                Text {
                    text: spApi.strings.edit_hint || "Кулдаун — пауза між запусками. Режим — що робити, якщо звук уже грає: restart / replace — почати спочатку, overlap — грати поверх, queue — стати в чергу, hold — повторювати, поки тримаєш хоткей."
                    color: "#5b6472"
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                CheremshaToggle {
                    label: spApi.strings.enabled || "Увімкнено"
                    checked: root.editEnabled
                    onToggled: root.editEnabled = on
                }
            }
        }

        footer: Component {
            RowLayout {
                spacing: 10
                Item { Layout.fillWidth: true }
                Button {
                    text: spApi.strings.cancel || "Скасувати"
                    hoverEnabled: true
                    implicitWidth: 120; implicitHeight: 38
                    contentItem: Text {
                        text: parent.text; color: "#b8c1cf"; font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9; color: parent.hovered ? "#141c2c" : "#0a0f19"
                        border.width: 1; border.color: "#232d42"
                    }
                    onClicked: editModal.closeRequested()
                }
                Button {
                    text: spApi.strings.save || "Зберегти"
                    hoverEnabled: true
                    font.bold: true
                    implicitWidth: 130; implicitHeight: 38
                    contentItem: Text {
                        text: parent.text; color: "white"; font.pixelSize: 13; font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle { radius: 9; color: parent.hovered ? "#a37bff" : root.primaryPurple }
                    onClicked: root._saveEditSound()
                }
            }
        }
    }

    // ---- Hotkey capture modal ----
    CheremshaModal {
        id: hotkeyModal
        anchors.fill: parent
        title: spApi.strings.hotkey_title || "Призначити хоткей"
        subtitle: root._soundNameById(root.hotkeyTargetId) || ""
        opened: root.showHotkeyModal
        onCloseRequested: { root.showHotkeyModal = false; }

        body: Component {
            ColumnLayout {
                spacing: 12
                Connections {
                    target: hotkeyModal
                    function onOpenedChanged() {
                        if (hotkeyModal.opened) captureZone.forceActiveFocus();
                    }
                }
                RowLayout {
                    spacing: 12
                    Text { text: spApi.strings.hotkey_prompt || "Натисніть комбінацію клавіш:"; color: root.muted; font.pixelSize: 13 }
                    CheremshaKeycap { keyText: root.capturedCombo }
                }
                Item {
                    id: captureZone
                    Layout.fillWidth: true
                    Layout.preferredHeight: 8
                    focus: hotkeyModal.opened && root.conflictOwnerId === ""
                    Keys.onPressed: function (event) {
                        if (event.key === Qt.Key_Escape) return;
                        var combo = root._comboFromEvent(event);
                        if (combo !== "") {
                            event.accepted = true;
                            root.capturedCombo = combo;
                            root.conflictOwnerId = "";
                            root._applyCapturedHotkey();
                        }
                    }
                }
                Text {
                    visible: root.conflictOwnerId !== ""
                    text: (spApi.strings.hotkey_conflict || "{combo} вже призначено: {name}")
                           .replace("{combo}", root.capturedCombo)
                           .replace("{name}", root._soundNameById(root.conflictOwnerId))
                    color: "#fbbf24"; font.pixelSize: 13
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                }
                Text {
                    visible: root.capturedCombo !== "" && root.conflictOwnerId === ""
                    text: (spApi.strings.hotkey_assigned || "Призначено: {combo}")
                           .replace("{combo}", root.capturedCombo)
                    color: "#22c55e"; font.pixelSize: 13
                }
                RowLayout {
                    visible: root.conflictOwnerId !== ""
                    spacing: 10
                    Button {
                        text: spApi.strings.hotkey_replace || "Замінити"
                        hoverEnabled: true
                        implicitWidth: 120; implicitHeight: 36
                        contentItem: Text {
                            text: parent.text; color: "white"; font.pixelSize: 13; font.bold: true
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle { radius: 8; color: parent.hovered ? "#a37bff" : root.primaryPurple }
                        onClicked: {
                            spApi.clearHotkey(root.conflictOwnerId);
                            var res = spApi.assignHotkey(root.hotkeyTargetId, root.capturedCombo);
                            if (res === "ok") root.showHotkeyModal = false;
                        }
                    }
                    Button {
                        text: spApi.strings.cancel || "Скасувати"
                        hoverEnabled: true
                        implicitWidth: 120; implicitHeight: 36
                        contentItem: Text {
                            text: parent.text; color: "#b8c1cf"; font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge
                        }
                        onClicked: hotkeyModal.closeRequested()
                    }
                }
                RowLayout {
                    spacing: 10
                    Item { Layout.fillWidth: true }
                    Button {
                        text: spApi.strings.hotkey_clear || "Очистити"
                        hoverEnabled: true
                        implicitWidth: 110; implicitHeight: 36
                        contentItem: Text {
                            text: parent.text; color: "#b8c1cf"; font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 8; color: "#1c2434"; border.width: 1; border.color: root.cardEdge
                        }
                        onClicked: spApi.clearHotkey(root.hotkeyTargetId)
                    }
                }
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
        try { root.outputModel = JSON.parse(spApi.outputDevices()); } catch (err2) { root.outputModel = []; }
        if (!st) return;
        if (typeof st.volume === "number") root.globalVol = st.volume;
        if (typeof st.output_device === "string" && st.output_device !== "") {
            var idx = root.outputModel.indexOf(st.output_device);
            if (idx >= 0) root.outputIndex = idx;
        }
    }
}
