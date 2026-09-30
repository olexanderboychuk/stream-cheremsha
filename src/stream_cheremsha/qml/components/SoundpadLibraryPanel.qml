import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Body of the MyInstants library modal (used inside CheremshaModal).
// Talks to spApi directly: rows/status/page come from its properties,
// actions go through its slots. All strings via spApi.libraryStrings.
Item {
    id: panel
    implicitHeight: 430

    // Palette — established Cheremsha values only (navy surfaces, purple accent).
    readonly property color rowBg: "#111a2a"
    readonly property color rowHoverBg: "#151f32"
    readonly property color rowBorder: "#26314a"
    readonly property color accentSoft: "#5a4fcf"   // hover border (rows, pagination)
    readonly property color accentStrong: "#8b5cf6" // playing / active state

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

                // Lightweight spinner — local SVG arc, no native controls.
                Item {
                    Layout.alignment: Qt.AlignHCenter
                    width: 26; height: 26
                    visible: panel.loading
                    Image {
                        id: spinnerImg
                        anchors.centerIn: parent
                        width: 24; height: 24
                        source: Qt.resolvedUrl("../../assets/icons/spinner.svg")
                        RotationAnimation {
                            target: spinnerImg
                            from: 0; to: 360
                            duration: 900
                            easing.type: Easing.Linear
                            running: panel.loading
                        }
                    }
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
                    scale: retryBtn.pressed ? 0.97 : 1.0
                    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
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

            // Styled scrollbar — no native Qt artifacts.
            ScrollBar.vertical: ScrollBar {
                width: 7
                policy: ScrollBar.AsNeeded
                background: Rectangle {
                    implicitWidth: 7
                    radius: 3
                    color: "#0f1219"
                }
                contentItem: Rectangle {
                    implicitWidth: 4
                    radius: 2
                    color: parent.pressed ? panel.accentStrong : (parent.hovered ? "#52607a" : "#3d4a60")
                }
            }

            delegate: Rectangle {
                id: rowItem
                width: listView.width
                height: 68
                radius: 10
                readonly property bool isPlaying: spApi.previewPlayingId === modelData.path
                readonly property bool isLoading: spApi.previewLoadingId === modelData.path
                color: (isPlaying || isLoading) ? panel.rowHoverBg
                       : (rowMa.containsMouse ? panel.rowHoverBg : panel.rowBg)
                border.width: 1
                border.color: isPlaying ? panel.accentStrong
                               : (isLoading ? panel.accentSoft
                               : (rowMa.containsMouse ? panel.accentSoft : panel.rowBorder))
                Behavior on color { ColorAnimation { duration: 140 } }
                Behavior on border.color { ColorAnimation { duration: 140 } }

                // Row hover layer FIRST (below content): the play/add controls
                // declared after it sit on top and receive their own clicks;
                // declaring this last would steal every click from them.
                MouseArea {
                    id: rowMa
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 14
                    spacing: 12

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title || modelData.path
                        color: "#e7ebf5"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    // Play / stop preview — shared component, card-consistent states.
                    // `accented` lights it up while the whole row is hovered;
                    // `loading` shows a spinner until the audio is cached and playing.
                    CheremshaPlayButton {
                        id: playBtn
                        diameter: 40
                        playing: rowItem.isPlaying
                        loading: rowItem.isLoading
                        accented: rowMa.containsMouse && !playBtn.playing && !playBtn.loading
                        onClicked: {
                            if (playBtn.playing || playBtn.loading) spApi.stopPreview();
                            else spApi.previewSound(modelData.path);
                        }
                    }

                    // Add to soundpad — primary CTA, app-wide gradient style.
                    Button {
                        id: addBtn
                        Layout.preferredWidth: 104
                        Layout.preferredHeight: 40
                        readonly property bool justAdded: panel.addedPath === modelData.path
                        hoverEnabled: true
                        focusPolicy: Qt.NoFocus
                        font.pixelSize: 13
                        scale: addBtn.pressed && !addBtn.justAdded ? 0.97 : 1.0
                        Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
                        contentItem: RowLayout {
                            spacing: 7
                            Image {
                                width: 15; height: 15
                                source: addBtn.justAdded ? Qt.resolvedUrl("../../assets/icons/check.svg")
                                                         : Qt.resolvedUrl("../../assets/icons/plus.svg")
                            }
                            Text {
                                text: addBtn.justAdded ? (spApi.libraryStrings.added || "Додано")
                                                       : (spApi.libraryStrings.add || "Додати")
                                color: addBtn.justAdded ? "#34d399" : "#f4f2ff"
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.2
                            }
                        }
                        background: Rectangle {
                            radius: 9
                            color: addBtn.justAdded ? "#1d3a2a" : "transparent"
                            border.width: addBtn.justAdded || addBtn.hovered ? 1 : 0
                            border.color: addBtn.justAdded ? "#34d399" : "#b3a6ff"
                            Behavior on color { ColorAnimation { duration: 150 } }

                            // Subtle hover glow — soft alpha ring, no blur/shaders.
                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width + 8
                                height: parent.height + 8
                                radius: parent.radius + 4
                                color: "#8b5cf6"
                                opacity: addBtn.hovered && !addBtn.justAdded ? 0.16 : 0.0
                                Behavior on opacity { NumberAnimation { duration: 150 } }
                            }

                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                visible: !addBtn.justAdded
                                gradient: Gradient {
                                    orientation: Gradient.Vertical
                                    GradientStop { position: 0.0; color: addBtn.pressed ? "#6a58dd" : (addBtn.hovered ? "#8f7dff" : "#7d6bf4") }
                                    GradientStop { position: 1.0; color: addBtn.pressed ? "#5b49c9" : (addBtn.hovered ? "#7463e8" : "#6452da") }
                                }
                            }
                        }
                        onClicked: {
                            panel.addedPath = modelData.path;
                            addedTimer.restart();
                            spApi.addLibrarySound(modelData.path);
                        }
                    }
                }
            }
        }

        // ---- Pagination ----
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
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
                implicitHeight: 36
                opacity: prevBtn.enabled ? 1.0 : 0.45
                scale: prevBtn.pressed && prevBtn.enabled ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
                contentItem: Text {
                    text: prevBtn.text; color: "#c7d2e5"; font: prevBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: (prevBtn.hovered && prevBtn.enabled) ? "#161d33" : "#0f1728"
                    border.width: 1; border.color: (prevBtn.hovered && prevBtn.enabled) ? panel.accentSoft : "#26314a"
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
                implicitHeight: 36
                scale: nextBtn.pressed && nextBtn.enabled ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
                contentItem: Text {
                    text: nextBtn.text; color: "#c7d2e5"; font: nextBtn.font
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 9; color: nextBtn.hovered ? "#161d33" : "#0f1728"
                    border.width: 1; border.color: nextBtn.hovered ? panel.accentSoft : "#26314a"
                }
                onClicked: spApi.loadLibraryPage(panel.page + 1)
            }
        }
    }
}
