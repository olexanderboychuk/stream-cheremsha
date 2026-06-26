import QtQuick
import QtQuick.Controls

import components

Button {
    id: pillCtl
    property int pillFontSize: 13
    property color colRest: "#1c2434"
    property color colHover: "#2a3750"
    property color colPress: "#34425c"
    property color borRest: ConnTheme.cardEdge
    property color borHover: "#56627a"
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    font.pixelSize: pillFontSize
    transformOrigin: Item.Center
    scale: pillCtl.hovered ? 1.02 : 1.0
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    contentItem: Text {
        text: pillCtl.text
        color: pillCtl.hovered ? "#f2f4f7" : ConnTheme.ink
        font.pixelSize: pillCtl.pillFontSize
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
    background: Rectangle {
        radius: 8
        color: pillCtl.pressed ? pillCtl.colPress : (pillCtl.hovered ? pillCtl.colHover : pillCtl.colRest)
        border.width: 1
        border.color: pillCtl.hovered ? pillCtl.borHover : pillCtl.borRest
        Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
}
