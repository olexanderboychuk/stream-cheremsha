pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Universal font picker for all widget settings.
// Compact trigger shows the current font name rendered in that font;
// clicking opens a premium modal dialog (centered, shadowed) with search,
// live preview, and the full system font list. Emits fontPicked(family).
Rectangle {
    id: root

    // ── Public API ──────────────────────────────────────────────────
    property string fontFamily: ""
    property string previewText: "The quick brown fox jumps over the lazy dog"
    property int previewFontPx: 30
    property int rowFontPx: 15
    signal fontPicked(string family)

    // ── Layout (matches other editor field controls) ───────────────
    Layout.preferredWidth: 220
    Layout.minimumWidth: 220
    Layout.maximumWidth: 220
    implicitHeight: 36

    // ── Style ───────────────────────────────────────────────────────
    color: "#0f172a"
    radius: 8
    border.width: 1
    border.color: triggerArea.containsMouse ? "#2d3748" : "#242b36"
    Behavior on border.color { ColorAnimation { duration: 160 } }

    // ── Internal state ──────────────────────────────────────────────
    property int fontCount: 0
    property string previewFont: ""
    property string searchText: ""
    property bool __syncing: false

    // Plain JS string arrays built in QML (never Python objects — avoids
    // V4ReferenceObject wrapping). filteredFamilies drives the ListView.
    property var allFontNames: []
    property var filteredFamilies: []

    function _loadNames() {
        var fams = [];
        try {
            if (typeof api !== "undefined" && api && typeof api.systemFontFamiliesJoined === "function") {
                var joined = api.systemFontFamiliesJoined();
                if (joined)
                    fams = joined.split("\n");
            }
        } catch (e) {}
        if (!fams.length)
            fams = ["system-ui", "Segoe UI", "Arial", "Verdana", "Tahoma"];
        allFontNames = fams;
        fontCount = fams.length;
    }

    function rebuildFilter() {
        var q = root.searchText.trim().toLowerCase();
        var out = [];
        for (var i = 0; i < allFontNames.length; ++i) {
            var fam = String(allFontNames[i]);
            if (!q || fam.toLowerCase().indexOf(q) >= 0)
                out.push(fam);
        }
        filteredFamilies = out;
    }

    function selectFont(family) {
        __syncing = true;
        fontFamily = family;
        __syncing = false;
        fontPicked(family);
        fontPopup.close();
    }

    Component.onCompleted: {
        _loadNames();
        rebuildFilter();
        if (!previewFont)
            previewFont = root.fontFamily || (allFontNames[0] || "");
    }
    onFontFamilyChanged: if (!__syncing) previewFont = fontFamily

    // ── Compact trigger ─────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 6

        Text {
            text: root.fontFamily || "Choose font…"
            color: root.fontFamily ? "#e8eaed" : "#8b95a5"
            font.family: root.fontFamily || "system-ui"
            font.pixelSize: 13
            Layout.fillWidth: true
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        Text {
            text: "▾"
            color: "#8b95a5"
            font.pixelSize: 12
            Layout.alignment: Qt.AlignVCenter
        }
    }

    MouseArea {
        id: triggerArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: fontPopup.open()
    }

    // ── Premium modal dialog ────────────────────────────────────────
    Popup {
        id: fontPopup
        parent: Overlay.overlay
        width: 520
        height: 620
        x: Math.round((Overlay.overlay.width - width) / 2)
        y: Math.round((Overlay.overlay.height - height) / 2)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0

        Transition {
            from: "top"
            to: "bottom"
            NumberAnimation { property: "opacity"; duration: 150; easing.type: Easing.OutCubic }
        }

        background: Item {
            // Soft drop shadow — stacked rounded rects for a blurred falloff
            Repeater {
                model: 8
                Rectangle {
                    required property int index
                    anchors.fill: parent
                    anchors.margins: -(3 + index * 3)
                    radius: 16 + (3 + index * 3)
                    color: "#020409"
                    opacity: 0.11 * (1 - index / 8)
                }
            }

            // Card
            Rectangle {
                anchors.fill: parent
                radius: 16
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#1a2231" }
                    GradientStop { position: 1.0; color: "#0f141d" }
                }
                border.width: 1
                border.color: "#2b3548"
            }
        }

        contentItem: Item {
            // NOTE: ColumnLayout margins (top/bottomMargin) are rejected by this
            // Qt build at compile time — use an Item wrapper for the padding.
            ColumnLayout {
                id: contentLayout
                anchors.fill: parent
                anchors.margins: 24
                spacing: 14

            // ── Header ───────────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    spacing: 3
                    Text {
                        text: "Choose font"
                        color: "#f2f4f8"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "Pick a typeface for this widget"
                        color: "#7d8798"
                        font.pixelSize: 12
                    }
                }
                Item { Layout.fillWidth: true }

                // Close button
                Rectangle {
                    id: closeBtn
                    width: 30
                    height: 30
                    radius: 15
                    color: closeArea.containsMouse ? "#ffffff14" : "transparent"
                    Behavior on color { ColorAnimation { duration: 120 } }

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeArea.containsMouse ? "#e8eaed" : "#7d8798"
                        font.pixelSize: 11
                    }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: fontPopup.close()
                    }
                }
            }

            // ── Search field ─────────────────────────────────────────
            Rectangle {
                id: searchBox
                Layout.fillWidth: true
                implicitHeight: 40
                radius: 12
                color: "#0c1119"
                border.width: 1
                border.color: searchField.activeFocus ? "#14b8a6" : "#273043"
                Behavior on border.color { ColorAnimation { duration: 160 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    // Magnifier icon (inline SVG — this QtQuick build has no Ellipse type)
                    Image {
                        source: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14'><circle cx='5.75' cy='5.75' r='4.25' fill='none' stroke='%237d8798' stroke-width='1.6'/><line x1='9.2' y1='9.2' x2='13' y2='13' stroke='%237d8798' stroke-width='1.6' stroke-linecap='round'/></svg>"
                        width: 14
                        height: 14
                        smooth: true
                        Layout.alignment: Qt.AlignVCenter
                    }

                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        placeholderText: "Search fonts…"
                        text: root.searchText
                        color: "#e8eaed"
                        font.pixelSize: 13
                        padding: 0
                        selectByMouse: true
                        background: Item {}
                        onTextChanged: {
                            root.searchText = text
                            root.rebuildFilter()
                        }
                    }

                    // Clear button
                    Text {
                        visible: searchField.text.length > 0
                        text: "✕"
                        color: "#7d8798"
                        font.pixelSize: 10
                        Layout.alignment: Qt.AlignVCenter
                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -6
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                searchField.text = ""
                                root.searchText = ""
                                root.rebuildFilter()
                                searchField.forceActiveFocus()
                            }
                        }
                    }
                }
            }

            // ── Live preview card ────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                radius: 12
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#1c2536" }
                    GradientStop { position: 1.0; color: "#131a28" }
                }
                border.width: 1
                border.color: "#273043"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4

                    Text {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: root.previewText
                        font.family: root.previewFont || "system-ui"
                        font.pixelSize: root.previewFontPx
                        color: "#f2f4f8"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: (root.previewFont || "—") + "  ·  " + root.previewFontPx + "px"
                        color: "#7d8798"
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            // ── Font list ────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#0b101a"
                border.width: 1
                border.color: "#232c3e"

                ListView {
                    id: fontList
                    anchors.fill: parent
                    anchors.margins: 6
                    leftMargin: 8
                    rightMargin: 8
                    clip: true
                    model: root.filteredFamilies
                    spacing: 2
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollIndicator.vertical: ScrollIndicator {
                        width: 4
                        padding: 4
                    }

                    delegate: Rectangle {
                        id: rowDelegate
                        required property var modelData
                        width: ListView.view.width
                        height: 38
                        radius: 9

                        color: (root.fontFamily === String(modelData)) ? "#14b8a626"
                             : (rowHover.containsMouse ? "#ffffff0d" : "transparent")
                        border.width: (root.fontFamily === String(modelData)) ? 1 : 0
                        border.color: "#14b8a670"
                        Behavior on color { ColorAnimation { duration: 120 } }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Text {
                                text: String(modelData)
                                font.family: String(modelData)
                                font.pixelSize: root.rowFontPx
                                color: (root.fontFamily === String(modelData)) ? "#ccfbf1" : "#dfe4ec"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }

                            // Selected badge
                            Rectangle {
                                visible: root.fontFamily === String(modelData)
                                width: 18
                                height: 18
                                radius: 9
                                color: "#14b8a6"
                                Layout.alignment: Qt.AlignVCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: "✓"
                                    color: "#052e2b"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                }
                            }
                        }

                        MouseArea {
                            id: rowHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: root.previewFont = String(modelData)
                            onClicked: root.selectFont(String(modelData))
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.filteredFamilies.length === 0
                    text: "No fonts found"
                    color: "#7d8798"
                    font.pixelSize: 12
                }
            }

            // ── Footer ───────────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.filteredFamilies.length + " font" + (root.filteredFamilies.length !== 1 ? "s" : "")
                    color: "#7d8798"
                    font.pixelSize: 12
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "Esc — close"
                    color: "#5b6472"
                    font.pixelSize: 11
                }
            }
            }
        }

        onOpened: {
            root.searchText = "";
            root.rebuildFilter();
            root.previewFont = root.fontFamily || (root.allFontNames[0] || "");
            fontList.positionViewAtBeginning();
            searchField.forceActiveFocus();
        }
    }
}
