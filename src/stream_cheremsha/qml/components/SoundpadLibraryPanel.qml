import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Body of the MyInstants library modal (used inside CheremshaModal).
// Talks to spApi directly: rows/status/page come from its properties,
// actions go through its slots. All strings via spApi.libraryStrings.
Item {
    id: panel
    implicitHeight: 430

    readonly property var rows: _rows()
    function _rows() {
        try { return JSON.parse(spApi.libraryRowsJson || "[]"); } catch (err) { return []; }
    }

    readonly property string status: spApi.libraryStatus
    readonly property int page: spApi.libraryPage
    readonly property bool loading: panel.status === "loading"
    readonly property bool failed: panel.status === "error"
    readonly property bool showStates: panel.loading || panel.failed || panel.rows.length === 0

    // Path of the row that was just added (drives the «Додано» flash).
    property string addedPath: ""
    Timer {
        id: addedTimer
        interval: 1600
        repeat: false
        onTriggered: panel.addedPath = ""
    }

    Connections {
        target: spApi
        function onLibraryAddFailed(path) {
            if (panel.addedPath === String(path)) panel.addedPath = "";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // ---- Loading / error / empty states ----
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: panel.showStates ? 340 : 0
            visible: panel.showStates

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                width: Math.min(360, parent.width - 40)

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: panel.loading ? (spApi.libraryStrings.loading || "Завантаження звуків…")
                                        : (panel.failed ? (spApi.libraryStrings.error_title || "Не вдалося завантажити звуки")
                                                        : (spApi.libraryStrings.empty_title || "На цій сторінці немає звуків"))
                    color: "#e8ecf5"
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                }

                BusyIndicator {
                    Layout.alignment: Qt.AlignHCenter
                    running: panel.loading
                    visible: panel.loading
                    width: 28; height: 28
                }

                Button {
                    id: retryBtn
                    visible: panel.failed && !panel.loading
                    text: spApi.libraryStrings.retry || "Спробувати ще раз"
                    hoverEnabled: true
                    focusPolicy: Qt.TabFocus
                    font.pixelSize: 13
                    implicitWidth: 170
                    implicitHeight: 36
                    contentItem: Text {
                        text: retryBtn.text; color: "white"; font: retryBtn.font
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 9
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: retryBtn.pressed ? "#7c3aed" : (retryBtn.hovered ? "#9d71f7" : "#9b5cff") }
                            GradientStop { position: 1.0; color: retryBtn.pressed ? "#6d28d9" : (retryBtn.hovered ? "#8b5cf6" : "#7c3aed") }
                        }
                    }
                    onClicked: spApi.loadLibraryPage(panel.page)
                }
            }
        }

        // ---- Sound list ----
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !panel.showStates
            model: panel.rows
            spacing: 8
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: rowItem
                width: listView.width
                height: 56
                radius: 10
                color: rowMa.containsMouse ? "#141d30" : "#0e1524"
                border.width: 1
                border.color: spApi.previewPlayingId === modelData.path ? "#7c3aed" : "#1e2942"
                Behavior on color { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title || modelData.path
                        color: "#e8ecf5"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    // Play / stop preview
                    Rectangle {
                        id: playBtn
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        radius: 17
                        readonly property bool playing: spApi.previewPlayingId === modelData.path
                        color: playing ? "#2a1e4d" : (playMa.containsMouse ? "#18233c" : "#101a2e")
                        border.width: 1
                        border.color: playing ? "#9b5cff" : (playMa.containsMouse ? "#3a4a6e" : "#26314a")
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Image {
                            anchors.centerIn: parent
                            width: 14; height: 14
                            source: playBtn.playing ? Qt.resolvedUrl("../../assets/icons/stop.svg")
                                                    : Qt.resolvedUrl("../../assets/icons/play.svg")
                            opacity: 0.95
                        }

                        MouseArea {
                            id: playMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (playBtn.playing) spApi.stopPreview();
                                else spApi.previewSound(modelData.path);
                            }
                        }
                    }

                    // Add to soundpad
                    Rectangle {
                        id: addBtn
                        Layout.preferredWidth: 92
                        Layout.preferredHeight: 34
                        radius: 9
                        readonly property bool justAdded: panel.addedPath === modelData.path
                        color: justAdded ? "#1d3a2a" : (addMa.containsMouse ? "#18233c" : "#101a2e")
                        border.width: 1
                        border.color: justAdded ? "#34d399" : (addMa.containsMouse ? "#3a4a6e" : "#26314a")
                        Behavior on color { ColorAnimation { duration: 120 } }

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Image {
                                width: 13; height: 13
                                source: addBtn.justAdded ? Qt.resolvedUrl("../../assets/icons/check.svg")
                                                         : Qt.resolvedUrl("../../assets/icons/web_plus.svg")
                                opacity: 0.95
                            }
                            Text {
                                text: addBtn.justAdded ? (spApi.libraryStrings.added || "Додано")
                                                       : (spApi.libraryStrings.add || "Додати")
                                color: addBtn.justAdded ? "#34d399" : "#c7d2e5"
                                font.pixelSize: 12
                            }
                        }

                        MouseArea {
                            id: addMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                panel.addedPath = modelData.path;
                                addedTimer.restart();
                                spApi.addLibrarySound(modelData.path);
                            }
                        }
                    }
                }

                MouseArea {
                    id: rowMa
                    anchors.fill: parent
                    hoverEnabled: true
                }
            }
        }

        // ---- Pagination ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            visible: !panel.showStates
            spacing: 10

            Button {
                id: prevBtn
                text: spApi.libraryStrings.prev || "Назад"
                enabled: panel.page > 1 && !panel.loading
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 12
                implicitWidth: 96
                implicitHeight: 34
                opacity: prevBtn.enabled ? 1.0 : 0.45
                contentItem: Text {
                    text: prevBtn.text; color: "#c7d2e5"; font: prevBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: (prevBtn.hovered && prevBtn.enabled) ? "#18233c" : "#0f1728"
                    border.width: 1; border.color: (prevBtn.hovered && prevBtn.enabled) ? "#3a4a6e" : "#26314a"
                }
                onClicked: spApi.loadLibraryPage(panel.page - 1)
            }

            Item { Layout.fillWidth: true }

            Text {
                text: (spApi.libraryStrings.page || "Сторінка {n}").replace("{n}", String(panel.page))
                color: "#7f8aa3"
                font.pixelSize: 12
            }

            Item { Layout.fillWidth: true }

            Button {
                id: nextBtn
                text: spApi.libraryStrings.next || "Далі"
                enabled: !panel.loading
                hoverEnabled: true
                focusPolicy: Qt.TabFocus
                font.pixelSize: 12
                implicitWidth: 96
                implicitHeight: 34
                contentItem: Text {
                    text: nextBtn.text; color: "#c7d2e5"; font: nextBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: nextBtn.hovered ? "#18233c" : "#0f1728"
                    border.width: 1; border.color: nextBtn.hovered ? "#3a4a6e" : "#26314a"
                }
                onClicked: spApi.loadLibraryPage(panel.page + 1)
            }
        }
    }
}
