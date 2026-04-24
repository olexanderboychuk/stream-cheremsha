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

    Component.onCompleted: _load()

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

                Button {
                    text: api ? api.loc("actions.add_rule") : "Add rule"
                    onClicked: {
                        rulesModel = rulesModel.concat([_defaultRule()]);
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
                                    modelData.enabled = checked;
                                    rulesModel[index] = modelData;
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

                            Button {
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
                        Layout.fillWidth: true
                        model: [
                            { text: api ? api.loc("actions.event.chat_keyword") : "Chat keyword", value: "chat_keyword" },
                            { text: api ? api.loc("actions.event.gift_received") : "Gift received", value: "gift_received" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        Component.onCompleted: currentIndex = rulesModel[selectedIdx].event.type === "gift_received" ? 1 : 0
                        onActivated: {
                            var r = rulesModel[selectedIdx];
                            r.event.type = currentValue;
                            r.event.params = (currentValue === "gift_received")
                                ? { gift_name: "", min_count: 1 }
                                : { text: "", match: "contains", case_sensitive: false };
                            rulesModel[selectedIdx] = r;
                            _save();
                        }
                    }

                    // Chat keyword editor
                    ColumnLayout {
                        visible: rulesModel[selectedIdx].event.type === "chat_keyword"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.keyword") : "Keyword"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.keyword_ph") : "word..."
                            text: rulesModel[selectedIdx].event.params.text || ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                var r = rulesModel[selectedIdx];
                                r.event.params.text = text;
                                rulesModel[selectedIdx] = r;
                                _save();
                            }
                        }
                    }

                    // Gift editor
                    ColumnLayout {
                        visible: rulesModel[selectedIdx].event.type === "gift_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.gift_name") : "Gift name"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.gift_name_ph") : "Rose..."
                            text: rulesModel[selectedIdx].event.params.gift_name || ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                var r = rulesModel[selectedIdx];
                                r.event.params.gift_name = text;
                                rulesModel[selectedIdx] = r;
                                _save();
                            }
                        }
                        Text { text: api ? api.loc("actions.min_count") : "Min count"; color: muted; font.pixelSize: 12 }
                        SpinBox {
                            from: 1
                            to: 999
                            value: rulesModel[selectedIdx].event.params.min_count || 1
                            onValueModified: {
                                var r = rulesModel[selectedIdx];
                                r.event.params.min_count = value;
                                rulesModel[selectedIdx] = r;
                                _save();
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }
                    Text { text: api ? api.loc("actions.actions") : "Actions"; color: ink; font.pixelSize: 14; font.bold: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: api ? api.loc("actions.play_sound") : "Play sound"; color: muted; width: 120 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.pick_mp3") : "Pick .mp3..."
                            text: (rulesModel[selectedIdx].actions[0].params.file_path || "")
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            readOnly: true
                        }
                        Button {
                            text: api ? api.loc("actions.browse") : "Browse…"
                            onClicked: {
                                var p = actApi.pickSoundFile();
                                if (!p) return;
                                var r = rulesModel[selectedIdx];
                                r.actions = [ { type: "play_sound", params: { file_path: p } } ];
                                rulesModel[selectedIdx] = r;
                                _save();
                            }
                        }
                        Button {
                            text: api ? api.loc("actions.clear") : "Clear"
                            onClicked: {
                                var r = rulesModel[selectedIdx];
                                r.actions[0].params.file_path = "";
                                rulesModel[selectedIdx] = r;
                                _save();
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}

