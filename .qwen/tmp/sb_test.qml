import QtQuick
import QtQuick.Controls
Item {
    width: 200; height: 200
    Flickable {
        anchors.fill: parent
        contentHeight: 500
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
    }
}
