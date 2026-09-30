import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Compact grouped add-sound form — NOT a generic form builder.
// Hotkey capture is an explicit 3-state flow: idle → listening → assigned.
// Key events are captured page-side, only while `listening` is true.
ColumnLayout {
    id: root
    property string draftName: ""
    property string draftCategory: "Меми"
    property double draftVolume: 1.0
    property string draftMode: "restart"
    property string hotkeyDraft: ""
    property string conflictText: ""
    property bool listening: false
    property string errorMsg: ""
    property var categoryModel: ["Меми", "Реакції", "Голоси", "Музика", "Атмосфера", "Ігри", "Alerts", "Custom"]
    property var modeModel: ["restart", "overlap", "replace", "queue", "hold"]
    signal nameChanged2(string v)
    signal categoryChanged2(string v)
    signal volumeChanged2(double v)
    signal modeChanged2(string v)
    signal startListening()
    signal clearHotkey()

    spacing: 10

    component FieldLabel: Text {
        property string label: ""
        text: label
        color: "#7f8aa3"
        font.pixelSize: 12
        font.weight: Font.Medium
        Layout.fillWidth: true
    }

    FieldLabel { label: spApi.strings.name_label || "Назва звуку" }
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: 40
        radius: 9; color: "#0c0f16"
        border.width: 1
        border.color: nameField.activeFocus ? "#8b5cf6" : "#26314a"
        Behavior on border.color { ColorAnimation { duration: 130 } }
        TextField {
            id: nameField
            anchors.fill: parent
            anchors.leftMargin: 12; anchors.rightMargin: 12
            placeholderText: "Airhorn"
            placeholderTextColor: "#4b5568"
            text: root.draftName
            onTextChanged: root.nameChanged2(text)
            color: "#e8ecf5"
            selectionColor: "#8b5cf6"
            font.pixelSize: 13
            background: null
        }
    }

    FieldLabel { label: spApi.strings.category_label || "Категорія" }
    ComboBox {
        id: catBox
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        model: root.categoryModel
        currentIndex: Math.max(0, model.indexOf(root.draftCategory))
        onActivated: root.categoryChanged2(currentText)
        font.pixelSize: 13
        contentItem: Text {
            leftPadding: 12; rightPadding: 30
            text: catBox.displayText; color: "#e8ecf5"; font: catBox.font
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 9; color: "#0c0f16"
            border.width: 1
            border.color: catBox.hovered ? "#4b5876" : "#26314a"
            Behavior on border.color { ColorAnimation { duration: 130 } }
        }
        indicator: Image {
            x: catBox.width - width - 12; y: (catBox.height - height) / 2
            source: Qt.resolvedUrl("../../assets/icons/chevron-down.svg")
            width: 14; height: 14
        }
        popup: Popup {
            y: catBox.height + 4; width: catBox.width
            background: Rectangle { radius: 9; color: "#0e1420"; border.width: 1; border.color: "#26314a" }
            contentItem: ListView {
                clip: true; implicitHeight: Math.min(220, contentHeight)
                model: catBox.popup.visible ? catBox.delegateModel : null
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
            highlighted: catBox.highlightedIndex === index
        }
    }

    FieldLabel { label: spApi.strings.mode_label || "Режим відтворення" }
    ComboBox {
        id: modeBox
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        model: root.modeModel
        currentIndex: Math.max(0, model.indexOf(root.draftMode))
        onActivated: root.modeChanged2(currentText)
        font.pixelSize: 13
        contentItem: Text {
            leftPadding: 12; rightPadding: 30
            text: modeBox.displayText; color: "#e8ecf5"; font: modeBox.font
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 9; color: "#0c0f16"
            border.width: 1
            border.color: modeBox.hovered ? "#4b5876" : "#26314a"
            Behavior on border.color { ColorAnimation { duration: 130 } }
        }
        indicator: Image {
            x: modeBox.width - width - 12; y: (modeBox.height - height) / 2
            source: Qt.resolvedUrl("../../assets/icons/chevron-down.svg")
            width: 14; height: 14
        }
        popup: Popup {
            y: modeBox.height + 4; width: modeBox.width
            background: Rectangle { radius: 9; color: "#0e1420"; border.width: 1; border.color: "#26314a" }
            contentItem: ListView {
                clip: true; implicitHeight: Math.min(220, contentHeight)
                model: modeBox.popup.visible ? modeBox.delegateModel : null
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
            highlighted: modeBox.highlightedIndex === index
        }
    }

    // volume grouped surface
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: 52
        radius: 9; color: "#101827"
        border.width: 1; border.color: "#1e2942"
        RowLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 10
            Image { source: Qt.resolvedUrl("../../assets/icons/web_volume.svg"); width: 15; height: 15 }
            Text { text: spApi.strings.volume_label || "Гучність"; color: "#9aa4b8"; font.pixelSize: 12 }
            CheremshaSlider {
                id: volS
                Layout.fillWidth: true
                from: 0; to: 1; value: root.draftVolume
                onValueChanged: root.volumeChanged2(value)
            }
            Text { text: Math.round(volS.value * 100) + "%"; color: "#7f8aa3"; font.pixelSize: 12; Layout.preferredWidth: 40; horizontalAlignment: Text.AlignRight }
        }
    }

    // hotkey capture surface: idle / listening / assigned
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: root.conflictText !== "" ? 76 : 52
        radius: 9
        color: root.listening ? "#1a1530" : "#101827"
        border.width: 1
        border.color: root.listening ? "#8b5cf6" : "#1e2942"
        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
        // Whole-surface click starts listening when idle (big friendly target).
        // Declared BELOW the content so buttons keep their hover/clicks.
        MouseArea {
            anchors.fill: parent
            enabled: !root.listening && root.hotkeyDraft === ""
            cursorShape: Qt.PointingHandCursor
            onClicked: root.startListening()
        }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Image { source: Qt.resolvedUrl("../../assets/icons/web_key.svg"); width: 15; height: 15 }
                Text { text: spApi.strings.hotkey_label || "Хоткей"; color: "#9aa4b8"; font.pixelSize: 12 }
                // listening prompt (pulsing dot + instructions)
                RowLayout {
                    visible: root.listening
                    spacing: 8
                    Rectangle {
                        width: 7; height: 7; radius: 3.5
                        color: "#a78bfa"
                        SequentialAnimation on opacity { loops: Animation.Infinite; running: root.listening
                            NumberAnimation { to: 0.3; duration: 500 }
                            NumberAnimation { to: 1.0; duration: 500 } }
                    }
                    Text {
                        text: spApi.strings.hotkey_listening || "Натисніть клавіші… (Esc — скасувати)"
                        color: "#c4b5fd"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                }
                // idle assign button
                Rectangle {
                    visible: !root.listening && root.hotkeyDraft === ""
                    Layout.preferredWidth: assignLbl.implicitWidth + 28
                    Layout.preferredHeight: 30
                    radius: 8
                    color: assignMa.containsMouse ? "#232e45" : "#1a2233"
                    border.width: 1
                    border.color: assignMa.containsMouse ? "#8b5cf6" : "#3b4458"
                    Behavior on color { ColorAnimation { duration: 120 } }
                    Behavior on border.color { ColorAnimation { duration: 120 } }
                    Text {
                        id: assignLbl
                        anchors.centerIn: parent
                        text: spApi.strings.hotkey_assign || "+ Призначити"
                        color: "#c9d1e0"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                    MouseArea {
                        id: assignMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.startListening()
                    }
                }
                // assigned keycap (+ replace on click)
                CheremshaKeycap {
                    visible: !root.listening && root.hotkeyDraft !== ""
                    keyText: root.hotkeyDraft
                    onClicked: root.startListening()
                }
                // clear button
                Rectangle {
                    visible: !root.listening && root.hotkeyDraft !== ""
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                    radius: 8
                    color: clearMa.containsMouse ? "#3d1a24" : "transparent"
                    border.width: 1
                    border.color: clearMa.containsMouse ? "#f87171" : "#2a3142"
                    Behavior on color { ColorAnimation { duration: 120 } }
                    Image {
                        anchors.centerIn: parent
                        width: 13; height: 13
                        source: Qt.resolvedUrl("../../assets/icons/x.svg")
                    }
                    MouseArea {
                        id: clearMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.clearHotkey()
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    visible: !root.listening && root.hotkeyDraft === ""
                    text: spApi.strings.optional || "необов'язково"
                    color: "#5b6472"; font.pixelSize: 11
                }
            }
            Text {
                visible: root.conflictText !== ""
                Layout.fillWidth: true
                text: (spApi.strings.hotkey_in_use || "Вже використовується: {name}")
                       .replace("{name}", root.conflictText)
                color: "#fbbf24"
                font.pixelSize: 11
                wrapMode: Text.Wrap
                elide: Text.ElideRight
            }
        }
    }

    Text {
        visible: root.errorMsg !== ""
        text: root.errorMsg; color: "#f87171"; font.pixelSize: 12
        Layout.fillWidth: true; wrapMode: Text.Wrap
    }
}
