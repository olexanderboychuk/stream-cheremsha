pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

// Shared color chooser for all widget settings, styled after the app theme
// (WidgetsView tokens: cardBase #10141a, cardEdge #242b36, fieldBg #0a0d12,
// ink #e8eaed, muted #8b95a5, accent #14b8a6, hover #0d9488).
// value: css color string (#rrggbb, #rrggbbaa, rgba(...)). Emits accepted(colorValue).
// The picker owns its display state (displayValue) so feedback is instant even
// when the parent binds `value:` to a JS-object subproperty (no change notify).
RowLayout {
    id: root
    property string value: "#14b8a6"
    property var presets: ["#14b8a6", "#22d3ee", "#a78bfa", "#e879f9", "#34d399", "#ffd700", "#ff3355", "#ff6600", "#f4f4f5", "#8b95a5", "#10141a", "#000000"]
    signal accepted(string colorValue)
    spacing: 8

    // What the swatch / hex field / dialog actually show. Synced from value.
    property string displayValue: normalizeCss(root.value)
    onValueChanged: {
        if (!hexField.activeFocus) {
            displayValue = normalizeCss(root.value)
            hexField.text = displayValue
        }
    }

    function commit(c) {
        var css = normalizeCss(c)
        displayValue = css
        hexField.text = css
        root.accepted(css)
    }

    // Normalize any input to #rrggbb / #rrggbbaa css. Never returns garbage.
    function normalizeCss(c) {
        if (c === undefined || c === null) return "#000000"
        var s = String(c).trim()
        if (s.startsWith("rgba") || s.startsWith("rgb")) {
            try {
                var m = s.match(/[\d.]+/g) || []
                var r = Math.round(Number(m[0] || 0)), g = Math.round(Number(m[1] || 0)), b = Math.round(Number(m[2] || 0))
                var a = m.length >= 4 ? Number(m[3]) : 1
                var toH = function(v) { var h = Math.max(0, Math.min(255, v)).toString(16); return h.length === 1 ? "0" + h : h }
                var hex = "#" + toH(r) + toH(g) + toH(b)
                if (a < 1) {
                    var ah = Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16)
                    hex += ah.length === 1 ? "0" + ah : ah
                }
                return hex
            } catch (e) { return "#000000" }
        }
        if (/^#[0-9a-fA-F]{3}$/.test(s))
            return ("#" + s[1] + s[1] + s[2] + s[2] + s[3] + s[3]).toLowerCase()
        if (/^#[0-9a-fA-F]{6}$/.test(s) || /^#[0-9a-fA-F]{8}$/.test(s)) return s.toLowerCase()
        return "#000000"
    }

    // QML `color` type uses #aarrggbb order; css uses #rrggbbaa. Convert for bindings.
    function toQmlColor(css) {
        var s = normalizeCss(css)
        if (s.length === 9) return "#" + s.slice(7, 9) + s.slice(1, 7)
        return s
    }
    // QColor.toString() gives #rrggbb or #aarrggbb -> back to css #rrggbbaa.
    function fromQmlColor(c) {
        var s = String(c).toLowerCase()
        if (/^#[0-9a-f]{8}$/.test(s)) return "#" + s.slice(3, 9) + s.slice(1, 3)
        return normalizeCss(s)
    }

    // Swatch: app card style — fieldBg well, accent ring on hover, checkerboard
    // underneath so translucent colors read correctly on the dark theme.
    Rectangle {
        id: swatch
        Layout.preferredWidth: 36; Layout.minimumWidth: 36; Layout.maximumWidth: 36
        Layout.preferredHeight: 36
        radius: 8
        color: "#0a0d12"
        border.width: 1
        border.color: swatchArea.containsMouse ? "#5eead4" : "#242b36"
        Behavior on border.color { ColorAnimation { duration: 160 } }

        Grid {
            anchors.fill: parent
            anchors.margins: 4
            columns: 4
            rows: 4
            Repeater {
                model: 16
                delegate: Rectangle {
                    required property int index
                    width: (swatch.width - 8) / 4
                    height: (swatch.height - 8) / 4
                    color: (Math.floor(index / 4) + index) % 2 ? "#1a2230" : "#0d1117"
                }
            }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: 5
            color: root.toQmlColor(root.displayValue)
            border.width: 1
            border.color: "#00000055"
        }
        Text {
            anchors.centerIn: parent
            text: "▾"
            color: "#e8eaed"
            opacity: 0.85
            font.pixelSize: 11
            style: Text.Outline
            styleColor: "#000000aa"
        }
        MouseArea {
            id: swatchArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                colorDialog.selectedColor = root.toQmlColor(root.displayValue)
                colorDialog.open()
            }
        }
    }

    // Hex field: same look as the other widget-setting text fields.
    TextField {
        id: hexField
        Layout.preferredWidth: 112
        Layout.minimumWidth: 112
        Layout.maximumWidth: 112
        implicitHeight: 36
        text: root.displayValue
        color: "#e8eaed"
        font.pixelSize: 12
        font.family: "monospace"
        selectByMouse: true
        hoverEnabled: true
        background: Rectangle {
            radius: 8
            color: "#0f172a"
            border.width: 1
            border.color: hexField.activeFocus ? "#14b8a6" : (hexField.hovered ? "#2d3748" : "#242b36")
            Behavior on border.color { ColorAnimation { duration: 160 } }
        }
        onEditingFinished: root.commit(text)
    }

    ColorDialog {
        id: colorDialog
        title: "Оберіть колір"
        options: ColorDialog.ShowAlphaChannel
        onAccepted: root.commit(root.fromQmlColor(selectedColor))
    }

    // Presets: app-palette dots, accent ring on the active one, soft ring on hover.
    Flow {
        Layout.fillWidth: true
        spacing: 6
        Repeater {
            model: root.presets
            delegate: Rectangle {
                required property var modelData
                required property int index
                property bool isActive: root.displayValue.toLowerCase() === String(modelData).toLowerCase()
                width: 22; height: 22; radius: 11
                color: "#0a0d12"
                border.width: isActive ? 2 : 1
                border.color: isActive ? "#5eead4" : (dotArea.containsMouse ? "#2d3748" : "#242b36")
                Behavior on border.color { ColorAnimation { duration: 150 } }
                Rectangle {
                    anchors.centerIn: parent
                    width: 14; height: 14; radius: 7
                    color: parent.modelData
                    border.width: 1
                    border.color: "#00000055"
                }
                MouseArea {
                    id: dotArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.commit(modelData)
                }
            }
        }
    }
}
