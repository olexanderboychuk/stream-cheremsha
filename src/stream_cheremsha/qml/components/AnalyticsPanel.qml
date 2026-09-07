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

    function _loc(key) {
        if (!api) return ""
        api.refreshCounter
        return api.loc(key)
    }

    readonly property int _minCardW: bigPictureMode ? 200 : (alwaysVisible ? 280 : 300)
    readonly property int _gap: 12
    // Order: TikTok + Twitch first so the reference pair shares the first row.
    readonly property int _panelCount: bigPictureMode
        ? 4
        : ((_tkOn ? 1 : 0) + (_twOn ? 1 : 0) + (_ytOn ? 1 : 0) + (_kkOn ? 1 : 0))

    readonly property int _gridCols: {
        if (bigPictureMode)
            return 1
        var n = _panelCount
        var vw = Math.max(1, analyticsFlick.width)
        if (n <= 0)
            return 1
        if (n === 1)
            return 1
        // Reference: at most 2 cards per row (each ~half width).
        var maxC = Math.max(1, Math.floor((vw + _gap) / (_minCardW + _gap)))
        if (maxC >= 2)
            return Math.min(2, n)
        // Too narrow: keep side-by-side via horizontal scroll.
        return n
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
    readonly property int _eventsH: bigPictureMode ? _bpEventsH : 264

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

    function _fmtCompact(n) {
        var v = Math.floor(Number(n) || 0)
        if (v >= 1000000) {
            var m = v / 1000000
            var ms = (Math.round(m * 10) / 10).toString().replace(".", ".")
            return ms + "M"
        }
        if (v >= 10000) {
            var k = v / 1000
            var ks = (Math.round(k * 10) / 10).toString()
            return ks + "K"
        }
        return _fmtNum(v)
    }

    function _esc(s) {
        return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    }

    function _avatarColor(name) {
        var palette = ["#1e293b", "#27272a", "#172554", "#3b0764", "#082f49", "#052e16", "#451a03", "#1c1917"]
        var h = 0
        var s = String(name || "?")
        for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 997
        return palette[h % palette.length]
    }

    function _kindColor(kind) {
        if (kind === "gift" || kind === "kick_gift" || kind === "cheer") return "#ec4899"
        if (kind === "follow") return "#22c55e"
        if (kind === "sub" || kind === "subscription" || kind === "gift") return "#a78bfa"
        if (kind === "raid") return "#f59e0b"
        if (kind === "join") return "#22d3ee"
        if (kind === "superchat" || kind === "supersticker") return "#facc15"
        if (kind === "member" || kind === "membership") return "#4ade80"
        return "#64748b"
    }

    component MetricTile: Rectangle {
        id: mt
        property string cap: ""
        property string valText: "0"
        property string iconSrc: ""
        implicitHeight: 64
        radius: 10
        color: ConnTheme.fieldBg
        border.width: 1
        border.color: ConnTheme.cardEdge
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: 10
            Image {
                source: mt.iconSrc
                sourceSize: Qt.size(48, 48)
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                Layout.alignment: Qt.AlignVCenter
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: true
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 2
                Text {
                    Layout.fillWidth: true
                    text: mt.cap
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: mt.valText
                    color: ConnTheme.ink
                    font.pixelSize: ConnTheme.metricPx
                    font.bold: true
                    font.letterSpacing: -0.3
                    elide: Text.ElideRight
                }
            }
        }
    }

    component OnlinePill: Rectangle {
        property bool online: false
        implicitWidth: pillTxt.implicitWidth + 16
        implicitHeight: 22
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

    component EventsHeader: RowLayout {
        property string titleText: ""
        property string filterText: ""
        Layout.fillWidth: true
        spacing: 8
        Text {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            text: parent.titleText
            color: ConnTheme.ink
            font.pixelSize: 13
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Rectangle {
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: filterTxt.implicitWidth + 26
            implicitHeight: 26
            radius: 7
            color: filterTap.containsMouse ? "#1c263c" : "#141a24"
            border.width: 1
            border.color: filterTap.containsMouse ? "#3a455c" : ConnTheme.cardEdge
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }
            RowLayout {
                anchors.centerIn: parent
                spacing: 6
                Text {
                    id: filterTxt
                    text: parent.parent.parent.filterText
                    color: ConnTheme.muted
                    font.pixelSize: 11
                    Layout.alignment: Qt.AlignVCenter
                }
                Item {
                    width: 10
                    height: 7
                    Layout.alignment: Qt.AlignVCenter
                    Rectangle {
                        width: 7
                        height: 1.6
                        radius: 1
                        color: ConnTheme.muted
                        anchors.centerIn: parent
                        anchors.horizontalCenterOffset: -2
                        rotation: 45
                    }
                    Rectangle {
                        width: 7
                        height: 1.6
                        radius: 1
                        color: ConnTheme.muted
                        anchors.centerIn: parent
                        anchors.horizontalCenterOffset: 2
                        rotation: -45
                    }
                }
            }
            MouseArea {
                id: filterTap
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
            }
        }
    }

    component EventFeedRow: Item {
        id: rowRoot
        property string timeText: ""
        property string userName: ""
        property string htmlBody: ""
        property string eventKind: ""
        property string platformIcon: ""
        property string avatarUrl: ""
        property string giftIcon: ""

        function _isHttp(u) {
            return u.length > 0 && (u.indexOf("https://") === 0 || u.indexOf("http://") === 0)
        }

        // Gifts show the gift icon (live iconUrl, catalog fallback in backend);
        // otherwise the real user avatar; initial circle as the last resort.
        readonly property string _photoSource: {
            if (rowRoot.eventKind === "gift" || rowRoot.eventKind === "kick_gift") {
                if (rowRoot._isHttp(rowRoot.giftIcon)) return rowRoot.giftIcon
            }
            if (rowRoot._isHttp(rowRoot.avatarUrl)) return rowRoot.avatarUrl
            if (rowRoot._isHttp(rowRoot.giftIcon)) return rowRoot.giftIcon
            return ""
        }

        implicitHeight: ConnTheme.eventRowH
        height: implicitHeight

        RowLayout {
            anchors.fill: parent
            anchors.topMargin: 7
            anchors.bottomMargin: 7
            spacing: 10

            Item {
                Layout.preferredWidth: 30
                Layout.preferredHeight: 30
                Layout.alignment: Qt.AlignVCenter
                Rectangle {
                    id: ava
                    anchors.fill: parent
                    radius: 15
                    visible: !photoCell.photoOk
                    color: analyticsSlot._avatarColor(rowRoot.userName)
                    border.width: 1
                    border.color: "#2b3446"
                    Text {
                        anchors.centerIn: parent
                        text: (rowRoot.userName || "?").charAt(0).toUpperCase()
                        color: "#e8eaed"
                        font.pixelSize: 13
                        font.bold: true
                    }
                }
                // Circular photo crop via Canvas2D (QtQuick core only —
                // no extra modules/engines). Repaints only on source change.
                Item {
                    id: photoCell
                    anchors.fill: parent
                    property bool photoOk: false
                    visible: photoOk
                    Canvas {
                        id: photoCanvas
                        anchors.fill: parent
                        antialiasing: true
                        renderStrategy: Canvas.Cooperative
                        property string imgUrl: rowRoot._photoSource
                        property string loadedUrl: ""
                        onImgUrlChanged: {
                            photoCell.photoOk = false
                            if (loadedUrl.length > 0 && loadedUrl !== imgUrl) {
                                unloadImage(loadedUrl)
                                loadedUrl = ""
                            }
                            if (imgUrl.length > 0) {
                                loadedUrl = imgUrl
                                loadImage(imgUrl)
                            } else {
                                requestPaint()
                            }
                        }
                        onImageLoaded: {
                            photoCell.photoOk = true
                            requestPaint()
                        }
                        onPaint: {
                            var ctx = getContext("2d")
                            var s = Math.min(width, height)
                            ctx.clearRect(0, 0, width, height)
                            if (!photoCell.photoOk) return
                            var url = photoCanvas.imgUrl
                            if (!isImageLoaded(url)) return
                            ctx.save()
                            ctx.beginPath()
                            ctx.arc(s / 2, s / 2, s / 2 - 0.5, 0, Math.PI * 2, false)
                            ctx.clip()
                            ctx.drawImage(url, 0, 0, s, s)
                            ctx.restore()
                        }
                        Component.onCompleted: {
                            if (imgUrl.length > 0) loadImage(imgUrl)
                        }
                    }
                }
                Rectangle {
                    width: 13
                    height: 13
                    radius: 7
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: -2
                    anchors.bottomMargin: -2
                    color: analyticsSlot._kindColor(rowRoot.eventKind)
                    border.width: 2
                    border.color: ConnTheme.cardBase
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                text: rowRoot.htmlBody
                textFormat: Text.RichText
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
                Layout.preferredWidth: 13
                Layout.preferredHeight: 13
                Layout.alignment: Qt.AlignVCenter
                source: rowRoot.platformIcon
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: true
                opacity: 0.6
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: "#1a2230"
            opacity: 0.7
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

                // ---- TikTok (reference: left card) ----
                AnalyticsCard {
                    id: tkCard
                    visible: analyticsSlot._tkShow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: tkCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    accent: ConnTheme.tkBar

                    ColumnLayout {
                        id: tkCardBody
                        anchors.fill: parent
                        anchors.margins: ConnTheme.cardPad
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/tiktok.svg")
                                sourceSize: Qt.size(48, 48)
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Layout.alignment: Qt.AlignVCenter
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_title") }
                                color: ConnTheme.ink
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
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
                            columns: 2
                            columnSpacing: ConnTheme.metricGap
                            rowSpacing: ConnTheme.metricGap
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }

                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/users-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_online") }
                                valText: analyticsSlot._fmtNum(tiktokAnalytics ? tiktokAnalytics.onlineViewersCurrent : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/eye-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_total") }
                                valText: analyticsSlot._fmtNum(tiktokAnalytics ? tiktokAnalytics.onlineViewersTotal : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/gift-pink.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_gifts") }
                                valText: analyticsSlot._fmtNum(tiktokAnalytics ? tiktokAnalytics.giftUnitsTotal : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/diamond-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.tiktok_analytics_diamonds") }
                                valText: analyticsSlot._fmtCompact(tiktokAnalytics ? tiktokAnalytics.diamondsTotal : 0)
                            }
                        }

                        EventsHeader {
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            titleText: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            filterText: analyticsSlot._loc("connections.all_events")
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            Layout.preferredHeight: analyticsSlot._eventsH
                            visible: { if (!api) return false; api.refreshCounter; return api.tiktokEnabled() }
                            radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: "#1a2230"
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !tkEvList.count
                            }

                            ListView {
                                id: tkEvList
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 2
                                anchors.bottomMargin: 2
                                spacing: 0
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                // Subtle entrance for new events (opacity only —
                                // cheap, no layout animation).
                                add: Transition {
                                    NumberAnimation {
                                        property: "opacity"
                                        from: 0
                                        to: 1
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                displaced: Transition {
                                    NumberAnimation {
                                        properties: "x,y"
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                model: tiktokAnalytics ? tiktokAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width - 20 : implicitWidth
                                    timeText: model.timeText || ""
                                    userName: model.userName || "?"
                                    eventKind: model.eventKind || ""
                                    avatarUrl: model.avatarUrl || ""
                                    giftIcon: model.iconUrl || ""
                                    platformIcon: Qt.resolvedUrl("../../assets/tiktok.svg")
                                    htmlBody: {
                                        var u = analyticsSlot._esc(model.userName || "?")
                                        var verb = analyticsSlot._tkEvVerb(model.eventKind)
                                        var kind = model.eventKind || ""
                                        if (kind === "gift") {
                                            var nm = analyticsSlot._esc(model.detailText || "")
                                            var c = model.giftCount || 1
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> × " + c + " </font>"
                                                + "<font color=\"#f472b6\">" + nm + "</font>"
                                        }
                                        return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                            + "<font color=\"#8b95a5\"> " + analyticsSlot._esc(verb) + "</font>"
                                    }
                                }
                            }
                        }

                        ConnPillButton {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            text: analyticsSlot._loc("connections.open_full_log") + "  →"
                            pillFontSize: 12
                            colRest: "#151b27"
                            colHover: "#1c263c"
                            colPress: "#232e44"
                        }
                    }
                }

                // ---- Twitch (reference: right card) ----
                AnalyticsCard {
                    id: twCard
                    visible: analyticsSlot._twShow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: twCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    accent: ConnTheme.twBar

                    ColumnLayout {
                        id: twCardBody
                        anchors.fill: parent
                        anchors.margins: ConnTheme.cardPad
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/twitch.svg")
                                sourceSize: Qt.size(48, 48)
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Layout.alignment: Qt.AlignVCenter
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_title") }
                                color: ConnTheme.ink
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
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
                            columns: 2
                            columnSpacing: ConnTheme.metricGap
                            rowSpacing: ConnTheme.metricGap
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }

                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/users-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_viewers") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.viewersCurrent : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/peak-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_peak") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.viewersPeak : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/heart-pink.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_follows") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.followsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/star-yellow.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_subs") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.subsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/bits-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_bits") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.bitsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/raid-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.twitch_analytics_raids") }
                                valText: analyticsSlot._fmtNum(twitchAnalytics ? twitchAnalytics.raidsSession : 0)
                            }
                        }

                        EventsHeader {
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            titleText: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            filterText: analyticsSlot._loc("connections.all_events")
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            Layout.preferredHeight: analyticsSlot._eventsH
                            visible: { if (!api) return false; api.refreshCounter; return api.twitchRunning() }
                            radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: "#1a2230"
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !twEvList.count
                            }

                            ListView {
                                id: twEvList
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 2
                                anchors.bottomMargin: 2
                                spacing: 0
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                // Subtle entrance for new events (opacity only —
                                // cheap, no layout animation).
                                add: Transition {
                                    NumberAnimation {
                                        property: "opacity"
                                        from: 0
                                        to: 1
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                displaced: Transition {
                                    NumberAnimation {
                                        properties: "x,y"
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                model: twitchAnalytics ? twitchAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width - 20 : implicitWidth
                                    timeText: model.timeText || ""
                                    userName: model.userName || "?"
                                    eventKind: model.eventKind || ""
                                    avatarUrl: model.avatarUrl || ""
                                    platformIcon: Qt.resolvedUrl("../../assets/twitch.svg")
                                    htmlBody: {
                                        var u = analyticsSlot._esc(model.userName || "?")
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._esc(analyticsSlot._twEvVerb(kind))
                                        var c = model.countValue || 0
                                        var d = analyticsSlot._esc(model.detailText || "")
                                        if (kind === "cheer")
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + " </font>"
                                                + "<font color=\"#c084fc\">" + c + " Bits</font>"
                                        if (kind === "raid")
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + " </font>"
                                                + "<font color=\"#c084fc\">(viewers: " + c + ")</font>"
                                        if (kind === "sub")
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + (d.length ? " (" + d + ")" : "") + "</font>"
                                        return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                            + "<font color=\"#8b95a5\"> " + verb + "</font>"
                                    }
                                }
                            }
                        }

                        ConnPillButton {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            text: analyticsSlot._loc("connections.open_full_log") + "  →"
                            pillFontSize: 12
                            colRest: "#151b27"
                            colHover: "#1c263c"
                            colPress: "#232e44"
                        }
                    }
                }

                // ---- YouTube ----
                AnalyticsCard {
                    id: ytCard
                    visible: analyticsSlot._ytShow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: ytCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    accent: ConnTheme.ytBar

                    ColumnLayout {
                        id: ytCardBody
                        anchors.fill: parent
                        anchors.margins: ConnTheme.cardPad
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/youtube.svg")
                                sourceSize: Qt.size(48, 48)
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Layout.alignment: Qt.AlignVCenter
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_title") }
                                color: ConnTheme.ink
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
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
                            columns: 2
                            columnSpacing: ConnTheme.metricGap
                            rowSpacing: ConnTheme.metricGap
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }

                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/users-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_viewers") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.viewersCurrent : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/peak-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_peak") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.viewersPeak : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/eye-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_messages") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.messagesSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/users-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_unique") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.uniqueChattersSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/star-yellow.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_superchats") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.superChatsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/heart-pink.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.youtube_analytics_memberships") }
                                valText: analyticsSlot._fmtNum(youtubeAnalytics ? youtubeAnalytics.membershipsSession : 0)
                            }
                        }

                        EventsHeader {
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            titleText: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            filterText: analyticsSlot._loc("connections.all_events")
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            Layout.preferredHeight: analyticsSlot._eventsH
                            visible: { if (!api) return false; api.refreshCounter; return api.youtubeRunning() }
                            radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: "#1a2230"
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !ytEvList.count
                            }

                            ListView {
                                id: ytEvList
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 2
                                anchors.bottomMargin: 2
                                spacing: 0
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                // Subtle entrance for new events (opacity only —
                                // cheap, no layout animation).
                                add: Transition {
                                    NumberAnimation {
                                        property: "opacity"
                                        from: 0
                                        to: 1
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                displaced: Transition {
                                    NumberAnimation {
                                        properties: "x,y"
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                model: youtubeAnalytics ? youtubeAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width - 20 : implicitWidth
                                    timeText: model.timeText || ""
                                    userName: model.userName || "?"
                                    eventKind: model.eventKind || ""
                                    avatarUrl: model.avatarUrl || ""
                                    platformIcon: Qt.resolvedUrl("../../assets/youtube.svg")
                                    htmlBody: {
                                        var u = analyticsSlot._esc(model.userName || "?")
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._esc(analyticsSlot._ytEvVerb(kind))
                                        var d = analyticsSlot._esc(model.detailText || "")
                                        if (kind === "chat")
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\">: " + d + "</font>"
                                        if (d.length)
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + " </font>"
                                                + "<font color=\"#f87171\">" + d + "</font>"
                                        return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                            + "<font color=\"#8b95a5\"> " + verb + "</font>"
                                    }
                                }
                            }
                        }

                        ConnPillButton {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            text: analyticsSlot._loc("connections.open_full_log") + "  →"
                            pillFontSize: 12
                            colRest: "#151b27"
                            colHover: "#1c263c"
                            colPress: "#232e44"
                        }
                    }
                }

                // ---- Kick ----
                AnalyticsCard {
                    id: kkCard
                    visible: analyticsSlot._kkShow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: analyticsSlot._minCardW
                    readonly property int _contentH: kkCardBody.implicitHeight + 24
                    implicitHeight: _contentH
                    Layout.preferredHeight: _contentH
                    accent: ConnTheme.kkBar

                    ColumnLayout {
                        id: kkCardBody
                        anchors.fill: parent
                        anchors.margins: ConnTheme.cardPad
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Image {
                                source: Qt.resolvedUrl("../../assets/kick.svg")
                                sourceSize: Qt.size(48, 48)
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                Layout.alignment: Qt.AlignVCenter
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                            }
                            Text {
                                text: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_title") }
                                color: ConnTheme.ink
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
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
                            columns: 2
                            columnSpacing: ConnTheme.metricGap
                            rowSpacing: ConnTheme.metricGap
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }

                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/users-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_viewers") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.viewersCurrent : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/peak-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_peak") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.viewersPeak : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/eye-cyan.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_messages") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.messagesSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/heart-pink.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_follows") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.followsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/star-yellow.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_subs") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.subscriptionsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/gift-pink.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_gift_subs") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.giftSubsSession : 0)
                            }
                            MetricTile {
                                Layout.fillWidth: true
                                Layout.columnSpan: 2
                                iconSrc: Qt.resolvedUrl("../../assets/metrics/bits-purple.svg")
                                cap: { if (!api) return ""; api.refreshCounter; return api.loc("connections.kick_analytics_kicks") }
                                valText: analyticsSlot._fmtNum(kickAnalytics ? kickAnalytics.kicksSession : 0)
                            }
                        }

                        EventsHeader {
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            titleText: { if (!api) return ""; api.refreshCounter; return api.loc("connections.events_recent") }
                            filterText: analyticsSlot._loc("connections.all_events")
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            Layout.preferredHeight: analyticsSlot._eventsH
                            visible: { if (!api) return false; api.refreshCounter; return api.kickEnabled() }
                            radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: "#1a2230"
                            clip: true

                            EventsEmpty {
                                anchors.fill: parent
                                visible: !kkEvList.count
                            }

                            ListView {
                                id: kkEvList
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 2
                                anchors.bottomMargin: 2
                                spacing: 0
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                visible: count > 0
                                // Subtle entrance for new events (opacity only —
                                // cheap, no layout animation).
                                add: Transition {
                                    NumberAnimation {
                                        property: "opacity"
                                        from: 0
                                        to: 1
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                displaced: Transition {
                                    NumberAnimation {
                                        properties: "x,y"
                                        duration: 160
                                        easing.type: Easing.OutCubic
                                    }
                                }
                                model: kickAnalytics ? kickAnalytics.feedModel : null

                                delegate: EventFeedRow {
                                    width: ListView.view ? ListView.view.width - 20 : implicitWidth
                                    timeText: model.timeText || ""
                                    userName: model.userName || "?"
                                    eventKind: model.eventKind || ""
                                    avatarUrl: model.avatarUrl || ""
                                    platformIcon: Qt.resolvedUrl("../../assets/kick.svg")
                                    htmlBody: {
                                        var u = analyticsSlot._esc(model.userName || "?")
                                        var kind = model.eventKind || ""
                                        var verb = analyticsSlot._esc(analyticsSlot._kkEvVerb(kind))
                                        var c = model.countValue || 0
                                        var d = analyticsSlot._esc(model.detailText || "")
                                        if (kind === "kick_gift")
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + " </font>"
                                                + "<font color=\"#4ade80\">× " + c + "</font>"
                                        if (d.length)
                                            return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                                + "<font color=\"#8b95a5\"> " + verb + " </font>"
                                                + "<font color=\"#4ade80\">" + d + "</font>"
                                        return "<b><font color=\"#e8eaed\">" + u + "</font></b>"
                                            + "<font color=\"#8b95a5\"> " + verb + "</font>"
                                    }
                                }
                            }
                        }

                        ConnPillButton {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            text: analyticsSlot._loc("connections.open_full_log") + "  →"
                            pillFontSize: 12
                            colRest: "#151b27"
                            colHover: "#1c263c"
                            colPress: "#232e44"
                        }
                    }
                }
            }
        }
    }
}
