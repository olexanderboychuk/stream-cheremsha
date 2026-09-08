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

    Layout.fillWidth: true
    spacing: 8

    RowLayout {
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
            value: Number(root.value || root.minimum)
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
            value: Number(root.value || root.minimum)
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
            Layout.preferredWidth: 140
            Layout.minimumWidth: 140
            Layout.maximumWidth: 140
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
        TextField {
            id: colorField
            visible: root.type === "color"
            Layout.preferredWidth: 120
            Layout.minimumWidth: 120
            Layout.maximumWidth: 120
            implicitHeight: 36
            text: root.value
            color: "#e8eaed"
            padding: 9
            hoverEnabled: true
            background: Rectangle { radius: 7; color: colorField.text; border.width: 1; border.color: "#566174" }
            onTextChanged: if (activeFocus) root.changed(root.field, text)
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
