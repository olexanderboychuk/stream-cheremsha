import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Reusable Cheremsha date field with calendar popup.
// Data contract: `text` is always "YYYY-MM-DD" (backend format, preserved).
// Internally the picked value is also exposed as `value` (QDate/JS date).
Rectangle {
    id: root
    implicitWidth: 200
    implicitHeight: 38
    width: 200
    height: 38
    color: "#0c0f16"
    border.color: fieldArea.containsMouse || calendarPopup.visible ? "#8b5cf6" : "#2a3142"
    border.width: 1
    radius: 8

    property date value: new Date()
    property string text: isoFromDate(new Date())
    signal datePicked(string isoDate)

    property bool __syncing: false
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color cardEdge: "#2a3142"
    readonly property url iconSource: Qt.resolvedUrl("../../assets/icons/web_calendar.svg")

    function _pad2(n) { return (n < 10 ? "0" : "") + n }
    function isoFromDate(d) {
        if (!d || isNaN(d.getTime()))
            return ""
        return d.getFullYear() + "-" + _pad2(d.getMonth() + 1) + "-" + _pad2(d.getDate())
    }
    function parseIso(s) {
        var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((s || "").trim())
        if (!m)
            return null
        var d = new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10))
        if (isNaN(d.getTime()))
            return null
        if (d.getFullYear() !== parseInt(m[1], 10) || (d.getMonth() + 1) !== parseInt(m[2], 10) || d.getDate() !== parseInt(m[3], 10))
            return null
        return d
    }
    function setIsoDate(s) {
        var d = parseIso(s)
        if (d === null)
            return false
        __syncing = true
        value = d
        text = isoFromDate(d)
        __syncing = false
        return true
    }

    onTextChanged: {
        if (__syncing)
            return
        var d = parseIso(text)
        if (d === null) {
            // Revert invalid external edits to keep the YYYY-MM-DD contract.
            __syncing = true
            text = isoFromDate(value)
            __syncing = false
            return
        }
        if (d.getTime() !== value.getTime()) {
            __syncing = true
            value = d
            var iso = isoFromDate(d)
            if (text !== iso)
                text = iso
            __syncing = false
        }
    }
    onValueChanged: {
        if (__syncing)
            return
        __syncing = true
        var iso = isoFromDate(value)
        if (text !== iso)
            text = iso
        __syncing = false
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 8
        Text {
            text: root.text
            color: ink
            font.pixelSize: 12
            Layout.fillWidth: true
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        Image {
            source: root.iconSource
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            Layout.alignment: Qt.AlignVCenter
        }
    }

    MouseArea {
        id: fieldArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: calendarPopup.open()
    }

    Popup {
        id: calendarPopup
        x: 0
        y: root.height + 4
        width: 280
        implicitHeight: cal.implicitHeight
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0
        background: Item {}

        contentItem: CheremshaCalendar {
            id: cal
            current_date: root.value
            onDateSelected: function (picked) {
                root.__syncing = true
                root.value = picked
                root.text = root.isoFromDate(picked)
                root.__syncing = false
                root.datePicked(root.text)
                calendarPopup.close()
            }
        }
        onOpened: {
            // Sync popup month/selection with the current field value.
            var d = root.parseIso(root.text)
            if (d !== null && d.getTime() !== root.value.getTime()) {
                root.__syncing = true
                root.value = d
                root.__syncing = false
            }
            cal.current_date = root.value
        }
    }
}
