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
        // Content-sized cards — do not stretch empty event areas to fill the viewport.
        return -1
    }
    readonly property bool _needsVScroll: {
        var total = analyticsGrid.implicitHeight
        return total > analyticsFlick.height + 1
    }
    readonly property bool _compact: bigPictureMode || _cardW <= 380
    readonly property int _bpEventsH: 96
    readonly property int _eventsH: bigPictureMode ? _bpEventsH : 280

    function _fmtNum(n) {
        var v = Math.floor(Number(n) || 0)
        var s = String(v)
        var out = ""
        while (s.length > 3) {
            out = " " + s.slice(-3) + out
            s = s.slice(0, -3)
        }
        return s + out
    }

    component StatMini: Rectangle {
        id: st
        property string cap: ""
        property int val: 0
        property int capPx: 10
        property int valPx: 22
        implicitHeight: 56
        radius: 10
        color: ConnTheme.fieldBg
        border.width: 1
        border.color: ConnTheme.cardEdge
        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 2
            Text {
                width: parent.width
                text: st.cap
                color: ConnTheme.muted
                font.pixelSize: st.capPx
                font.weight: Font.Medium
                font.letterSpacing: 0.3
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: analyticsSlot._fmtNum(st.val)
                color: ConnTheme.ink
                font.pixelSize: st.valPx
                font.bold: true
                font.letterSpacing: -0.3
            }
        }
    }

    component OnlinePill: Rectangle {
        property bool online: false
        implicitWidth: pillTxt.implicitWidth + 16
        implicitHeight: 20
        radius: 999
        color: online ? "#0f2a1c" : "#161b24"
        border.width: 1
        border.color: online ? "#1a3d2a" : "#252b38"
        Row {
            anchors.centerIn: parent
            spacing: 5
            Rectangle {
                width: 6
                height: 6
                radius: 3
                color: online ? "#22c55e" : "#64748b"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                id: pillTxt
                text: {
                    if (!api) return ""
                    api.refreshCounter
                    return online
                        ? api.loc("connections.analytics_online_pill")
                        : api.loc("connections.status_disabled")
                }
                color: online ? "#86efac" : "#94a3b8"
                font.pixelSize: 10
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    component AnalyticsCard: Rectangle {
        id: card
        property color accent: ConnTheme.tkBar
        radius: ConnTheme.cardRadius
        color: ConnTheme.cardBase
        border.width: 1
        border.color: cardHover.containsMouse ? Qt.lighter(ConnTheme.cardEdge, 1.25) : ConnTheme.cardEdge
        clip: true
        Behavior on border.color { ColorAnimation { duration: 140 } }

        MouseArea {
            id: cardHover
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
            z: 0
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: 1
            width: 3
            radius: 1
            color: card.accent
            opacity: 0.9
            z: 1
        }
    }

    component EventFeedRow: Item {
        id: rowRoot
        property string timeText: ""
        property string bodyText: ""
        property string iconGlyph: "●"
        property string iconUrl: ""
        property color iconColor: ConnTheme.tkHi
        property string platformIcon: ""

        implicitHeight: 28
        height: implicitHeight

        RowLayout {
            anchors.fill: parent
            spacing: 8

            Rectangle {
                width: 5
                height: 5
                radius: 3
                color: rowRoot.iconColor
                opacity: 0.9
                Layout.alignment: Qt.AlignVCenter
                visible: rowRoot.iconUrl.length === 0
            }

            Image {
                visible: rowRoot.iconUrl.length > 0
                Layout.preferredWidth: 14
                Layout.preferredHeight: 14
                Layout.alignment: Qt.AlignVCenter
                source: rowRoot.iconUrl
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: true
            }

            Text {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                text: rowRoot.bodyText
                color: ConnTheme.ink
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Text {
                Layout.alignment: Qt.AlignVCenter
                text: rowRoot.timeText
                color: ConnTheme.muted
                font.pixelSize: 10
                font.family: "Consolas, Cascadia Mono, monospace"
            }

            Image {
                visible: rowRoot.platformIcon.length > 0
                Layout.preferredWidth: 12
                Layout.preferredHeight: 12
                Layout.alignment: Qt.AlignVCenter
                source: rowRoot.platformIcon
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: true
                opacity: 0.7
            }
        }
    }

    component EventsEmpty: Item {
        Column {
            anchors.centerIn: parent
            spacing: 6
            Rectangle {
                width: 28
                height: 28
                radius: 14
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#141a24"
                border.width: 1
                border.color: ConnTheme.cardEdge
                Text {
                    anchors.centerIn: parent
                    text: "⌁"
                    color: ConnTheme.muted
                    font.pixelSize: 14
                    opacity: 0.65
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: {
                    if (!api) return ""
                    api.refreshCounter
                    return api.loc("connections.events_empty")
                }
                color: ConnTheme.muted
                font.pixelSize: 12
                font.weight: Font.DemiBold
                opacity: 0.85
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: {
                    if (!api) return ""
                    api.refreshCounter
                    return api.loc("connections.events_waiting")
                }
                color: ConnTheme.muted
                font.pixelSize: 10
                opacity: 0.55
            }
        }
    }

    Flickable {
        id: analyticsFlick
        anchors.fill: parent
        anchors.margins: bigPictureMode ? 8 : 0
        anchors.bottomMargin: footerReserve
        clip: true
        interactive: analyticsSlot._needsVScroll || analyticsSlot._needsHScroll
        flickableDirection: {
            if (analyticsSlot._needsVScroll && analyticsSlot._needsHScroll)
                return Flickable.HorizontalAndVerticalFlick
            if (analyticsSlot._needsVScroll)
                return Flickable.VerticalFlick
            return Flickable.HorizontalFlick
        }
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.horizontal: ScrollBar {
            policy: analyticsSlot._needsHScroll ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        }
        ScrollBar.vertical: ScrollBar {
            policy: analyticsSlot._needsVScroll ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        }

        contentWidth: analyticsSlot.bigPictureMode ? width : contentRoot.implicitWidth
        contentHeight: Math.max(height, contentRoot.implicitHeight)

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
            height: implicitHeight
            implicitWidth: analyticsSlot.bigPictureMode
                ? analyticsFlick.width
                : Math.max(
                    analyticsFlick.width,
                    analyticsSlot._gridCols * analyticsSlot._minCardW
                    + Math.max(0, analyticsSlot._gridCols - 1) * analyticsSlot._gap)
            implicitHeight: analyticsGrid.implicitHeight

            GridLayout {
                id: analyticsGrid
                width: parent.width
                columns: analyticsSlot._gridCols
                columnSpacing: analyticsSlot._gap
                rowSpacing: analyticsSlot._gap
                Layout.alignment: Qt.AlignTop

                AnalyticsCard {
                    id: tkCard
                    visible: analyticsSlot._tkShow
                    Layout.fillWidth: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: tkCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    Layout.alignment: Qt.AlignTop
                    accent: ConnTheme.tkBar

                    ColumnLayout {
                        id: tkCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        height: implicitHeight
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/tiktok.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 22
                                height: 22
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_title") }
                                color: ConnTheme.tkHi
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            OnlinePill {
                                online: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                                Layout.alignment: Qt.AlignVCenter
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
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_online") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_total") }
                                val: tiktokAnalytics ? tiktokAnalytics.onlineViewersTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_gifts") }
                                val: tiktokAnalytics ? tiktokAnalytics.giftUnitsTotal : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_diamonds") }
                                val: tiktokAnalytics ? tiktokAnalytics.diamondsTotal : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            Layout.fillHeight: false
                            Layout.preferredHeight: analyticsSlot._eventsH
                            Layout.maximumHeight: analyticsSlot._eventsH
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !tkEvList.count
                            }

                            ListView {
                                id: tkEvList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                model: tiktokAnalytics ? tiktokAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconUrl: (model.iconUrl && model.iconUrl.length) ? model.iconUrl : ""
                                    iconColor: ConnTheme.tkHi
                                    platformIcon: Qt.resolvedUrl("../../assets/tiktok.svg")
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
                    readonly property int _contentH: ytCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    Layout.alignment: Qt.AlignTop
                    accent: ConnTheme.ytBar

                    ColumnLayout {
                        id: ytCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        height: implicitHeight
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/youtube.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 22
                                height: 22
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_title") }
                                color: ConnTheme.ytHi
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            OnlinePill {
                                online: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                                Layout.alignment: Qt.AlignVCenter
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
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_viewers") }
                                val: youtubeAnalytics ? youtubeAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_peak") }
                                val: youtubeAnalytics ? youtubeAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_messages") }
                                val: youtubeAnalytics ? youtubeAnalytics.messagesSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_unique") }
                                val: youtubeAnalytics ? youtubeAnalytics.uniqueChattersSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_superchats") }
                                val: youtubeAnalytics ? youtubeAnalytics.superChatsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_memberships") }
                                val: youtubeAnalytics ? youtubeAnalytics.membershipsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            Layout.fillHeight: false
                            Layout.preferredHeight: analyticsSlot._eventsH
                            Layout.maximumHeight: analyticsSlot._eventsH
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !ytEvList.count
                            }

                            ListView {
                                id: ytEvList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                model: youtubeAnalytics ? youtubeAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconColor: ConnTheme.ytHi
                                    platformIcon: Qt.resolvedUrl("../../assets/youtube.svg")
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
                    readonly property int _contentH: twCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    Layout.alignment: Qt.AlignTop
                    accent: ConnTheme.twBar

                    ColumnLayout {
                        id: twCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        height: implicitHeight
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/twitch.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 22
                                height: 22
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_title") }
                                color: ConnTheme.twHi
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            OnlinePill {
                                online: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                                Layout.alignment: Qt.AlignVCenter
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
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_viewers") }
                                val: twitchAnalytics ? twitchAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_peak") }
                                val: twitchAnalytics ? twitchAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_follows") }
                                val: twitchAnalytics ? twitchAnalytics.followsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_subs") }
                                val: twitchAnalytics ? twitchAnalytics.subsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_bits") }
                                val: twitchAnalytics ? twitchAnalytics.bitsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_raids") }
                                val: twitchAnalytics ? twitchAnalytics.raidsSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            Layout.fillHeight: false
                            Layout.preferredHeight: analyticsSlot._eventsH
                            Layout.maximumHeight: analyticsSlot._eventsH
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !twEvList.count
                            }

                            ListView {
                                id: twEvList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                model: twitchAnalytics ? twitchAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconColor: ConnTheme.twHi
                                    platformIcon: Qt.resolvedUrl("../../assets/twitch.svg")
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
                    readonly property int _contentH: kkCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    Layout.alignment: Qt.AlignTop
                    accent: ConnTheme.kkBar

                    ColumnLayout {
                        id: kkCardBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        height: implicitHeight
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/kick.svg")
                                sourceSize: Qt.size(64, 64)
                                width: 22
                                height: 22
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_title") }
                                color: ConnTheme.kkHi
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            OnlinePill {
                                online: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                                Layout.alignment: Qt.AlignVCenter
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
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_viewers") }
                                val: kickAnalytics ? kickAnalytics.viewersCurrent : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_peak") }
                                val: kickAnalytics ? kickAnalytics.viewersPeak : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_messages") }
                                val: kickAnalytics ? kickAnalytics.messagesSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_follows") }
                                val: kickAnalytics ? kickAnalytics.followsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_subs") }
                                val: kickAnalytics ? kickAnalytics.subscriptionsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_gift_subs") }
                                val: kickAnalytics ? kickAnalytics.giftSubsSession : 0
                            }
                            StatMini {
                                Layout.fillWidth: true
                                capPx: 10
                                valPx: analyticsSlot._compact ? 20 : 22
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_kicks") }
                                val: kickAnalytics ? kickAnalytics.kicksSession : 0
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            color: ConnTheme.muted
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            Layout.fillHeight: false
                            Layout.preferredHeight: analyticsSlot._eventsH
                            Layout.maximumHeight: analyticsSlot._eventsH
                            radius: 10
                            color: ConnTheme.fieldBg
                            border.width: 1
                            border.color: ConnTheme.cardEdge
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !kkEvList.count
                            }

                            ListView {
                                id: kkEvList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                model: kickAnalytics ? kickAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width : implicitWidth
                                    timeText: model.timeText || ""
                                    iconColor: ConnTheme.kkHi
                                    platformIcon: Qt.resolvedUrl("../../assets/kick.svg")
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
