import QtQuick
import QtQuick.Layouts

// Generic centered modal overlay for Cheremsha desktop UI.
// Lightweight: plain opacity/scale NumberAnimations (~160ms), no effects,
// no blur, no shaders. Body/footer injected via Components; Loaders report
// the loaded item's implicitHeight so the dialog sizes to its content and
// nothing collapses or overlaps.
Item {
    id: modal
    anchors.fill: parent
    visible: false
    focus: true
    z: 1000

    property string title: ""
    property string subtitle: ""
    property bool opened: false
    // Backdrop target: rgba(0,0,0,0.45-0.55). Pure black at 0.5 keeps the
    // page recognizable instead of hiding it.
    property real dimOpacity: 0.5
    property Component body: null
    property Component footer: null

    signal closeRequested()

    function open() {
        visible = true;
        forceActiveFocus();
        backdrop.opacity = modal.dimOpacity;
        dialog.opacity = 1.0;
        dialog.scale = 1.0;
    }

    function close() {
        backdrop.opacity = 0.0;
        dialog.opacity = 0.0;
        dialog.scale = 0.97;
        hideTimer.restart();
    }

    onOpenedChanged: {
        if (opened) open();
        else if (visible) close();
    }

    Timer {
        id: hideTimer
        interval: 180
        repeat: false
        onTriggered: {
            if (!modal.opened) modal.visible = false;
        }
    }

    Rectangle {
        id: backdrop
        anchors.fill: parent
        color: "#000000"
        opacity: 0.0
        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onClicked: modal.closeRequested()
            onWheel: function (wheel) { wheel.accepted = true; }
        }
    }

    Rectangle {
        id: dialog
        anchors.centerIn: parent
        width: Math.min(560, parent.width - 64)
        // Content-driven height: never a tiny strip, never overflowing.
        height: Math.max(380, Math.min(parent.height - 48, bodyCol.implicitHeight + 44))
        opacity: 0.0
        scale: 0.97
        transformOrigin: Item.Center
        radius: 13
        color: "#0e1420"
        border.width: 1
        border.color: "#26314a"
        Behavior on opacity { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 1
            anchors.leftMargin: 13
            anchors.rightMargin: 13
            height: 2
            radius: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#7c3aed55" }
                GradientStop { position: 1.0; color: "#22d3ee55" }
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: function (mouse) { mouse.accepted = true; }
        }

        ColumnLayout {
            id: bodyCol
            // Anchored left/right/top ONLY: implicitHeight is computed from
            // children (header + body + footer) and drives dialog.height.
            // Anchoring bottom as well would force the layout into the
            // dialog's height and collapse the Loaders.
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 22
            anchors.rightMargin: 22
            anchors.topMargin: 20
            spacing: 0

            RowLayout {
                id: headerRow
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 4
                    Text {
                        text: modal.title
                        color: "#e8eaed"
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        visible: modal.subtitle !== ""
                        text: modal.subtitle
                        color: "#8b95a5"
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignTop
                    radius: 8
                    color: closeMa.containsMouse ? "#1d2a44" : "#141c2c"
                    border.width: 1
                    border.color: closeMa.containsMouse ? "#33415e" : "#26314a"
                    Behavior on color { ColorAnimation { duration: 120 } }
                    Image {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        source: Qt.resolvedUrl("../../assets/icons/x.svg")
                    }
                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: modal.closeRequested()
                    }
                }
            }

            Item { Layout.preferredHeight: 20 }

            Loader {
                id: bodyLoader
                Layout.fillWidth: true
                Layout.preferredHeight: item ? item.implicitHeight : 0
                sourceComponent: modal.body
                active: modal.body !== null
            }

            Item { Layout.preferredHeight: 16 }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#1e2942"
            }

            Loader {
                id: footerLoader
                Layout.fillWidth: true
                Layout.topMargin: 16
                Layout.bottomMargin: 6
                Layout.preferredHeight: item ? item.implicitHeight : 0
                sourceComponent: modal.footer
                active: modal.footer !== null
            }
        }

        Keys.onEscapePressed: modal.closeRequested()
    }

    Keys.onEscapePressed: modal.closeRequested()
}
