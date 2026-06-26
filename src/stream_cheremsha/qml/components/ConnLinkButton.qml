import QtQuick
import QtQuick.Controls

import components

Button {
    id: linkCtl
    flat: true
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    padding: 0
    contentItem: Text {
        text: linkCtl.text
        color: linkCtl.pressed ? "#cdd5e1" : (linkCtl.hovered ? "#f2f4f7" : ConnTheme.muted)
        font.underline: true
        font.pixelSize: 12
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        Behavior on color { ColorAnimation { duration: 100; easing.type: Easing.OutCubic } }
    }
    background: Item {}
}
