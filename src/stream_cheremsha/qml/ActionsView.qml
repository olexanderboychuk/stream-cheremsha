import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    width: 820
    height: 560

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

    function _syncSelected() {
        if (selectedIdx < 0 || selectedIdx >= rulesModel.length) {
            selectedRule = null;
            selectedIdx = -1;
            return;
        }
        selectedRule = rulesModel[selectedIdx];
    }

    function _setRule(idx, ruleObj) {
        var copy = rulesModel.slice();
        copy[idx] = ruleObj;
        rulesModel = copy;
        _syncSelected();
    }

    function _defaultRule() {
        return {
            id: ("" + Math.random()).slice(2),
            enabled: true,
            event: { type: "chat_keyword", params: { text: "", match: "contains", case_sensitive: false } },
            actions: [ { type: "play_sound", params: { file_path: "" } } ]
        }
    }

    function _load() {
        if (!actApi) return;
        try {
            var txt = actApi.loadRulesJson(platform, accountKey);
            var parsed = JSON.parse(txt);
            rulesModel = parsed.rules || [];
        } catch (e) {
            rulesModel = [];
        }
    }

    function _save() {
        if (!actApi) return;
        var payload = { schema_version: 1, rules: rulesModel };
        actApi.saveRulesJson(platform, accountKey, JSON.stringify(payload));
    }

    function _reloadGifts() {
        if (!actApi) { giftOptions = []; return; }
        try {
            giftOptions = JSON.parse(actApi.giftOptionsJson(platform, accountKey));
        } catch (e) {
            giftOptions = [];
        }
    }

    Component.onCompleted: {
        _load()
        _reloadGifts()
    }
    onSelectedIdxChanged: _syncSelected()
    onRulesModelChanged: _syncSelected()
    onSelectedRuleChanged: {
        if (selectedRule === null) return;
        eventTypeCombo.currentIndex = selectedRule.event.type === "gift_received" ? 1 : 0;
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
                    text: (api ? api.loc("actions.title") : "Actions") + " · " + platform + " · " + accountKey
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                    wrapMode: Text.Wrap
                }

                ConnPillButton {
                    text: api ? api.loc("actions.add_rule") : "Add rule"
                    onClicked: {
                        var copy = rulesModel.slice();
                        copy.push(_defaultRule());
                        rulesModel = copy;
                        selectedIdx = rulesModel.length - 1;
                        _save();
                    }
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: rulesModel
                    delegate: Rectangle {
                        width: ListView.view.width
                        height: 58
                        radius: 10
                        color: index === selectedIdx ? "#1a2232" : "#111827"
                        border.width: 1
                        border.color: cardEdge

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Switch {
                                checked: modelData.enabled
                                onClicked: {
                                    var r = modelData;
                                    r.enabled = checked;
                                    _setRule(index, r);
                                    _save();
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
                                    text: {
                                        if (!modelData.event) return "IF —";
                                        if (modelData.event.type === "chat_keyword")
                                            return "IF chat has \"" + ((modelData.event.params && modelData.event.params.text) || "") + "\"";
                                        if (modelData.event.type === "gift_received")
                                            return "IF gift \"" + ((modelData.event.params && modelData.event.params.gift_name) || "") + "\"";
                                        return "IF " + modelData.event.type;
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    color: muted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    text: "THEN " + (modelData.actions && modelData.actions.length ? modelData.actions[0].type : "—")
                                }
                            }

                            ConnPillButton {
                                text: api ? api.loc("actions.delete") : "Delete"
                                onClicked: {
                                    var copy = rulesModel.slice();
                                    copy.splice(index, 1);
                                    rulesModel = copy;
                                    if (selectedIdx === index) selectedIdx = -1;
                                    _save();
                                }
                            }
                        }

                        MouseArea { anchors.fill: parent; onClicked: selectedIdx = index }
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

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    text: api ? api.loc("actions.edit") : "Edit"
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                }

                Text {
                    visible: selectedIdx < 0
                    text: api ? api.loc("actions.pick_rule_hint") : "Pick a rule on the left."
                    color: muted
                    font.pixelSize: 12
                }

                ColumnLayout {
                    visible: selectedIdx >= 0
                    Layout.fillWidth: true
                    spacing: 10

                    ComboBox {
                        id: eventTypeCombo
                        Layout.fillWidth: true
                        model: [
                            { text: api ? api.loc("actions.event.chat_keyword") : "Chat keyword", value: "chat_keyword" },
                            { text: api ? api.loc("actions.event.gift_received") : "Gift received", value: "gift_received" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        onActivated: function (idx) {
                            if (selectedRule === null) return;
                            var val = model[idx].value;
                            var r = selectedRule;
                            r.event.type = val;
                            r.event.params = (val === "gift_received")
                                ? { gift_name: "", min_count: 1 }
                                : { text: "", match: "contains", case_sensitive: false };
                            _setRule(selectedIdx, r);
                            _save();
                        }
                    }

                    // Chat keyword editor
                    ColumnLayout {
                        visible: selectedRule !== null && selectedRule.event.type === "chat_keyword"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.keyword") : "Keyword"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.keyword_ph") : "word..."
                            text: selectedRule !== null ? (selectedRule.event.params.text || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (selectedRule === null) return;
                                var r = selectedRule;
                                r.event.params.text = text;
                                _setRule(selectedIdx, r);
                                _save();
                            }
                        }
                    }

                    // Gift editor
                    ColumnLayout {
                        visible: selectedRule !== null && selectedRule.event.type === "gift_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.gift_pick") : "Gift"; color: muted; font.pixelSize: 12 }
                        ComboBox {
                            Layout.fillWidth: true
                            model: giftOptions
                            textRole: "name"
                            valueRole: "id"
                            editable: true
                            onActivated: function (idx) {
                                if (selectedRule === null) return;
                                var r = selectedRule;
                                var g = model[idx];
                                r.event.params.gift_id = g.id || "";
                                r.event.params.gift_name = g.name || "";
                                _setRule(selectedIdx, r);
                                _save();
                            }
                            onAccepted: {
                                // Manual entry fallback: store as gift_name.
                                if (selectedRule === null) return;
                                var r = selectedRule;
                                r.event.params.gift_id = "";
                                r.event.params.gift_name = editText || "";
                                _setRule(selectedIdx, r);
                                _save();
                            }
                        }
                        Text { text: api ? api.loc("actions.min_count") : "Min count"; color: muted; font.pixelSize: 12 }
                        SpinBox {
                            from: 1
                            to: 999
                            value: selectedRule !== null ? (selectedRule.event.params.min_count || 1) : 1
                            onValueModified: {
                                if (selectedRule === null) return;
                                var r = selectedRule;
                                r.event.params.min_count = value;
                                _setRule(selectedIdx, r);
                                _save();
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }
                    Text { text: api ? api.loc("actions.actions") : "Actions"; color: ink; font.pixelSize: 14; font.bold: true }
                    Repeater {
                        model: (selectedRule && selectedRule.actions) ? selectedRule.actions.length : 0
                        delegate: RowLayout {
                            width: parent.width
                            spacing: 8
                            readonly property int aIdx: index
                            Text { text: api ? api.loc("actions.play_sound") : "Play sound"; color: muted; width: 120 }
                            TextField {
                                Layout.fillWidth: true
                                color: ink
                                placeholderTextColor: muted
                                placeholderText: api ? api.loc("actions.pick_mp3") : "Pick .mp3..."
                                text: selectedRule.actions[aIdx].params.file_path || ""
                                background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                readOnly: true
                            }
                            ConnPillButton {
                                text: api ? api.loc("actions.browse") : "Browse…"
                                onClicked: {
                                    if (selectedRule === null) return;
                                    var p = actApi.pickSoundFile();
                                    if (!p) return;
                                    var r = selectedRule;
                                    r.actions[aIdx].params.file_path = p;
                                    _setRule(selectedIdx, r);
                                    _save();
                                }
                            }
                            ConnPillButton {
                                text: api ? api.loc("actions.delete") : "Delete"
                                onClicked: {
                                    if (selectedRule === null) return;
                                    var r = selectedRule;
                                    var aa = r.actions.slice();
                                    aa.splice(aIdx, 1);
                                    if (aa.length === 0) aa = [ { type: "play_sound", params: { file_path: "" } } ];
                                    r.actions = aa;
                                    _setRule(selectedIdx, r);
                                    _save();
                                }
                            }
                        }
                    }

                    ConnPillButton {
                        text: api ? api.loc("actions.add_action") : "+ Add action"
                        pillFontSize: 12
                        onClicked: {
                            if (selectedRule === null) return;
                            var r = selectedRule;
                            var aa = (r.actions || []).slice();
                            aa.push({ type: "play_sound", params: { file_path: "" } });
                            r.actions = aa;
                            _setRule(selectedIdx, r);
                            _save();
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}

