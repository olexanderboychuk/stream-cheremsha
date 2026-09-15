pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string description: ""
    property string type: "text"
    property string field: ""
    property var value: ""
    property var options: []
    property var optionLabels: []
    property real minimum: 0
    property real maximum: 100
    property bool wide: false
    signal changed(string field, var value)

    component PlatField: TextField {
        implicitHeight: 36
        color: "#e8eaed"
        font.pixelSize: 13
        padding: 9
        hoverEnabled: true
        selectByMouse: true
        background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: parent.activeFocus ? "#14b8a6" : (parent.hovered ? "#2d3748" : "#242b36"); Behavior on border.color { ColorAnimation { duration: 160 } } }
    }
    component IconBtn: Rectangle {
        property string glyph: ""
        property bool disabled: false
        signal clicked()
        implicitWidth: 36
        implicitHeight: 36
        radius: 8
        opacity: disabled ? 0.35 : 1.0
        color: btnArea.pressed ? "#0f766e" : (btnArea.containsMouse && !disabled ? "#2d3748" : "#0f172a")
        border.width: 1
        border.color: btnArea.containsMouse && !disabled ? "#2d3748" : "#242b36"
        Behavior on color { ColorAnimation { duration: 160 } }
        Text { anchors.centerIn: parent; text: parent.glyph; color: "#e8eaed"; font.pixelSize: 14; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
        MouseArea { id: btnArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; enabled: !parent.disabled; onClicked: parent.clicked() }
    }

    Layout.fillWidth: true
    spacing: 8

    RowLayout {
        visible: root.type !== "social_platforms" && root.type !== "leaderboard_sequence"
        Layout.fillWidth: true
        spacing: 12
        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 4
            Text { text: root.label; color: "#e8eaed"; font.pixelSize: 12; font.weight: Font.DemiBold }
            Text {
                visible: root.description !== ""
                text: root.description
                color: "#8b95a5"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        TextField {
            id: textField
            visible: root.type === "text" || root.type === "url" || root.type === "hotkey"
            Layout.preferredWidth: 150
            Layout.minimumWidth: 150
            Layout.maximumWidth: 150
            implicitHeight: 36
            text: root.value
            color: "#e8eaed"
            padding: 9
            hoverEnabled: true
            placeholderText: root.type === "url" ? "https://" : "Введіть значення"
            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: textField.activeFocus ? "#14b8a6" : (textField.hovered ? "#2d3748" : "#242b36"); Behavior on border.color { ColorAnimation { duration: 160 } } }
            onTextChanged: if (activeFocus) root.changed(root.field, text)
        }
        SpinBox {
            id: spinBox
            visible: root.type === "number"
            Layout.preferredWidth: 124
            Layout.minimumWidth: 124
            Layout.maximumWidth: 124
            from: root.minimum; to: root.maximum
            value: Number(root.value === undefined || root.value === null || root.value === "" ? root.minimum : root.value)
             function stepBy(delta) {
                 value = Math.max(from, Math.min(to, value + delta * stepSize));
                 root.changed(root.field, value);
             }
            editable: true
            implicitHeight: 36
            font.pixelSize: 13
            contentItem: TextInput { text: spinBox.displayText; color: "#e8eaed"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; readOnly: !spinBox.editable }
            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: spinBox.activeFocus ? "#14b8a6" : "#242b36" }
            down.indicator: Item {
                implicitWidth: 36; implicitHeight: 36
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.fill: parent; color: spinDown.pressed ? "#0f766e" : (spinDown.containsMouse ? "#2d3748" : "#10141a"); border.color: "#242b36"; border.width: 1 }
                Text { anchors.centerIn: parent; text: "−"; color: "#e8eaed"; font.pixelSize: 16 }
                MouseArea { id: spinDown; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: spinBox.stepBy(-1) }
            }
            up.indicator: Item {
                implicitWidth: 36; implicitHeight: 36
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.fill: parent; color: spinUp.pressed ? "#0f766e" : (spinUp.containsMouse ? "#2d3748" : "#10141a"); border.color: "#242b36"; border.width: 1 }
                Text { anchors.centerIn: parent; text: "+"; color: "#e8eaed"; font.pixelSize: 16 }
                MouseArea { id: spinUp; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: spinBox.stepBy(1) }
            }
            onValueModified: root.changed(root.field, value)
        }
        Slider {
            visible: root.type === "slider"
            Layout.preferredWidth: 150
            Layout.minimumWidth: 150
            Layout.maximumWidth: 150
            from: root.minimum; to: root.maximum
            value: Number(root.value === undefined || root.value === null || root.value === "" ? root.minimum : root.value)
            onMoved: root.changed(root.field, value)
        }
        Switch {
            visible: root.type === "toggle" || root.type === "checkbox"
            id: switchControl
            leftPadding: 0
            rightPadding: 0
            implicitWidth: 46
            implicitHeight: 26
            Layout.preferredWidth: 46
            Layout.minimumWidth: 46
            Layout.maximumWidth: 46
            indicator: Rectangle {
                x: switchControl.leftPadding
                y: switchControl.height / 2 - height / 2
                width: 46; height: 24; radius: 12
                color: switchControl.checked ? "#134e4a" : "#0a0d12"
                border.width: 1
                border.color: switchControl.checked ? "#14b8a6" : "#2d3748"
                Behavior on color { ColorAnimation { duration: 160 } }
                Rectangle {
                    x: switchControl.checked ? parent.width - width - 3 : 3
                    anchors.verticalCenter: parent.verticalCenter
                    width: 18; height: 18; radius: 9
                    color: switchControl.checked ? "#5eead4" : "#8b95a5"
                    Behavior on x { NumberAnimation { duration: 160 } }
                }
            }
            checked: root.value === true || root.value === "true" || root.value === "1"
            onClicked: root.changed(root.field, checked)
        }
        ComboBox {
            id: comboBox
            visible: root.type === "select" || root.type === "dropdown" || root.type === "font"
            Layout.preferredWidth: root.type === "font" ? 220 : 140
            Layout.minimumWidth: root.type === "font" ? 220 : 140
            Layout.maximumWidth: root.type === "font" ? 220 : 140
            model: root.optionLabels.length ? root.optionLabels : root.options
            currentIndex: Math.max(0, root.options.indexOf(root.value))
            hoverEnabled: true
            implicitHeight: 36
            contentItem: Text { text: comboBox.displayText; color: "#e8eaed"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: comboBox.hovered ? "#2d3748" : "#242b36"; Behavior on border.color { ColorAnimation { duration: 160 } } }
            indicator: Text { x: comboBox.width - width - 10; y: comboBox.height / 2 - height / 2; text: "⌄"; color: comboBox.popup.visible ? "#5eead4" : "#8b95a5"; font.pixelSize: 14 }
            delegate: ItemDelegate {
                id: comboDelegate
                required property int index
                width: comboBox.width - 8
                implicitHeight: 35
                highlighted: comboBox.currentIndex === index
                hoverEnabled: true
                contentItem: Text { text: comboBox.textAt(comboDelegate.index); color: "#e8eaed"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                background: Rectangle { radius: 6; color: comboDelegate.highlighted ? "#14b8a620" : (comboDelegate.hovered ? "#2d3748" : "transparent"); border.width: comboDelegate.highlighted ? 1 : 0; border.color: "#14b8a6"; Behavior on color { ColorAnimation { duration: 150 } } }
            }
            popup: Popup {
                y: comboBox.height + 4
                width: comboBox.width
                padding: 4
                implicitHeight: Math.min(240, contentItem.implicitHeight + 8)
                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: comboBox.popup.visible ? comboBox.delegateModel : null
                    currentIndex: comboBox.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator { width: 5 }
                }
                background: Rectangle {
                    radius: 8
                    color: "#10141a"
                    border.width: 1
                    border.color: "#242b36"
                    Rectangle { anchors.fill: parent; anchors.margins: 3; color: "transparent"; border.width: 1; border.color: "#090a0d"; opacity: 0.35; radius: 6; z: -1 }
                }
            }
            onActivated: root.changed(root.field, root.options[currentIndex])
        }
        CheremshaColorPicker {
            visible: root.type === "color"
            Layout.preferredWidth: 300
            Layout.minimumWidth: 280
            Layout.maximumWidth: 340
            Layout.fillWidth: true
            value: String(root.value === undefined || root.value === null ? "#000000" : root.value)
            onAccepted: function(colorValue) { root.changed(root.field, colorValue) }
        }
        Button {
            id: utilityButton
            visible: ["list", "repeater", "draggable", "file", "image", "button"].indexOf(root.type) >= 0
            text: root.type === "button" ? root.label : "Налаштувати"
            hoverEnabled: true
            implicitHeight: 36
            Layout.preferredWidth: 120
            Layout.minimumWidth: 120
            leftPadding: 12; rightPadding: 12
            contentItem: Text { text: utilityButton.text; color: "#e8eaed"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { radius: 8; color: utilityButton.pressed ? "#2d3748" : (utilityButton.hovered ? "#2d3748" : "#10141a"); border.width: 1; border.color: utilityButton.hovered ? "#2d3748" : "#242b36"; Behavior on color { ColorAnimation { duration: 160 } } }
            onClicked: {
                if (root.type === "list") {
                    try { listEditor.text = JSON.stringify(root.value || [], null, 2) } catch (e) { listEditor.text = "[]" }
                    listPopup.open()
                } else {
                    root.changed(root.field, root.value)
                }
            }
        }
    }

    ColumnLayout {
        id: platEditor
        visible: root.type === "social_platforms"
        Layout.fillWidth: true
        spacing: 8
        property var platformOptions: root.options && root.options.length ? root.options : ["twitch", "youtube", "kick", "telegram", "tiktok", "instagram", "discord", "x", "facebook"]
        property var entries: []
        function syncFromValue() {
            var v = root.value;
            if (typeof v === "string") {
                try { v = JSON.parse(v); } catch (e) { v = []; }
            }
            if (!Array.isArray(v)) v = [];
            var out = [];
            for (var i = 0; i < v.length; ++i) {
                var r = v[i] || {};
                out.push({id: r.id || "", platform: String(r.platform || "twitch").toLowerCase(), username: String(r.username || ""), url: String(r.url || ""), enabled: r.enabled !== false, order: i});
            }
            entries = out;
        }
        Component.onCompleted: syncFromValue()
        onVisibleChanged: if (visible) syncFromValue()
        Connections { target: root; function onValueChanged() { platEditor.syncFromValue(); } }
        function commit(list) {
            var out = [];
            for (var i = 0; i < list.length; ++i) {
                var r = list[i] || {};
                out.push({id: r.id || "", platform: String(r.platform || "twitch").toLowerCase(), username: String(r.username || ""), url: String(r.url || ""), enabled: r.enabled !== false, order: i});
            }
            entries = JSON.parse(JSON.stringify(out));
            root.changed(root.field, out);
        }
        function currentList() { return entries; }
        function cloneList() { return JSON.parse(JSON.stringify(entries)); }
        Text {
            visible: platEditor.entries.length === 0
            text: "No platforms yet — pick one below and press + Add platform."
            color: "#8b95a5"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Repeater {
            model: platEditor.entries
            delegate: Rectangle {
                required property int index
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: platCol.implicitHeight + 20
                radius: 12
                color: "#10141a"
                border.width: 1
                border.color: "#242b36"
                ColumnLayout {
                    id: platCol
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: String(index + 1).padStart(2, "0")
                            color: "#5eead4"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 22
                        }
                        ComboBox {
                            id: platCombo
                            Layout.preferredWidth: 140
                            Layout.minimumWidth: 140
                            Layout.maximumWidth: 140
                            implicitHeight: 36
                            hoverEnabled: true
                            model: platEditor.platformOptions
                            currentIndex: Math.max(0, platEditor.platformOptions.indexOf(String(modelData.platform || "").toLowerCase()))
                            contentItem: Text { text: platCombo.displayText; color: "#e8eaed"; font.pixelSize: 13; font.capitalization: Font.Capitalize; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: platCombo.hovered ? "#2d3748" : "#242b36"; Behavior on border.color { ColorAnimation { duration: 160 } } }
                            indicator: Text { x: platCombo.width - width - 10; y: platCombo.height / 2 - height / 2; text: "⌄"; color: platCombo.popup.visible ? "#5eead4" : "#8b95a5"; font.pixelSize: 14 }
                            delegate: ItemDelegate {
                                required property int index
                                width: platCombo.width - 8
                                implicitHeight: 35
                                highlighted: platCombo.currentIndex === index
                                hoverEnabled: true
                                contentItem: Text { text: platCombo.textAt(index); color: "#e8eaed"; font.pixelSize: 12; font.capitalization: Font.Capitalize; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                                background: Rectangle { radius: 6; color: highlighted ? "#14b8a620" : (hovered ? "#2d3748" : "transparent"); border.width: highlighted ? 1 : 0; border.color: "#14b8a6" }
                            }
                            popup: Popup {
                                y: platCombo.height + 4
                                width: platCombo.width
                                padding: 4
                                implicitHeight: Math.min(240, contentItem.implicitHeight + 8)
                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: platCombo.popup.visible ? platCombo.delegateModel : null
                                    currentIndex: platCombo.highlightedIndex
                                    ScrollIndicator.vertical: ScrollIndicator { width: 5 }
                                }
                                background: Rectangle { radius: 8; color: "#10141a"; border.width: 1; border.color: "#242b36" }
                            }
                            onActivated: function(idx) {
                                var list = platEditor.cloneList();
                                list[index].platform = platEditor.platformOptions[idx];
                                platEditor.commit(list);
                            }
                        }
                        PlatField {
                            Layout.fillWidth: true
                            placeholderText: "@username"
                            text: modelData.username || ""
                            onEditingFinished: {
                                var list = platEditor.cloneList();
                                list[index].username = text;
                                platEditor.commit(list);
                            }
                        }
                        Switch {
                            leftPadding: 0
                            rightPadding: 0
                            implicitWidth: 46
                            implicitHeight: 26
                            Layout.preferredWidth: 46
                            Layout.minimumWidth: 46
                            Layout.maximumWidth: 46
                            checked: modelData.enabled !== false
                            indicator: Rectangle {
                                x: 0
                                y: parent.height / 2 - height / 2
                                width: 46; height: 24; radius: 12
                                color: parent.checked ? "#134e4a" : "#0a0d12"
                                border.width: 1
                                border.color: parent.checked ? "#14b8a6" : "#2d3748"
                                Behavior on color { ColorAnimation { duration: 160 } }
                                Rectangle {
                                    x: parent.parent.checked ? parent.width - width - 3 : 3
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 18; height: 18; radius: 9
                                    color: parent.parent.checked ? "#5eead4" : "#8b95a5"
                                    Behavior on x { NumberAnimation { duration: 160 } }
                                }
                            }
                            onClicked: {
                                var list = platEditor.cloneList();
                                list[index].enabled = checked;
                                platEditor.commit(list);
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Item { Layout.preferredWidth: 22; Layout.minimumWidth: 22; Layout.maximumWidth: 22 }
                        PlatField {
                            Layout.fillWidth: true
                            placeholderText: "https://… (optional URL override)"
                            font.pixelSize: 12
                            text: modelData.url || ""
                            onEditingFinished: {
                                var list = platEditor.cloneList();
                                list[index].url = text;
                                platEditor.commit(list);
                            }
                        }
                        IconBtn { glyph: "↑"; disabled: index <= 0; onClicked: { var l = platEditor.cloneList(); var t = l[index-1]; l[index-1] = l[index]; l[index] = t; platEditor.commit(l); } }
                        IconBtn { glyph: "↓"; disabled: index >= platEditor.currentList().length - 1; onClicked: { var l = platEditor.cloneList(); var t = l[index+1]; l[index+1] = l[index]; l[index] = t; platEditor.commit(l); } }
                        IconBtn { glyph: "✕"; onClicked: { var l = platEditor.cloneList(); l.splice(index, 1); platEditor.commit(l); } }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: addRow.implicitHeight + 20
            radius: 12
            color: "transparent"
            border.width: 1
            border.color: "#2d3748"
            RowLayout {
                id: addRow
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                Text { text: "+"; color: "#5eead4"; font.pixelSize: 14; font.weight: Font.DemiBold }
                ComboBox {
                    id: platAddBox
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 140
                    implicitHeight: 36
                    hoverEnabled: true
                    model: platEditor.platformOptions
                    contentItem: Text { text: platAddBox.displayText; color: "#e8eaed"; font.pixelSize: 13; font.capitalization: Font.Capitalize; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                    background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: platAddBox.hovered ? "#2d3748" : "#242b36" }
                    indicator: Text { x: platAddBox.width - width - 10; y: platAddBox.height / 2 - height / 2; text: "⌄"; color: "#8b95a5"; font.pixelSize: 14 }
                    popup: Popup {
                        y: platAddBox.height + 4
                        width: platAddBox.width
                        padding: 4
                        contentItem: ListView {
                            clip: true
                            implicitHeight: Math.min(240, contentHeight)
                            model: platAddBox.popup.visible ? platAddBox.delegateModel : null
                            ScrollIndicator.vertical: ScrollIndicator { width: 5 }
                        }
                        background: Rectangle { radius: 8; color: "#10141a"; border.width: 1; border.color: "#242b36" }
                    }
                }
                Button {
                    Layout.fillWidth: true
                    implicitHeight: 36
                    text: "Add platform"
                    hoverEnabled: true
                    contentItem: Text { text: "Add platform"; color: "#041615"; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { radius: 8; color: parent.hovered ? "#0d9488" : "#14b8a6"; Behavior on color { ColorAnimation { duration: 160 } } }
                    onClicked: {
                        var list = platEditor.cloneList();
                        var v = platEditor.platformOptions[platAddBox.currentIndex] || "twitch";
                        list.push({id: "", platform: v, username: "", url: "", enabled: true, order: list.length});
                        platEditor.commit(list);
                    }
                }
            }
        }
    }

    ColumnLayout {
        id: seqEditor
        visible: root.type === "leaderboard_sequence"
        Layout.fillWidth: true
        spacing: 8
        property var sourceOptions: ["likers", "gifters", "sharers", "commenters", "contributors"]
        property var sourceLabels: ["Лайкери", "Донори", "Шери", "Коментатори", "Контриб'ютори"]
        property var sceneOptions: ["hall_of_fame", "arena", "energy_network"]
        property var sceneLabels: ["Зал слави", "Арена", "Енергомережа"]
        property var entries: []
        function syncFromValue() {
            var v = root.value;
            if (typeof v === "string") {
                try { v = JSON.parse(v); } catch (e) { v = []; }
            }
            if (!Array.isArray(v)) v = [];
            var out = [];
            for (var i = 0; i < v.length; ++i) {
                var r = v[i] || {};
                var src = String(r.source_id || r.source || "likers").toLowerCase();
                if (seqEditor.sourceOptions.indexOf(src) < 0) src = "likers";
                var scn = String(r.scene_id || r.scene || "hall_of_fame").toLowerCase();
                if (seqEditor.sceneOptions.indexOf(scn) < 0) scn = "hall_of_fame";
                var dur = Math.max(1, Math.min(120, Math.round(Number(r.duration_sec || r.duration || 8))));
                if (isNaN(dur)) dur = 8;
                out.push({source_id: src, scene_id: scn, duration_sec: dur});
            }
            entries = out;
        }
        Component.onCompleted: syncFromValue()
        onVisibleChanged: if (visible) syncFromValue()
        Connections { target: root; function onValueChanged() { seqEditor.syncFromValue(); } }
        function commit(list) {
            entries = JSON.parse(JSON.stringify(list));
            root.changed(root.field, JSON.parse(JSON.stringify(list)));
        }
        function cloneList() { return JSON.parse(JSON.stringify(entries)); }
        Text {
            text: root.label
            color: "#e8eaed"
            font.pixelSize: 12
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }
        Text {
            visible: seqEditor.entries.length === 0
            text: "Порожньо — додайте крок нижче."
            color: "#8b95a5"
            font.pixelSize: 11
            Layout.fillWidth: true
        }
        Repeater {
            model: seqEditor.entries
            delegate: Rectangle {
                required property int index
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: seqRow.implicitHeight + 20
                radius: 12
                color: "#10141a"
                border.width: 1
                border.color: "#242b36"
                ColumnLayout {
                    id: seqRow
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: String(index + 1).padStart(2, "0")
                            color: "#5eead4"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 22
                        }
                        ComboBox {
                            id: seqSourceBox
                            Layout.fillWidth: true
                            implicitHeight: 36
                            hoverEnabled: true
                            textRole: "text"
                            valueRole: "value"
                            model: ListModel {
                                ListElement { value: "likers"; text: "Лайкери" }
                                ListElement { value: "gifters"; text: "Донори" }
                                ListElement { value: "sharers"; text: "Шери" }
                                ListElement { value: "commenters"; text: "Коментатори" }
                                ListElement { value: "contributors"; text: "Контриб'ютори" }
                            }
                            currentIndex: Math.max(0, seqEditor.sourceOptions.indexOf(String(modelData.source_id || "likers")))
                            contentItem: Text { text: seqSourceBox.displayText; color: "#e8eaed"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: seqSourceBox.hovered ? "#2d3748" : "#242b36" }
                            onActivated: function(idx) {
                                var list = seqEditor.cloneList();
                                list[index].source_id = seqEditor.sourceOptions[idx] || "likers";
                                seqEditor.commit(list);
                            }
                        }
                        ComboBox {
                            id: seqSceneBox
                            Layout.fillWidth: true
                            implicitHeight: 36
                            hoverEnabled: true
                            textRole: "text"
                            valueRole: "value"
                            model: ListModel {
                                ListElement { value: "hall_of_fame"; text: "Зал слави" }
                                ListElement { value: "arena"; text: "Арена" }
                                ListElement { value: "energy_network"; text: "Енергомережа" }
                            }
                            currentIndex: Math.max(0, seqEditor.sceneOptions.indexOf(String(modelData.scene_id || "hall_of_fame")))
                            contentItem: Text { text: seqSceneBox.displayText; color: "#e8eaed"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                            background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: seqSceneBox.hovered ? "#2d3748" : "#242b36" }
                            onActivated: function(idx) {
                                var list = seqEditor.cloneList();
                                list[index].scene_id = seqEditor.sceneOptions[idx] || "hall_of_fame";
                                seqEditor.commit(list);
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: "Тривалість (с)"; color: "#8b95a5"; font.pixelSize: 11; Layout.fillWidth: true }
                        SpinBox {
                            from: 1; to: 120; stepSize: 1
                            value: Math.max(1, Math.min(120, Number(modelData.duration_sec || 8)))
                            editable: true
                            implicitHeight: 36
                            onValueModified: {
                                var list = seqEditor.cloneList();
                                list[index].duration_sec = value;
                                seqEditor.commit(list);
                            }
                        }
                        IconBtn { glyph: "↑"; disabled: index === 0; onClicked: {
                            var list = seqEditor.cloneList();
                            var tmp = list[index - 1]; list[index - 1] = list[index]; list[index] = tmp;
                            seqEditor.commit(list);
                        } }
                        IconBtn { glyph: "↓"; disabled: index >= seqEditor.entries.length - 1; onClicked: {
                            var list = seqEditor.cloneList();
                            var tmp = list[index + 1]; list[index + 1] = list[index]; list[index] = tmp;
                            seqEditor.commit(list);
                        } }
                        IconBtn { glyph: "✕"; disabled: seqEditor.entries.length <= 1; onClicked: {
                            var list = seqEditor.cloneList();
                            list.splice(index, 1);
                            seqEditor.commit(list);
                        } }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            ComboBox {
                id: seqAddSource
                Layout.fillWidth: true
                implicitHeight: 36
                hoverEnabled: true
                textRole: "text"
                valueRole: "value"
                model: ListModel {
                    ListElement { value: "likers"; text: "Лайкери" }
                    ListElement { value: "gifters"; text: "Донори" }
                    ListElement { value: "sharers"; text: "Шери" }
                    ListElement { value: "commenters"; text: "Коментатори" }
                    ListElement { value: "contributors"; text: "Контриб'ютори" }
                }
                contentItem: Text { text: seqAddSource.displayText; color: "#e8eaed"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: seqAddSource.hovered ? "#2d3748" : "#242b36" }
            }
            ComboBox {
                id: seqAddScene
                Layout.fillWidth: true
                implicitHeight: 36
                hoverEnabled: true
                textRole: "text"
                valueRole: "value"
                model: ListModel {
                    ListElement { value: "hall_of_fame"; text: "Зал слави" }
                    ListElement { value: "arena"; text: "Арена" }
                    ListElement { value: "energy_network"; text: "Енергомережа" }
                }
                contentItem: Text { text: seqAddScene.displayText; color: "#e8eaed"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                background: Rectangle { radius: 8; color: "#0f172a"; border.width: 1; border.color: seqAddScene.hovered ? "#2d3748" : "#242b36" }
            }
            IconBtn { glyph: "+"; onClicked: {
                var list = seqEditor.cloneList();
                var src = seqAddSource.currentIndex >= 0 ? seqEditor.sourceOptions[seqAddSource.currentIndex] : "likers";
                var scn = seqAddScene.currentIndex >= 0 ? seqEditor.sceneOptions[seqAddScene.currentIndex] : "hall_of_fame";
                list.push({source_id: src || "likers", scene_id: scn || "hall_of_fame", duration_sec: 8});
                seqEditor.commit(list);
            } }
        }
    }

    Popup {
        id: listPopup
        parent: Overlay.overlay
        implicitWidth: Math.min(560, Math.max(360, root.width))
        implicitHeight: 360
        modal: true
        padding: 16
        background: Rectangle { radius: 8; color: "#10141a"; border.width: 1; border.color: "#242b36" }
        contentItem: ColumnLayout {
            spacing: 10
            Text { text: root.label; color: "#e8eaed"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Text { text: "Edit the existing list entries without changing their stored schema."; color: "#8b95a5"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            TextArea {
                id: listEditor
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#e8eaed"
                font.family: "monospace"
                font.pixelSize: 11
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                background: Rectangle { radius: 8; color: "#0a0d12"; border.width: 1; border.color: listEditor.activeFocus ? "#14b8a6" : "#242b36" }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button { text: "Скасувати"; onClicked: listPopup.close() }
                Button {
                    text: "Застосувати"
                    onClicked: {
                        try {
                            var parsed = JSON.parse(listEditor.text)
                            if (!Array.isArray(parsed)) return
                            root.changed(root.field, parsed)
                            listPopup.close()
                        } catch (e) {}
                    }
                }
            }
        }
    }
}
