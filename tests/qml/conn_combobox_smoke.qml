import QtQuick
import QtQuick.Controls

// Minimal repro of ConnComboBox selection contract (default delegate + picked via index change).
Item {
    id: root
    width: 320
    height: 64

    property string probeDisplayText: ""
    property int probeCurrentIndex: -1
    property var probeModelCount: 0

    ComboBox {
        id: probeCombo
        objectName: "probeCombo"
        anchors.centerIn: parent
        width: 280
        model: [
            { text: "Kick", value: "kick" },
            { text: "Twitch", value: "twitch" }
        ]
        textRole: "text"
        valueRole: "value"
        currentIndex: 0

        signal picked(int index)
        onActivated: function (index) {
            if (currentIndex >= 0)
                picked(currentIndex);
        }
    }

    Component.onCompleted: {
        root.probeDisplayText = probeCombo.displayText;
        root.probeCurrentIndex = probeCombo.currentIndex;
        root.probeModelCount = probeCombo.count;
    }
}
