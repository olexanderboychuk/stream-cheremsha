import QtQuick
import QtQuick.Dialogs
Item {
    FileDialog { id: fd; title: "t"; folder: Qt.urlFromLocalPath("/tmp"); nameFilters: ["Audio (*.mp3)"] }
}
