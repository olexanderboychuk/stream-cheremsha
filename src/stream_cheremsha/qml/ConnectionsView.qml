import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// stream-cheremsha — connection cards (dark glass, brand headers, stream toggles)
Item {
    id: root
    anchors.fill: parent

    property bool twCollapsed: false
    property bool ytCollapsed: false
    property bool tkCollapsed: false
    property bool platformCardsHidden: false

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
    readonly property int footerPad: root.platformCardsHidden ? 102 : 0
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    component CollapseHandle: Item {
        id: h
        property bool collapsed: false
        property color accent: "#7c3aed"
        signal toggled()

        implicitWidth: 30
        implicitHeight: 30

        readonly property color _bgRest: "#151b27"
        readonly property color _bgHover: "#1a2232"
        readonly property color _bgPress: "#212b40"

        Rectangle {
            id: pill
            anchors.fill: parent
            radius: 999
            border.width: 1
            border.color: tap.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
            color: tap.pressed ? h._bgPress : (tap.containsMouse ? h._bgHover : h._bgRest)
            scale: tap.pressed ? 0.96 : (tap.containsMouse ? 1.05 : 1.0)
            Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }
        }

        Item {
            id: chev
            width: 14
            height: 10
            anchors.centerIn: parent

            // Base chevron points DOWN (expand). When expanded, rotate to point UP (collapse).
            rotation: h.collapsed ? 0 : 180
            transformOrigin: Item.Center
            Behavior on rotation { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

            scale: tap.pressed ? 0.9 : 1.0
            Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

            Rectangle {
                width: 9
                height: 2
                radius: 1
                color: ink
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: -3
                rotation: 45
                antialiasing: true
            }
            Rectangle {
                width: 9
                height: 2
                radius: 1
                color: ink
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: 3
                rotation: -45
                antialiasing: true
            }
        }

        MouseArea {
            id: tap
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: h.toggled()
        }
    }

    component SideCollapseHandle: Item {
        id: sh
        property bool collapsed: false
        property color accent: "#7c3aed"
        signal toggled()

        implicitWidth: 26
        implicitHeight: 110

        Rectangle {
            anchors.fill: parent
            radius: 999
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.08)
            color: tap.pressed ? "#182033" : (tap.containsMouse ? "#1c263c" : "#151b27")
            scale: tap.pressed ? 0.98 : (tap.containsMouse ? 1.03 : 1.0)
            Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 140 } }
        }

        Text {
            anchors.centerIn: parent
            // Show the *action*:
            // - when collapsed -> clicking shows left panel (chevron points right)
            // - when expanded  -> clicking hides left panel (chevron points left)
            text: sh.collapsed ? "❯" : "❮"
            color: ink
            font.pixelSize: 18
            scale: tap.pressed ? 0.92 : 1.0
            Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }

        MouseArea {
            id: tap
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: sh.toggled()
        }
    }

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

    component ConnMainSwitch: Switch {
        id: mainSw
        padding: 0
        implicitWidth: 46
        implicitHeight: 24
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        // Keep the right edge visually aligned with the card border: scaling from center
        // can overflow outside the card when the control is right-aligned.
        transformOrigin: Item.Right
        scale: mainSw.hovered ? 1.06 : 1.0
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

        indicator: Rectangle {
            width: mainSw.implicitWidth
            height: mainSw.implicitHeight
            radius: 12
            color: mainSw.checked ? "#16a34a" : "#dc2626" // green / red
            border.width: 1
            border.color: mainSw.checked ? "#22c55e" : "#ef4444"
            opacity: mainSw.enabled ? 1.0 : 0.55
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

            Rectangle {
                width: 18
                height: 18
                radius: 9
                y: 3
                x: mainSw.checked ? (parent.width - width - 3) : 3
                color: "#0b0f17"
                border.width: 1
                border.color: "#1f2937"
                Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            }
        }

        contentItem: Item {}
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
            implicitHeight: root.platformCardsHidden
                ? Math.max(1, sc.availableHeight)
                : (Math.max(col.implicitHeight, analyticsSlot.implicitHeight) + 24)
            height: root.platformCardsHidden ? Math.max(1, sc.availableHeight) : implicitHeight
            readonly property int _viewportH: Math.max(1, sc.availableHeight - root.footerPad)

            states: [
                State {
                    name: "platformsHidden"
                    when: root.platformCardsHidden
                    PropertyChanges { target: scInner; height: scInner._viewportH; implicitHeight: scInner._viewportH }
                }
            ]

            RowLayout {
                id: row
                width: Math.max(1, scInner.width - 32)
                anchors {
                    top: parent.top
                    left: parent.left
                    topMargin: 10
                    leftMargin: 16
                    bottomMargin: 20
                }
                spacing: 14

                states: [
                    State {
                        name: "platformsHidden"
                        when: root.platformCardsHidden
                        AnchorChanges {
                            target: row
                            anchors.bottom: scInner.bottom
                        }
                        PropertyChanges {
                            target: row.anchors
                            bottomMargin: 10
                        }
                    }
                ]

                ColumnLayout {
                    id: col
                    property real _targetW: Math.min(560, row.width)
                    property real _animW: root.platformCardsHidden ? 0 : _targetW
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: _animW
                    Layout.minimumWidth: 0
                    Layout.maximumWidth: _animW
                    Layout.fillHeight: true
                    spacing: root.platformCardsHidden ? 0 : 12
                    opacity: root.platformCardsHidden ? 0.0 : 1.0
                    clip: true
                    Behavior on _animW { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
                    Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

            // -------- Twitch card (Item sizes to ColumnLayout; Rectangle is background only) --------
            Item {
                id: twCard
                Layout.fillWidth: true
                implicitHeight: twCol.implicitHeight + 28
                Layout.preferredHeight: root.twCollapsed ? (twHeader.implicitHeight + 28) : (twCol.implicitHeight + 28)
                Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                clip: true

                CollapseHandle {
                    anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
                    z: 5
                    collapsed: root.twCollapsed
                    accent: twBar
                    onToggled: root.twCollapsed = !root.twCollapsed
                }

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: cardTop; opacity: 0.45 }
                }

                ColumnLayout {
                    id: twCol
                    x: 14; y: 14
                    width: parent.width - 28
                    spacing: 10

                    RowLayout {
                        id: twHeader
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
                            color: twHi; font.pixelSize: 18; font.bold: true; font.letterSpacing: 0.2
                            Layout.alignment: Qt.AlignVCenter
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        opacity: root.twCollapsed ? 0.0 : 1.0
                        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

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
                        spacing: 4
                        Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tw.channel") } color: muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                        TextField {
                            id: twCh; width: parent.width; color: ink; leftPadding: 10; rightPadding: 10; topPadding: 8; bottomPadding: 8; font.pixelSize: 13
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
                        spacing: 12
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        Switch {
                            id: twTtsSw
                            padding: 0
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            transformOrigin: Item.Center
                            Layout.alignment: Qt.AlignVCenter
                            checked: { if (!api) return true; api.refreshCounter; return api.twitchChatTtsEnabled() }
                            onClicked: { if (api) api.twitchSetChatTtsEnabled(!api.twitchChatTtsEnabled()) }
                            scale: twTtsSw.hovered ? 1.08 : 1.0
                            Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                        }

                        RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 12
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        ConnMainSwitch {
                            id: twSw
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
                Layout.preferredHeight: root.ytCollapsed ? (ytHeader.implicitHeight + 28) : (ytCol.implicitHeight + 28)
                Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                clip: true

                CollapseHandle {
                    anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
                    z: 5
                    collapsed: root.ytCollapsed
                    accent: ytBar
                    onToggled: root.ytCollapsed = !root.ytCollapsed
                }

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#4a1d1d"; opacity: 0.4 }
                }

                ColumnLayout {
                    id: ytCol
                    x: 14; y: 14
                    width: parent.width - 28
                    spacing: 10
                    RowLayout {
                        id: ytHeader
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
                            color: ytHi; font.pixelSize: 18; font.bold: true; Layout.alignment: Qt.AlignVCenter; Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        opacity: root.ytCollapsed ? 0.0 : 1.0
                        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

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
                            id: ytV; visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() } color: ink; leftPadding: 10; rightPadding: 10; topPadding: 8; bottomPadding: 8; font.pixelSize: 13
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
                        spacing: 12
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        Switch {
                            id: ytTtsSw
                            padding: 0
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            transformOrigin: Item.Center
                            Layout.alignment: Qt.AlignVCenter
                            checked: { if (!api) return true; api.refreshCounter; return api.youtubeChatTtsEnabled() }
                            onClicked: { if (api) api.youtubeSetChatTtsEnabled(!api.youtubeChatTtsEnabled()) }
                            scale: ytTtsSw.hovered ? 1.08 : 1.0
                            Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                        }

                        RowLayout {
                        visible: { if (!api) return false; api.refreshCounter; return api.googleLinked() }
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 12
                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        ConnMainSwitch {
                            id: ytSw
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
                Layout.preferredHeight: root.tkCollapsed ? (tkHeader.implicitHeight + 28) : (tkCol.implicitHeight + 28)
                Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                clip: true

                CollapseHandle {
                    anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
                    z: 5
                    collapsed: root.tkCollapsed
                    accent: tkBar
                    onToggled: root.tkCollapsed = !root.tkCollapsed
                }

                Rectangle {
                    anchors.fill: parent
                    z: 0
                    color: cardBase; radius: 16; border.width: 1; border.color: cardEdge
                    Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 } height: 1; color: "#103044"; opacity: 0.35 }
                }

                ColumnLayout {
                    id: tkCol
                    x: 14; y: 14
                    width: parent.width - 28
                    spacing: 10

                    RowLayout {
                        id: tkHeader
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
                            color: tkHi; font.pixelSize: 18; font.bold: true; Layout.alignment: Qt.AlignVCenter; Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        opacity: root.tkCollapsed ? 0.0 : 1.0
                        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

                        Text {
                            text: { if (!api) return ""; api.refreshCounter; return api.tiktokConnectedTextGet() }
                            color: ink; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: { if (!api) return ""; api.refreshCounter; return api.loc("tk.username") } color: muted; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 0.2 }
                            TextField {
                                id: tkUser; width: parent.width; color: ink; leftPadding: 10; rightPadding: 10; topPadding: 8; bottomPadding: 8; font.pixelSize: 13
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
                            spacing: 12
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tts_chat") }
                                color: muted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignVCenter
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            Switch {
                                id: tkTtsSw
                                padding: 0
                                focusPolicy: Qt.NoFocus
                                hoverEnabled: true
                                transformOrigin: Item.Center
                                Layout.alignment: Qt.AlignVCenter
                                checked: { if (!api) return true; api.refreshCounter; return api.tiktokChatTtsEnabled() }
                                onClicked: { if (api) api.tiktokSetChatTtsEnabled(!api.tiktokChatTtsEnabled()) }
                                scale: tkTtsSw.hovered ? 1.08 : 1.0
                                Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            spacing: 12
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.platform_enabled") }
                                color: muted
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignVCenter
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            ConnMainSwitch {
                                id: tkSw
                                Layout.alignment: Qt.AlignVCenter
                                Layout.rightMargin: 6
                                checked: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                                // Avoid feeding Switch's internal checked state back into backend.
                                // Binding-controlled checked + user interaction can cause double flips.
                                onClicked: { if (api) api.tiktokSetEnabled(!api.tiktokEnabled()) }
                            }
                        }
                    }
                }
            }

            // end ColumnLayout col
        }

        Item {
            Layout.preferredWidth: 36
            Layout.fillHeight: true
            visible: analyticsSlot._anyPanelEnabled

            SideCollapseHandle {
                anchors.centerIn: parent
                collapsed: root.platformCardsHidden
                accent: "#52607a"
                onToggled: root.platformCardsHidden = !root.platformCardsHidden
            }
        }

        // Analytics panels (dynamic grid: TikTok + Twitch).
        Item {
            id: analyticsSlot
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            readonly property bool _tkOn: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
            readonly property bool _twOn: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
            readonly property bool _ytOn: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
            readonly property bool _anyPanelEnabled: _tkOn || _twOn || _ytOn

            visible: _anyPanelEnabled && (root.platformCardsHidden || (row.width > (col.Layout.maximumWidth + 180)))

            function _tkEvVerb(kind) {
                if (!api) return "";
                api.refreshCounter;
                if (kind === "follow") return api.loc("connections.tiktok_analytics_follow");
                if (kind === "join") return api.loc("connections.tiktok_analytics_join");
                return api.loc("connections.tiktok_analytics_gift_suffix");
            }

            function _twEvVerb(kind) {
                if (!api) return "";
                api.refreshCounter;
                if (kind === "follow") return api.loc("connections.twitch_analytics_follow");
                if (kind === "sub") return api.loc("connections.twitch_analytics_sub");
                if (kind === "cheer") return api.loc("connections.twitch_analytics_cheer");
                return api.loc("connections.twitch_analytics_raid");
            }

            function _ytEvVerb(kind) {
                if (!api) return "";
                api.refreshCounter;
                if (kind === "superchat") return api.loc("connections.youtube_analytics_superchat");
                if (kind === "supersticker") return api.loc("connections.youtube_analytics_supersticker");
                if (kind === "member" || kind === "membership") return api.loc("connections.youtube_analytics_member");
                return api.loc("connections.youtube_analytics_chat");
            }

            readonly property int _footerReserve: {
                if (!root.platformCardsHidden) return 0;
                if (!api) return 0;
                api.refreshCounter;
                return Math.max(0, api.footerHeightPx || 0);
            }
            Layout.bottomMargin: _footerReserve

            readonly property int _cardH: Math.max(180, height - 28 - _footerReserve)

            readonly property int _minCardW: 360
            readonly property int _gap: 12
            readonly property bool _needsHScroll: width < (_minCardW * 2 + _gap)

            // Shared mini-stat tile used by both panels.
            component StatMini: Rectangle {
                id: st
                property string cap: ""
                property int val: 0
                property int capPx: 11
                property int valPx: 18
                implicitHeight: capCol.implicitHeight + 16
                radius: 10
                color: fieldBg
                border.width: 1
                border.color: cardEdge
                Column {
                    id: capCol
                    anchors.centerIn: parent
                    width: parent.width - 12
                    spacing: 2
                    Text {
                        width: parent.width
                        text: st.cap
                        color: muted
                        font.pixelSize: st.capPx
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                    }
                    Text {
                        width: parent.width
                        text: String(st.val)
                        color: ink
                        font.pixelSize: st.valPx
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            // Panel card container (keeps consistent look).
            component AnalyticsCard: Rectangle {
                id: card
                property color topLine: "#334155"
                radius: 16
                color: cardBase
                border.width: 1
                border.color: cardEdge
                Rectangle {
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 }
                    height: 1
                    color: card.topLine
                    opacity: 0.35
                }
            }

            // Wide layout: Flow wraps into 2 columns. Narrow layout: keep 2 cards in a row + horizontal scroll.
            Flickable {
                id: analyticsFlick
                anchors.fill: parent
                anchors.margins: 14
                anchors.bottomMargin: analyticsSlot._footerReserve
                clip: true
                interactive: analyticsSlot._needsHScroll
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                contentWidth: contentRoot.implicitWidth
                contentHeight: height

                // Snap to nearest card when horizontal scrolling is used.
                function _snapToNearestCard() {
                    if (!analyticsSlot._needsHScroll) return;
                    var step = analyticsSlot._minCardW + analyticsSlot._gap;
                    if (step <= 0) return;
                    var target = Math.round(contentX / step) * step;
                    target = Math.max(0, Math.min(target, contentWidth - width));
                    snapAnim.to = target;
                    snapAnim.restart();
                }

                onMovementEnded: _snapToNearestCard()
                onFlickEnded: _snapToNearestCard()

                NumberAnimation on contentX {
                    id: snapAnim
                    duration: 180
                    easing.type: Easing.OutCubic
                }

                Item {
                    id: contentRoot
                    width: Math.max(parent.width, implicitWidth)
                    height: parent.height
                    implicitWidth: analyticsSlot._needsHScroll ? (analyticsSlot._minCardW * 2 + analyticsSlot._gap) : flow.implicitWidth

                    Flow {
                        id: flow
                        anchors.fill: parent
                        spacing: analyticsSlot._gap
                        flow: Flow.LeftToRight

                        // Compute responsive width per card so Flow wraps naturally (but never below min width).
                        property int columns: analyticsSlot._needsHScroll ? 2 : Math.max(2, Math.floor((width + spacing) / (420 + spacing)))
                        property real cardW: analyticsSlot._needsHScroll
                            ? analyticsSlot._minCardW
                            : Math.max(analyticsSlot._minCardW, Math.floor((width - spacing * (columns - 1)) / columns))
                        property bool compact: cardW <= 380

                        // --- TikTok card ---
                        AnalyticsCard {
                            width: flow.cardW
                            height: analyticsSlot._cardH
                    topLine: "#103044"
                    visible: analyticsSlot._tkOn

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: tkBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../assets/tiktok.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 26
                                height: 26
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_title") }
                                color: tkHi
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return true; api.refreshCounter; return !api.tiktokEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_offline") }
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: flow.compact ? 2 : 4
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_online") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_total") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_gifts") }
                                val: tiktokAnalytics ? tiktokAnalytics.giftUnitsTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_diamonds") }
                                val: tiktokAnalytics ? tiktokAnalytics.diamondsTotal : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_activity") }
                            color: muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 120
                            radius: 10
                            color: fieldBg
                            border.width: 1
                            border.color: cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8
                                visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                                model: tiktokAnalytics ? tiktokAnalytics.feedModel : null

                                delegate: RowLayout {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    spacing: 8

                                    Text { text: model.timeText || ""; color: muted; font.pixelSize: 11; Layout.alignment: Qt.AlignTop }

                                    Item {
                                        width: 28
                                        height: 28
                                        Layout.alignment: Qt.AlignTop
                                        Image {
                                            anchors.centerIn: parent
                                            width: (model.iconUrl && model.iconUrl.length) ? 28 : 0
                                            height: (model.iconUrl && model.iconUrl.length) ? 28 : 0
                                            visible: model.iconUrl && model.iconUrl.length
                                            source: (model.iconUrl && model.iconUrl.length) ? model.iconUrl : ""
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            asynchronous: true
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            visible: !model.iconUrl || !model.iconUrl.length
                                            text: (model.eventKind === "gift") ? "🎁" : (model.eventKind === "follow" ? "＋" : "→")
                                            font.pixelSize: 14
                                            color: tkHi
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: {
                                            var u = model.userName || "";
                                            var verb = analyticsSlot._tkEvVerb(model.eventKind);
                                            if (model.eventKind === "gift") {
                                                var nm = model.detailText || "";
                                                var c = model.giftCount || 1;
                                                return u + " · " + nm + " × " + String(c);
                                            }
                                            return u + " · " + verb;
                                        }
                                        color: ink
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }

                        // --- YouTube card ---
                        AnalyticsCard {
                            width: flow.cardW
                            height: analyticsSlot._cardH
                    topLine: "#4a1d1d"
                    visible: analyticsSlot._ytOn

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: ytBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../assets/youtube.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 26
                                height: 26
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_title") }
                                color: ytHi
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return true; api.refreshCounter; return !api.youtubeRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_offline") }
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: flow.compact ? 2 : 4
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_messages") }
                                val: youtubeAnalytics ? youtubeAnalytics.messagesSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_unique") }
                                val: youtubeAnalytics ? youtubeAnalytics.uniqueChattersSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_superchats") }
                                val: youtubeAnalytics ? youtubeAnalytics.superChatsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_memberships") }
                                val: youtubeAnalytics ? youtubeAnalytics.membershipsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_activity") }
                            color: muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 120
                            radius: 10
                            color: fieldBg
                            border.width: 1
                            border.color: cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8
                                visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                                model: youtubeAnalytics ? youtubeAnalytics.feedModel : null

                                delegate: RowLayout {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    spacing: 8

                                    Text { text: model.timeText || ""; color: muted; font.pixelSize: 11; Layout.alignment: Qt.AlignTop }

                                    Text {
                                        text: (model.eventKind === "superchat" || model.eventKind === "supersticker") ? "💬" : ((model.eventKind === "member") ? "⭐" : "▶")
                                        font.pixelSize: 14
                                        color: ytHi
                                        Layout.alignment: Qt.AlignTop
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: {
                                            var u = model.userName || "";
                                            var kind = model.eventKind || "";
                                            var verb = analyticsSlot._ytEvVerb(kind);
                                            var d = model.detailText || "";
                                            if (kind === "chat") return u + " · " + d;
                                            if (d.length) return u + " · " + verb + " · " + d;
                                            return u + " · " + verb;
                                        }
                                        color: ink
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }

                        // --- Twitch card ---
                        AnalyticsCard {
                            width: flow.cardW
                            height: analyticsSlot._cardH
                    topLine: "#4c1d95"
                    visible: analyticsSlot._twOn

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: twBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../assets/twitch.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 26
                                height: 26
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_title") }
                                color: twHi
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return true; api.refreshCounter; return !api.twitchRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_offline") }
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: flow.compact ? 2 : 3
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_viewers") }
                                val: twitchAnalytics ? twitchAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_peak") }
                                val: twitchAnalytics ? twitchAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_follows") }
                                val: twitchAnalytics ? twitchAnalytics.followsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_subs") }
                                val: twitchAnalytics ? twitchAnalytics.subsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_bits") }
                                val: twitchAnalytics ? twitchAnalytics.bitsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: flow.compact ? 10 : 11
                                valPx: flow.compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_raids") }
                                val: twitchAnalytics ? twitchAnalytics.raidsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_activity") }
                            color: muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 120
                            radius: 10
                            color: fieldBg
                            border.width: 1
                            border.color: cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8
                                visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                                model: twitchAnalytics ? twitchAnalytics.feedModel : null

                                delegate: RowLayout {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    spacing: 8

                                    Text { text: model.timeText || ""; color: muted; font.pixelSize: 11; Layout.alignment: Qt.AlignTop }

                                    Text {
                                        text: (model.eventKind === "sub") ? "⭐" : ((model.eventKind === "cheer") ? "💠" : ((model.eventKind === "raid") ? "⚡" : "＋"))
                                        font.pixelSize: 14
                                        color: twHi
                                        Layout.alignment: Qt.AlignTop
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: {
                                            var u = model.userName || "";
                                            var kind = model.eventKind || "";
                                            var verb = analyticsSlot._twEvVerb(kind);
                                            var c = model.countValue || 0;
                                            var d = model.detailText || "";
                                            if (kind === "cheer") return u + " · " + verb + " × " + String(c);
                                            if (kind === "raid") return u + " · " + verb + " · " + String(c);
                                            if (kind === "sub") return u + " · " + verb + (d.length ? (" · " + d) : "");
                                            return u + " · " + verb;
                                        }
                                        color: ink
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                } // Flow
            } // contentRoot
            } // Flickable

        }
    } // RowLayout row
} // Item scInner
} // ScrollView sc
} // root Item
}
