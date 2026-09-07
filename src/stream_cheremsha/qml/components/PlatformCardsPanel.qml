import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

ColumnLayout {
    id: root
    property bool compact: false
    property bool twCollapsed: compact
    property bool ytCollapsed: true
    property bool tkCollapsed: true
    property bool kkCollapsed: true

    spacing: ConnTheme.cardGap

    property bool twShowAdvanced: false
    property bool ytShowAdvanced: false
    property bool kkShowAdvanced: false

    Component.onCompleted: {
        if (api) {
            twCollapsed = api.platformCardCollapsedGet("twitch")
            ytCollapsed = api.platformCardCollapsedGet("youtube")
            tkCollapsed = api.platformCardCollapsedGet("tiktok")
            kkCollapsed = api.platformCardCollapsedGet("kick")
        }
        if (compact) {
            twCollapsed = true
            ytCollapsed = true
            tkCollapsed = true
            kkCollapsed = true
        }
    }
    onTwCollapsedChanged: if (api && !compact) api.platformCardCollapsedSet("twitch", twCollapsed)
    onYtCollapsedChanged: if (api && !compact) api.platformCardCollapsedSet("youtube", ytCollapsed)
    onTkCollapsedChanged: if (api && !compact) api.platformCardCollapsedSet("tiktok", tkCollapsed)
    onKkCollapsedChanged: if (api && !compact) api.platformCardCollapsedSet("kick", kkCollapsed)

    function _loc(key) {
        if (!api) return ""
        api.refreshCounter
        return api.loc(key)
    }

    function _statusLabel(kind) {
        if (kind === "live") return _loc("connections.status_live")
        if (kind === "connected") return _loc("connections.status_connected_plain") || _loc("connections.status_connected")
        if (kind === "attention") return _loc("connections.status_attention")
        if (kind === "error") return _loc("connections.status_error")
        return _loc("connections.status_disabled")
    }

    // Platform cards show "Підключено" for both live and connected (reference).
    function _cardStatusLabel(kind) {
        if (kind === "live" || kind === "connected")
            return _loc("connections.status_connected_plain") || _loc("connections.status_connected")
        return _statusLabel(kind)
    }

    function _twKind() {
        if (!api) return "disabled"
        api.refreshCounter
        if (api.twitchKeyringSession()) return "connected"
        if (!api.twitchClientConfigured()) return "attention"
        return "disabled"
    }

    function _twHint() {
        if (!api) return ""
        api.refreshCounter
        if (api.twitchKeyringSession()) return ""
        if (!api.twitchClientConfigured()) return _loc("connections.hint_twitch_client")
        return _loc("connections.hint_login")
    }

    function _ytKind() {
        if (!api) return "disabled"
        api.refreshCounter
        if (api.googleLinked()) return "connected"
        return "disabled"
    }

    function _ytHint() {
        if (!api) return ""
        api.refreshCounter
        if (api.googleLinked()) return ""
        return _loc("connections.hint_login")
    }

    function _tkKind() {
        if (!api) return "disabled"
        api.refreshCounter
        var u = api.tiktokUsernameGet()
        var configured = u && String(u).length > 0
        if (configured && api.tiktokEnabled()) return "live"
        if (configured) return "connected"
        return "disabled"
    }

    function _tkHint() {
        if (!api) return ""
        api.refreshCounter
        var u2 = api.tiktokUsernameGet()
        if (!u2 || String(u2).length === 0) return _loc("connections.hint_tiktok_disabled")
        return ""
    }

    function _kkKind() {
        if (!api) return "disabled"
        api.refreshCounter
        var ch = ""
        try { ch = api.kickChannelGet() } catch (e) { ch = "" }
        var configured = api.kickKeyringSession() || (ch && String(ch).length > 0)
        if (configured && api.kickEnabled()) return "live"
        if (configured) return "connected"
        if (!api.kickClientConfigured()) return "attention"
        return "attention"
    }

    function _kkHint() {
        if (!api) return ""
        api.refreshCounter
        if (api.kickKeyringSession()) {
            return ""
        }
        if (!api.kickClientConfigured()) return _loc("connections.hint_kick_client")
        return _loc("connections.hint_kick_redirect")
    }

    component AttentionHint: Rectangle {
        property string message: ""
        property bool showConfigure: true
        signal configure()

        visible: message.length > 0
        Layout.fillWidth: true
        implicitHeight: hintCol.implicitHeight + 12
        radius: 8
        color: "#1c1910"
        border.width: 1
        border.color: "#3d3518"

        ColumnLayout {
            id: hintCol
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: message
                color: "#fde047"
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ConnLinkButton {
                visible: showConfigure
                text: root._loc("connections.configure")
                onClicked: configure()
            }
        }
    }

    // Plain dot + status text (reference platform-card language, no capsule).
    component PlatformStatus: Row {
        property string kind: "disabled"
        property string label: ""
        spacing: 6
        Rectangle {
            width: 7
            height: 7
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: {
                if (kind === "live" || kind === "connected") return "#22c55e"
                if (kind === "attention") return "#eab308"
                if (kind === "error") return "#ef4444"
                return "#64748b"
            }
        }
        Text {
            text: label
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: ConnTheme.statusPx
            font.weight: Font.DemiBold
            color: {
                if (kind === "live" || kind === "connected") return "#4ade80"
                if (kind === "attention") return "#fde047"
                if (kind === "error") return "#fca5a5"
                return "#94a3b8"
            }
        }
    }

    component CardShell: Item {
        id: shell
        property bool collapsed: false
        property bool forceCollapseHeight: false
        property int headerHeight: 36
        property int collapsedExtra: 0
        property color accent: ConnTheme.twBar
        property color hoverEdge: ConnTheme.cardEdge
        signal collapseToggled()

        default property alias content: bodyCol.data

        Layout.fillWidth: true
        implicitHeight: bodyCol.implicitHeight + ConnTheme.cardPad * 2
        // Collapsed: header + breathing room + summary, with ~8-10px bottom
        // padding so the toggle row is never clipped by the card boundary.
        Layout.preferredHeight: (shell.collapsed && shell.forceCollapseHeight)
            ? (shell.headerHeight + 26 + shell.collapsedExtra)
            : (bodyCol.implicitHeight + ConnTheme.cardPad * 2)
        Behavior on Layout.preferredHeight { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        clip: true

        Rectangle {
            id: bg
            anchors.fill: parent
            z: 0
            color: ConnTheme.cardBase
            radius: ConnTheme.cardRadius
            border.width: 1
            border.color: cardHover.containsMouse ? Qt.lighter(shell.hoverEdge, 1.35) : ConnTheme.cardEdge
            Behavior on border.color { ColorAnimation { duration: 140 } }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: 1
                width: 3
                radius: 1
                color: shell.accent
                opacity: 0.9
            }
        }

        MouseArea {
            id: cardHover
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
            z: 1
        }

        CollapseHandle {
            anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
            z: 5
            collapsed: shell.collapsed
            accent: shell.accent
            onToggled: shell.collapseToggled()
        }

        ColumnLayout {
            id: bodyCol
            x: ConnTheme.cardPad
            y: 14
            width: parent.width - ConnTheme.cardPad * 2
            spacing: 10
            z: 2
        }
    }

    // -------- Twitch --------
    CardShell {
        id: twCard
        collapsed: root.twCollapsed
        forceCollapseHeight: !root.compact
        accent: ConnTheme.twBar
        hoverEdge: "#3b2a5c"
        headerHeight: twHeader.implicitHeight
        collapsedExtra: twSummary.visible ? (twSummary.implicitHeight + 6) : 0
        onCollapseToggled: root.twCollapsed = !root.twCollapsed


            RowLayout {
                id: twHeader
                Layout.fillWidth: true
                Layout.rightMargin: 34
                spacing: 10
                Item {
                    // Fixed-size icon cell with genuinely zero implicit size,
                    // so the rasterized sourceSize can never force the row wider.
                    Layout.preferredWidth: root.twCollapsed ? 26 : 32
                    Layout.preferredHeight: root.twCollapsed ? 26 : 32
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 0
                    implicitHeight: 0
                    Image {
                        anchors.centerIn: parent
                        width: root.twCollapsed ? 26 : 32
                        height: root.twCollapsed ? 26 : 32
                        source: Qt.resolvedUrl("../../assets/twitch.svg")
                        sourceSize: Qt.size(64, 64)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        asynchronous: true
                    }
                }
                Text {
                    text: root._loc("ui.twitch_head")
                    color: ConnTheme.ink
                    font.pixelSize: root.twCollapsed ? 15 : ConnTheme.cardTitlePx
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                }
                PlatformStatus {
                    kind: root._twKind()
                    label: root._cardStatusLabel(kind)
                }
                Item { Layout.fillWidth: true }
            }

            // Collapsed summary: account line + enable toggle
            RowLayout {
                id: twSummary
                visible: root.twCollapsed
                Layout.fillWidth: true
                Layout.leftMargin: 36
                spacing: 8
                // Flexible text cell: genuinely zero implicit width, so long text
                // can never push the fixed switch outside the card.
                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitHeight: twAccText.implicitHeight
                    Text {
                        id: twAccText
                        anchors.fill: parent
                        text: { if (!api) return ""; api.refreshCounter; return api.twitchConnectedTextGet() }
                        visible: text.length > 0
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                ConnMainSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                    onToggled: { if (api) api.twitchTransport() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.twCollapsed
                opacity: root.twCollapsed ? 0.0 : 1.0
                Layout.minimumWidth: 0
                Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                spacing: 14

                AttentionHint {
                    message: (!root.twCollapsed && root._twKind() === "attention") ? root._twHint() : ""
                    onConfigure: root.twShowAdvanced = true
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return !api.twitchKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 8
                    ConnPillButton {
                        text: root._loc("tw.btn_browser")
                        onClicked: api.twitchBrowserLogin()
                    }
                    Item { Layout.fillWidth: true }
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return root.twShowAdvanced && !api.twitchKeyringSession() && !api.twitchClientConfigured()
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
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ConnPillButton {
                        text: root._loc("tw.logout")
                        onClicked: api.twitchLogout()
                        pillFontSize: 12
                        colRest: "#1a2230"
                        colHover: "#232a38"
                        colPress: "#2c3444"
                        Layout.alignment: Qt.AlignTop
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: root._loc("tw.channel")
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                    TextField {
                        id: twCh
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 12
                        rightPadding: 34
                        topPadding: 9
                        bottomPadding: 9
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: root._loc("tw.channel_ph")
                        onTextChanged: if (activeFocus) api.setTwitchChannelText(text)
                        onEditingFinished: if (api) api.twitchChannelCommit(text)
                        background: Rectangle {
                            radius: ConnTheme.fieldRadius
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: parent.activeFocus ? ConnTheme.twBar : ConnTheme.cardEdge
                        }
                        Component.onCompleted: { if (api) twCh.text = api.twitchChannelGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!twCh.activeFocus) twCh.text = api.twitchChannelGet() } }
                        Image {
                            source: Qt.resolvedUrl("../../assets/metrics/copy.svg")
                            width: 15
                            height: 15
                            anchors.right: parent.right
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            opacity: copyTwTap.containsMouse ? 1.0 : 0.65
                            Behavior on opacity { NumberAnimation { duration: 120 } }
                            MouseArea {
                                id: copyTwTap
                                anchors.fill: parent
                                anchors.margins: -8
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { twCh.selectAll(); twCh.copy(); twCh.deselect() }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_chat")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return true; api.refreshCounter; return api.twitchChatTtsEnabled() }
                        onClicked: { if (api) api.twitchSetChatTtsEnabled(!api.twitchChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                        onToggled: { if (api) api.twitchTransport() }
                    }
                }
            }
    }

    // -------- YouTube --------
    CardShell {
        collapsed: root.ytCollapsed
        forceCollapseHeight: !root.compact
        accent: ConnTheme.ytBar
        hoverEdge: "#4a1d1d"
        headerHeight: ytHeader.implicitHeight
        collapsedExtra: ytSummary.visible ? (ytSummary.implicitHeight + 6) : 0
        onCollapseToggled: root.ytCollapsed = !root.ytCollapsed


            RowLayout {
                id: ytHeader
                Layout.fillWidth: true
                Layout.rightMargin: 34
                spacing: 10
                Item {
                    // Fixed-size icon cell with genuinely zero implicit size,
                    // so the rasterized sourceSize can never force the row wider.
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 0
                    implicitHeight: 0
                    Image {
                        anchors.centerIn: parent
                        width: 26
                        height: 26
                        source: Qt.resolvedUrl("../../assets/youtube.svg")
                        sourceSize: Qt.size(64, 64)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        asynchronous: true
                    }
                }
                Text {
                    text: root._loc("ui.youtube_head")
                    color: ConnTheme.ink
                    font.pixelSize: 15
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                }
                PlatformStatus {
                    kind: root._ytKind()
                    label: root._cardStatusLabel(kind)
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                id: ytSummary
                visible: {
                    if (!root.ytCollapsed) return false
                    if (!api) return false
                    api.refreshCounter
                    return api.googleLinked()
                }
                Layout.fillWidth: true
                Layout.leftMargin: 36
                spacing: 8
                // Flexible text cell: genuinely zero implicit width, so long text
                // can never push the fixed switch outside the card.
                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitHeight: ytAccText.implicitHeight
                    Text {
                        id: ytAccText
                        anchors.fill: parent
                        text: { if (!api) return ""; api.refreshCounter; return api.youtubeConnectedTextGet() }
                        visible: text.length > 0
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                ConnMainSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                    onToggled: { if (api) api.youtubeTransport() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.ytCollapsed
                opacity: root.ytCollapsed ? 0.0 : 1.0
                Layout.minimumWidth: 0
                Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                spacing: 14

                AttentionHint {
                    message: (!root.ytCollapsed && root._ytKind() === "attention") ? root._ytHint() : ""
                    onConfigure: root.ytShowAdvanced = true
                }

                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return root.ytShowAdvanced && !api.googleLinked()
                    }
                    text: { if (!api) return ""; api.refreshCounter; return api.youtubeOauthHelpHtml() }
                    textFormat: Text.RichText
                    color: ConnTheme.muted
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    onLinkActivated: l => api.openUrl(l)
                }
                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() }
                    Layout.fillWidth: true
                    spacing: 8
                    ConnPillButton {
                        text: root._loc("yt.btn_google")
                        onClicked: api.youtubeOauth()
                    }
                    Item { Layout.fillWidth: true }
                }
                ConnPillButton {
                    visible: { if (!api) return false; api.refreshCounter; return !api.googleLinked() }
                    text: root._loc("yt.forget_json")
                    onClicked: api.youtubeForgetClient()
                    pillFontSize: 12
                    colRest: "#1a2230"
                    colHover: "#232a38"
                    colPress: "#2c3444"
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    Layout.fillWidth: true
                    spacing: 10
                    Text {
                        text: { if (!api) return ""; api.refreshCounter; return api.youtubeConnectedTextGet() }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ConnPillButton {
                        text: root._loc("yt.logout")
                        onClicked: api.youtubeLogout()
                        pillFontSize: 12
                        colRest: "#1a2230"
                        colHover: "#232a38"
                        colPress: "#2c3444"
                    }
                }
                Text {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    text: root._loc("yt.video_label")
                    color: ConnTheme.muted
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    Layout.fillWidth: true
                }
                TextField {
                    id: ytV
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    color: ConnTheme.ink
                    leftPadding: 12
                    rightPadding: 12
                    topPadding: 9
                    bottomPadding: 9
                    font.pixelSize: 13
                    placeholderTextColor: ConnTheme.muted
                    placeholderText: root._loc("yt.video_ph")
                    onTextChanged: if (activeFocus) api.setYoutubeVideoText(text)
                    background: Rectangle {
                        radius: ConnTheme.fieldRadius
                        color: ConnTheme.fieldBg
                        border.width: 1
                        border.color: parent.activeFocus ? ConnTheme.ytBar : ConnTheme.cardEdge
                    }
                    Layout.fillWidth: true
                    Connections { target: api; function onRefreshCounterChanged() { if (!ytV.activeFocus) ytV.text = api.youtubeVideoGet() } }
                    Component.onCompleted: { if (api) ytV.text = api.youtubeVideoGet() }
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return api.googleLinked()
                    }
                    text: root.ytShowAdvanced ? root._loc("connections.hide") : root._loc("connections.details")
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    font.underline: true
                    Layout.fillWidth: true
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.ytShowAdvanced = !root.ytShowAdvanced
                    }
                }
                Text {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() && root.ytShowAdvanced }
                    text: { if (!api) return ""; api.refreshCounter; return api.youtubeStudioLinkHtml() }
                    textFormat: Text.RichText
                    color: ConnTheme.muted
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    onLinkActivated: l => api.openUrl(l)
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_chat")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return true; api.refreshCounter; return api.youtubeChatTtsEnabled() }
                        onClicked: { if (api) api.youtubeSetChatTtsEnabled(!api.youtubeChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                        onToggled: { if (api) api.youtubeTransport() }
                    }
                }
            }
    }

    // -------- TikTok --------
    CardShell {
        collapsed: root.tkCollapsed
        forceCollapseHeight: !root.compact
        accent: ConnTheme.tkBar
        hoverEdge: "#0e3a44"
        headerHeight: tkHeader.implicitHeight
        collapsedExtra: tkSummary.visible ? (tkSummary.implicitHeight + 6) : 0
        onCollapseToggled: root.tkCollapsed = !root.tkCollapsed


            RowLayout {
                id: tkHeader
                Layout.fillWidth: true
                Layout.rightMargin: 34
                spacing: 10
                Item {
                    // Fixed-size icon cell with genuinely zero implicit size,
                    // so the rasterized sourceSize can never force the row wider.
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 0
                    implicitHeight: 0
                    Image {
                        anchors.centerIn: parent
                        width: 26
                        height: 26
                        source: Qt.resolvedUrl("../../assets/tiktok.svg")
                        sourceSize: Qt.size(64, 64)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        asynchronous: true
                    }
                }
                Text {
                    text: root._loc("ui.tiktok_head")
                    color: ConnTheme.ink
                    font.pixelSize: 15
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                }
                PlatformStatus {
                    kind: root._tkKind()
                    label: root._cardStatusLabel(kind)
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                id: tkSummary
                visible: root.tkCollapsed
                Layout.fillWidth: true
                Layout.leftMargin: 36
                spacing: 8
                // Flexible text cell: genuinely zero implicit width, so long text
                // can never push the fixed switch outside the card.
                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitHeight: tkAccText.implicitHeight
                    Text {
                        id: tkAccText
                        anchors.fill: parent
                        text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                        visible: text.length > 0
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                ConnMainSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                    onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.tkCollapsed
                opacity: root.tkCollapsed ? 0.0 : 1.0
                Layout.minimumWidth: 0
                Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                spacing: 14

                AttentionHint {
                    message: (!root.tkCollapsed && root._tkKind() === "attention") ? root._tkHint() : ""
                    showConfigure: false
                }

                Text {
                    text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                    color: ConnTheme.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    visible: text.length > 0
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: root._loc("tk.username")
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                    TextField {
                        id: tkUser
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 12
                        rightPadding: 12
                        topPadding: 9
                        bottomPadding: 9
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: root._loc("tk.username_ph")
                        onTextChanged: if (activeFocus) api.setTiktokUsernameText(text)
                        onEditingFinished: if (api) api.tiktokUsernameCommit(text)
                        background: Rectangle {
                            radius: ConnTheme.fieldRadius
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: parent.activeFocus ? ConnTheme.tkBar : ConnTheme.cardEdge
                        }
                        Component.onCompleted: { if (api) tkUser.text = api.tiktokUsernameGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!tkUser.activeFocus) tkUser.text = api.tiktokUsernameGet() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_chat")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return true; api.refreshCounter; return api.tiktokChatTtsEnabled() }
                        onClicked: { if (api) api.tiktokSetChatTtsEnabled(!api.tiktokChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                        onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                    }
                }
            }
    }

    // -------- Kick --------
    CardShell {
        collapsed: root.kkCollapsed
        forceCollapseHeight: !root.compact
        accent: ConnTheme.kkBar
        hoverEdge: "#1c3a20"
        headerHeight: kkHeader.implicitHeight
        collapsedExtra: kkSummary.visible ? (kkSummary.implicitHeight + 6) : 0
        onCollapseToggled: root.kkCollapsed = !root.kkCollapsed


            RowLayout {
                id: kkHeader
                Layout.fillWidth: true
                Layout.rightMargin: 34
                spacing: 10
                Item {
                    // Fixed-size icon cell with genuinely zero implicit size,
                    // so the rasterized sourceSize can never force the row wider.
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 0
                    implicitHeight: 0
                    Image {
                        anchors.centerIn: parent
                        width: 26
                        height: 26
                        source: Qt.resolvedUrl("../../assets/kick.svg")
                        sourceSize: Qt.size(64, 64)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        asynchronous: true
                    }
                }
                Text {
                    text: root._loc("ui.kick_head")
                    color: ConnTheme.ink
                    font.pixelSize: 15
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                }
                PlatformStatus {
                    kind: root._kkKind()
                    label: root._cardStatusLabel(kind)
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                id: kkSummary
                visible: root.kkCollapsed
                Layout.fillWidth: true
                Layout.leftMargin: 36
                spacing: 8
                // Flexible text cell: genuinely zero implicit width, so long text
                // can never push the fixed switch outside the card.
                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                    implicitHeight: kkAccText.implicitHeight
                    Text {
                        id: kkAccText
                        anchors.fill: parent
                        text: {
                            if (!api) return ""
                            api.refreshCounter
                            var t = api.kickConnectedTextGet()
                            if (t && t.length) return t
                            return root._loc("connections.not_connected")
                        }
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                ConnMainSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                    onClicked: { if (api) api.kickSetEnabled(!api.kickEnabled()) }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.kkCollapsed
                opacity: root.kkCollapsed ? 0.0 : 1.0
                Layout.minimumWidth: 0
                Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                spacing: 14

                AttentionHint {
                    message: (!root.kkCollapsed && root._kkKind() === "attention") ? root._kkHint() : ""
                    onConfigure: root.kkShowAdvanced = true
                }

                RowLayout {
                    visible: { if (!api) return false; api.refreshCounter; return !api.kickKeyringSession() }
                    Layout.fillWidth: true
                    spacing: 8
                    ConnPillButton {
                        text: root._loc("kick.btn_browser")
                        onClicked: api.kickBrowserLogin()
                    }
                    Item { Layout.fillWidth: true }
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return root.kkShowAdvanced && !api.kickKeyringSession() && !api.kickClientConfigured()
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
                ConnLinkButton {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return !api.kickKeyringSession() && api.kickClientConfigured()
                    }
                    text: root.kkShowAdvanced ? root._loc("connections.hide_uri") : root._loc("connections.show_uri")
                    onClicked: root.kkShowAdvanced = !root.kkShowAdvanced
                }
                Text {
                    visible: {
                        if (!api) return false
                        api.refreshCounter
                        return root.kkShowAdvanced && !api.kickKeyringSession() && api.kickClientConfigured()
                    }
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
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ConnPillButton {
                        text: root._loc("kick.logout")
                        onClicked: api.kickLogout()
                        pillFontSize: 12
                        colRest: "#1a2230"
                        colHover: "#232a38"
                        colPress: "#2c3444"
                        Layout.alignment: Qt.AlignTop
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: root._loc("kick.channel")
                        color: ConnTheme.muted
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                    TextField {
                        id: kkCh
                        width: parent.width
                        color: ConnTheme.ink
                        leftPadding: 12
                        rightPadding: 12
                        topPadding: 9
                        bottomPadding: 9
                        font.pixelSize: 13
                        placeholderTextColor: ConnTheme.muted
                        placeholderText: root._loc("kick.channel_ph")
                        onTextChanged: if (activeFocus) api.setKickChannelText(text)
                        onEditingFinished: if (api) api.kickChannelCommit(text)
                        background: Rectangle {
                            radius: ConnTheme.fieldRadius
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: parent.activeFocus ? ConnTheme.kkBar : ConnTheme.cardEdge
                        }
                        Component.onCompleted: { if (api) kkCh.text = api.kickChannelGet() }
                        Connections { target: api; function onRefreshCounterChanged() { if (!kkCh.activeFocus) kkCh.text = api.kickChannelGet() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_chat")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.tts_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnPrefSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return true; api.refreshCounter; return api.kickChatTtsEnabled() }
                        onClicked: { if (api) api.kickSetChatTtsEnabled(!api.kickChatTtsEnabled()) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled")
                            color: ConnTheme.ink
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root._loc("connections.platform_enabled_desc")
                            color: ConnTheme.muted
                            font.pixelSize: ConnTheme.secondaryPx
                            wrapMode: Text.Wrap
                        }
                    }
                    ConnMainSwitch {
                        Layout.alignment: Qt.AlignVCenter
                        checked: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                        onClicked: { if (api) api.kickSetEnabled(!api.kickEnabled()) }
                    }
                }
            }
    }
}
