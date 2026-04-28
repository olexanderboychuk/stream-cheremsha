import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    // Let the hosting QQuickView control the actual size (adaptive on resize).
    implicitWidth: 820
    implicitHeight: 560

    // Provided by MainWindow when opening the editor.
    property string platform: ""
    property string accountKey: ""

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"

    Rectangle { anchors.fill: parent; color: base }

    property var rulesModel: []
    property int selectedIdx: -1
    property var selectedRule: null
    property var giftOptions: []
    property var actionsModel: []
    property int selectedActionIdx: -1
    property bool isActionTextEditing: false
    // true while we set event/gift comboboxes from the rule; blocks onActivated/onAccepted
    // (Qt can emit them when currentIndex is set, which re-saved the same state to all rows).
    property bool _suppressRuleCombos: false

    Timer {
        id: ruleCombosSuppressEnd
        interval: 1
        repeat: false
        onTriggered: root._suppressRuleCombos = false
    }

    Timer {
        id: actionsAutosaveTimer
        interval: 800
        repeat: false
        onTriggered: {
            // Never rebuild the model while the user is typing, otherwise focus is lost.
            if (root.isActionTextEditing) {
                actionsAutosaveTimer.restart();
                return;
            }
            root._commitSelectedRuleActions(false);
        }
    }

    property bool _savedToastVisible: false

    Timer {
        id: savedToastTimer
        interval: 1400
        repeat: false
        onTriggered: root._savedToastVisible = false
    }

    function _notifySaved() {
        root._savedToastVisible = true;
        savedToastTimer.restart();
    }

    function _restoreScrollIfPossible(flickable, y) {
        if (!flickable) return;
        if (y === undefined || y === null) return;
        // Defer until after bindings/layout settle.
        Qt.callLater(function() {
            if (!flickable) return;
            var maxY = Math.max(0, (flickable.contentHeight || 0) - (flickable.height || 0));
            flickable.contentY = Math.max(0, Math.min(y, maxY));
        });
    }

    function _preserveScroll(fn) {
        var leftY = rulesList ? rulesList.contentY : 0;
        var rightF = rightScroll ? rightScroll.contentItem : null;
        var rightY = rightF ? rightF.contentY : 0;
        fn();
        _restoreScrollIfPossible(rulesList, leftY);
        _restoreScrollIfPossible(rightF, rightY);
    }

    function _commitSelectedRuleActions(showToast) {
        if (selectedRule === null) return;
        var r;
        var a;
        try { r = JSON.parse(JSON.stringify(selectedRule)); } catch (e) { return; }
        try { a = JSON.parse(JSON.stringify(actionsModel)); } catch (e2) { a = []; }
        r.actions = a;
        root._preserveScroll(function() {
            _setRule(selectedIdx, r);
            _save(!!showToast);
        });
    }

    function _scheduleCommitSelectedRuleActions() {
        actionsAutosaveTimer.restart();
    }

    readonly property var actionTypeModel: [
        { text: api ? api.loc("actions.play_sound") : "Play sound", value: "play_sound" },
        { text: api ? api.loc("actions.write_file") : "Write to file", value: "write_file" },
        { text: api ? api.loc("actions.run_program") : "Run program", value: "run_program" },
        { text: api ? api.loc("actions.speak_tts") : "Speak text (TTS)", value: "speak_tts" }
    ]

    function _actionTypeIndex(t) {
        var raw = (t || "play_sound");
        var v = (raw === "run_exe") ? "run_program" : raw;
        for (var i = 0; i < actionTypeModel.length; i++) {
            if (actionTypeModel[i].value === v) return i;
        }
        return 0;
    }

    component ConnPillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property color colRest: "#1c2434"
        property color colHover: "#263246"
        property color colPress: "#303a50"
        property color borRest: root.cardEdge
        property color borHover: "#3b4458"
        hoverEnabled: true
        font.pixelSize: pillFontSize
        contentItem: Text {
            text: pillCtl.text
            color: root.ink
            font.pixelSize: pillCtl.pillFontSize
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 8
            color: pillCtl.pressed ? pillCtl.colPress : (pillCtl.hovered ? pillCtl.colHover : pillCtl.colRest)
            border.width: 1
            border.color: pillCtl.hovered ? pillCtl.borHover : pillCtl.borRest
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    component ConnComboBox: ComboBox {
        id: cb
        hoverEnabled: true
        font.pixelSize: 13
        padding: 10
        contentItem: Text {
            text: cb.displayText
            color: root.ink
            font.pixelSize: cb.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: root.fieldBg
            border.width: 1
            border.color: cb.hovered ? "#3b4458" : root.cardEdge
        }
        delegate: ItemDelegate {
            width: ListView.view ? ListView.view.width : implicitWidth
            contentItem: Text {
                text: cb.textRole ? (modelData[cb.textRole] || "") : (modelData || "")
                color: root.ink
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 6
                color: highlighted ? "#1a2232" : "#111827"
            }
        }
    }

    // _copyRule / _setRule: JSON round-trip so list rows never share one object
    // (e.g. duplicate had re-inserted the same ref; one gift edit touched every row).
    function _copyRule(rule) {
        if (rule == null) return null;
        try { return JSON.parse(JSON.stringify(rule)); } catch (e) { return null; }
    }

    function _cloneOrEmptyRule(src) {
        var o = _copyRule(src);
        if (o) return o;
        return { id: ("" + Math.random()).slice(2), name: "", enabled: true,
            event: root._chatEvent({ text: "", match: "contains", case_sensitive: false }),
            actions: [] };
    }

    // Never mutate r.event / r.event.params in place: separate rules can share references.
    // Always replace event with a fresh object tree.
    function _chatEvent(p) {
        return {
            type: "chat_keyword",
            params: {
                text: p.text != null && p.text !== undefined ? p.text : "",
                match: p.match || "contains",
                case_sensitive: !!p.case_sensitive
            }
        };
    }

    function _giftEvent(p) {
        return {
            type: "gift_received",
            params: {
                gift_id: p.gift_id != null && p.gift_id !== undefined ? p.gift_id : "",
                gift_name: p.gift_name != null && p.gift_name !== undefined ? p.gift_name : "",
                min_count: p.min_count !== undefined && p.min_count !== null ? p.min_count : 1
            }
        };
    }

    function _syncSelected() {
        if (selectedIdx < 0 || selectedIdx >= rulesModel.length) {
            selectedRule = null;
            selectedIdx = -1;
            actionsModel = [];
            selectedActionIdx = -1;
            return;
        }
        // Force a change notification even if the rule reference is unchanged.
        selectedRule = null;
        selectedRule = rulesModel[selectedIdx];
        try {
            actionsModel = (selectedRule && selectedRule.actions)
                ? JSON.parse(JSON.stringify(selectedRule.actions)) : [];
        } catch (e) {
            actionsModel = [];
        }
        selectedActionIdx = actionsModel.length ? 0 : -1;
    }

    function _setRule(idx, ruleObj) {
        var full;
        try { full = JSON.parse(JSON.stringify(rulesModel)); }
        catch (e) { return; }
        if (idx < 0 || idx >= full.length) return;
        var one;
        try { one = JSON.parse(JSON.stringify(ruleObj)); }
        catch (e) { return; }
        full[idx] = one;
        root._preserveScroll(function() {
            rulesModel = full;
            _syncSelected();
        });
    }

    function _defaultRule() {
        return {
            id: ("" + Math.random()).slice(2),
            name: "",
            enabled: true,
            event: { type: "chat_keyword", params: { text: "", match: "contains", case_sensitive: false } },
            actions: []
        }
    }

    function _giftOptionIndexForRule(rule) {
        if (!rule || !rule.event || rule.event.type !== "gift_received" || !rule.event.params)
            return -1;
        var gid = (rule.event.params.gift_id != null) ? ("" + rule.event.params.gift_id).trim() : "";
        var gname = (rule.event.params.gift_name != null) ? ("" + rule.event.params.gift_name).trim() : "";
        var n = giftOptions.length;
        var i, o, nm;
        if (gid) {
            for (i = 0; i < n; i++) {
                o = giftOptions[i];
                if (o && ("" + (o.id || "")).trim() === gid) return i;
            }
        }
        if (gname) {
            var gl = gname.toLowerCase();
            for (i = 0; i < n; i++) {
                o = giftOptions[i];
                if (o && o.name) {
                    nm = ("" + o.name).toLowerCase();
                    if (nm === gl) return i;
                }
            }
        }
        return -1;
    }

    function _ruleListTitle(r) {
        if (!r) return "—";
        var n = (r.name || "").trim();
        if (n) return n;
        if (!r.event) return "—";
        if (r.event.type === "chat_keyword") {
            var kw = (r.event.params && r.event.params.text) || "";
            return (api ? api.loc("actions.rule_chat_brief") : "Chat") + ": " + kw;
        }
        if (r.event.type === "gift_received") {
            var g = (r.event.params && r.event.params.gift_name) || "";
            return (api ? api.loc("actions.rule_gift_brief") : "Gift") + ": " + g;
        }
        return r.event.type;
    }

    function _ruleListSubtitle(r) {
        if (!r || !r.actions || !r.actions.length)
            return api ? api.loc("actions.rule_no_actions") : "no actions";
        var parts = [];
        for (var i = 0; i < r.actions.length; i++)
            parts.push(r.actions[i].type || "?");
        return parts.join(", ");
    }

    function _duplicateRuleAt(i) {
        if (i < 0 || i >= rulesModel.length) return;
        var r = _cloneOrEmptyRule(rulesModel[i]);
        r.id = ("" + Math.random()).slice(2);
        var nm = (r.name || "").trim();
        if (nm) {
            var suff = api ? api.loc("actions.rule_name_copy_suffix") : " (copy)";
            r.name = (nm + suff).substring(0, 200);
        }
        var full;
        try { full = JSON.parse(JSON.stringify(rulesModel)); }
        catch (e) { full = rulesModel.slice(); }
        if (!full) full = [];
        full.splice(i + 1, 0, r);
        rulesModel = full;
        selectedIdx = i + 1;
        _save();
    }

    function _load() {
        if (!actApi) return;
        try {
            var txt = actApi.loadRulesJson(platform, accountKey);
            var parsed = JSON.parse(txt);
            var raw = parsed.rules || [];
            try { rulesModel = JSON.parse(JSON.stringify(raw)); }
            catch (e2) { rulesModel = raw; }
        } catch (e) {
            rulesModel = [];
        }
    }

    function _save(showToast) {
        if (!actApi) return;
        var payload = { schema_version: 1, rules: rulesModel };
        actApi.saveRulesJson(platform, accountKey, JSON.stringify(payload));
        if (showToast) _notifySaved();
    }

    function _reloadGifts() {
        if (!actApi) { giftOptions = []; return; }
        try {
            giftOptions = JSON.parse(actApi.giftOptionsJson(platform, accountKey));
        } catch (e) {
            giftOptions = [];
        }
    }

    function _tryInit() {
        // QML Component.onCompleted can run before MainWindow sets platform/accountKey.
        if (!platform || !accountKey) return;
        _load()
        _reloadGifts()
    }

    Component.onCompleted: _tryInit()
    onPlatformChanged: _tryInit()
    onAccountKeyChanged: _tryInit()
    onSelectedIdxChanged: _syncSelected()
    onRulesModelChanged: _syncSelected()
    onGiftOptionsChanged: {
        if (root.selectedRule === null || !root.selectedRule.event) return;
        if (root.selectedRule.event.type !== "gift_received" || !giftRuleCombo) return;
        root._suppressRuleCombos = true;
        var gi = root._giftOptionIndexForRule(root.selectedRule);
        if (gi >= 0) giftRuleCombo.currentIndex = gi;
        else if (giftRuleCombo.count > 0) giftRuleCombo.currentIndex = -1;
        ruleCombosSuppressEnd.restart();
    }
    onSelectedRuleChanged: {
        if (root.selectedRule === null) return;
        root._suppressRuleCombos = true;
        eventTypeCombo.currentIndex = root.selectedRule.event.type === "gift_received" ? 1 : 0;
        if (root.selectedRule.event && root.selectedRule.event.type === "gift_received" && giftRuleCombo) {
            var gi = root._giftOptionIndexForRule(root.selectedRule);
            if (gi >= 0) giftRuleCombo.currentIndex = gi;
            else if (giftRuleCombo.count > 0) giftRuleCombo.currentIndex = -1;
        }
        ruleCombosSuppressEnd.restart();
    }
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 340
            Layout.fillHeight: true
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: (function() {
                        var t = api ? api.loc("actions.title") : "Actions";
                        if (platform === "tiktok")
                            return t + " · " + (api ? api.loc("ui.tiktok_head") : "TikTok");
                        return t + " · " + platform + " · " + accountKey;
                    })()
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    ConnPillButton {
                        text: api ? api.loc("actions.add_rule") : "Add rule"
                        onClicked: {
                            var copy = rulesModel.slice();
                            copy.push(_defaultRule());
                            rulesModel = copy;
                            selectedIdx = rulesModel.length - 1;
                            _save(false);
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ConnPillButton {
                        text: api ? api.loc("actions.save") : "Save"
                        onClicked: root._commitSelectedRuleActions(true)
                    }

                    ConnPillButton {
                        text: api ? api.loc("actions.close") : "Close"
                        pillFontSize: 12
                        colRest: "#1a2230"
                        colHover: "#232a38"
                        colPress: "#2c3444"
                        onClicked: {
                            var w = root.Window.window;
                            if (w) w.close();
                        }
                    }
                }

                ListView {
                    id: rulesList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: rulesModel
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                    delegate: Rectangle {
                        id: ruleCard
                        property var rootRef: root
                        width: ListView.view.width
                        height: 58
                        radius: 10
                        color: index === ruleCard.rootRef.selectedIdx ? "#1a2232" : "#111827"
                        border.width: 1
                        border.color: cardEdge

                        // Background click selects the rule, but must not steal clicks from buttons.
                        MouseArea {
                            anchors.fill: parent
                            z: -1
                            onClicked: ruleCard.rootRef.selectedIdx = index
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Switch {
                                checked: modelData.enabled
                                onClicked: {
                                    var r = ruleCard.rootRef._copyRule(modelData);
                                    if (r == null) return;
                                    r.enabled = checked;
                                    ruleCard.rootRef._setRule(index, r);
                                    ruleCard.rootRef._save();
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    color: ink
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    text: ruleCard.rootRef._ruleListTitle(modelData)
                                }
                                Text {
                                    Layout.fillWidth: true
                                    color: muted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    text: ruleCard.rootRef._ruleListSubtitle(modelData)
                                }
                            }

                            ConnPillButton {
                                text: "▶"
                                pillFontSize: 12
                                onClicked: {
                                    actApi.previewRule(platform, accountKey, modelData.id)
                                }
                            }

                            ConnPillButton {
                                text: api ? api.loc("actions.duplicate_btn") : "Copy"
                                pillFontSize: 12
                                onClicked: {
                                    ruleCard.rootRef._duplicateRuleAt(index);
                                }
                            }

                            ConnPillButton {
                                text: api ? api.loc("actions.delete") : "Delete"
                                onClicked: {
                                    var copy = rulesModel.slice();
                                    copy.splice(index, 1);
                                    rulesModel = copy;
                                    if (ruleCard.rootRef.selectedIdx === index) ruleCard.rootRef.selectedIdx = -1;
                                    else if (ruleCard.rootRef.selectedIdx > index) ruleCard.rootRef.selectedIdx = ruleCard.rootRef.selectedIdx - 1;
                                    ruleCard.rootRef._save();
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge
            ScrollView {
                id: rightScroll
                anchors.fill: parent
                anchors.margins: 14
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                ColumnLayout {
                    // Fill the available viewport width (prevents "squeezed to the left").
                    width: Math.max(1, rightScroll.availableWidth)
                    spacing: 10

                Text {
                    text: api ? api.loc("actions.edit") : "Edit"
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                }

                Text {
                    visible: root.selectedIdx < 0
                    text: api ? api.loc("actions.pick_rule_hint") : "Pick a rule on the left."
                    color: muted
                    font.pixelSize: 12
                }

                ColumnLayout {
                    visible: root.selectedIdx >= 0
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: api ? api.loc("actions.rule_name") : "Name"; color: muted; font.pixelSize: 12 }
                    TextField {
                        Layout.fillWidth: true
                        color: ink
                        placeholderTextColor: muted
                        placeholderText: api ? api.loc("actions.rule_name_ph") : "e.g. Rose → OBS"
                        text: root.selectedRule !== null ? (root.selectedRule.name || "") : ""
                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                        onEditingFinished: {
                            if (root.selectedRule === null) return;
                            var v = text.trim();
                            if (v.length > 200) v = v.substring(0, 200);
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            r.name = v;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    ConnComboBox {
                        id: eventTypeCombo
                        Layout.fillWidth: true
                        model: [
                            { text: api ? api.loc("actions.event.chat_keyword") : "Chat keyword", value: "chat_keyword" },
                            { text: api ? api.loc("actions.event.gift_received") : "Gift received", value: "gift_received" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        onActivated: function (idx) {
                            if (root._suppressRuleCombos) return;
                            if (root.selectedRule === null) return;
                            var val = model[idx].value;
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            r.event = val === "gift_received"
                                ? root._giftEvent({ gift_id: "", gift_name: "", min_count: 1 })
                                : root._chatEvent({ text: "", match: "contains", case_sensitive: false });
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    // Chat keyword editor
                    ColumnLayout {
                        visible: root.selectedRule !== null && root.selectedRule.event.type === "chat_keyword"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.keyword") : "Keyword"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.keyword_ph") : "word..."
                            text: root.selectedRule !== null ? (root.selectedRule.event.params.text || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var r = root._copyRule(root.selectedRule);
                                if (r == null) return;
                                var ep = (r.event && r.event.params) || {};
                                r.event = root._chatEvent({ text: text, match: ep.match, case_sensitive: ep.case_sensitive });
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    // Gift editor
                    ColumnLayout {
                        visible: root.selectedRule !== null && root.selectedRule.event.type === "gift_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.gift_pick") : "Gift"; color: muted; font.pixelSize: 12 }
                        ConnComboBox {
                            id: giftRuleCombo
                            Layout.fillWidth: true
                            model: giftOptions
                            textRole: "name"
                            valueRole: "id"
                            editable: true
                            delegate: ItemDelegate {
                                width: ListView.view ? ListView.view.width : implicitWidth
                                contentItem: RowLayout {
                                    spacing: 10
                                    Image {
                                        Layout.preferredWidth: 24
                                        Layout.preferredHeight: 24
                                        source: modelData && modelData.image_url ? modelData.image_url : ""
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                        cache: true
                                        visible: source !== ""
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData && modelData.name ? modelData.name : ""
                                        color: root.ink
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: modelData && modelData.price ? (modelData.price + " 🪙") : ""
                                        color: root.muted
                                        font.pixelSize: 12
                                    }
                                }
                            }
                            onActivated: function (idx) {
                                if (root._suppressRuleCombos) return;
                                if (root.selectedRule === null) return;
                                if (idx < 0) return;
                                var r = root._copyRule(root.selectedRule);
                                if (r == null) return;
                                var ep = (r.event && r.event.params) || {};
                                var g = model[idx];
                                r.event = root._giftEvent({
                                    gift_id: (g && g.id) || "",
                                    gift_name: (g && g.name) || "",
                                    min_count: ep.min_count
                                });
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                            onAccepted: {
                                if (root._suppressRuleCombos) return;
                                // Manual entry fallback: store as gift_name.
                                if (root.selectedRule === null) return;
                                var r = root._copyRule(root.selectedRule);
                                if (r == null) return;
                                var ep = (r.event && r.event.params) || {};
                                r.event = root._giftEvent({
                                    gift_id: "",
                                    gift_name: editText || "",
                                    min_count: ep.min_count
                                });
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.min_count") : "Min count"; color: muted; font.pixelSize: 12 }
                        SpinBox {
                            from: 1
                            to: 999
                            value: root.selectedRule !== null ? (root.selectedRule.event.params.min_count || 1) : 1
                            onValueModified: {
                                if (root.selectedRule === null) return;
                                var r = root._copyRule(root.selectedRule);
                                if (r == null) return;
                                var ep = (r.event && r.event.params) || {};
                                r.event = root._giftEvent({
                                    gift_id: ep.gift_id,
                                    gift_name: ep.gift_name,
                                    min_count: value
                                });
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }
                    Text { text: api ? api.loc("actions.actions") : "Actions"; color: ink; font.pixelSize: 14; font.bold: true }

                    ListView {
                        id: actionsList
                        Layout.fillWidth: true
                        width: parent.width
                        clip: true
                        interactive: true
                        spacing: 10
                        model: root.actionsModel
                        implicitHeight: contentHeight
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                        // Expose root API & action types to delegate via ListView.view.*
                        property var rootApi: root
                        property var actionTypes: root.actionTypeModel

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            width: actionsList.width
                            radius: 10
                            color: "#111827"
                            border.width: 1
                            border.color: (index === root.selectedActionIdx) ? "#3b4458" : cardEdge

                            readonly property int aIdx: index
                            readonly property string aType: ((modelData && modelData.type) || "play_sound")
                            readonly property string aKind: (aType === "run_exe") ? "run_program" : aType
                            readonly property bool isOpen: index === root.selectedActionIdx

                            // ListView delegates must have a reliable implicit height.
                            implicitHeight: cardLayout.implicitHeight + 20
                            height: implicitHeight

                            ColumnLayout {
                                id: cardLayout
                                x: 10
                                y: 10
                                width: Math.max(1, parent.width - 20)
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    ConnComboBox {
                                        Layout.preferredWidth: 200
                                        Layout.fillWidth: true
                                        model: actionsList.actionTypes
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: actionsList.rootApi._actionTypeIndex(aType)
                                        onActivated: function (idx) {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var t = model[idx].value;
                                            var aa = apiRef.actionsModel.slice();
                                            var ac = apiRef._copyRule(aa[aIdx]);
                                            if (ac) aa[aIdx] = ac;
                                            aa[aIdx].type = t;
                                            if (t === "play_sound") aa[aIdx].params = { file_path: "" };
                                            if (t === "write_file") aa[aIdx].params = { file_path: "", text: "", mode: "overwrite" };
                                            if (t === "run_program") aa[aIdx].params = { program_path: "", arguments: "" };
                                            if (t === "speak_tts") aa[aIdx].params = { text: "" };
                                            apiRef.actionsModel = aa;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }

                                    ConnPillButton {
                                        text: api ? api.loc("actions.delete") : "Delete"
                                        onClicked: {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var aa = apiRef.actionsModel.slice();
                                            aa.splice(aIdx, 1);
                                            apiRef.actionsModel = aa;
                                            if (root.selectedActionIdx === aIdx) root.selectedActionIdx = -1;
                                            else if (root.selectedActionIdx > aIdx) root.selectedActionIdx = root.selectedActionIdx - 1;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }
                                }

                                // Play sound config
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "play_sound"

                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.pick_mp3") : "Pick .mp3..."
                                        text: (modelData && modelData.params && modelData.params.file_path) ? modelData.params.file_path : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        readOnly: true
                                    }
                                    ConnPillButton {
                                        text: api ? api.loc("actions.browse") : "Browse…"
                                        onClicked: {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var p = actApi.pickSoundFile();
                                            if (!p) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var aa = apiRef.actionsModel.slice();
                                            var ac = apiRef._copyRule(aa[aIdx]);
                                            if (ac) aa[aIdx] = ac;
                                            aa[aIdx].params = aa[aIdx].params || {};
                                            aa[aIdx].params.file_path = p;
                                            apiRef.actionsModel = aa;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }
                                }

                                // Write file config
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "write_file"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.write_mode") : "Mode"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        ConnComboBox {
                                            Layout.fillWidth: true
                                            model: [
                                                api ? api.loc("actions.write_mode_overwrite") : "Overwrite",
                                                api ? api.loc("actions.write_mode_append") : "Append"
                                            ]
                                            currentIndex: {
                                                var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "overwrite";
                                                return (m === "append") ? 1 : 0;
                                            }
                                            onActivated: function(index) {
                                                var aa = root.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.mode = (index === 1) ? "append" : "overwrite";
                                                root.actionsModel = aa;
                                                root._scheduleCommitSelectedRuleActions();
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_file") : "Pick file..."
                                            text: (modelData && modelData.params && modelData.params.file_path) ? modelData.params.file_path : ""
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: false
                                            onTextChanged: {
                                                // Keep binding updated without rebuilding the full rulesModel
                                                var aa = root.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.file_path = text;
                                                root.actionsModel = aa;
                                                root._scheduleCommitSelectedRuleActions();
                                            }
                                            onActiveFocusChanged: {
                                                if (!activeFocus) root._commitSelectedRuleActions(false);
                                            }
                                        }
                                        ConnPillButton {
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                var p = actApi.pickWriteFile();
                                                if (!p) return;
                                                var r = apiRef._copyRule(apiRef.selectedRule);
                                                if (r == null) return;
                                                var aa = apiRef.actionsModel.slice();
                                                var ac = apiRef._copyRule(aa[aIdx]);
                                                if (ac) aa[aIdx] = ac;
                                                aa[aIdx].params = aa[aIdx].params || {};
                                                aa[aIdx].params.file_path = p;
                                                apiRef.actionsModel = aa;
                                                r.actions = aa;
                                                apiRef._setRule(apiRef.selectedIdx, r);
                                                apiRef._save();
                                            }
                                        }
                                    }

                                    TextArea {
                                        Layout.fillWidth: true
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.write_text_ph") : "Text..."
                                        text: (modelData && modelData.params && modelData.params.text) ? modelData.params.text : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            // Do NOT rebuild the full rulesModel on every keystroke,
                                            // otherwise the delegate is recreated and the field loses focus.
                                            var aa = root.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.text = text;
                                            root.actionsModel = aa; // keep binding updated without cloning everything
                                            root._scheduleCommitSelectedRuleActions();
                                        }
                                        onActiveFocusChanged: {
                                            root.isActionTextEditing = activeFocus;
                                            if (!activeFocus) root._commitSelectedRuleActions(false);
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint_file") : "Placeholders (text & file path): giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: root.muted
                                    }
                                }

                                // Run program (cross-platform)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aKind === "run_program"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_program") : "Pick executable…"
                                            text: {
                                                if (!modelData || !modelData.params) return "";
                                                return modelData.params.program_path || modelData.params.exe_path || "";
                                            }
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: true
                                        }
                                        ConnPillButton {
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                var p = actApi.pickProgramFile();
                                                if (!p) return;
                                                var r = apiRef._copyRule(apiRef.selectedRule);
                                                if (r == null) return;
                                                var aa = apiRef.actionsModel.slice();
                                                var ac = apiRef._copyRule(aa[aIdx]);
                                                if (ac) aa[aIdx] = ac;
                                                aa[aIdx].params = aa[aIdx].params || {};
                                                aa[aIdx].params.program_path = p;
                                                delete aa[aIdx].params.exe_path;
                                                if (aa[aIdx].type === "run_exe") aa[aIdx].type = "run_program";
                                                apiRef.actionsModel = aa;
                                                r.actions = aa;
                                                apiRef._setRule(apiRef.selectedIdx, r);
                                                apiRef._save();
                                            }
                                        }
                                    }

                                    Text { text: api ? api.loc("actions.program_args") : "Arguments"; color: muted; font.pixelSize: 12 }
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.program_args_ph") : "e.g. --foo bar"
                                        text: (modelData && modelData.params && modelData.params.arguments) ? modelData.params.arguments : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onEditingFinished: {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var aa = apiRef.actionsModel.slice();
                                            var ac = apiRef._copyRule(aa[aIdx]);
                                            if (ac) aa[aIdx] = ac;
                                            aa[aIdx].params = aa[aIdx].params || {};
                                            aa[aIdx].params.arguments = text;
                                            apiRef.actionsModel = aa;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders: giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: root.muted
                                    }
                                }

                                // TTS speak text
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "speak_tts"

                                    Text { text: api ? api.loc("actions.speak_tts_text") : "Text to speak"; color: muted; font.pixelSize: 12 }
                                    TextArea {
                                        Layout.fillWidth: true
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.speak_tts_text_ph") : "phrase…"
                                        text: (modelData && modelData.params && modelData.params.text) ? modelData.params.text : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = root.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.text = text;
                                            root.actionsModel = aa;
                                            root._scheduleCommitSelectedRuleActions();
                                        }
                                        onActiveFocusChanged: {
                                            root.isActionTextEditing = activeFocus;
                                            if (!activeFocus) root._commitSelectedRuleActions(false);
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders: giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: root.muted
                                    }
                                }
                            }

                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: root.selectedActionIdx = index
                            }
                        }
                    }

                    ConnPillButton {
                        text: api ? api.loc("actions.add_action") : "+ Add action"
                        pillFontSize: 12
                        onClicked: {
                            if (root.selectedRule === null) return;
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            var aa = root.actionsModel.slice();
                            aa.push({ type: "play_sound", params: { file_path: "" } });
                            root.actionsModel = aa;
                            root.selectedActionIdx = aa.length - 1;
                            r.actions = aa;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    ConnPillButton {
                        text: api ? (api.loc("actions.clear") || "Clear") : "Clear"
                        pillFontSize: 12
                        onClicked: {
                            if (root.selectedRule === null) return;
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            root.actionsModel = [];
                            root.selectedActionIdx = -1;
                            r.actions = [];
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
                }
            }
        }
    }

    // Simple toast "Saved" notification (only for explicit Save button).
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18
        width: Math.min(parent.width - 36, savedToastText.implicitWidth + 24)
        height: savedToastText.implicitHeight + 16
        radius: 10
        color: "#0f172a"
        border.width: 1
        border.color: "#334155"
        visible: root._savedToastVisible
        opacity: root._savedToastVisible ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: 120 } }

        Text {
            id: savedToastText
            anchors.centerIn: parent
            width: parent.width - 16
            text: api ? api.loc("actions.saved") : "Saved"
            color: root.ink
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}

