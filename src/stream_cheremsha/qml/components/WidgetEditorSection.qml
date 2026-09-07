import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string description: ""
    property string icon: ""
    property bool collapsible: true
    property bool expanded: true
    property string validationState: "normal" // normal | warning | invalid
    property bool headerHovered: false
    default property alias content: contentColumn.data

    Layout.fillWidth: true
    implicitHeight: sectionColumn.implicitHeight + 36
    color: "#10141a"
    border.width: 1
    border.color: root.headerHovered ? "#2d3748" : "#242b36"
    Behavior on border.color { ColorAnimation { duration: 160 } }
    radius: 9

    ColumnLayout {
        id: sectionColumn
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        ColumnLayout {
            id: header
            Layout.fillWidth: true
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: root.icon; visible: text !== ""; color: "#5eead4"; font.pixelSize: 13 }
                Text {
                    Layout.fillWidth: true
                    text: root.title.toUpperCase()
                    color: root.headerHovered ? "#f3f4f6" : "#e8eaed"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.1
                }
                Text {
                    visible: root.validationState !== "normal"
                    text: root.validationState === "invalid" ? "!" : "·"
                    color: root.validationState === "invalid" ? "#fb7185" : "#fbbf24"
                    font.bold: true
                }
                Text {
                    visible: root.collapsible
                    text: root.expanded ? "⌃" : "⌄"
                    color: "#8b95a5"
                    font.pixelSize: 16
                }
            }
            Text {
                visible: root.description !== ""
                Layout.fillWidth: true
                text: root.description
                color: "#8b95a5"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }
        Item {
            id: body
            Layout.fillWidth: true
            visible: root.expanded
            implicitHeight: visible ? contentColumn.implicitHeight : 0
            clip: true
            GridLayout {
                id: contentColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
            columns: width < 430 ? 1 : 2
            columnSpacing: 28
            rowSpacing: 12
            }
        }
    }

    HoverHandler {
        id: headerHover
        onHoveredChanged: root.headerHovered = hovered
    }
    TapHandler {
        enabled: root.collapsible
        onTapped: root.expanded = !root.expanded
    }
}
