import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import components

Item {
    id: analyticsSlot
    property bool fillHeight: false
    property bool alwaysVisible: false
    property bool bigPictureMode: false
    property int footerReserve: 0

    readonly property bool _tkOn: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
    readonly property bool _twOn: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
    readonly property bool _ytOn: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
    readonly property bool _kkOn: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
    readonly property bool _tkShow: bigPictureMode || _tkOn
    readonly property bool _twShow: bigPictureMode || _twOn
    readonly property bool _ytShow: bigPictureMode || _ytOn
    readonly property bool _kkShow: bigPictureMode || _kkOn
    readonly property bool _anyPanelEnabled: bigPictureMode || _tkOn || _twOn || _ytOn || _kkOn

    visible: alwaysVisible || (_anyPanelEnabled && _visibilityWide)
    property bool _visibilityWide: true

    function _tkEvVerb(kind) {
        if (!api) return ""
        api.refreshCounter
        if (kind === "follow") return api.loc("connections.tiktok_analytics_follow")
        if (kind === "join") return api.loc("connections.tiktok_analytics_join")
        return api.loc("connections.tiktok_analytics_gift_suffix")
    }

    function _twEvVerb(kind) {
        if (!api) return ""
        api.refreshCounter
        if (kind === "follow") return api.loc("connections.twitch_analytics_follow")
        if (kind === "sub") return api.loc("connections.twitch_analytics_sub")
        if (kind === "cheer") return api.loc("connections.twitch_analytics_cheer")
        return api.loc("connections.twitch_analytics_raid")
    }

    function _ytEvVerb(kind) {
        if (!api) return ""
        api.refreshCounter
        if (kind === "superchat") return api.loc("connections.youtube_analytics_superchat")
        if (kind === "supersticker") return api.loc("connections.youtube_analytics_supersticker")
        if (kind === "member" || kind === "membership") return api.loc("connections.youtube_analytics_member")
        return api.loc("connections.youtube_analytics_chat")
    }

    function _kkEvVerb(kind) {
        if (!api) return ""
        api.refreshCounter
        if (kind === "follow") return api.loc("connections.kick_analytics_follow")
        if (kind === "subscription") return api.loc("connections.kick_analytics_sub")
        if (kind === "gift") return api.loc("connections.kick_analytics_gift_sub")
        if (kind === "kick_gift") return api.loc("connections.kick_analytics_kick_gift")
        return "·"
    }

    readonly property int _minCardW: bigPictureMode ? 200 : (alwaysVisible ? 280 : 360)
    readonly property int _gap: 12
    readonly property int _panelCount: bigPictureMode
        ? 4
        : ((_tkOn ? 1 : 0) + (_ytOn ? 1 : 0) + (_twOn ? 1 : 0) + (_kkOn ? 1 : 0))

    readonly property int _gridCols: {
        if (bigPictureMode)
            return 1
        var n = _panelCount
        var vw = Math.max(1, analyticsFlick.width)
        if (n <= 0)
            return 1
        var maxC = Math.max(1, Math.floor((vw + _gap) / (_minCardW + _gap)))
        var cols = Math.min(n, maxC)
        if (cols === 1 && n > 1)
            return n
        return cols
    }
    readonly property int _gridRows: {
        var n = _panelCount
        if (n <= 0)
            return 1
        return Math.ceil(n / _gridCols)
    }
    readonly property bool _needsHScroll: {
        var n = _panelCount
        if (n <= 0)
            return false
        if (_gridCols < n)
            return false
        var vw = Math.max(1, analyticsFlick.width)
        return (n * _minCardW + (n - 1) * _gap) > vw + 0.5
    }
    readonly property real _cardW: {
        var c = _gridCols
        if (c <= 0)
            return _minCardW
        var vw = Math.max(1, analyticsFlick.width)
        var gapTotal = (c - 1) * _gap
        if (_needsHScroll)
            return _minCardW
        return Math.max(_minCardW, (vw - gapTotal) / c)
    }
    readonly property int _cellCardH: {
        var fh = Math.max(1, analyticsFlick.height)
        var r = _gridRows
        if (bigPictureMode) {
            var share = Math.max(220, Math.floor((fh - Math.max(0, r - 1) * _gap) / Math.max(1, r)))
            return Math.min(share, 340)
        }
        if (fillHeight && r <= 1)
            return Math.max(180, Math.floor(fh))
        if (r <= 1)
            return Math.max(180, Math.floor(fh))
        return Math.max(160, Math.floor((fh - Math.max(0, r - 1) * _gap) / r))
    }
    readonly property bool _needsVScroll: {
        if (!bigPictureMode)
            return false
        var total = analyticsGrid.implicitHeight
        return total > analyticsFlick.height + 1
    }
    readonly property bool _compact: bigPictureMode || _cardW <= 380
    readonly property int _bpEventsH: 96

    component StatMini: Rectangle {
        id: st
        property string cap: ""
        property int val: 0
        property int capPx: 11
        property int valPx: 18
        implicitHeight: capCol.implicitHeight + 16
        radius: 10
        color: ConnTheme.fieldBg
        border.width: 1
        border.color: ConnTheme.cardEdge
        Column {
            id: capCol
            anchors.centerIn: parent
            width: parent.width - 12
            spacing: 2
            Text {
                width: parent.width
                text: st.cap
                color: ConnTheme.muted
                font.pixelSize: st.capPx
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
            Text {
                width: parent.width
                text: String(st.val)
                color: ConnTheme.ink
                font.pixelSize: st.valPx
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    component AnalyticsCard: Rectangle {
        id: card
        property color topLine: "#334155"
        radius: 16
        color: ConnTheme.cardBase
        border.width: 1
        border.color: ConnTheme.cardEdge
        clip: true
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 }
            height: 1
            color: card.topLine
            opacity: 0.35
        }
    }

    component EventFeedRow: Item {
        id: rowRoot
        property string timeText: ""
        property string bodyText: ""
        property string iconGlyph: "→"
        property string iconUrl: ""
        property color iconColor: ConnTheme.tkHi

        implicitHeight: 30
        height: implicitHeight

        Row {
            id: row
            anchors.fill: parent
            spacing: 8

            Text {
                width: 54
                height: rowRoot.height
                verticalAlignment: Text.AlignVCenter
                text: rowRoot.timeText
                color: ConnTheme.muted
                font.pixelSize: 11
                font.family: "Consolas, Cascadia Mono, monospace"
                elide: Text.ElideRight
            }

            Item {
                width: 20
                height: rowRoot.height

                Image {
                    anchors.centerIn: parent
                    visible: rowRoot.iconUrl.length > 0
                    width: 18
                    height: 18
                    source: rowRoot.iconUrl
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                }

                Text {
                    anchors.centerIn: parent
                    visible: rowRoot.iconUrl.length === 0
                    text: rowRoot.iconGlyph
                    font.pixelSize: 13
                    color: rowRoot.iconColor
                }
            }

            Text {
                width: Math.max(0, rowRoot.width - 54 - 8 - 20 - 8)
                height: rowRoot.height
                verticalAlignment: Text.AlignVCenter
                text: rowRoot.bodyText
                color: ConnTheme.ink
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }
    }

    Flickable {
        id: analyticsFlick
        anchors.fill: parent
        anchors.margins: bigPictureMode ? 8 : 14
        anchors.bottomMargin: footerReserve
        clip: true
        interactive: analyticsSlot.bigPictureMode
            ? analyticsSlot._needsVScroll
            : analyticsSlot._needsHScroll
        flickableDirection: analyticsSlot.bigPictureMode
            ? Flickable.VerticalFlick
            : Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.horizontal: ScrollBar {
            policy: analyticsSlot.bigPictureMode ? ScrollBar.AlwaysOff : ScrollBar.AsNeeded
        }
        ScrollBar.vertical: ScrollBar {
            policy: analyticsSlot.bigPictureMode ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        }

        contentWidth: analyticsSlot.bigPictureMode ? width : contentRoot.implicitWidth
        contentHeight: analyticsSlot.bigPictureMode ? contentRoot.implicitHeight : height

        function _snapToNearestCard() {
            if (analyticsSlot.bigPictureMode || !analyticsSlot._needsHScroll)
                return
            var step = analyticsSlot._minCardW + analyticsSlot._gap
            if (step <= 0) return
            var target = Math.round(contentX / step) * step
            target = Math.max(0, Math.min(target, contentWidth - width))
            snapAnim.to = target
            snapAnim.restart()
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
            width: analyticsSlot.bigPictureMode ? analyticsFlick.width : implicitWidth
            height: analyticsSlot.bigPictureMode ? implicitHeight : parent.height
            implicitWidth: analyticsSlot.bigPictureMode
                ? analyticsFlick.width
                : Math.max(
                    analyticsFlick.width,
                    analyticsSlot._gridCols * analyticsSlot._minCardW
                    + Math.max(0, analyticsSlot._gridCols - 1) * analyticsSlot._gap)
            implicitHeight: analyticsSlot.bigPictureMode
                ? analyticsGrid.implicitHeight
                : parent.height

            GridLayout {
                id: analyticsGrid
                width: parent.width
                columns: analyticsSlot._gridCols
                columnSpacing: analyticsSlot._gap
                rowSpacing: analyticsSlot._gap

                AnalyticsCard {
                    id: tkCard
                    visible: analyticsSlot._tkShow
                    Layout.fillWidth: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: tkCardBody.implicitHeight + 28
                    implicitHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.preferredHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.maximumHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    topLine: "#103044"

                    ColumnLayout {
                        id: tkCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 14
                        height: analyticsSlot.bigPictureMode ? implicitHeight : (parent.height - 28)
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: ConnTheme.tkBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../../assets/tiktok.svg")
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
                                color: ConnTheme.tkHi
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
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: analyticsSlot._compact ? 2 : 4
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_online") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_total") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_gifts") }
                                val: tiktokAnalytics ? tiktokAnalytics.giftUnitsTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_diamonds") }
                                val: tiktokAnalytics ? tiktokAnalytics.diamondsTotal : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_activity") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            Layout.fillHeight: !analyticsSlot.bigPictureMode
                            Layout.preferredHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 0
                            Layout.minimumHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 120
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                                model: tiktokAnalytics ? tiktokAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconUrl: (model.iconUrl && model.iconUrl.length) ? model.iconUrl : ""
                                    iconGlyph: (model.eventKind === "gift") ? "🎁" : (model.eventKind === "follow" ? "＋" : "→")
                                    iconColor: ConnTheme.tkHi
                                    bodyText: {
                                        var u = model.userName || ""
                                        var verb = analyticsSlot._tkEvVerb(model.eventKind)
                                        if (model.eventKind === "gift") {
                                            var nm = model.detailText || ""
                                            var c = model.giftCount || 1
                                            return u + " · " + nm + " × " + String(c)
                                        }
                                        return u + " · " + verb
                                    }
                                }
                            }
                        }
                    }
                }

                AnalyticsCard {
                    id: ytCard
                    visible: analyticsSlot._ytShow
                    Layout.fillWidth: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: ytCardBody.implicitHeight + 28
                    implicitHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.preferredHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.maximumHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    topLine: "#4a1d1d"

                    ColumnLayout {
                        id: ytCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 14
                        height: analyticsSlot.bigPictureMode ? implicitHeight : (parent.height - 28)
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: ConnTheme.ytBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../../assets/youtube.svg")
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
                                color: ConnTheme.ytHi
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
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: analyticsSlot._compact ? 2 : 3
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_viewers") }
                                val: youtubeAnalytics ? youtubeAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_peak") }
                                val: youtubeAnalytics ? youtubeAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_messages") }
                                val: youtubeAnalytics ? youtubeAnalytics.messagesSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_unique") }
                                val: youtubeAnalytics ? youtubeAnalytics.uniqueChattersSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_superchats") }
                                val: youtubeAnalytics ? youtubeAnalytics.superChatsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_memberships") }
                                val: youtubeAnalytics ? youtubeAnalytics.membershipsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_activity") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            Layout.fillHeight: !analyticsSlot.bigPictureMode
                            Layout.preferredHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 0
                            Layout.minimumHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 120
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                                model: youtubeAnalytics ? youtubeAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconGlyph: (model.eventKind === "superchat" || model.eventKind === "supersticker") ? "💬" : ((model.eventKind === "member") ? "⭐" : "▶")
                                    iconColor: ConnTheme.ytHi
                                    bodyText: {
                                        var u = model.userName || ""
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._ytEvVerb(kind)
                                        var d = model.detailText || ""
                                        if (kind === "chat") return u + " · " + d
                                        if (d.length) return u + " · " + verb + " · " + d
                                        return u + " · " + verb
                                    }
                                }
                            }
                        }
                    }
                }

                AnalyticsCard {
                    id: twCard
                    visible: analyticsSlot._twShow
                    Layout.fillWidth: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: twCardBody.implicitHeight + 28
                    implicitHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.preferredHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.maximumHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    topLine: "#4c1d95"

                    ColumnLayout {
                        id: twCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 14
                        height: analyticsSlot.bigPictureMode ? implicitHeight : (parent.height - 28)
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: ConnTheme.twBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../../assets/twitch.svg")
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
                                color: ConnTheme.twHi
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
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: analyticsSlot._compact ? 2 : 3
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_viewers") }
                                val: twitchAnalytics ? twitchAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_peak") }
                                val: twitchAnalytics ? twitchAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_follows") }
                                val: twitchAnalytics ? twitchAnalytics.followsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_subs") }
                                val: twitchAnalytics ? twitchAnalytics.subsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_bits") }
                                val: twitchAnalytics ? twitchAnalytics.bitsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_raids") }
                                val: twitchAnalytics ? twitchAnalytics.raidsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_activity") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            Layout.fillHeight: !analyticsSlot.bigPictureMode
                            Layout.preferredHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 0
                            Layout.minimumHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 120
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                                model: twitchAnalytics ? twitchAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconGlyph: (model.eventKind === "sub") ? "⭐" : ((model.eventKind === "cheer") ? "💠" : ((model.eventKind === "raid") ? "⚡" : "＋"))
                                    iconColor: ConnTheme.twHi
                                    bodyText: {
                                        var u = model.userName || ""
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._twEvVerb(kind)
                                        var c = model.countValue || 0
                                        var d = model.detailText || ""
                                        if (kind === "cheer") return u + " · " + verb + " × " + String(c)
                                        if (kind === "raid") return u + " · " + verb + " · " + String(c)
                                        if (kind === "sub") return u + " · " + verb + (d.length ? (" · " + d) : "")
                                        return u + " · " + verb
                                    }
                                }
                            }
                        }
                    }
                }

                AnalyticsCard {
                    id: kkCard
                    visible: analyticsSlot._kkShow
                    Layout.fillWidth: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: kkCardBody.implicitHeight + 28
                    implicitHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.preferredHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    Layout.maximumHeight: analyticsSlot.bigPictureMode ? _contentH : analyticsSlot._cellCardH
                    topLine: "#166534"

                    ColumnLayout {
                        id: kkCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 14
                        height: analyticsSlot.bigPictureMode ? implicitHeight : (parent.height - 28)
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { width: 3; height: 24; radius: 1; color: ConnTheme.kkBar; Layout.alignment: Qt.AlignVCenter }
                            Image {
                                source: Qt.resolvedUrl("../../assets/kick.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 26
                                height: 26
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_title") }
                                color: ConnTheme.kkHi
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return true; api.refreshCounter; return !api.kickEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_offline") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: analyticsSlot._compact ? 2 : 4
                            columnSpacing: 8
                            rowSpacing: 8
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }

                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_viewers") }
                                val: kickAnalytics ? kickAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_peak") }
                                val: kickAnalytics ? kickAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_messages") }
                                val: kickAnalytics ? kickAnalytics.messagesSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_follows") }
                                val: kickAnalytics ? kickAnalytics.followsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_subs") }
                                val: kickAnalytics ? kickAnalytics.subscriptionsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_gift_subs") }
                                val: kickAnalytics ? kickAnalytics.giftSubsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: analyticsSlot._compact ? 10 : 11
                                valPx: analyticsSlot._compact ? 16 : 18
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_kicks") }
                                val: kickAnalytics ? kickAnalytics.kicksSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_activity") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            Layout.fillHeight: !analyticsSlot.bigPictureMode
                            Layout.preferredHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 0
                            Layout.minimumHeight: analyticsSlot.bigPictureMode ? analyticsSlot._bpEventsH : 120
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                                model: kickAnalytics ? kickAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconGlyph: (model.eventKind === "subscription") ? "⭐" : ((model.eventKind === "kick_gift") ? "💰" : ((model.eventKind === "gift") ? "🎁" : "＋"))
                                    iconColor: ConnTheme.kkHi
                                    bodyText: {
                                        var u = model.userName || ""
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._kkEvVerb(kind)
                                        var c = model.countValue || 0
                                        var d = model.detailText || ""
                                        if (kind === "kick_gift") return u + " · " + verb + " × " + String(c)
                                        if (kind === "gift") return u + " · " + verb + (d.length ? (" · " + d) : "")
                                        if (kind === "subscription") return u + " · " + verb + (d.length ? (" · " + d) : "")
                                        return u + " · " + verb
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
