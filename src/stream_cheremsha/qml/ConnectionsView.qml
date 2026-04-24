import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// stream-cheremsha — connection cards (dark glass, brand headers, stream toggles)
Item {
    id: root
    anchors.fill: parent

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color cardTop: "#3b4a63"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    readonly property color twBar: "#7c3aed"
    readonly property color twHi: "#a78bfa"
    readonly property color ytBar: "#dc2626"
    readonly property color ytHi: "#f87171"
    readonly property color tkBar: "#0ea5e9"
    readonly property color tkHi: "#7dd3fc"
    Rectangle { anchors.fill: parent; color: base }

    component ConnPillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property color colRest: "#1c2434"
        property color colHover: "#2a3750"
        property color colPress: "#34425c"
        property color borRest: root.cardEdge
        property color borHover: "#56627a"
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: pillFontSize
        transformOrigin: Item.Center
        scale: pillCtl.hovered ? 1.02 : 1.0
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        contentItem: Text {
            text: pillCtl.text
            color: pillCtl.hovered ? "#f2f4f7" : root.ink
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

    component ConnLinkButton: Button {
        id: linkCtl
        flat: true
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        padding: 0
        contentItem: Text {
            text: linkCtl.text
            color: linkCtl.pressed ? "#cdd5e1" : (linkCtl.hovered ? "#f2f4f7" : root.muted)
            font.underline: true
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Behavior on color { ColorAnimation { duration: 100; easing.type: Easing.OutCubic } }
        }
        background: Item {}
    }

    ScrollView {
        id: sc
        anchors.fill: parent
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
            id: scInner
            width: root.width
            implicitHeight: col.implicitHeight

            ColumnLayout {
                id: col
                width: Math.min(720, scInner.width - 32)
                anchors {
                    top: parent.top
                    horizontalCenter: parent.horizontalCenter
                    topMargin: 10
                    bottomMargin: 20
                }
                spacing: 18

            // -------- Twitch card (Item sizes to ColumnLayout; Rectangle is background only) --------
            Item {
                id: twCard
                Layout.fillWidth: true
                implicitHeight: twCol.implicitHeight + 40

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: cardTop; opacity: 0.45 }
                }

                ColumnLayout {
                    id: twCol
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Rectangle { width: 3; height: 26; radius: 1; color: twBar; Layout.alignment: Qt.AlignVCenter }
                        Image {
                            source: Qt.resolvedUrl("../assets/twitch.svg")
                            sourceSize: Qt.size(64, 64)
                            width: 28
                            height: 28
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            asynchronous: true
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.twitch_head") }
                            color: twHi; font.pixelSize: 22; font.bold: true; font.letterSpacing: 0.2
                            Layout.alignment: Qt.AlignVCenter; Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        visible: { if (!api) return false; api.refreshCounter; return !api.twitchKeyringSession() }
                        Layout.fillWidth: true; spacing: 8
                        Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.account") } color: muted; width: 96 }
                        ConnPillButton {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.btn_browser") }
                            onClicked: api.twitchBrowserLogin()
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Text {
                        visible: {
                            if (!api) return false;
                            api.refreshCounter;
                            return !api.twitchKeyringSession() && !api.twitchClientConfigured();
                        }
                        text: {
                            if (!api) return "";
                            api.refreshCounter;
                            return api.loc("tw.client_id_env_required").replace("{env}", api.twitchClientIdEnvName());
                        }
                        textFormat: Text.RichText
                        color: muted
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        visible: { if (!api) return false; api.refreshCounter; return api.twitchKeyringSession() }
                        Layout.fillWidth: true; spacing: 10
                        Text {
                            id: twStat
                            text: { if (!api) return ""; api.refreshCounter; return api.twitchConnectedTextGet() }
                            color: ink; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            Layout.maximumWidth: twCol.width - 120
                        }
                        ConnLinkButton {
                            id: twLo
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.logout") }
                            onClicked: api.twitchLogout()
                            Layout.alignment: Qt.AlignTop
                        }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.channel") } color: muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                        TextField {
                            id: twCh; width: parent.width; color: ink; leftPadding: 12; rightPadding: 12; topPadding: 10; bottomPadding: 10; font.pixelSize: 14
                            placeholderTextColor: muted
                            placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("tw.channel_ph") }
                            onTextChanged: if (activeFocus) api.setTwitchChannelText(text)
                            onEditingFinished: if (api) api.twitchChannelCommit(text)
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            Component.onCompleted: { if (api) twCh.text = api.twitchChannelGet() }
                            Connections { target: api; function onRefreshCounterChanged() { if (!twCh.activeFocus) twCh.text = api.twitchChannelGet() } }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        Item { height: 1; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter }
                        Switch {
                            id: twSw
                            padding: 0
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            transformOrigin: Item.Center
                            Layout.alignment: Qt.AlignVCenter
                            checked: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            onToggled: { if (api) api.twitchTransport() }
                            scale: twSw.hovered ? 1.08 : 1.0
                            Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                    }
                }
            }

            // -------- YouTube card --------
            Item {
                id: ytCard
                Layout.fillWidth: true
                implicitHeight: ytCol.implicitHeight + 40

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#4a1d1d"; opacity: 0.4 }
                }

                ColumnLayout {
                    id: ytCol
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 14
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Rectangle { width: 3; height: 26; radius: 1; color: ytBar; Layout.alignment: Qt.AlignVCenter }
                        Image {
                            source: Qt.resolvedUrl("../assets/youtube.svg")
                            sourceSize: Qt.size(64, 64)
                            width: 28
                            height: 28
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            asynchronous: true
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.youtube_head") }
                            color: ytHi; font.pixelSize: 22; font.bold: true; Layout.alignment: Qt.AlignVCenter; Layout.fillWidth: true
                        }
                    }

                    Text { visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.youtubeOauthHelpHtml() } textFormat: Text.RichText; color: muted; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; onLinkActivated: l => api.openUrl(l) }
                    RowLayout { visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() } Layout.fillWidth: true; spacing: 8
                        Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.account") } color: muted; width: 96 }
                        ConnPillButton {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.btn_google") }
                            onClicked: api.youtubeOauth()
                        }
                        Item { Layout.fillWidth: true }
                    }
                    ConnPillButton {
                        visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() }
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.forget_json") }
                        onClicked: api.youtubeForgetClient()
                        pillFontSize: 12
                        colRest: "#1a2230"
                        colHover: "#232a38"
                        colPress: "#2c3444"
                    }

                    RowLayout { visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } Layout.fillWidth: true; spacing: 10
                        Text { id: yts; text: { if (!api) return ""; api.refreshCounter; return api.youtubeConnectedTextGet() } color: ink; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.maximumWidth: ytCol.width - 120 }
                        ConnLinkButton {
                            id: ytl
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.logout") }
                            onClicked: api.youtubeLogout()
                        }
                    }
                    Text { visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.video_label") } color: muted; font.pixelSize: 12; font.weight: Font.Medium; Layout.fillWidth: true }
                    TextField {
                        id: ytV; visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } color: ink; leftPadding: 12; rightPadding: 12; topPadding: 10; bottomPadding: 10; font.pixelSize: 13
                        placeholderTextColor: muted
                        placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("yt.video_ph") }
                        onTextChanged: if (activeFocus) api.setYoutubeVideoText(text)
                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                        Layout.fillWidth: true; Connections { target: api; function onRefreshCounterChanged() { if (!ytV.activeFocus) ytV.text = api.youtubeVideoGet() } }
                        Component.onCompleted: { if (api) ytV.text = api.youtubeVideoGet() }
                    }
                    Text { visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.youtubeStudioLinkHtml() } textFormat: Text.RichText; color: muted; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; onLinkActivated: l => api.openUrl(l) }
                    RowLayout {
                        visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        Item { height: 1; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter }
                        Switch {
                            id: ytSw
                            padding: 0
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            transformOrigin: Item.Center
                            Layout.alignment: Qt.AlignVCenter
                            checked: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            onToggled: { if (api) api.youtubeTransport() }
                            scale: ytSw.hovered ? 1.08 : 1.0
                            Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                    }
                }
            }

            // -------- TikTok card --------
            Item {
                id: tkCard
                Layout.fillWidth: true
                implicitHeight: tkCol.implicitHeight + 40

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#103044"; opacity: 0.35 }
                }

                ColumnLayout {
                    id: tkCol
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Rectangle { width: 3; height: 26; radius: 1; color: tkBar; Layout.alignment: Qt.AlignVCenter }
                        Image {
                            source: Qt.resolvedUrl("../assets/tiktok.svg")
                            sourceSize: Qt.size(64, 64)
                            width: 28
                            height: 28
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            asynchronous: true
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.tiktok_head") }
                            color: tkHi; font.pixelSize: 22; font.bold: true; Layout.alignment: Qt.AlignVCenter; Layout.fillWidth: true
                        }
                    }

                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                        color: ink; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        ConnPillButton {
                            visible: {
                                if (!api) return false;
                                api.refreshCounter;
                                return (api.tiktokUsernameGet() || "").trim().length > 0;
                            }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("actions.btn") }
                            onClicked: { if (api) api.openTikTokActions() }
                            pillFontSize: 12
                            colRest: "#1a2232"
                            colHover: "#232c40"
                            colPress: "#2d384e"
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tk.username") } color: muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                        TextField {
                            id: tkUser; width: parent.width; color: ink; leftPadding: 12; rightPadding: 12; topPadding: 10; bottomPadding: 10; font.pixelSize: 14
                            placeholderTextColor: muted
                            placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("tk.username_ph") }
                            onTextChanged: if (activeFocus) api.setTiktokUsernameText(text)
                            onEditingFinished: if (api) api.tiktokUsernameCommit(text)
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            Component.onCompleted: { if (api) tkUser.text = api.tiktokUsernameGet() }
                            Connections { target: api; function onRefreshCounterChanged() { if (!tkUser.activeFocus) tkUser.text = api.tiktokUsernameGet() } }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        Item { height: 1; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter }
                        Switch {
                            id: tkSw
                            padding: 0
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            transformOrigin: Item.Center
                            Layout.alignment: Qt.AlignVCenter
                            checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            // Avoid feeding Switch's internal checked state back into backend.
                            // Binding-controlled checked + user interaction can cause double flips.
                            onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                            scale: tkSw.hovered ? 1.08 : 1.0
                            Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                    }
                }
            }
        }
        }
    }
}
