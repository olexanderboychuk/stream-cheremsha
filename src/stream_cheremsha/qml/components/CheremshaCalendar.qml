import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Reusable Cheremsha calendar popup.
// Public API (preserved):
//   property date current_date — selected date (JS Date / QDate representation)
//   signal dateSelected(date)  — emitted when the user picks a day
Rectangle {
    id: root
    width: 280
    implicitHeight: body.implicitHeight + 24
    height: implicitHeight
    color: "#0a0b0e"
    border.color: "#2a3142"
    border.width: 1
    radius: 10

    property date current_date: new Date(2026, 0, 1)
    property date viewDate: current_date
    property bool selected: false
    signal dateSelected(date newDate)

    readonly property color primaryPurple: "#8b5cf6"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"

    readonly property var monthNames: ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"]

    onCurrent_dateChanged: {
        if (!_sameDay(viewDate, current_date)) {
            viewDate = new Date(current_date.getFullYear(), current_date.getMonth(), 1)
            _rebuild()
        }
    }
    onViewDateChanged: _rebuild()

    function _sameDay(a, b) {
        return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
    }

    function _shiftMonth(delta) {
        viewDate = new Date(viewDate.getFullYear(), viewDate.getMonth() + delta, 1)
    }

    function _isToday(y, m, d) {
        var n = new Date()
        return n.getFullYear() === y && n.getMonth() === (m - 1) && n.getDate() === d
    }

    function _isSelected(y, m, d) {
        return current_date.getFullYear() === y && current_date.getMonth() === (m - 1) && current_date.getDate() === d
    }

    function _rebuild() {
        var cells = []
        var y = viewDate.getFullYear()
        var m = viewDate.getMonth() // 0-based
        var first = new Date(y, m, 1)
        var offset = (first.getDay() + 6) % 7 // Monday-first
        var today = new Date()
        for (var i = 0; i < 42; i++) {
            var d = new Date(y, m, 1 - offset + i)
            var dy = d.getFullYear()
            var dm = d.getMonth() + 1
            var dd = d.getDate()
            cells.push({
                "day": dd,
                "month": dm,
                "year": dy,
                "inMonth": d.getMonth() === m,
                "isSelected": current_date.getFullYear() === dy && current_date.getMonth() === (dm - 1) && current_date.getDate() === dd,
                "isToday": today.getFullYear() === dy && today.getMonth() === (dm - 1) && today.getDate() === dd
            })
        }
        dayRepeater.model = cells
    }

    Component.onCompleted: {
        viewDate = new Date(current_date.getFullYear(), current_date.getMonth(), 1)
        _rebuild()
    }

    ColumnLayout {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                text: root.monthNames[viewDate.getMonth()] + " " + viewDate.getFullYear()
                color: ink
                font.pixelSize: 14
                font.weight: Font.DemiBold
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Rectangle {
                Layout.preferredWidth: 26
                Layout.preferredHeight: 26
                radius: 7
                color: prevArea.containsMouse ? "#1a2233" : "transparent"
                border.width: 1
                border.color: prevArea.containsMouse ? "#2a3142" : "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "<"
                    color: ink
                    font.pixelSize: 14
                    font.weight: Font.Bold
                }
                MouseArea {
                    id: prevArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root._shiftMonth(-1)
                }
            }
            Rectangle {
                Layout.preferredWidth: 26
                Layout.preferredHeight: 26
                radius: 7
                color: nextArea.containsMouse ? "#1a2233" : "transparent"
                border.width: 1
                border.color: nextArea.containsMouse ? "#2a3142" : "transparent"
                Text {
                    anchors.centerIn: parent
                    text: ">"
                    color: ink
                    font.pixelSize: 14
                    font.weight: Font.Bold
                }
                MouseArea {
                    id: nextArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root._shiftMonth(1)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
                delegate: Text {
                    required property string modelData
                    text: modelData
                    color: muted
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 7
            rowSpacing: 2
            columnSpacing: 0
            Repeater {
                id: dayRepeater
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    radius: 7
                    color: modelData.isSelected ? "#8b5cf6" : (dayArea.containsMouse ? "#161d2c" : "transparent")
                    border.width: modelData.isToday && !modelData.isSelected ? 1 : 0
                    border.color: "#3d4a63"
                    Text {
                        anchors.centerIn: parent
                        text: modelData.day
                        color: modelData.isSelected ? "white" : (modelData.inMonth ? "#e8eaed" : "#5b6a82")
                        font.pixelSize: 13
                        font.weight: modelData.isSelected ? Font.DemiBold : Font.Normal
                    }
                    MouseArea {
                        id: dayArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var picked = new Date(modelData.year, modelData.month - 1, modelData.day)
                            root.current_date = picked
                            root.selected = true
                            root._rebuild()
                            root.dateSelected(picked)
                        }
                    }
                }
            }
        }
    }
}
