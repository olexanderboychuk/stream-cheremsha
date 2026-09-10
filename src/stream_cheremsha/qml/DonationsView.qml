import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

// Donation platforms (Donatik, Donatello, …) — Cheremsha design system:
// service grid, token settings cards, filter toolbar, donation history.
Item {
    id: root
    anchors.fill: parent

    // Micro entrance transition, retriggered by MainWindow (enterPulse toggle)
    // on every cached navigation. GPU-cheap root opacity only, 120ms.
    property bool enterPulse: false
    onEnterPulseChanged: enterFade.restart()
    NumberAnimation {
        id: enterFade
        target: root
        property: "opacity"
        from: 0.97
        to: 1.0
        duration: 120
        easing.type: Easing.OutCubic
    }

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    readonly property color primaryPurple: "#8b5cf6"
    readonly property color divider: "#1e2636"
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
    function openDonatik(fromDate, toDate) {
        root.screen = "donatik"
        if (donApi.donatikConfigured && fromDate.length && toDate.length)
            Qt.callLater(function () {
                donApi.donatikFetch(fromDate, toDate, String(donApi.page))
            })
    }
    function openDonatello() {
        root.screen = "donatello"
        if (donApi.donatelloConfigured)
            Qt.callLater(function () { donApi.donatelloFetch("0") })
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    // ---- Cheremsha button system (same language as DocksView) ----
    component PrimaryButton: Button {
        id: primaryBtn
        property int fontSize: 13
        property string btnIcon: ""
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: fontSize
        font.bold: true
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: primaryBtn.btnIcon
                visible: primaryBtn.btnIcon !== ""
                width: 14
                height: 14
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: primaryBtn.text
                color: "white"
                font: primaryBtn.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            implicitHeight: 34
            radius: 8
            gradient: Gradient {
                GradientStop { position: 0.0; color: primaryBtn.pressed ? "#7c3aed" : (primaryBtn.hovered ? "#9d71f7" : root.primaryPurple) }
                GradientStop { position: 1.0; color: primaryBtn.pressed ? "#6d28d9" : (primaryBtn.hovered ? "#8b5cf6" : "#7c3aed") }
            }
            border.width: 1
            border.color: primaryBtn.pressed ? "#6d28d9" : (primaryBtn.hovered ? "#a78bfa" : "#8b54f5")
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    component SecondaryButton: Button {
        id: secondaryBtn
        property int fontSize: 13
        property string btnIcon: ""
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: fontSize
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: secondaryBtn.btnIcon
                visible: secondaryBtn.btnIcon !== ""
                width: 14
                height: 14
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: secondaryBtn.text
                color: "#b8c1cf"
                font: secondaryBtn.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            implicitHeight: 34
            radius: 8
            color: secondaryBtn.hovered ? "#141c2c" : "#0a0f19"
            border.width: 1
            border.color: secondaryBtn.hovered ? "#3d4a63" : "#232d42"
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    component DangerButton: Button {
        id: dangerBtn
        property int fontSize: 12
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: fontSize
        contentItem: Text {
            text: dangerBtn.text
            color: dangerBtn.hovered ? "#fecaca" : "#fca5a5"
            font: dangerBtn.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitHeight: 32
            radius: 8
            color: dangerBtn.pressed ? "#2a1216" : (dangerBtn.hovered ? "#241419" : "#1a1216")
            border.width: 1
            border.color: dangerBtn.hovered ? "#b91c1c" : "#7f1d1d"
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    // ---- Global Donation Filter Properties ----
    property string donFrom: defaultFrom()
    property string donTo: defaultTo()

    // ---- Compact error alert (icon + message, red tint) ----
    component ErrorAlert: Rectangle {
        id: alertRoot
        property string alertText: ""
        Layout.fillWidth: true
        implicitHeight: alertRow.implicitHeight + 20
        radius: 10
        color: "#1a1216"
        border.width: 1
        border.color: "#7f1d1d"
        RowLayout {
            id: alertRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 10
            Image {
                source: Qt.resolvedUrl("../assets/icons/web_alert.svg")
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                text: alertRoot.alertText
                color: "#fca5a5"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    // ---- Data-driven donation row (amount + donor/message/source + meta) ----
    component DonationRow: Rectangle {
        id: rowRoot
        property string amountText: ""
        property string donorName: "—"
        property string messageText: ""
        property string sourceText: ""
        property string timeText: ""
        property string statusMain: ""
        property color statusMainColor: "#e2e8f0"
        property string statusSub: ""
        property color statusSubColor: "#c4b5fd"

        radius: 10
        color: "#161b24"
        border.width: 1
        border.color: "#252d3d"
        height: rowBox.implicitHeight + 22

        RowLayout {
            id: rowBox
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
                    text: rowRoot.amountText
                    color: "#bbf7d0"
                    font.pixelSize: 14
                    font.weight: Font.Black
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: rowRoot.donorName
                    color: ink
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    visible: rowRoot.messageText !== ""
                    text: rowRoot.messageText
                    color: root.listBody
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    Layout.fillWidth: true
                }
                Text {
                    visible: rowRoot.sourceText !== ""
                    text: rowRoot.sourceText
                    color: root.listHint
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                spacing: 5
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: rowRoot.timeText
                    color: root.listSecondary
                    font.pixelSize: 11
                    elide: Text.ElideLeft
                }
                Text {
                    visible: rowRoot.statusMain !== ""
                    Layout.alignment: Qt.AlignRight
                    text: rowRoot.statusMain
                    color: rowRoot.statusMainColor
                    font.pixelSize: 11
                }
                Text {
                    visible: rowRoot.statusSub !== ""
                    Layout.alignment: Qt.AlignRight
                    text: rowRoot.statusSub
                    color: rowRoot.statusSubColor
                    font.pixelSize: 11
                    elide: Text.ElideLeft
                }
            }
        }
    }

    // ---- Token connection card (label + secure input + save) ----
    component TokenCard: Rectangle {
        id: tokenRoot
        property string cardTitle: ""
        property string fieldLabel: ""
        property string fieldPlaceholder: ""
        property string saveText: ""
        property alias tokenText: tokenField.text
        signal saveClicked()
        function clearToken() { tokenField.clear() }

        Layout.fillWidth: true
        implicitHeight: tokenBody.implicitHeight + 32
        radius: 14
        color: cardBase
        border.width: 1
        border.color: cardEdge

        ColumnLayout {
            id: tokenBody
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Image {
                    source: Qt.resolvedUrl("../assets/icons/web_key.svg")
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: tokenRoot.cardTitle
                    color: ink
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            Text {
                text: tokenRoot.fieldLabel
                color: muted
                font.pixelSize: 11
                font.weight: Font.Medium
            }
            TextField {
                id: tokenField
                Layout.fillWidth: true
                Layout.maximumWidth: 520
                echoMode: TextInput.Password
                selectByMouse: true
                placeholderTextColor: muted
                placeholderText: tokenRoot.fieldPlaceholder
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
                    border.color: tokenField.activeFocus ? "#8b5cf6" : cardEdge
                    Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                PrimaryButton {
                    text: tokenRoot.saveText
                    onClicked: tokenRoot.saveClicked()
                }
                Item { Layout.fillWidth: true }
            }
        }
    }

    // ---- Small informational card (icon + title + rich body) ----
    component InfoCard: Rectangle {
        property string infoIcon: ""
        property string infoTitle: ""
        property string infoHtml: ""

        Layout.fillWidth: true
        implicitHeight: infoBody.implicitHeight + 28
        radius: 14
        color: cardBase
        border.width: 1
        border.color: cardEdge

        RowLayout {
            id: infoBody
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 14
            spacing: 12

            Item {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignTop

                Rectangle {
                    anchors.fill: parent
                    radius: 9
                    color: "#38bdf8"
                    opacity: 0.12
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 9
                    color: "transparent"
                    border.width: 1
                    border.color: "#38bdf8"
                    opacity: 0.45
                }
                Image {
                    anchors.centerIn: parent
                    source: infoIcon
                    width: 20
                    height: 20
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: infoTitle
                    color: ink
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }
                Text {
                    text: infoHtml
                    textFormat: Text.RichText
                    linkColor: "#93c5fd"
                    color: muted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    onLinkActivated: function (link) { donApi.openUrl(link) }
                }
            }
        }
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
            anchors.margins: 20
            spacing: 12

            // ---- Page header (same language as Docks) ----
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                SecondaryButton {
                    visible: root.screen !== "pick"
                    Layout.alignment: Qt.AlignTop
                    Layout.topMargin: 2
                    btnIcon: Qt.resolvedUrl("../assets/icons/web_back.svg")
                    text: { donApi.uiTick; return donApi.loc("donations.back_services") }
                    onClicked: root.screen = "pick"
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
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
                        font.pixelSize: 26
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: {
                            donApi.uiTick
                            if (root.screen === "pick")
                                return donApi.loc("donations.subtitle_pick")
                            if (root.screen === "donatik")
                                return donApi.loc("donations.card_donatik_hint")
                            return donApi.loc("donations.card_donatello_hint")
                        }
                        color: muted
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                    }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.topMargin: 8
                currentIndex: root.stackIdx

                // ================= SCREEN 1 — service selection =================
                ScrollView {
                    id: pickScroll
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
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

                    ColumnLayout {
                        width: Math.min(pickScroll.availableWidth, 1060)
                        spacing: 12

                        GridLayout {
                            Layout.fillWidth: true
                            columns: pickScroll.availableWidth >= 680 ? 2 : 1
                            columnSpacing: 12
                            rowSpacing: 12

                            // Donatik card (data-driven, no per-service visuals)
                            CheremshaServiceCard {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumWidth: 300
                                title: "Donatik"
                                description: { donApi.uiTick; return donApi.loc("donations.card_donatik_hint") }
                                iconSource: Qt.resolvedUrl("../assets/icons/web_donatik.svg")
                                accentColor: "#f59e0b"
                                connected: donApi.donatikConfigured
                                statusConnectedText: { donApi.uiTick; return donApi.loc("donations.status_connected") }
                                statusDisconnectedText: { donApi.uiTick; return donApi.loc("donations.status_disconnected") }
                                actionText: { donApi.uiTick; return donApi.loc("donations.action_setup") }
                                descriptionMinHeight: 36
                                showToggles: true
                                liveOn: donApi.donatikLivePoll
                                ttsOn: donApi.donatikTtsNew
                                liveLabel: { donApi.uiTick; return donApi.loc("donations.card_live_abbr") }
                                ttsLabel: { donApi.uiTick; return donApi.loc("donations.card_tts_abbr") }
                                onActionClicked: root.openDonatik(root.donFrom, root.donTo)
                                onCardClicked: root.openDonatik(root.donFrom, root.donTo)
                                onLiveToggled: function (on) {
                                    donApi.setDonatikLivePoll(on)
                                    donApi.donatikSyncPollDates(root.donFrom, root.donTo)
                                }
                                onTtsToggled: function (on) { donApi.setDonatikTtsNew(on) }
                            }

                            // Donatello card (data-driven, no per-service visuals)
                            CheremshaServiceCard {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumWidth: 300
                                title: "Donatello"
                                description: { donApi.uiTick; return donApi.loc("donations.card_donatello_hint") }
                                iconSource: Qt.resolvedUrl("../assets/icons/web_donatello.svg")
                                accentColor: "#10b981"
                                connected: donApi.donatelloConfigured
                                statusConnectedText: { donApi.uiTick; return donApi.loc("donations.status_connected") }
                                statusDisconnectedText: { donApi.uiTick; return donApi.loc("donations.status_disconnected") }
                                actionText: { donApi.uiTick; return donApi.loc("donations.action_setup") }
                                descriptionMinHeight: 36
                                showToggles: true
                                liveOn: donApi.donatelloLivePoll
                                ttsOn: donApi.donatelloTtsNew
                                liveLabel: { donApi.uiTick; return donApi.loc("donations.card_live_abbr") }
                                ttsLabel: { donApi.uiTick; return donApi.loc("donations.card_tts_abbr") }
                                onActionClicked: root.openDonatello()
                                onCardClicked: root.openDonatello()
                                onLiveToggled: function (on) { donApi.setDonatelloLivePoll(on) }
                                onTtsToggled: function (on) { donApi.setDonatelloTtsNew(on) }
                            }
                        }

                        // Subtle "more services" placeholder card (not floating text)
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            implicitHeight: soonRow.implicitHeight + 24
                            radius: 12
                            color: cardBase
                            border.width: 1
                            border.color: cardEdge

                            RowLayout {
                                id: soonRow
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 10
                                Image {
                                    source: Qt.resolvedUrl("../assets/icons/web_plus.svg")
                                    Layout.preferredWidth: 15
                                    Layout.preferredHeight: 15
                                    Layout.alignment: Qt.AlignVCenter
                                    opacity: 0.7
                                }
                                Text {
                                    text: { donApi.uiTick; return donApi.loc("donations.more_soon") }
                                    color: muted
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                // ================= SCREEN 2 — Donatik history =================
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        // ---- Token setup (only while not configured) ----
                        TokenCard {
                            id: donatikTokenCard
                            visible: !donApi.donatikConfigured
                            cardTitle: { donApi.uiTick; return donApi.loc("donations.connection") }
                            fieldLabel: { donApi.uiTick; return donApi.loc("donations.api_token") }
                            fieldPlaceholder: { donApi.uiTick; return donApi.loc("donations.token_ph") }
                            saveText: { donApi.uiTick; return donApi.loc("donations.save_token") }
                            onSaveClicked: {
                                if (donApi.donatikSaveToken(donatikTokenCard.tokenText)) {
                                    donatikTokenCard.clearToken()
                                    root.donFrom = defaultFrom()
                                    root.donTo = defaultTo()
                                    donatikHistory.fromDate = root.donFrom
                                    donatikHistory.toDate = root.donTo
                                    donApi.donatikSyncPollDates(root.donFrom, root.donTo)
                                    donApi.donatikFetch(root.donFrom, root.donTo, "1")
                                }
                            }
                        }

                        InfoCard {
                            visible: !donApi.donatikConfigured
                            infoIcon: Qt.resolvedUrl("../assets/icons/web_shield.svg")
                            infoTitle: { donApi.uiTick; return donApi.loc("donations.about_donatik") }
                            infoHtml: { donApi.uiTick; return donApi.loc("donations.setup_intro_html") }
                        }

                        // ---- Donatik history (universal ServiceHistoryPage) ----
                        Component {
                            id: donatikRowDelegate
                            DonationRow {
                                width: ListView.view.width
                                amountText: {
                                    var pay = modelData.payment || {}
                                    return (pay.amount || "?") + " " + (pay.currency || "")
                                }
                                donorName: modelData.name || "—"
                                messageText: modelData.message || ""
                                sourceText: {
                                    var pr = (modelData.payment && modelData.payment.paymentProvider) || {}
                                    return pr.name || ""
                                }
                                timeText: {
                                    var raw = modelData.createdAt || ""
                                    return raw.length > 22 ? raw.substring(0, 22) : raw
                                }
                                statusMain: modelData.verifyStatus || ""
                                statusSub: {
                                    var st = (modelData.payment && modelData.payment.status) || ""
                                    return st
                                }
                                statusSubColor: {
                                    var st = (modelData.payment && modelData.payment.status) || ""
                                    return st === "COMPLETED" ? "#4ade80" : "#c4b5fd"
                                }
                            }
                        }
                        Component {
                            id: donatikFooterActions
                            RowLayout {
                                spacing: 8
                                DangerButton {
                                    text: { donApi.uiTick; return donApi.loc("donations.forget_token") }
                                    onClicked: donApi.donatikForgetToken()
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }
                        ServiceHistoryPage {
                            id: donatikHistory
                            visible: donApi.donatikConfigured
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 240

                            showDateFilter: true
                            showLive: true
                            showTts: true

                            livePoll: donApi.donatikLivePoll
                            ttsNew: donApi.donatikTtsNew
                            isLoading: donApi.donatikLoading
                            errorMessage: donApi.errorMessage
                            rows: JSON.parse(donApi.donationsJson || "[]")
                            total: donApi.total
                            page: donApi.page
                            pageCount: donApi.pageCount

                            periodLabel: { donApi.uiTick; return donApi.loc("donations.period") }
                            fromLabel: { donApi.uiTick; return donApi.loc("donations.from") }
                            toLabel: { donApi.uiTick; return donApi.loc("donations.to") }
                            refreshLabel: { donApi.uiTick; return donApi.loc("donations.refresh") }
                            liveLabel: { donApi.uiTick; return donApi.loc("donations.live_poll") }
                            ttsLabel: { donApi.uiTick; return donApi.loc("donations.tts_new") }
                            historyTitle: { donApi.uiTick; return donApi.loc("donations.history") }
                            summaryText: { donApi.uiTick; return donApi.summaryLine }
                            emptyTitle: { donApi.uiTick; return donApi.loc("donations.empty_title") }
                            emptyHint: { donApi.uiTick; return donApi.loc("donations.empty_hint") }
                            loadingText: { donApi.uiTick; return donApi.loc("donations.loading") }
                            prevLabel: { donApi.uiTick; return donApi.loc("donations.prev") }
                            nextLabel: { donApi.uiTick; return donApi.loc("donations.next") }

                            rowDelegate: donatikRowDelegate
                            footerActions: donatikFooterActions

                            Component.onCompleted: {
                                donatikHistory.fromDate = root.donFrom
                                donatikHistory.toDate = root.donTo
                            }
                            onFromDateChanged: {
                                root.donFrom = donatikHistory.fromDate
                                donApi.donatikSyncPollDates(root.donFrom, root.donTo)
                            }
                            onToDateChanged: {
                                root.donTo = donatikHistory.toDate
                                donApi.donatikSyncPollDates(root.donFrom, root.donTo)
                            }
                            onRefreshRequested: {
                                donApi.donatikSyncPollDates(donatikHistory.fromDate, donatikHistory.toDate)
                                donApi.donatikFetch(donatikHistory.fromDate, donatikHistory.toDate, "1")
                            }
                            onPageRequested: function (p) {
                                donApi.donatikFetch(root.donFrom, root.donTo, String(p))
                            }
                            onLiveToggled: function (on) {
                                donApi.setDonatikLivePoll(on)
                                donApi.donatikSyncPollDates(root.donFrom, root.donTo)
                            }
                            onTtsToggled: function (on) { donApi.setDonatikTtsNew(on) }
                        }
                    }
                }

                // ================= SCREEN 3 — Donatello configuration =================
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        // ---- Token setup (only while not configured) ----
                        TokenCard {
                            id: donatelloTokenCard
                            visible: !donApi.donatelloConfigured
                            cardTitle: { donApi.uiTick; return donApi.loc("donations.connection") }
                            fieldLabel: { donApi.uiTick; return donApi.loc("donations.api_token") }
                            fieldPlaceholder: { donApi.uiTick; return donApi.loc("donations.token_ph") }
                            saveText: { donApi.uiTick; return donApi.loc("donations.save_token") }
                            onSaveClicked: {
                                if (donApi.donatelloSaveToken(donatelloTokenCard.tokenText)) {
                                    donatelloTokenCard.clearToken()
                                    donApi.donatelloFetch("0")
                                }
                            }
                        }

                        InfoCard {
                            visible: !donApi.donatelloConfigured
                            infoIcon: Qt.resolvedUrl("../assets/icons/web_shield.svg")
                            infoTitle: { donApi.uiTick; return donApi.loc("donations.about_donatello") }
                            infoHtml: { donApi.uiTick; return donApi.loc("donations.setup_intro_donatello_html") }
                        }

                        // ---- Donatello history (universal ServiceHistoryPage) ----
                        Component {
                            id: donatelloRowDelegate
                            DonationRow {
                                width: ListView.view.width
                                amountText: (modelData.amount || "?") + " " + (modelData.currency || "")
                                donorName: modelData.clientName || "—"
                                messageText: modelData.message || ""
                                sourceText: modelData.goal || ""
                                timeText: modelData.createdAt || ""
                                statusMain: {
                                    donApi.uiTick
                                    if (modelData.isPublished)
                                        return donApi.loc("donations.donatello_published")
                                    return donApi.loc("donations.donatello_draft")
                                }
                                statusMainColor: modelData.isPublished ? "#4ade80" : "#8b95a5"
                                statusSub: modelData.pubId || ""
                            }
                        }
                        Component {
                            id: donatelloFooterActions
                            RowLayout {
                                spacing: 8
                                DangerButton {
                                    text: { donApi.uiTick; return donApi.loc("donations.forget_token") }
                                    onClicked: donApi.donatelloForgetToken()
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }
                        ServiceHistoryPage {
                            id: donatelloHistory
                            visible: donApi.donatelloConfigured
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 240

                            showDateFilter: false
                            showLive: true
                            showTts: true

                            livePoll: donApi.donatelloLivePoll
                            ttsNew: donApi.donatelloTtsNew
                            isLoading: donApi.donatelloLoading
                            errorMessage: donApi.errorMessage
                            rows: JSON.parse(donApi.donatelloJson || "[]")
                            total: donApi.donatelloTotal
                            page: donApi.donatelloPage + 1
                            pageCount: (!donApi.donatelloFirst || !donApi.donatelloLast) ? Math.max(2, donApi.donatelloPages) : 1
                            prevEnabled: !donApi.donatelloFirst
                            nextEnabled: !donApi.donatelloLast

                            periodLabel: { donApi.uiTick; return donApi.loc("donations.period") }
                            fromLabel: { donApi.uiTick; return donApi.loc("donations.from") }
                            toLabel: { donApi.uiTick; return donApi.loc("donations.to") }
                            refreshLabel: { donApi.uiTick; return donApi.loc("donations.refresh") }
                            liveLabel: { donApi.uiTick; return donApi.loc("donations.live_poll") }
                            ttsLabel: { donApi.uiTick; return donApi.loc("donations.tts_new") }
                            historyTitle: { donApi.uiTick; return donApi.loc("donations.history") }
                            summaryText: { donApi.uiTick; return donApi.donatelloSummaryLine }
                            emptyTitle: { donApi.uiTick; return donApi.loc("donations.empty_title") }
                            emptyHint: { donApi.uiTick; return donApi.loc("donations.empty_hint") }
                            loadingText: { donApi.uiTick; return donApi.loc("donations.loading") }
                            prevLabel: { donApi.uiTick; return donApi.loc("donations.prev") }
                            nextLabel: { donApi.uiTick; return donApi.loc("donations.next") }

                            rowDelegate: donatelloRowDelegate
                            footerActions: donatelloFooterActions

                            onRefreshRequested: {
                                donApi.donatelloFetch(String(donApi.donatelloPage))
                            }
                            onPageRequested: function (p) {
                                donApi.donatelloFetch(String(p - 1))
                            }
                            onLiveToggled: function (on) { donApi.setDonatelloLivePoll(on) }
                            onTtsToggled: function (on) { donApi.setDonatelloTtsNew(on) }
                        }
                    }
                }
            }

            Connections {
                target: donApi
                function onDonatikConfiguredChanged() {
                    if (root.screen === "donatik" && donApi.donatikConfigured
                            && root.donFrom.length && root.donTo.length) {
                        donApi.donatikFetch(root.donFrom, root.donTo, "1")
                    }
                }
                function onDonatelloConfiguredChanged() {
                    if (root.screen === "donatello" && donApi.donatelloConfigured)
                        donApi.donatelloFetch("0")
                }
            }
        }
    }
}
