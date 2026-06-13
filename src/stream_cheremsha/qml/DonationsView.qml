import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Donation platforms (Donatik, Donatello, …) — compact list, dates, pagination
Item {
    id: root
    anchors.fill: parent

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    readonly property color accent: "#f59e0b"
    readonly property color accentHi: "#fcd34d"
    readonly property color dellBar: "#059669"
    readonly property color dellHi: "#6ee7b7"
    // List rows: larger / higher-contrast than global `muted` (#8b95a5)
    readonly property color listBody: "#d1d9e6"
    readonly property color listSecondary: "#b8c4d4"
    readonly property color listHint: "#9eb0c8"

    property string screen: "pick" // "pick" | "donatik" | "donatello"
    readonly property int stackIdx: {
        if (root.screen === "pick")
            return 0
        if (root.screen === "donatik")
            return 1
        return 2
    }

    function _pad2(n) { return (n < 10 ? "0" : "") + n }
    function _iso(d) {
        return d.getFullYear() + "-" + _pad2(d.getMonth() + 1) + "-" + _pad2(d.getDate())
    }
    function defaultTo() { return _iso(new Date()) }
    function defaultFrom() {
        var d = new Date()
        d.setDate(d.getDate() - 30)
        return _iso(d)
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    component PillButton: Button {
        id: pb
        property int psz: 12
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: psz
        font.weight: Font.DemiBold
        contentItem: Text {
            text: pb.text
            color: pb.hovered ? "#fffbeb" : ink
            font: pb.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitHeight: 32
            implicitWidth: 88
            radius: 8
            color: pb.pressed ? "#b45309" : (pb.hovered ? "#d97706" : "#b45309")
            border.width: 1
            border.color: pb.hovered ? accentHi : "#92400e"
        }
    }

    component GhostButton: Button {
        id: gb
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: 12
        contentItem: Text {
            text: gb.text
            color: gb.hovered ? "#f1f5f9" : muted
            font: gb.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitHeight: 30
            radius: 8
            color: gb.pressed ? "#252b38" : (gb.hovered ? "#1e2533" : "#161b26")
            border.width: 1
            border.color: cardEdge
        }
    }

    // Same preference toggle as ConnectionsView.qml `ConnPrefSwitch`.
    component ConnPrefSwitch: Switch {
        id: prefSw
        padding: 0
        implicitWidth: 46
        implicitHeight: 24
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        transformOrigin: Item.Right
        scale: prefSw.hovered ? 1.06 : 1.0
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

        indicator: Rectangle {
            width: prefSw.implicitWidth
            height: prefSw.implicitHeight
            radius: 12
            color: prefSw.checked ? "#134e4a" : "#252d3d"
            border.width: 1
            border.color: prefSw.checked ? "#14b8a6" : "#3b4a63"
            opacity: prefSw.enabled ? 1.0 : 0.55
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

            Rectangle {
                width: 18
                height: 18
                radius: 9
                y: 3
                x: prefSw.checked ? (parent.width - width - 3) : 3
                color: prefSw.checked ? "#e8eaed" : "#52607a"
                border.width: 1
                border.color: prefSw.checked ? "#cbd5e1" : "#3d4a60"
                Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
                Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            }
        }

        contentItem: Item {}
    }

    // `donApi` is injected as a context property from Python. When it is not set yet (or
    // the QML is loaded without it), bindings like `donApi.loc(...)` throw and spam logs.
    // Guard by only instantiating the main UI when `donApi` exists.
    Loader {
        id: apiGate
        anchors.fill: parent
        active: typeof donApi !== "undefined" && donApi !== null
        sourceComponent: gatedUi
    }

    Text {
        anchors.centerIn: parent
        visible: !apiGate.active
        text: "Donations API is not available yet."
        color: muted
        font.pixelSize: 13
    }

    Component {
        id: gatedUi
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            PillButton {
                visible: root.screen !== "pick"
                psz: 11
                text: { donApi.uiTick; return "← " + donApi.loc("donations.back_services") }
                onClicked: root.screen = "pick"
            }
            Text {
                Layout.fillWidth: true
                text: {
                    donApi.uiTick
                    if (root.screen === "pick")
                        return donApi.loc("donations.title_pick")
                    if (root.screen === "donatik")
                        return donApi.loc("donations.title_donatik")
                    return donApi.loc("donations.title_donatello")
                }
                color: ink
                font.pixelSize: 17
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.stackIdx

            // ---- Service cards ----
            ScrollView {
                id: pickScroller
                clip: true
                contentWidth: availableWidth
                background: Item {}

                ScrollBar.vertical: ScrollBar {
                    width: 10
                    policy: ScrollBar.AsNeeded
                    background: Rectangle {
                        implicitWidth: 10
                        radius: 5
                        color: "#0f1219"
                        border.width: 1
                        border.color: "#1e2430"
                    }
                    contentItem: Rectangle {
                        implicitWidth: 6
                        radius: 4
                        color: parent.pressed ? "#0d9488" : (parent.hovered ? "#52607a" : "#3d4a60")
                    }
                }

                Item {
                    id: donPick
                    implicitWidth: pickScroller.availableWidth
                    implicitHeight: cardsCol.height + 24

                    Column {
                        id: cardsCol
                        width: Math.min(560, pickScroller.availableWidth - 8)
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 14

                        Text {
                            width: parent.width
                            text: { donApi.uiTick; return donApi.loc("donations.subtitle_pick") }
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        // Donatik card
                        Rectangle {
                            width: parent.width
                            height: donBody.implicitHeight + 36
                            radius: 16
                            color: cardBase
                            border.width: 1
                            border.color: cardEdge
                            Rectangle {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: 1
                                }
                                height: 1
                                color: "#78350f"
                                opacity: 0.45
                            }

                            ColumnLayout {
                                id: donBody
                                x: 18
                                y: 18
                                width: parent.width - 36
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Rectangle {
                                        width: 3
                                        height: 22
                                        radius: 1
                                        color: accent
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Text {
                                        text: "Donatik"
                                        color: accentHi
                                        font.pixelSize: 20
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: { donApi.uiTick; return donApi.donatikConfigured ? "●" : "○" }
                                        color: donApi.donatikConfigured ? "#34d399" : muted
                                        font.pixelSize: 11
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: { donApi.uiTick; return donApi.loc("donations.card_donatik_hint") }
                                    color: muted
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: { donApi.uiTick; return donApi.loc("donations.tap_to_open") }
                                    color: muted
                                    font.pixelSize: 11
                                    font.italic: true
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    spacing: 10
                                    Text {
                                        text: { donApi.uiTick; return donApi.loc("donations.card_live_abbr") }
                                        color: listHint
                                        font.pixelSize: 11
                                        font.weight: Font.Medium
                                    }
                                    ConnPrefSwitch {
                                        id: swCardDonatikLive
                                        checked: donApi.donatikLivePoll
                                        onToggled: {
                                            donApi.setDonatikLivePoll(swCardDonatikLive.checked)
                                            donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                        }
                                    }
                                    Text {
                                        text: { donApi.uiTick; return donApi.loc("donations.card_tts_abbr") }
                                        color: listHint
                                        font.pixelSize: 11
                                        font.weight: Font.Medium
                                    }
                                    ConnPrefSwitch {
                                        id: swCardDonatikTts
                                        checked: donApi.donatikTtsNew
                                        onToggled: donApi.setDonatikTtsNew(swCardDonatikTts.checked)
                                    }
                                    Item { Layout.fillWidth: true }
                                }
                            }

                            MouseArea {
                                z: 2
                                anchors.fill: parent
                                anchors.bottomMargin: 44
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.screen = "donatik"
                                    if (donApi.donatikConfigured && donFrom.text.length && donTo.text.length)
                                        Qt.callLater(function () {
                                            donApi.donatikFetch(donFrom.text, donTo.text, String(donApi.page))
                                        })
                                }
                            }
                        }

                        // Donatello card
                        Rectangle {
                            width: parent.width
                            height: dellBody.implicitHeight + 36
                            radius: 16
                            color: cardBase
                            border.width: 1
                            border.color: cardEdge
                            Rectangle {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: 1
                                }
                                height: 1
                                color: "#064e3b"
                                opacity: 0.5
                            }

                            ColumnLayout {
                                id: dellBody
                                x: 18
                                y: 18
                                width: parent.width - 36
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Rectangle {
                                        width: 3
                                        height: 22
                                        radius: 1
                                        color: dellBar
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Text {
                                        text: "Donatello"
                                        color: dellHi
                                        font.pixelSize: 20
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: { donApi.uiTick; return donApi.donatelloConfigured ? "●" : "○" }
                                        color: donApi.donatelloConfigured ? "#34d399" : muted
                                        font.pixelSize: 11
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: { donApi.uiTick; return donApi.loc("donations.card_donatello_hint") }
                                    color: muted
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: { donApi.uiTick; return donApi.loc("donations.tap_to_open") }
                                    color: muted
                                    font.pixelSize: 11
                                    font.italic: true
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    spacing: 10
                                    Text {
                                        text: { donApi.uiTick; return donApi.loc("donations.card_live_abbr") }
                                        color: listHint
                                        font.pixelSize: 11
                                        font.weight: Font.Medium
                                    }
                                    ConnPrefSwitch {
                                        id: swCardDonatelloLive
                                        checked: donApi.donatelloLivePoll
                                        onToggled: donApi.setDonatelloLivePoll(swCardDonatelloLive.checked)
                                    }
                                    Text {
                                        text: { donApi.uiTick; return donApi.loc("donations.card_tts_abbr") }
                                        color: listHint
                                        font.pixelSize: 11
                                        font.weight: Font.Medium
                                    }
                                    ConnPrefSwitch {
                                        id: swCardDonatelloTts
                                        checked: donApi.donatelloTtsNew
                                        onToggled: donApi.setDonatelloTtsNew(swCardDonatelloTts.checked)
                                    }
                                    Item { Layout.fillWidth: true }
                                }
                            }

                            MouseArea {
                                z: 2
                                anchors.fill: parent
                                anchors.bottomMargin: 44
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.screen = "donatello"
                                    if (donApi.donatelloConfigured)
                                        Qt.callLater(function () { donApi.donatelloFetch("0") })
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            text: { donApi.uiTick; return donApi.loc("donations.more_soon") }
                            color: muted
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }

            // ---- Donatik detail ----
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Text {
                        visible: !donApi.donatikConfigured
                        Layout.fillWidth: true
                        text: { donApi.uiTick; return donApi.loc("donations.setup_intro_html") }
                        textFormat: Text.RichText
                        color: muted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        onLinkActivated: function (link) { donApi.openUrl(link) }
                    }

                    ColumnLayout {
                        visible: !donApi.donatikConfigured
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: { donApi.uiTick; return donApi.loc("donations.api_token") }
                            color: muted
                            font.pixelSize: 11
                            font.weight: Font.Medium
                        }
                        TextField {
                            id: tokDonatik
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderTextColor: muted
                            placeholderText: { donApi.uiTick; return donApi.loc("donations.token_ph") }
                            color: ink
                            leftPadding: 12
                            rightPadding: 12
                            topPadding: 10
                            bottomPadding: 10
                            font.pixelSize: 13
                            background: Rectangle {
                                radius: 8
                                color: fieldBg
                                border.width: 1
                                border.color: cardEdge
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            PillButton {
                                text: { donApi.uiTick; return donApi.loc("donations.save_token") }
                                onClicked: {
                                    if (donApi.donatikSaveToken(tokDonatik.text)) {
                                        tokDonatik.clear()
                                        donFrom.text = defaultFrom()
                                        donTo.text = defaultTo()
                                        donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                        donApi.donatikFetch(donFrom.text, donTo.text, "1")
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }

                    ColumnLayout {
                        visible: donApi.donatikConfigured
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            ColumnLayout {
                                Layout.preferredWidth: 140
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.from") }
                                    color: muted
                                    font.pixelSize: 10
                                }
                                TextField {
                                    id: donFrom
                                    color: ink
                                    leftPadding: 10
                                    rightPadding: 10
                                    topPadding: 8
                                    bottomPadding: 8
                                    font.pixelSize: 12
                                    placeholderTextColor: muted
                                    placeholderText: "YYYY-MM-DD"
                                    background: Rectangle {
                                        radius: 8
                                        color: fieldBg
                                        border.width: 1
                                        border.color: cardEdge
                                    }
                                    Component.onCompleted: text = defaultFrom()
                                    onEditingFinished: donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                }
                            }
                            ColumnLayout {
                                Layout.preferredWidth: 140
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.to") }
                                    color: muted
                                    font.pixelSize: 10
                                }
                                TextField {
                                    id: donTo
                                    color: ink
                                    leftPadding: 10
                                    rightPadding: 10
                                    topPadding: 8
                                    bottomPadding: 8
                                    font.pixelSize: 12
                                    placeholderTextColor: muted
                                    placeholderText: "YYYY-MM-DD"
                                    background: Rectangle {
                                        radius: 8
                                        color: fieldBg
                                        border.width: 1
                                        border.color: cardEdge
                                    }
                                    Component.onCompleted: text = defaultTo()
                                    onEditingFinished: donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                }
                            }
                            ColumnLayout {
                                spacing: 4
                                Item { Layout.preferredHeight: 14 }
                                PillButton {
                                    text: {
                                        if (donApi.donatikLoading)
                                            return "…"
                                        donApi.uiTick
                                        return donApi.loc("donations.refresh")
                                    }
                                    enabled: !donApi.donatikLoading
                                    onClicked: {
                                        donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                        donApi.donatikFetch(donFrom.text, donTo.text, "1")
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            spacing: 18
                            RowLayout {
                                spacing: 8
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.live_poll") }
                                    color: muted
                                    font.pixelSize: 12
                                }
                                ConnPrefSwitch {
                                    id: swDonatikLive
                                    checked: donApi.donatikLivePoll
                                    onToggled: {
                                        donApi.setDonatikLivePoll(swDonatikLive.checked)
                                        donApi.donatikSyncPollDates(donFrom.text, donTo.text)
                                    }
                                }
                            }
                            RowLayout {
                                spacing: 8
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.tts_new") }
                                    color: muted
                                    font.pixelSize: 12
                                }
                                ConnPrefSwitch {
                                    id: swDonatikTts
                                    checked: donApi.donatikTtsNew
                                    onToggled: donApi.setDonatikTtsNew(swDonatikTts.checked)
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            GhostButton {
                                text: { donApi.uiTick; return donApi.loc("donations.forget_token") }
                                onClicked: donApi.donatikForgetToken()
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: { donApi.uiTick; return donApi.summaryLine }
                                color: muted
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: donApi.errorMessage.length > 0
                            text: donApi.errorMessage
                            color: "#fca5a5"
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: cardBase
                            border.width: 1
                            border.color: cardEdge

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                clip: true
                                spacing: 6
                                model: JSON.parse(donApi.donationsJson || "[]")

                                ScrollBar.vertical: ScrollBar {
                                    policy: ScrollBar.AsNeeded
                                    width: 8
                                }

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: row.implicitHeight + 22
                                    radius: 10
                                    color: "#161b24"
                                    border.width: 1
                                    border.color: "#252d3d"

                                    RowLayout {
                                        id: row
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 12

                                        Rectangle {
                                            Layout.alignment: Qt.AlignTop
                                            Layout.topMargin: 2
                                            implicitWidth: amt.implicitWidth + 18
                                            implicitHeight: 32
                                            radius: 8
                                            color: "#14532d"
                                            border.width: 1
                                            border.color: "#22c55e"
                                            Text {
                                                id: amt
                                                anchors.centerIn: parent
                                                text: {
                                                    var pay = modelData.payment || {}
                                                    return (pay.amount || "?") + " " + (pay.currency || "")
                                                }
                                                color: "#bbf7d0"
                                                font.pixelSize: 14
                                                font.weight: Font.Black
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Text {
                                                text: modelData.name || "—"
                                                color: ink
                                                font.pixelSize: 15
                                                font.weight: Font.DemiBold
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: modelData.message || ""
                                                color: root.listBody
                                                font.pixelSize: 13
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 3
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                visible: (modelData.payment && modelData.payment.paymentProvider)
                                                text: {
                                                    var pr = (modelData.payment && modelData.payment.paymentProvider) || {}
                                                    return pr.name || ""
                                                }
                                                color: root.listHint
                                                font.pixelSize: 12
                                            }
                                        }

                                        Column {
                                            Layout.alignment: Qt.AlignTop
                                            spacing: 5
                                            Text {
                                                text: {
                                                    var raw = modelData.createdAt || ""
                                                    return raw.length > 22 ? raw.substring(0, 22) : raw
                                                }
                                                color: root.listSecondary
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                            Text {
                                                text: modelData.verifyStatus || ""
                                                color: "#e2e8f0"
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                            Text {
                                                text: {
                                                    var st = (modelData.payment && modelData.payment.status) || ""
                                                    return st
                                                }
                                                color: "#c4b5fd"
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: donApi.donatikConfigured && donApi.pageCount > 1
                            spacing: 8
                            GhostButton {
                                text: "← " + donApi.loc("donations.prev")
                                enabled: !donApi.donatikLoading && donApi.page > 1
                                onClicked: donApi.donatikFetch(donFrom.text, donTo.text, String(donApi.page - 1))
                            }
                            Item { Layout.fillWidth: true }
                            GhostButton {
                                text: donApi.loc("donations.next") + " →"
                                enabled: !donApi.donatikLoading && donApi.page < donApi.pageCount
                                onClicked: donApi.donatikFetch(donFrom.text, donTo.text, String(donApi.page + 1))
                            }
                        }
                    }
                }
            }

            // ---- Donatello detail ----
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Text {
                        visible: !donApi.donatelloConfigured
                        Layout.fillWidth: true
                        text: { donApi.uiTick; return donApi.loc("donations.setup_intro_donatello_html") }
                        textFormat: Text.RichText
                        color: muted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        onLinkActivated: function (link) { donApi.openUrl(link) }
                    }

                    ColumnLayout {
                        visible: !donApi.donatelloConfigured
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: { donApi.uiTick; return donApi.loc("donations.api_token") }
                            color: muted
                            font.pixelSize: 11
                            font.weight: Font.Medium
                        }
                        TextField {
                            id: tokDonatello
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderTextColor: muted
                            placeholderText: { donApi.uiTick; return donApi.loc("donations.token_ph") }
                            color: ink
                            leftPadding: 12
                            rightPadding: 12
                            topPadding: 10
                            bottomPadding: 10
                            font.pixelSize: 13
                            background: Rectangle {
                                radius: 8
                                color: fieldBg
                                border.width: 1
                                border.color: cardEdge
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            PillButton {
                                text: { donApi.uiTick; return donApi.loc("donations.save_token") }
                                onClicked: {
                                    if (donApi.donatelloSaveToken(tokDonatello.text)) {
                                        tokDonatello.clear()
                                        donApi.donatelloFetch("0")
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }

                    ColumnLayout {
                        visible: donApi.donatelloConfigured
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Item { Layout.fillWidth: true }
                            PillButton {
                                text: {
                                    if (donApi.donatelloLoading)
                                        return "…"
                                    donApi.uiTick
                                    return donApi.loc("donations.refresh")
                                }
                                enabled: !donApi.donatelloLoading
                                onClicked: donApi.donatelloFetch(String(donApi.donatelloPage))
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            spacing: 18
                            RowLayout {
                                spacing: 8
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.live_poll") }
                                    color: muted
                                    font.pixelSize: 12
                                }
                                ConnPrefSwitch {
                                    id: swDonatelloLive
                                    checked: donApi.donatelloLivePoll
                                    onToggled: donApi.setDonatelloLivePoll(swDonatelloLive.checked)
                                }
                            }
                            RowLayout {
                                spacing: 8
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.tts_new") }
                                    color: muted
                                    font.pixelSize: 12
                                }
                                ConnPrefSwitch {
                                    id: swDonatelloTts
                                    checked: donApi.donatelloTtsNew
                                    onToggled: donApi.setDonatelloTtsNew(swDonatelloTts.checked)
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            GhostButton {
                                text: { donApi.uiTick; return donApi.loc("donations.forget_token") }
                                onClicked: donApi.donatelloForgetToken()
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: { donApi.uiTick; return donApi.donatelloSummaryLine }
                                color: muted
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: donApi.errorMessage.length > 0
                            text: donApi.errorMessage
                            color: "#fca5a5"
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: cardBase
                            border.width: 1
                            border.color: cardEdge

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                clip: true
                                spacing: 6
                                model: JSON.parse(donApi.donatelloJson || "[]")

                                ScrollBar.vertical: ScrollBar {
                                    policy: ScrollBar.AsNeeded
                                    width: 8
                                }

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: drow.implicitHeight + 22
                                    radius: 10
                                    color: "#161b24"
                                    border.width: 1
                                    border.color: "#252d3d"

                                    RowLayout {
                                        id: drow
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 12

                                        Rectangle {
                                            Layout.alignment: Qt.AlignTop
                                            Layout.topMargin: 2
                                            implicitWidth: damt.implicitWidth + 18
                                            implicitHeight: 32
                                            radius: 8
                                            color: "#14532d"
                                            border.width: 1
                                            border.color: "#22c55e"
                                            Text {
                                                id: damt
                                                anchors.centerIn: parent
                                                text: (modelData.amount || "?") + " " + (modelData.currency || "")
                                                color: "#bbf7d0"
                                                font.pixelSize: 14
                                                font.weight: Font.Black
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Text {
                                                text: modelData.clientName || "—"
                                                color: ink
                                                font.pixelSize: 15
                                                font.weight: Font.DemiBold
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: modelData.message || ""
                                                color: root.listBody
                                                font.pixelSize: 13
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 3
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                visible: (modelData.goal || "").length > 0
                                                text: modelData.goal || ""
                                                color: root.listHint
                                                font.pixelSize: 12
                                                Layout.fillWidth: true
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 2
                                            }
                                        }

                                        Column {
                                            Layout.alignment: Qt.AlignTop
                                            spacing: 5
                                            Text {
                                                text: modelData.createdAt || ""
                                                color: root.listSecondary
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                            Text {
                                                text: {
                                                    donApi.uiTick
                                                    if (modelData.isPublished)
                                                        return donApi.loc("donations.donatello_published")
                                                    return donApi.loc("donations.donatello_draft")
                                                }
                                                color: modelData.isPublished ? "#4ade80" : root.listSecondary
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                            Text {
                                                text: modelData.pubId || ""
                                                color: "#c4b5fd"
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignRight
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: donApi.donatelloConfigured && (!donApi.donatelloFirst || !donApi.donatelloLast)
                            spacing: 8
                            GhostButton {
                                text: "← " + donApi.loc("donations.prev")
                                enabled: !donApi.donatelloLoading && !donApi.donatelloFirst
                                onClicked: donApi.donatelloFetch(String(Math.max(0, donApi.donatelloPage - 1)))
                            }
                            Item { Layout.fillWidth: true }
                            GhostButton {
                                text: donApi.loc("donations.next") + " →"
                                enabled: !donApi.donatelloLoading && !donApi.donatelloLast
                                onClicked: donApi.donatelloFetch(String(donApi.donatelloPage + 1))
                            }
                        }
                    }
                }
            }
        }
        }
    }

    Connections {
        target: donApi
        function onDonatikConfiguredChanged() {
            if (root.screen === "donatik" && donApi.donatikConfigured
                    && donFrom.text.length && donTo.text.length) {
                donApi.donatikFetch(donFrom.text, donTo.text, "1")
            }
        }
        function onDonatelloConfiguredChanged() {
            if (root.screen === "donatello" && donApi.donatelloConfigured)
                donApi.donatelloFetch("0")
        }
    }
}
