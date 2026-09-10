import QtQuick
import QtQuick.Layouts

Item {
    id: root

    property int columns: 1
    property real columnSpacing: 14
    property real rowSpacing: 14

    // Child items are placed by the same concrete-width GridLayout used by
    // the Widgets gallery. Keeping this as the default property lets callers
    // place a Repeater followed by a Create card in one sequential flow.
    default property alias content: cardGrid.data

    implicitWidth: cardGrid.implicitWidth
    implicitHeight: cardGrid.implicitHeight
    height: cardGrid.implicitHeight

    GridLayout {
        id: cardGrid
        width: root.width
        columns: Math.max(1, root.columns)
        columnSpacing: root.columnSpacing
        rowSpacing: root.rowSpacing
    }
}
