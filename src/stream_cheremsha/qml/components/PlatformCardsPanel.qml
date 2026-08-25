import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

ColumnLayout {
    id: root
    property bool compact: false
    property bool twCollapsed: compact
    property bool ytCollapsed: compact
    property bool tkCollapsed: compact
    property bool kkCollapsed: compact

    spacing: compact ? 8 : 12

    Component.onCompleted: {
        if (compact) {
            twCollapsed = true
            ytCollapsed = true
            tkCollapsed = true
            kkCollapsed = true
        }
    }

    // -------- Twitch card --------
    Item {
        id: twCard
        Layout.fillWidth: true
        implicitHeight: twCol.implicitHeight + 28
        Layout.preferredHeight: root.twCollapsed && !root.compact
            ? (twHeader.implicitHeight + 28)
            : (twCol.implicitHeight + 28)
        Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        clip: true

        CollapseHandle {
            anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
            z: 5
            collapsed: root.twCollapsed
            accent: ConnTheme.twBar
            onToggled: root.twCollapsed = !root.twCollapsed
        }

        Rectangle {
            anchors.fill: parent
            z: 0
            color: ConnTheme.cardBase
            radius: 16
            border.width: 1
            border.color: ConnTheme.cardEdge
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 }
                height: 1
                color: ConnTheme.cardTop
                opacity: 0.45
            }
        }

        ColumnLayout {
            id: twCol
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 10

            RowLayout {
                id: twHeader
                Layout.fillWidth: true
                spacing: 10
                Rectangle { width: 3; height: 26; radius: 1; color: ConnTheme.twBar; Layout.alignment: Qt.AlignVCenter }
                Image {
                    source: Qt.resolvedUrl("../../assets/twitch.svg")
                    sourceSize: Qt.size(64, 64)
                    width: root.compact ? 22 : 28
                    height: root.compact ? 22 : 28
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.twitch_head") }
                    color: ConnTheme.twHi
                    font.pixelSize: root.compact ? 15 : 18
                    font.bold: true
                    font.letterSpacing: 0.2
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                visible: root.compact && root.twCollapsed
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.twitchConnectedTextGet() }
                    color: ConnTheme.ink
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                ConnPrefSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return true; api.refreshCounter; return api.twitchChatTtsEnabled() }
                    onClicked: { if (api) api.twitchSetChatTtsEnabled(!api.twitchChatTtsEnabled()) }
                }
                ConnMainSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                    onToggled: { if (api) api.twitchTransport() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.twCollapsed || !root.compact
                opacity: root.twCollapsed ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return !api.twitchKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.account") } color: ConnTheme.muted; width: 96 }
                    ConnPillButton {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.btn_browser") }
                        onClicked: api.twitchBrowserLogin()
                    }
                    Item { Layout.fillWidth: true }
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return !api.twitchKeyringSession() && !api.twitchClientConfigured()
                    }
                    text: {
                        if (!api) return ""
                        api.refreshCounter
                        return api.loc("tw.client_id_env_required").replace("{env}", api.twitchClientIdEnvName())
                    }
                    textFormat: Text.RichText
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.twitchKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 10
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.twitchConnectedTextGet() }
                        color: ConnTheme.ink
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Layout.maximumWidth: twCol.width - 120
                    }
                    ConnLinkButton {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.logout") }
                        onClicked: api.twitchLogout()
                        Layout.alignment: Qt.AlignTop
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.channel") } color: ConnTheme.muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                    TextField {
                        id: twCh
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 8
                        bottomPadding: 8
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("tw.channel_ph") }
                        onTextChanged: if (activeFocus) api.setTwitchChannelText(text)
                        onEditingFinished: if (api) api.twitchChannelCommit(text)
                        background: Rectangle { radius: 8; color: ConnTheme.fieldBg; border.width: 1; border.color: ConnTheme.cardEdge }
                        Component.onCompleted: { if (api) twCh.text = api.twitchChannelGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!twCh.activeFocus) twCh.text = api.twitchChannelGet() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return true; api.refreshCounter; return api.twitchChatTtsEnabled() }
                        onClicked: { if (api) api.twitchSetChatTtsEnabled(!api.twitchChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                        onToggled: { if (api) api.twitchTransport() }
                    }
                }
            }
        }
    }

    // -------- YouTube card --------
    Item {
        id: ytCard
        Layout.fillWidth: true
        implicitHeight: ytCol.implicitHeight + 28
        Layout.preferredHeight: root.ytCollapsed && !root.compact
            ? (ytHeader.implicitHeight + 28)
            : (ytCol.implicitHeight + 28)
        Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        clip: true

        CollapseHandle {
            anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
            z: 5
            collapsed: root.ytCollapsed
            accent: ConnTheme.ytBar
            onToggled: root.ytCollapsed = !root.ytCollapsed
        }

        Rectangle {
            anchors.fill: parent
            z: 0
            color: ConnTheme.cardBase
            radius: 16
            border.width: 1
            border.color: ConnTheme.cardEdge
            Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#4a1d1d"; opacity: 0.4 }
        }

        ColumnLayout {
            id: ytCol
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 10

            RowLayout {
                id: ytHeader
                Layout.fillWidth: true
                spacing: 10
                Rectangle { width: 3; height: 26; radius: 1; color: ConnTheme.ytBar; Layout.alignment: Qt.AlignVCenter }
                Image {
                    source: Qt.resolvedUrl("../../assets/youtube.svg")
                    sourceSize: Qt.size(64, 64)
                    width: root.compact ? 22 : 28
                    height: root.compact ? 22 : 28
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.youtube_head") }
                    color: ConnTheme.ytHi
                    font.pixelSize: root.compact ? 15 : 18
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                visible: {
                    if (!root.compact || !root.ytCollapsed) return false
                    if (!api) return false
                    api.refreshCounter
                    return api.googleLinked()
                }
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.youtubeConnectedTextGet() }
                    color: ConnTheme.ink
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                ConnPrefSwitch {
                    checked: { if (!api) return true; api.refreshCounter; return api.youtubeChatTtsEnabled() }
                    onClicked: { if (api) api.youtubeSetChatTtsEnabled(!api.youtubeChatTtsEnabled()) }
                }
                ConnMainSwitch {
                    checked: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                    onToggled: { if (api) api.youtubeTransport() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.ytCollapsed || !root.compact
                opacity: root.ytCollapsed ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

                Text { visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.youtubeOauthHelpHtml() } textFormat: Text.RichText; color: ConnTheme.muted; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; onLinkActivated: l => api.openUrl(l) }
                RowLayout { visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() } Layout.fillWidth: true; spacing: 8
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.account") } color: ConnTheme.muted; width: 96 }
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
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.youtubeConnectedTextGet() } color: ConnTheme.ink; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.maximumWidth: ytCol.width - 120 }
                    ConnLinkButton {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.logout") }
                        onClicked: api.youtubeLogout()
                    }
                }
                Text { visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.loc("yt.video_label") } color: ConnTheme.muted; font.pixelSize: 12; font.weight: Font.Medium; Layout.fillWidth: true }
                TextField {
                    id: ytV
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    color: ConnTheme.ink
                    leftPadding: 10
                    rightPadding: 10
                    topPadding: 8
                    bottomPadding: 8
                    font.pixelSize: 13
                    placeholderTextColor: ConnTheme.muted
                    placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("yt.video_ph") }
                    onTextChanged: if (activeFocus) api.setYoutubeVideoText(text)
                    background: Rectangle { radius: 8; color: ConnTheme.fieldBg; border.width: 1; border.color: ConnTheme.cardEdge }
                    Layout.fillWidth: true
                    Connections { target: api; function onRefreshCounterChanged() { if (!ytV.activeFocus) ytV.text = api.youtubeVideoGet() } }
                    Component.onCompleted: { if (api) ytV.text = api.youtubeVideoGet() }
                }
                Text { visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } text: { if (!api) return ""; api.refreshCounter; return api.youtubeStudioLinkHtml() } textFormat: Text.RichText; color: ConnTheme.muted; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; onLinkActivated: l => api.openUrl(l) }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return true; api.refreshCounter; return api.youtubeChatTtsEnabled() }
                        onClicked: { if (api) api.youtubeSetChatTtsEnabled(!api.youtubeChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                        onToggled: { if (api) api.youtubeTransport() }
                    }
                }
            }
        }
    }

    // -------- TikTok card --------
    Item {
        id: tkCard
        Layout.fillWidth: true
        implicitHeight: tkCol.implicitHeight + 28
        Layout.preferredHeight: root.tkCollapsed && !root.compact
            ? (tkHeader.implicitHeight + 28)
            : (tkCol.implicitHeight + 28)
        Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        clip: true

        CollapseHandle {
            anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
            z: 5
            collapsed: root.tkCollapsed
            accent: ConnTheme.tkBar
            onToggled: root.tkCollapsed = !root.tkCollapsed
        }

        Rectangle {
            anchors.fill: parent
            z: 0
            color: ConnTheme.cardBase
            radius: 16
            border.width: 1
            border.color: ConnTheme.cardEdge
            Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#103044"; opacity: 0.35 }
        }

        ColumnLayout {
            id: tkCol
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 10

            RowLayout {
                id: tkHeader
                Layout.fillWidth: true
                spacing: 10
                Rectangle { width: 3; height: 26; radius: 1; color: ConnTheme.tkBar; Layout.alignment: Qt.AlignVCenter }
                Image {
                    source: Qt.resolvedUrl("../../assets/tiktok.svg")
                    sourceSize: Qt.size(64, 64)
                    width: root.compact ? 22 : 28
                    height: root.compact ? 22 : 28
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.tiktok_head") }
                    color: ConnTheme.tkHi
                    font.pixelSize: root.compact ? 15 : 18
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                visible: root.compact && root.tkCollapsed
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                    color: ConnTheme.ink
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                ConnPrefSwitch {
                    checked: { if (!api) return true; api.refreshCounter; return api.tiktokChatTtsEnabled() }
                    onClicked: { if (api) api.tiktokSetChatTtsEnabled(!api.tiktokChatTtsEnabled()) }
                }
                ConnMainSwitch {
                    checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                    onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.tkCollapsed || !root.compact
                opacity: root.tkCollapsed ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                    color: ConnTheme.ink
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tk.username") } color: ConnTheme.muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                    TextField {
                        id: tkUser
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 8
                        bottomPadding: 8
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("tk.username_ph") }
                        onTextChanged: if (activeFocus) api.setTiktokUsernameText(text)
                        onEditingFinished: if (api) api.tiktokUsernameCommit(text)
                        background: Rectangle { radius: 8; color: ConnTheme.fieldBg; border.width: 1; border.color: ConnTheme.cardEdge }
                        Component.onCompleted: { if (api) tkUser.text = api.tiktokUsernameGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!tkUser.activeFocus) tkUser.text = api.tiktokUsernameGet() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return true; api.refreshCounter; return api.tiktokChatTtsEnabled() }
                        onClicked: { if (api) api.tiktokSetChatTtsEnabled(!api.tiktokChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                        onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                    }
                }
            }
        }
    }

    // -------- Kick card --------
    Item {
        id: kkCard
        Layout.fillWidth: true
        implicitHeight: kkCol.implicitHeight + 28
        Layout.preferredHeight: root.kkCollapsed && !root.compact
            ? (kkHeader.implicitHeight + 28)
            : (kkCol.implicitHeight + 28)
        Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        clip: true

        CollapseHandle {
            anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
            z: 5
            collapsed: root.kkCollapsed
            accent: ConnTheme.kkBar
            onToggled: root.kkCollapsed = !root.kkCollapsed
        }

        Rectangle {
            anchors.fill: parent
            z: 0
            color: ConnTheme.cardBase
            radius: 16
            border.width: 1
            border.color: ConnTheme.cardEdge
            Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#1c3a20"; opacity: 0.4 }
        }

        ColumnLayout {
            id: kkCol
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 10

            RowLayout {
                id: kkHeader
                Layout.fillWidth: true
                spacing: 10
                Rectangle { width: 3; height: 26; radius: 1; color: ConnTheme.kkBar; Layout.alignment: Qt.AlignVCenter }
                Image {
                    source: Qt.resolvedUrl("../../assets/kick.svg")
                    sourceSize: Qt.size(64, 64)
                    width: root.compact ? 22 : 28
                    height: root.compact ? 22 : 28
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.loc("ui.kick_head") }
                    color: ConnTheme.kkHi
                    font.pixelSize: root.compact ? 15 : 18
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                visible: root.compact && root.kkCollapsed
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.kickConnectedTextGet() }
                    color: ConnTheme.ink
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                ConnPrefSwitch {
                    checked: { if (!api) return true; api.refreshCounter; return api.kickChatTtsEnabled() }
                    onClicked: { if (api) api.kickSetChatTtsEnabled(!api.kickChatTtsEnabled()) }
                }
                ConnMainSwitch {
                    checked: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                    onClicked: { if (api) api.kickSetEnabled(!api.kickEnabled()) }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.kkCollapsed || !root.compact
                opacity: root.kkCollapsed ? 0.0 : 1.0
                Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return !api.kickKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("kick.account") } color: ConnTheme.muted; width: 96 }
                    ConnPillButton {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("kick.btn_browser") }
                        onClicked: api.kickBrowserLogin()
                    }
                    Item { Layout.fillWidth: true }
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return !api.kickKeyringSession() && !api.kickClientConfigured()
                    }
                    text: {
                        if (!api) return ""
                        api.refreshCounter
                        return api.loc("kick.client_id_env_required")
                            .replace("{env}", api.kickClientIdEnvName())
                            .replace("{secret_env}", "STREAM_CHEREMSHA_KICK_CLIENT_SECRET")
                    }
                    textFormat: Text.RichText
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                Text {
                    visible: { if (!api) return false; api.refreshCounter; return api.kickKeyringSession() || api.kickClientConfigured() }
                    text: {
                        if (!api) return ""
                        api.refreshCounter
                        return api.loc("kick.oauth_redirect").replace("{uri}", api.kickRedirectUri())
                    }
                    textFormat: Text.RichText
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.kickKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 10
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.kickConnectedTextGet() }
                        color: ConnTheme.ink
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Layout.maximumWidth: kkCol.width - 120
                    }
                    ConnLinkButton {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("kick.logout") }
                        onClicked: api.kickLogout()
                        Layout.alignment: Qt.AlignTop
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("kick.channel") } color: ConnTheme.muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                    TextField {
                        id: kkCh
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 8
                        bottomPadding: 8
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: { if (!api) return ""; api.refreshCounter; return api.loc("kick.channel_ph") }
                        onTextChanged: if (activeFocus) api.setKickChannelText(text)
                        onEditingFinished: if (api) api.kickChannelCommit(text)
                        background: Rectangle { radius: 8; color: ConnTheme.fieldBg; border.width: 1; border.color: ConnTheme.cardEdge }
                        Component.onCompleted: { if (api) kkCh.text = api.kickChannelGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!kkCh.activeFocus) kkCh.text = api.kickChannelGet() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return true; api.refreshCounter; return api.kickChatTtsEnabled() }
                        onClicked: { if (api) api.kickSetChatTtsEnabled(!api.kickChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 12
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignVCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: 6
                        checked: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                        onClicked: { if (api) api.kickSetEnabled(!api.kickEnabled()) }
                    }
                }
            }
        }
    }
}
