import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import components

Item {
    id: root
    implicitWidth: 800
    implicitHeight: 900

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
    readonly property color secondaryCyan: "#06b6d4"
    readonly property color accentAmber: "#f59e0b"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    component IconButton: Button {
        id: iconBtn
        property string iconSource: ""
        property int size: 32
        property int iconSize: 16
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        implicitWidth: size
        implicitHeight: size
        contentItem: Image {
            source: iconBtn.iconSource || ""
            width: iconBtn.iconSize
            height: iconBtn.iconSize
            anchors.centerIn: parent
        }
        background: Rectangle {
            radius: 6
            color: iconBtn.hovered ? "#1c2434" : "transparent"
            border.width: 1
            border.color: root.cardEdge
        }
    }

    component PillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property color colRest: "#1c2434"
        property color colHover: "#263246"
        property color colPress: "#303a50"
        property color borRest: root.cardEdge
        property color borHover: "#3b4458"
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: pillFontSize
        transformOrigin: Item.Center
        scale: pillCtl.hovered ? 1.02 : 1.0
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        contentItem: Text {
            text: pillCtl.text
            color: root.ink
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
            radius: 8
            color: secondaryBtn.hovered ? "#141c2c" : "#0a0f19"
            border.width: 1
            border.color: secondaryBtn.hovered ? "#3d4a63" : "#232d42"
            Behavior on color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    component StatusPill: Rectangle {
        id: statusPill
        property bool active: false
        signal toggled()
        implicitWidth: pillRow.implicitWidth + 16
        implicitHeight: 26
        radius: 13
        color: statusPill.active ? "#0e2a21" : "#222b3a"
        border.width: 1
        border.color: statusPill.active ? "#1d6a4c" : "#3a4356"
        Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Row {
            id: pillRow
            anchors.centerIn: parent
            spacing: 7
            Rectangle {
                width: 7
                height: 7
                radius: 3.5
                color: statusPill.active ? "#10d9a5" : "#8b95a5"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: statusPill.active ? (dockApi.strings.enabled || "Увімкнено") : (dockApi.strings.disabled || "Вимкнено")
                color: statusPill.active ? "#7ee2b8" : "#9aa4b2"
                font.pixelSize: 12
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: statusPill.toggled()
        }
    }

    component StepBadge: Rectangle {
        property string step: "01"
        implicitWidth: 28
        implicitHeight: 28
        radius: 14
        color: "#1d1533"
        border.width: 1
        border.color: "#6d5bd0"
        Text {
            anchors.centerIn: parent
            text: step
            color: "#c4b5fd"
            font.pixelSize: 11
            font.bold: true
        }
    }

    component StepConnector: RowLayout {
        Layout.alignment: Qt.AlignVCenter
        spacing: 3
        Rectangle {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 1
            Layout.alignment: Qt.AlignVCenter
            color: "#2b3650"
        }
        Image {
            source: Qt.resolvedUrl("../assets/icons/web_arrow_right.svg")
            Layout.preferredWidth: 15
            Layout.preferredHeight: 15
            Layout.alignment: Qt.AlignVCenter
        }
    }

    Loader {
        id: apiGate
        anchors.fill: parent
        active: typeof dockApi !== "undefined" && dockApi !== null
        sourceComponent: gatedUi
    }

    Text {
        anchors.centerIn: parent
        visible: !apiGate.active
        text: dockApi.strings.not_available || "Docks API is not available yet."
        color: muted
        font.pixelSize: 13
    }

    Component {
        id: gatedUi
        ScrollView {
            id: pageScroll
            anchors.fill: parent
            anchors.margins: 20
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: pageCol
                objectName: "pageCol"
                width: pageScroll.availableWidth
                spacing: 12

            // Page Header
            ColumnLayout {
                objectName: "secHeader"
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: dockApi.strings.header_title || "Доки"
                    color: ink
                    font.pixelSize: 32
                    font.bold: true
                    Layout.fillWidth: true
                }

                Text {
                    text: dockApi.strings.header_subtitle || "Веб-доки для стримінгу"
                    color: ink
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                Text {
                    text: dockApi.strings.header_hint || "Використовуйте ці посилання у будь-якому стрімінговому софті або відкрийте у браузері."
                    color: muted
                    font.pixelSize: 13
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }

            // Public Access Hero Card — compact single-row layout:
            // [icon] [title + status / description] [URL field] [copy]
            Rectangle {
                objectName: "secHero"
                Layout.fillWidth: true
                Layout.topMargin: 8
                // Content-driven height: anchored children do not propagate
                // implicit size, so derive it from the internal row.
                implicitHeight: heroBody.implicitHeight + 32
                radius: 14
                color: "#0a0f19"
                border.width: 1
                border.color: "#1f6b78"
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0a0f19" }
                    GradientStop { position: 1.0; color: "#102029" }
                }

                RowLayout {
                    id: heroBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 52
                        Layout.preferredHeight: 52
                        Layout.alignment: Qt.AlignVCenter
                        radius: 11
                        color: "#0f2b33"
                        border.width: 1
                        border.color: "#1f6b78"

                        Image {
                            anchors.centerIn: parent
                            source: Qt.resolvedUrl("../assets/icons/web_globe.svg")
                            width: 28
                            height: 28
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 120
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: dockApi.strings.public_access || "Публічний доступ"
                                color: ink
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            StatusPill {
                                active: tunnelApi ? tunnelApi.tunnelEnabled : false
                                onToggled: if (tunnelApi) tunnelApi.setTunnelEnabled(!tunnelApi.tunnelEnabled)
                            }
                        }

                        Text {
                            text: dockApi.strings.public_hint || "Дозволяє використовувати ваші веб-доки через зовнішню мережу."
                            color: muted
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                    }

                    // Quiet divider: groups URL + actions as one control cluster.
                    Rectangle {
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        Layout.topMargin: 8
                        Layout.bottomMargin: 8
                        color: "#1e2839"
                    }

                    Rectangle {
                        Layout.preferredWidth: 260
                        Layout.minimumWidth: 120
                        Layout.preferredHeight: 32
                        Layout.alignment: Qt.AlignVCenter
                        radius: 8
                        color: root.fieldBg
                        border.width: 1
                        border.color: "#33405a"

                        Text {
                            text: tunnelApi ? tunnelApi.tunnelStatusText : "https://app.cheremsha.click:17171/"
                            color: "#9aa7bc"
                            font.pixelSize: 11
                            font.family: "monospace"
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            elide: Text.ElideRight
                        }
                    }

                    PrimaryButton {
                        Layout.alignment: Qt.AlignVCenter
                        text: dockApi.strings.copy_url || "Копіювати URL"
                        btnIcon: Qt.resolvedUrl("../assets/icons/web_copy.svg")
                        onClicked: if (tunnelApi && tunnelApi.tunnelStatusText) dockApi.copyText(tunnelApi.tunnelStatusText)
                    }
                }
            }

            // Available Web Docs Section
            ColumnLayout {
                objectName: "secSection"
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: dockApi.strings.available_title || "Доступні веб-доки"
                        color: ink
                        font.pixelSize: 20
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        radius: 9
                        color: "#141c2c"
                        border.width: 1
                        border.color: root.cardEdge
                        Layout.preferredWidth: countLabel.implicitWidth + 18
                        Layout.preferredHeight: 22
                        Text {
                            id: countLabel
                            anchors.centerIn: parent
                            text: dockApi.countText(3)
                            color: root.muted
                            font.pixelSize: 11
                        }
                    }
                }

                Text {
                    text: dockApi.strings.available_hint || "Готові джерела для вашого стріму. Скопіюйте URL і додайте у ваш стрімінговий софт."
                    color: muted
                    font.pixelSize: 13
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }

            // Three Document Cards Grid
            RowLayout {
                objectName: "secCards"
                Layout.fillWidth: true
                spacing: 12
                CheremshaSourceCard {
                    title: { dockApi.strings; return dockApi.tr("dock.multichat.title") || "MultiChat"; }
                    description: dockApi.strings.multichat_desc || "Чат з усіх підключених платформ в одному вікні. Підтримує Twitch, YouTube, TikTok, Kick та інші."
                    url: dockApi ? dockApi.multichatDockUrlValue : ""
                    iconSource: Qt.resolvedUrl("../assets/icons/web_multichat.svg")
                    accentColor: primaryPurple
                    statusText: dockApi.strings.web_dock_badge || "Веб-док"
                    copyButtonText: dockApi.strings.copy_url || "Копіювати URL"
                    openButtonText: dockApi.strings.open || "Відкрити"
                    onCopyClicked: dockApi.copyMultichatDockUrl()
                    onOpenClicked: dockApi.openMultichatDockUrl()
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    previewContent: Component {
                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: "#0c111c"
                            border.width: 1
                            border.color: "#2b3650"
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 5
                                    Image {
                                        source: Qt.resolvedUrl("../assets/twitch.svg")
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                    }
                                    Text { text: "<b><font color=\"#a970ff\">luna</font></b> <font color=\"#c3cddc\">Крутий стрім, друзі!</font> <font color=\"#5b6575\">12:04</font>"; textFormat: Text.RichText; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 5
                                    Image {
                                        source: Qt.resolvedUrl("../assets/youtube.svg")
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                    }
                                    Text { text: "<b><font color=\"#f87171\">darkness</font></b> <font color=\"#c3cddc\">Всім привіт!</font> <font color=\"#5b6575\">12:05</font>"; textFormat: Text.RichText; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 5
                                    Image {
                                        source: Qt.resolvedUrl("../assets/tiktok.svg")
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                    }
                                    Text { text: "<b><font color=\"#67e8f9\">sakura</font></b> <font color=\"#c3cddc\">great stream, love it!</font> <font color=\"#5b6575\">12:06</font>"; textFormat: Text.RichText; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 5
                                    Image {
                                        source: Qt.resolvedUrl("../assets/kick.svg")
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                    }
                                    Text { text: "<b><font color=\"#6ee7a0\">mira</font></b> <font color=\"#c3cddc\">Саунд топ!</font> <font color=\"#5b6575\">12:07</font>"; textFormat: Text.RichText; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                }

                CheremshaSourceCard {
                    title: { dockApi.strings; return dockApi.tr("dock.activity.title") || "Активність"; }
                    description: dockApi.strings.activity_desc || "Останні події: підписки, донати, подарунки, рейди та інша активність у реальному часі."
                    url: dockApi ? dockApi.activityDockUrlValue : ""
                    iconSource: Qt.resolvedUrl("../assets/icons/web_activity.svg")
                    accentColor: accentAmber
                    statusText: dockApi.strings.web_dock_badge || "Веб-док"
                    copyButtonText: dockApi.strings.copy_url || "Копіювати URL"
                    openButtonText: dockApi.strings.open || "Відкрити"
                    onCopyClicked: dockApi.copyActivityDockUrl()
                    onOpenClicked: dockApi.openActivityDockUrl()
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    previewContent: Component {
                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: "#0c111c"
                            border.width: 1
                            border.color: "#2b3650"
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Image {
                                        source: Qt.resolvedUrl("../assets/icons/web_event_subscribe.svg")
                                        Layout.preferredWidth: 13
                                        Layout.preferredHeight: 13
                                    }
                                    Text { text: dockApi.strings.preview_sub || "Підписка"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                    Text { text: "luna"; color: "#9aa7bc"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: "2 хв"; color: root.muted; font.pixelSize: 9 }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Image {
                                        source: Qt.resolvedUrl("../assets/icons/web_event_donation.svg")
                                        Layout.preferredWidth: 13
                                        Layout.preferredHeight: 13
                                    }
                                    Text { text: dockApi.strings.preview_donation || "Донат $5"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                    Text { text: "darkness"; color: "#9aa7bc"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: "5 хв"; color: root.muted; font.pixelSize: 9 }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Image {
                                        source: Qt.resolvedUrl("../assets/icons/web_event_gift.svg")
                                        Layout.preferredWidth: 13
                                        Layout.preferredHeight: 13
                                    }
                                    Text { text: dockApi.strings.preview_gift || "Подарунок"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                    Text { text: "sakura"; color: "#9aa7bc"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: "9 хв"; color: root.muted; font.pixelSize: 9 }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Image {
                                        source: Qt.resolvedUrl("../assets/icons/web_event_raid.svg")
                                        Layout.preferredWidth: 13
                                        Layout.preferredHeight: 13
                                    }
                                    Text { text: dockApi.strings.preview_raid || "Рейд ×42"; color: "#dbe2ec"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                    Text { text: "void"; color: "#9aa7bc"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: "12 хв"; color: root.muted; font.pixelSize: 9 }
                                }
                            }
                        }
                    }
                }

                CheremshaSourceCard {
                    title: { dockApi.strings; return dockApi.tr("dock.online.title") || "Онлайн"; }
                    description: dockApi.strings.online_desc || "Показує поточний онлайн, глядачів з усіх платформ та загальну статистику стріму."
                    url: dockApi ? dockApi.onlineDockUrlValue : ""
                    iconSource: Qt.resolvedUrl("../assets/icons/web_online.svg")
                    accentColor: secondaryCyan
                    statusText: dockApi.strings.web_dock_badge || "Веб-док"
                    copyButtonText: dockApi.strings.copy_url || "Копіювати URL"
                    openButtonText: dockApi.strings.open || "Відкрити"
                    onCopyClicked: dockApi.copyOnlineDockUrl()
                    onOpenClicked: dockApi.openOnlineDockUrl()
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    previewContent: Component {
                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: "#0c111c"
                            border.width: 1
                            border.color: "#2b3650"
                            clip: true

                            RowLayout {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "01:24:17"; color: root.ink; font.pixelSize: 13; font.bold: true }
                                    Text { text: dockApi.strings.preview_online || "Онлайн"; color: root.muted; font.pixelSize: 9 }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 3
                                        radius: 1.5
                                        color: "#1c2536"
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: parent.width * 0.85
                                            height: 3
                                            radius: 1.5
                                            color: "#22d3ee"
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "1 247"; color: root.ink; font.pixelSize: 13; font.bold: true }
                                    Text { text: dockApi.strings.preview_viewers || "Глядачі"; color: root.muted; font.pixelSize: 9 }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 3
                                        radius: 1.5
                                        color: "#1c2536"
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: parent.width * 0.6
                                            height: 3
                                            radius: 1.5
                                            color: "#8b5cf6"
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "892"; color: root.ink; font.pixelSize: 13; font.bold: true }
                                    Text { text: dockApi.strings.preview_followers || "Підписники"; color: root.muted; font.pixelSize: 9 }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 3
                                        radius: 1.5
                                        color: "#1c2536"
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: parent.width * 0.4
                                            height: 3
                                            radius: 1.5
                                            color: "#10b981"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // How it works card
            Rectangle {
                objectName: "secHow"
                Layout.fillWidth: true
                Layout.topMargin: 4
                // Content-driven height: anchored children do not propagate
                // implicit size, so derive it from the internal column.
                implicitHeight: howBody.implicitHeight + 20
                radius: 14
                color: root.cardBase
                border.width: 1
                border.color: root.cardEdge

                ColumnLayout {
                    id: howBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Image {
                            source: Qt.resolvedUrl("../assets/icons/web_lightbulb.svg")
                            Layout.preferredWidth: 20
                            Layout.preferredHeight: 20
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Text {
                            text: dockApi.strings.how_title || "Як це працює?"
                            color: ink
                            font.pixelSize: 17
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }
                    }

                    Text {
                        text: dockApi.strings.how_hint || "Коротка інструкція з використання веб-доків."
                        color: muted
                        font.pixelSize: 13
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            StepBadge { step: "01" }

                            Text {
                                text: dockApi.strings.step1_title || "Скопіюйте URL"
                                color: ink
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }

                            Text {
                                text: dockApi.strings.step1_hint || "Натисніть кнопку «Копіювати URL» біля потрібного доку."
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                maximumLineCount: 1
                                elide: Text.ElideRight
                            }
                        }

                        StepConnector {}

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            StepBadge { step: "02" }

                            Text {
                                text: dockApi.strings.step2_title || "Додайте у стрімінговий софт"
                                color: ink
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }

                            Text {
                                text: dockApi.strings.step2_hint || "Вставте URL як Browser Source у ваш софт."
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                maximumLineCount: 1
                                elide: Text.ElideRight
                            }
                        }

                        StepConnector {}

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            StepBadge { step: "03" }

                            Text {
                                text: dockApi.strings.step3_title || "Готово!"
                                color: ink
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }

                            Text {
                                text: dockApi.strings.step3_hint || "Док буде автоматично оновлюватися в реальному часі."
                                color: muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                maximumLineCount: 1
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            // Stretch belongs ONLY after all real content: absorbs any
            // leftover space inside tall viewports. Inside a ScrollView the
            // column is content-sized, so this stays zero-height there.
            Item { Layout.fillHeight: true }
            }
        }
    }
}