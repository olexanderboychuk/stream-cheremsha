import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// Universal service-history page for ANY Cheremsha provider
// (Donatik, Donatello, future donation/service providers).
//
// The generic component owns: header structure, period/date filters,
// date picker controls, Live toggle, TTS toggle slot, refresh button,
// history list layout, pagination metadata, loading/empty/error states.
//
// The service provides: labels, history data (rows), pagination values,
// row delegate (service-specific fields), footer actions (e.g. destructive
// service actions such as "forget token").
//
// Data contract: dates are always "YYYY-MM-DD" (backend format preserved).
// Polling behavior/timers live in the service backend; only labels are shown.
Item {
    id: root

    // ---- Generic state ----
    property string fromDate: ""
    property string toDate: ""
    property bool showDateFilter: true
    property bool showLive: true
    property bool showTts: true
    property bool livePoll: false
    property bool ttsNew: false
    property bool isLoading: false
    property string errorMessage: ""
    property var rows: []
    property int total: 0
    property int page: 1
    property int pageCount: 1
    property bool prevEnabled: page > 1
    property bool nextEnabled: page < pageCount

    // ---- Service-provided labels ----
    property string periodLabel: "Period"
    property string fromLabel: "From"
    property string toLabel: "To"
    property string refreshLabel: "Refresh"
    property string liveLabel: "Live"
    property string ttsLabel: "TTS for new"
    property string historyTitle: "History"
    property string summaryText: ""
    property string emptyTitle: "No results"
    property string emptyHint: "Nothing found for the selected period."
    property string loadingText: "Loading…"
    property string prevLabel: "Prev"
    property string nextLabel: "Next"

    // ---- Service-provided content ----
    property Component rowDelegate: null
    property Component footerActions: null

    // ---- Service callbacks ----
    signal refreshRequested()
    signal pageRequested(int page)
    signal liveToggled(bool on)
    signal ttsToggled(bool on)

    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    readonly property color divider: "#1e2636"
    readonly property color primaryPurple: "#8b5cf6"

    readonly property url calendarIcon: Qt.resolvedUrl("../../assets/icons/web_calendar.svg")
    readonly property url refreshIcon: Qt.resolvedUrl("../../assets/icons/web_refresh.svg")
    readonly property url volumeIcon: Qt.resolvedUrl("../../assets/icons/web_volume.svg")
    readonly property url historyIcon: Qt.resolvedUrl("../../assets/icons/donation.svg")
    readonly property url alertIcon: Qt.resolvedUrl("../../assets/icons/web_alert.svg")

    // Keep pickers in sync when the service sets dates imperatively.
    onFromDateChanged: {
        if (fromDate !== "" && fromPicker.text !== fromDate)
            fromPicker.setIsoDate(fromDate)
    }
    onToDateChanged: {
        if (toDate !== "" && toPicker.text !== toDate)
            toPicker.setIsoDate(toDate)
    }

    component HistoryPrimaryButton: Button {
        id: _primaryBtn
        property string btnIcon: ""
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: 13
        font.bold: true
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: _primaryBtn.btnIcon
                visible: _primaryBtn.btnIcon !== ""
                width: 14
                height: 14
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: _primaryBtn.text
                color: "white"
                font: _primaryBtn.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            implicitHeight: 34
            implicitWidth: 120
            radius: 8
            gradient: Gradient {
                GradientStop { position: 0.0; color: _primaryBtn.pressed ? "#7c3aed" : (_primaryBtn.hovered ? "#9d71f7" : "#8b5cf6") }
                GradientStop { position: 1.0; color: _primaryBtn.pressed ? "#6d28d9" : (_primaryBtn.hovered ? "#8b5cf6" : "#7c3aed") }
            }
            border.width: 1
            border.color: _primaryBtn.pressed ? "#6d28d9" : (_primaryBtn.hovered ? "#a78bfa" : "#8b54f5")
        }
    }

    component HistorySecondaryButton: Button {
        id: _secondaryBtn
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: 13
        contentItem: Text {
            text: _secondaryBtn.text
            color: "#b8c1cf"
            font: _secondaryBtn.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitHeight: 34
            implicitWidth: 110
            radius: 8
            color: _secondaryBtn.hovered ? "#141c2c" : "#0a0f19"
            border.width: 1
            border.color: _secondaryBtn.hovered ? "#3d4a63" : "#232d42"
        }
    }

    component HistoryErrorCard: Rectangle {
        id: _alertRoot
        property string alertText: ""
        Layout.fillWidth: true
        implicitHeight: _alertRow.implicitHeight + 20
        radius: 10
        color: "#1a1216"
        border.width: 1
        border.color: "#7f1d1d"
        RowLayout {
            id: _alertRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 10
            Image {
                source: root.alertIcon
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                text: _alertRoot.alertText
                color: "#fca5a5"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    // Generic fallback row: probes common service field aliases so any
    // provider renders something meaningful even without a custom delegate.
    component HistoryFallbackRow: Rectangle {
        radius: 10
        color: "#161b24"
        border.width: 1
        border.color: "#252d3d"
        height: _fbBox.implicitHeight + 22
        RowLayout {
            id: _fbBox
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: {
                        var r = modelData || {}
                        return r.name || r.clientName || r.donor || r.username || "—"
                    }
                    color: "#e8eaed"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    visible: text !== ""
                    text: {
                        var r = modelData || {}
                        return r.message || ""
                    }
                    color: "#d1d9e6"
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    Layout.fillWidth: true
                }
            }
            Text {
                Layout.alignment: Qt.AlignTop
                text: {
                    var r = modelData || {}
                    var pay = r.payment || {}
                    var amt = pay.amount || r.amount || "?"
                    var cur = pay.currency || r.currency || ""
                    return (amt + " " + cur).trim()
                }
                color: "#b8c4d4"
                font.pixelSize: 12
            }
        }
    }

    Component {
        id: _fallbackDelegate
        HistoryFallbackRow {}
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        HistoryErrorCard {
            visible: root.errorMessage.length > 0
            alertText: root.errorMessage
        }

        // ================= Filter toolbar =================
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _toolbarBody.implicitHeight + 32
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge

            ColumnLayout {
                id: _toolbarBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Image {
                        source: calendarIcon
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        text: root.periodLabel
                        color: ink
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                // Responsive: dates + refresh share one row on desktop,
                // stack naturally on narrow windows (no clipping/overlap).
                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width >= 560 ? 3 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    ColumnLayout {
                        visible: root.showDateFilter
                        Layout.fillWidth: true
                        Layout.minimumWidth: 110
                        spacing: 4
                        Text {
                            text: root.fromLabel
                            color: muted
                            font.pixelSize: 11
                        }
                        CheremshaDatePicker {
                            id: fromPicker
                            Layout.fillWidth: true
                            onDatePicked: function (iso) { root.fromDate = iso }
                        }
                    }
                    ColumnLayout {
                        visible: root.showDateFilter
                        Layout.fillWidth: true
                        Layout.minimumWidth: 110
                        spacing: 4
                        Text {
                            text: root.toLabel
                            color: muted
                            font.pixelSize: 11
                        }
                        CheremshaDatePicker {
                            id: toPicker
                            Layout.fillWidth: true
                            onDatePicked: function (iso) { root.toDate = iso }
                        }
                    }
                    ColumnLayout {
                        spacing: 4
                        Item {
                            Layout.preferredHeight: root.showDateFilter ? 18 : 0
                            visible: root.showDateFilter
                        }
                        HistoryPrimaryButton {
                            btnIcon: refreshIcon
                            text: root.isLoading ? "…" : root.refreshLabel
                            enabled: !root.isLoading
                            onClicked: root.refreshRequested()
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: divider
                    visible: root.showLive || root.showTts
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    visible: root.showLive || root.showTts
                    RowLayout {
                        visible: root.showLive
                        spacing: 8
                        Rectangle {
                            Layout.preferredWidth: 8
                            Layout.preferredHeight: 8
                            radius: 4
                            color: root.livePoll ? "#4ade80" : "#475569"
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: root.liveLabel
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                        }
                        ConnPrefSwitch {
                            Layout.alignment: Qt.AlignVCenter
                            checked: root.livePoll
                            onToggled: root.liveToggled(checked)
                        }
                    }
                    RowLayout {
                        visible: root.showTts
                        spacing: 8
                        Image {
                            source: volumeIcon
                            Layout.preferredWidth: 15
                            Layout.preferredHeight: 15
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: root.ttsLabel
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                        }
                        ConnPrefSwitch {
                            Layout.alignment: Qt.AlignVCenter
                            checked: root.ttsNew
                            onToggled: root.ttsToggled(checked)
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: divider
                    visible: root.footerActions !== null
                }

                Loader {
                    Layout.fillWidth: true
                    sourceComponent: root.footerActions
                    visible: root.footerActions !== null
                }
            }
        }

        // ================= History list =================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 240
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Image {
                        source: historyIcon
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        text: root.historyTitle
                        color: ink
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        elide: Text.ElideRight
                    }
                    Text {
                        text: root.summaryText
                        color: muted
                        font.pixelSize: 11
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        anchors.fill: parent
                        clip: true
                        spacing: 6
                        visible: root.rows.length > 0
                        model: root.rows
                        delegate: root.rowDelegate !== null ? root.rowDelegate : _fallbackDelegate

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                            width: 8
                        }
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(320, parent.width - 32)
                        spacing: 8
                        visible: root.rows.length === 0 && !root.isLoading
                        Image {
                            source: historyIcon
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 44
                            Layout.alignment: Qt.AlignHCenter
                            opacity: 0.85
                        }
                        Text {
                            text: root.emptyTitle
                            color: ink
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Text {
                            text: root.emptyHint
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: root.rows.length === 0 && root.isLoading
                        text: root.loadingText
                        color: muted
                        font.pixelSize: 13
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root.pageCount > 1
                    spacing: 8
                    HistorySecondaryButton {
                        text: root.prevLabel
                        enabled: !root.isLoading && root.prevEnabled
                        onClicked: root.pageRequested(root.page - 1)
                    }
                    Item { Layout.fillWidth: true }
                    HistorySecondaryButton {
                        text: root.nextLabel
                        enabled: !root.isLoading && root.nextEnabled
                        onClicked: root.pageRequested(root.page + 1)
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        if (fromDate !== "")
            fromPicker.setIsoDate(fromDate)
        if (toDate !== "")
            toPicker.setIsoDate(toDate)
    }
}
