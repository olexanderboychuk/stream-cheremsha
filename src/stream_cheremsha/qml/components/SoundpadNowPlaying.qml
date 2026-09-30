import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Now-playing console bar: NOW PLAYING / waveform-progress / time / volume /
// output select / monitor+stream toggles / stop. All Cheremsha-styled.
Rectangle {
    id: root
    property string trackName: ""
    property string trackCategory: ""
    property bool active: false
    property double position: 0.0
    property double duration: 0.0
    property double volume: 0.78
    property var outputModel: []
    property int outputIndex: -1

    signal volumeRequested(double v)
    signal outputPicked(int idx)
    signal stopRequested()

    function fmt(sec) {
        var s = Math.max(0, Math.floor(Number(sec) || 0));
        return "00:" + (s < 10 ? "0" + s : s);
    }

    radius: 12
    color: "#0e1420"
    border.width: 1
    border.color: root.active ? "#4b3a86" : "#26314a"
    Behavior on border.color { ColorAnimation { duration: 160 } }
    implicitHeight: 68

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 14

        // LEFT: status + title
        RowLayout {
            Layout.preferredWidth: 230
            spacing: 10
            Rectangle {
                width: 7; height: 7; radius: 3.5
                color: root.active ? "#22d3ee" : "#3b4458"
                Layout.alignment: Qt.AlignVCenter
                SequentialAnimation on opacity { running: root.active; loops: Animation.Infinite
                    NumberAnimation { to: 0.4; duration: 600 }
                    NumberAnimation { to: 1.0; duration: 600 } }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: root.active ? (spApi.strings.np_playing || "● NOW PLAYING")
                                      : (spApi.strings.np_idle || "SOUNDPAD IDLE")
                    color: root.active ? "#22d3ee" : "#5b6472"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
                Text {
                    text: root.active ? root.trackName : "—"
                    color: "#e8ecf5"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        // CENTER: progress + time
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 16
                // mini waveform-progress track
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: 5
                    radius: 2.5
                    color: "#1c2434"
                    Rectangle {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width * (root.duration > 0 ? Math.min(1, root.position / root.duration) : 0)
                        height: parent.height
                        radius: 2.5
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "#8b5cf6" }
                            GradientStop { position: 1.0; color: "#22d3ee" }
                        }
                    }
                    Rectangle {
                        visible: root.active
                        x: parent.width * (root.duration > 0 ? Math.min(1, root.position / root.duration) : 0) - 5
                        anchors.verticalCenter: parent.verticalCenter
                        width: 10; height: 10; radius: 5
                        color: "#e8ecf5"
                        border.width: 2
                        border.color: "#8b5cf6"
                    }
                }
            }
            RowLayout {
                spacing: 8
                Text {
                    visible: root.active
                    text: root.fmt(root.position) + " / " + root.fmt(root.duration)
                    color: "#7f8aa3"
                    font.pixelSize: 11
                }
                Text {
                    visible: root.active && root.trackCategory !== ""
                    text: "· " + root.trackCategory
                    color: "#5b6472"
                    font.pixelSize: 11
                }
                Item { Layout.fillWidth: true }
            }
        }

        // volume
        RowLayout {
            spacing: 7
            Image { source: Qt.resolvedUrl("../../assets/icons/web_volume.svg"); width: 15; height: 15 }
            CheremshaSlider {
                id: vol
                Layout.preferredWidth: 120
                from: 0; to: 1
                value: root.volume
                onValueChanged: root.volumeRequested(value)
            }
            Text { text: Math.round(vol.value * 100) + "%"; color: "#7f8aa3"; font.pixelSize: 11; Layout.preferredWidth: 34 }
        }

        // output select (Cheremsha styled)
        ComboBox {
            id: out
            Layout.preferredWidth: 200
            Layout.preferredHeight: 34
            model: root.outputModel
            currentIndex: root.outputIndex
            onActivated: root.outputPicked(currentIndex)
            font.pixelSize: 12
            delegate: ItemDelegate {
                width: ListView.view ? ListView.view.width : implicitWidth
                contentItem: Text {
                    text: modelData
                    color: parent.highlighted ? "#ffffff" : "#c9d1e0"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 6
                    color: parent.highlighted ? "#8b5cf6" : (parent.hovered ? "#1c2434" : "transparent")
                }
                highlighted: out.highlightedIndex === index
            }
            contentItem: Text {
                leftPadding: 10; rightPadding: 26
                text: out.displayText
                color: "#b8c1cf"
                font: out.font
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 8
                color: out.hovered ? "#141c2c" : "#0a0f19"
                border.width: 1
                border.color: out.hovered ? "#4b5876" : "#232d42"
                Behavior on border.color { ColorAnimation { duration: 120 } }
            }
            indicator: Image {
                x: out.width - width - 10; y: (out.height - height) / 2
                source: Qt.resolvedUrl("../../assets/icons/chevron-down.svg")
                width: 13; height: 13
            }
            popup: Popup {
                y: out.height + 4
                width: out.width
                background: Rectangle { radius: 8; color: "#0e1420"; border.width: 1; border.color: "#26314a" }
                contentItem: ListView {
                    clip: true
                    implicitHeight: Math.min(200, contentHeight)
                    model: out.popup.visible ? out.delegateModel : null
                }
            }
        }

        // stop
        Button {
            Layout.preferredWidth: 40
            Layout.preferredHeight: 34
            visible: root.active
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
            contentItem: Image {
                source: Qt.resolvedUrl("../../assets/icons/stop.svg")
                width: 12; height: 12
                anchors.centerIn: parent
            }
            background: Rectangle {
                radius: 8
                color: parent.hovered ? "#3d1a24" : "#1c2434"
                border.width: 1
                border.color: parent.hovered ? "#f87171" : "#2a3142"
                Behavior on color { ColorAnimation { duration: 120 } }
            }
            onClicked: root.stopRequested()
        }
    }
}
