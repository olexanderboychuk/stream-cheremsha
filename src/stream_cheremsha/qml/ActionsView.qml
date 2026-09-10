import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQml

Item {
    id: root
    // Embedded in main window stack (QQuickWidget); implicit size hints layout.
    implicitWidth: 820
    implicitHeight: 560

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

    // Provided by MainWindow when opening the editor.
    property string platform: ""
    property string accountKey: ""

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"
    // Cheremsha automation-center accents (shared with Widgets/Docks/Donations/TTS).
    readonly property color accentPurple: "#8b5cf6"
    readonly property color accentPurpleSoft: "#a78bfa"
    readonly property color accentTeal: "#14b8a6"
    readonly property color okGreen: "#34d399"
    readonly property color dangerRed: "#ef4444"

    // Rule library filter state (search only filters the visible list, never the model).
    property string ruleSearchText: ""
    property string libraryFilter: "all"
    property bool showActionPicker: false
    // -1 means append; otherwise the picker replaces the selected existing action type.
    property int actionPickerReplaceIdx: -1
    property string actionPickerQuery: ""
    // Collapsible advanced sections in the rule builder (persist per session only).
    property bool whenAdvancedOpen: false
    property bool thenAdvancedOpen: false
    // Tracks unsaved edits for the sticky save bar (set on any local edit, cleared on save/load).
    property bool hasUnsavedChanges: false

    function _assetUrl(name) {
        // Resolve local SVG assets relative to this QML file.
        return Qt.resolvedUrl("../assets/icons/" + name);
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f172a" }
            GradientStop { position: 0.55; color: "#0b1220" }
            GradientStop { position: 1.0; color: "#070910" }
        }
    }

    property var rulesModel: []
    property var rulesUiTree: []
    property string rulesUiRevision: ""
    property string selectedRuleId: ""
    property int selectedIdx: -1
    property bool dndDebug: false

    // Pointer DnD state. The list stays laid out by its existing Column/Repeater;
    // only visual transforms are applied while this state is active.
    property bool reducedMotion: false
    property bool dndActive: false
    property bool dndArmed: false
    property bool dndDropPending: false
    property string dndKind: ""
    property string dndId: ""
    property string dndTargetMode: "none"
    property string dndTargetBeforeId: ""
    property string dndTargetFolderId: ""
    property string dndTargetParentFolderId: ""
    property real dndPointerX: 0
    property real dndPointerY: 0
    property real dndPressX: 0
    property real dndPressY: 0
    property real dndIndicatorY: 0
    property real dndIndicatorX: 0
    property real dndIndicatorWidth: 0
    property var dndSourceTarget: null
    property var dndTarget: null
    property var _dndTargets: []
    property var _dndPendingDrop: null
    property int dndRevision: 0
    readonly property int dndAnimationDuration: reducedMotion ? 0 : 150

    function _registerDndTarget(target) {
        if (!target)
            return;
        var next = root._dndTargets.slice();
        if (next.indexOf(target) < 0) {
            next.push(target);
            root._dndTargets = next;
        }
    }

    function _unregisterDndTarget(target) {
        var next = root._dndTargets.slice();
        var ix = next.indexOf(target);
        if (ix >= 0) {
            next.splice(ix, 1);
            root._dndTargets = next;
        }
    }

    function _dndNode(target) {
        return target && target.node ? target.node : null;
    }

    function _dndNodeId(node) {
        if (!node)
            return "";
        return node.kind === "folder" ? ("" + (node.id || "")) : ("" + (node.rule_id || ""));
    }

    function _dndTargetParent(target) {
        return target && target.dndParentFolderId ? ("" + target.dndParentFolderId) : "";
    }

    function _dndRect(target) {
        if (!target || !target.dndArea)
            return null;
        if (!target.dndArea.visible && target !== root.dndSourceTarget)
            return null;
        try {
            var area = target.dndArea;
            // Map from the target's parent so its own active Translate is not
            // fed back into hit testing or neighbor displacement calculations.
            var mapParent = target.parent || area.parent;
            var p = mapParent.mapToItem(root, (target.x || 0) + (area.x || 0),
                                        (target.y || 0) + (area.y || 0));
            return { x: p.x, y: p.y, width: area.width, height: area.height };
        } catch (e) {
            return null;
        }
    }

    function _dndSiblingId(target) {
        var sibling = target ? target.nextSibling : null;
        return sibling ? _dndNodeId(sibling) : "";
    }

    function _dndSourceSpan() {
        if (!root.dndSourceTarget)
            return 0;
        return Math.max(1, root.dndSourceTarget.height || root.dndSourceTarget.dndArea.height || 1);
    }

    function _dndOffsetFor(target) {
        var revision = root.dndRevision;
        if (!root.dndActive || root.dndTargetMode !== "between"
                || !root.dndSourceTarget || !target || target === root.dndSourceTarget)
            return 0;
        var sourceRect = root._dndRect(root.dndSourceTarget);
        var rect = root._dndRect(target);
        if (!sourceRect || !rect)
            return 0;
        var span = root._dndSourceSpan() + 4;
        var sourceTop = sourceRect.y;
        var line = root.dndIndicatorY;
        // The source keeps its slot. Siblings between it and the insertion point
        // slide by that slot using a GPU-friendly transform only.
        if (line < sourceTop && rect.y >= line && rect.y < sourceTop)
            return span;
        if (line > sourceTop + span - 4 && rect.y > sourceTop && rect.y < line)
            return -span;
        return 0;
    }

    function _dndClearTarget() {
        root.dndTargetMode = "none";
        root.dndTargetBeforeId = "";
        root.dndTargetFolderId = "";
        root.dndTargetParentFolderId = "";
        root.dndTarget = null;
        root.dndIndicatorWidth = 0;
    }

    function _dndSetBetweenTarget(target, before, rect) {
        var node = root._dndNode(target);
        if (!node || !rect)
            return;
        root.dndTargetMode = "between";
        root.dndTarget = target;
        root.dndTargetFolderId = "";
        root.dndTargetParentFolderId = root._dndTargetParent(target);
        root.dndTargetBeforeId = before ? root._dndNodeId(node) : root._dndSiblingId(target);
        root.dndIndicatorX = rect.x;
        root.dndIndicatorWidth = Math.max(24, rect.width);
        root.dndIndicatorY = before ? rect.y : rect.y + rect.height;
    }

    function _dndChooseTarget(x, y) {
        if (!root.dndActive)
            return;
        root.dndPointerX = x;
        root.dndPointerY = y;

        var targets = root._dndTargets || [];
        var folderCandidate = null;
        for (var i = 0; i < targets.length; i++) {
            if (targets[i] === root.dndSourceTarget)
                continue;
            var folderNode = root._dndNode(targets[i]);
            var folderRect = root._dndRect(targets[i]);
            if (!folderNode || folderNode.kind !== "folder" || !folderRect)
                continue;
            // The middle of a folder header means “move into”; its edges remain
            // reorder zones so dropping above/below is never ambiguous.
            if (root.dndKind === "rule"
                    && y >= folderRect.y + folderRect.height * 0.24
                    && y <= folderRect.y + folderRect.height * 0.76) {
                folderCandidate = { target: targets[i], rect: folderRect };
                break;
            }
        }
        if (folderCandidate) {
            root.dndTargetMode = "folder";
            root.dndTarget = folderCandidate.target;
            root.dndTargetFolderId = root._dndNodeId(root._dndNode(folderCandidate.target));
            root.dndTargetParentFolderId = root._dndTargetParent(folderCandidate.target);
            root.dndTargetBeforeId = "";
            root.dndIndicatorWidth = 0;
            root.dndRevision++;
            return;
        }

        var best = null;
        var bestDistance = Number.MAX_VALUE;
        for (var j = 0; j < targets.length; j++) {
            if (targets[j] === root.dndSourceTarget)
                continue;
            var node = root._dndNode(targets[j]);
            var rect = root._dndRect(targets[j]);
            if (!node || !rect || rect.height <= 0)
                continue;
            var distance = y < rect.y ? rect.y - y : (y > rect.y + rect.height ? y - rect.y - rect.height : 0);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = { target: targets[j], rect: rect };
            }
        }
        if (!best) {
            root._dndClearTarget();
            root.dndRevision++;
            return;
        }
        root._dndSetBetweenTarget(best.target, y < best.rect.y + best.rect.height / 2, best.rect);
        root.dndRevision++;
    }

    function _dndAutoScroll() {
        if (!root.dndActive || !rulesList)
            return;
        var viewport = rulesList.contentItem;
        if (!viewport)
            return;
        var topLeft = rulesList.mapToItem(root, 0, 0);
        var edge = 36;
        var delta = 0;
        if (root.dndPointerY < topLeft.y + edge)
            delta = -Math.max(2, (topLeft.y + edge - root.dndPointerY) * 0.28);
        else if (root.dndPointerY > topLeft.y + rulesList.height - edge)
            delta = Math.max(2, (root.dndPointerY - (topLeft.y + rulesList.height - edge)) * 0.28);
        if (delta) {
            var maxY = Math.max(0, viewport.contentHeight - viewport.height);
            viewport.contentY = Math.max(0, Math.min(maxY, viewport.contentY + delta));
            root._dndChooseTarget(root.dndPointerX, root.dndPointerY);
        }
    }

    function _dndArm(kind, id, target, x, y) {
        if (root.dndActive || root.dndDropPending)
            return;
        root.dndKind = kind;
        root.dndId = "" + id;
        root.dndSourceTarget = target;
        root.dndPressX = x;
        root.dndPressY = y;
        root.dndPointerX = x;
        root.dndPointerY = y;
        root.dndArmed = true;
    }

    function _dndStart(target) {
        if (root.dndActive || !target)
            return;
        root.dndArmed = false;
        root.dndActive = true;
        root.dndSourceTarget = target;
        root.dndPointerX = root.dndPressX;
        root.dndPointerY = root.dndPressY;
        root._dndChooseTarget(root.dndPointerX, root.dndPointerY);
        root.dndRevision++;
    }

    function _dndMovePointer(x, y) {
        if (root.dndArmed && !root.dndActive) {
            var dx = x - root.dndPressX;
            var dy = y - root.dndPressY;
            if (Math.sqrt(dx * dx + dy * dy) >= 4)
                root._dndStart(root.dndSourceTarget);
        }
        if (root.dndActive)
            root._dndChooseTarget(x, y);
    }

    function _dndApplyPendingDrop() {
        var pending = root._dndPendingDrop;
        root._dndPendingDrop = null;
        root.dndDropPending = false;
        if (!pending)
            return;
        if (pending.mode === "folder" && pending.kind === "rule") {
            root._dropRuleOntoFolder(pending.id, pending.folderId);
        } else if (pending.mode === "between") {
            if (pending.kind === "rule") {
                if (pending.parentFolderId)
                    root._dropOntoFolderBetween(pending.parentFolderId, pending.id, pending.beforeId);
                else
                    root._dropOntoRootBetween(pending.id, pending.beforeId);
            } else if (pending.kind === "folder") {
                root._moveFolderToParentBefore(pending.id, pending.parentFolderId, pending.beforeId);
            }
        }
    }

    // The single drag cleanup path. It restores the source delegate and all
    // transient state before any persistence/model operation is allowed to run.
    function finishDrag(commitDrop) {
        var wasActive = root.dndActive;
        var shouldCommit = commitDrop === true && wasActive;
        if (!wasActive && !root.dndArmed && !root.dndDropPending)
            return;

        if (shouldCommit) {
            root._dndPendingDrop = {
                mode: root.dndTargetMode,
                kind: root.dndKind,
                id: root.dndId,
                folderId: root.dndTargetFolderId,
                parentFolderId: root.dndTargetParentFolderId,
                beforeId: root.dndTargetBeforeId
            };
            root.dndDropPending = true;
            dndSettleTimer.interval = root.reducedMotion ? 0 : 125;
            dndSettleTimer.restart();
        } else {
            root._dndPendingDrop = null;
            root.dndDropPending = false;
            dndSettleTimer.stop();
        }

        root.dndActive = false;
        root.dndArmed = false;
        root._dndClearTarget();
        root.dndSourceTarget = null;
        root.dndKind = "";
        root.dndId = "";
        root.dndRevision++;
    }

    function _dndFinish() {
        root.finishDrag(true);
    }

    function _cancelDnd() {
        root.finishDrag(false);
    }

    function _dndTargetDestroyed(target) {
        root._unregisterDndTarget(target);
        if (root.dndSourceTarget === target)
            root.finishDrag(false);
    }

    function _dndKeyboardMove(step) {
        if (!root.dndActive)
            return;
        var visible = [];
        var targets = root._dndTargets || [];
        for (var i = 0; i < targets.length; i++) {
            if (targets[i] === root.dndSourceTarget)
                continue;
            var node = root._dndNode(targets[i]);
            var rect = root._dndRect(targets[i]);
            if (node && rect)
                visible.push({ target: targets[i], rect: rect });
        }
        visible.sort(function(a, b) { return a.rect.y - b.rect.y; });
        var current = -1;
        for (var j = 0; j < visible.length; j++) {
            if (visible[j].target === root.dndTarget) {
                current = j;
                break;
            }
        }
        var next = Math.max(0, Math.min(visible.length - 1, (current < 0 ? 0 : current) + step));
        if (visible.length && next !== current) {
            root._dndSetBetweenTarget(visible[next].target, step < 0, visible[next].rect);
            root.dndRevision++;
        }
    }

    Timer {
        id: dndAutoScrollTimer
        interval: 16
        repeat: true
        running: root.dndActive
        onTriggered: root._dndAutoScroll()
    }

    Timer {
        id: dndSettleTimer
        interval: 125
        repeat: false
        onTriggered: root._dndApplyPendingDrop()
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.dndArmed || root.dndActive || root.dndDropPending
        onActivated: root._cancelDnd()
    }
    property var selectedRule: null
    property var giftOptions: []
    property var actionsModel: []
    property int selectedActionIdx: -1
    onSelectedActionIdxChanged: {
        var ix = root.selectedActionIdx;
        var aa = root.actionsModel;
        var isObs = ix >= 0 && aa && ix < aa.length && ("" + (aa[ix].type || "")).trim() === "obs_scene";
        if (isObs) {
            root._obsPickCanvases = [];
            root._obsPickScenes = [];
            root._obsPickSources = [];
        }
        root._scheduleObsBrowseAutoRefresh();
    }
    property var _obsPickCanvases: []
    property var _obsPickScenes: []
    property var _obsPickSources: []
    property bool _suppressObsBrowseCombos: false
    property int selectedTriggerIdx: 0
    // Inline so QML tracks selectedRule + selectedTriggerIdx (not hidden inside a JS function).
    readonly property var editingTrigger: {
        if (selectedRule === null)
            return null;
        var norm = root._normalizeRuleEvents(root._copyRule(selectedRule));
        if (!norm || !norm.events || !norm.events.length)
            return null;
        var ix = Math.max(0, Math.min(selectedTriggerIdx, norm.events.length - 1));
        return norm.events[ix];
    }

    // Same resolution as editingTrigger but as a function: safe to call in the same
    // handler tick as selectedTriggerIdx changes (bindings are not flushed yet).
    function _activeEventForCombos() {
        if (root.selectedRule === null)
            return null;
        var norm = root._normalizeRuleEvents(root._copyRule(root.selectedRule));
        if (!norm || !norm.events || !norm.events.length)
            return null;
        var ix = Math.max(0, Math.min(root.selectedTriggerIdx, norm.events.length - 1));
        return norm.events[ix];
    }

    property bool isActionTextEditing: false
    property int _lastSyncedRuleIdx: -2
    property bool _suppressActionsAutosave: false
    // true while we set event/gift comboboxes from the rule; blocks onPicked/onAccepted
    // (Qt can emit them when currentIndex is set, which re-saved the same state to all rows).
    property bool _suppressRuleCombos: false
    // Block disk writes while rules are loading (avoids empty model autosave wiping QSettings).
    property bool _rulesPersistBlocked: false

    Timer {
        id: ruleCombosSuppressEnd
        interval: 1
        repeat: false
        onTriggered: root._suppressRuleCombos = false
    }

    Timer {
        id: actionsAutosaveTimer
        interval: 800
        repeat: false
        onTriggered: {
            // Never rebuild the model while the user is typing, otherwise focus is lost.
            if (root.isActionTextEditing) {
                actionsAutosaveTimer.restart();
                return;
            }
            root._save(false);
        }
    }

    property bool _savedToastVisible: false

    Timer {
        id: savedToastTimer
        interval: 1400
        repeat: false
        onTriggered: root._savedToastVisible = false
    }

    function _notifySaved() {
        root._savedToastVisible = true;
        savedToastTimer.restart();
    }

    property bool _previewToastVisible: false
    property string _previewToastText: ""

    Timer {
        id: previewToastTimer
        interval: 2600
        repeat: false
        onTriggered: root._previewToastVisible = false
    }

    Timer {
        id: obsBrowseAutoRefresh
        interval: 120
        repeat: false
        onTriggered: root._obsBrowseAutoRefreshTick()
    }

    function _scheduleObsBrowseAutoRefresh() {
        obsBrowseAutoRefresh.restart();
    }

    function _obsBrowseAutoRefreshTick() {
        var ix = root.selectedActionIdx;
        if (ix < 0) {
            return;
        }
        var aa = root.actionsModel;
        if (!aa || ix >= aa.length) {
            return;
        }
        var row = aa[ix];
        if (!row || ("" + (row.type || "")).trim() !== "obs_scene") {
            return;
        }
        if (!actApi) return;
        root._obsRefreshFromObs(ix, true);
    }

    function _notifyPreviewToast(msg) {
        var s = ("" + (msg || "")).trim();
        if (!s)
            return;
        root._previewToastText = s;
        root._previewToastVisible = true;
        previewToastTimer.restart();
    }

    function _obsComboLabel(row) {
        if (!row) return "";
        var n = (row.name !== undefined && row.name !== null) ? ("" + row.name).trim() : "";
        var v = (row.value !== undefined && row.value !== null) ? ("" + row.value).trim() : "";
        if (n !== "") return n;
        if (v !== "") return v;
        return api ? api.loc("actions.obs_canvas_default") : "Main canvas";
    }

    function _obsRowsToComboModel(rows) {
        var out = [];
        if (!rows || !rows.length) return out;
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i];
            var val = (r && r.value !== undefined && r.value !== null) ? ("" + r.value) : "";
            out.push({ text: root._obsComboLabel(r), value: val });
        }
        return out;
    }

    function _obsFindComboIndex(modelArr, currentValue) {
        var s = (currentValue !== undefined && currentValue !== null) ? ("" + currentValue) : "";
        for (var i = 0; i < modelArr.length; i++) {
            if (modelArr[i].value === s) return i;
        }
        return -1;
    }

    function _obsReloadScenesPickList() {
        if (!actApi) return;
        var aa = root.actionsModel;
        var ix = root.selectedActionIdx;
        if (!aa || ix < 0 || ix >= aa.length) return;
        var pr = aa[ix].params || {};
        var cu = (pr.canvas_uuid !== undefined && pr.canvas_uuid !== null) ? ("" + pr.canvas_uuid).trim() : "";
        var scn = JSON.parse(actApi.obsListScenesJson(cu));
        if (scn.error) {
            root._obsPickScenes = [];
            root._notifyPreviewToast(scn.error);
            return;
        }
        root._obsPickScenes = root._obsRowsToComboModel(scn.items || []);
    }

    function _obsReloadSourcesPickList() {
        if (!actApi) return;
        var aa = root.actionsModel;
        var ix = root.selectedActionIdx;
        if (!aa || ix < 0 || ix >= aa.length) return;
        var pr = aa[ix].params || {};
        var cu = (pr.canvas_uuid !== undefined && pr.canvas_uuid !== null) ? ("" + pr.canvas_uuid).trim() : "";
        var sn = (pr.scene_name !== undefined && pr.scene_name !== null) ? ("" + pr.scene_name).trim() : "";
        if (!sn) {
            root._obsPickSources = [];
            return;
        }
        var srcj = JSON.parse(actApi.obsListSceneSourcesJson(cu, sn));
        if (srcj.error) {
            root._obsPickSources = [];
            root._notifyPreviewToast(srcj.error);
            return;
        }
        root._obsPickSources = root._obsRowsToComboModel(srcj.items || []);
    }

    function _obsRefreshFromObs(aIdx, silentToast) {
        var st = silentToast === true;
        if (!actApi) {
            if (!st) root._notifyPreviewToast("OBS: actApi missing");
            return;
        }
        var aa = root.actionsModel;
        if (!aa || aIdx < 0 || aIdx >= aa.length) return;
        root._suppressObsBrowseCombos = true;
        var pr = aa[aIdx].params || {};
        var cu = (pr.canvas_uuid !== undefined && pr.canvas_uuid !== null) ? ("" + pr.canvas_uuid).trim() : "";
        var sn = (pr.scene_name !== undefined && pr.scene_name !== null) ? ("" + pr.scene_name).trim() : "";
        var mode = (pr.mode !== undefined && pr.mode !== null) ? ("" + pr.mode) : "program_scene";

        var canv = JSON.parse(actApi.obsListCanvasesJson());
        if (canv.error) {
            root._obsPickCanvases = [];
            if (!st) root._notifyPreviewToast(canv.error);
        } else {
            root._obsPickCanvases = root._obsRowsToComboModel(canv.items || []);
        }

        var scn = JSON.parse(actApi.obsListScenesJson(cu));
        if (scn.error) {
            root._obsPickScenes = [];
            if (!st) root._notifyPreviewToast(scn.error);
        } else {
            root._obsPickScenes = root._obsRowsToComboModel(scn.items || []);
        }

        if (mode === "source_visible" && sn) {
            var srcj = JSON.parse(actApi.obsListSceneSourcesJson(cu, sn));
            if (srcj.error) {
                root._obsPickSources = [];
                if (!st) root._notifyPreviewToast(srcj.error);
            } else {
                root._obsPickSources = root._obsRowsToComboModel(srcj.items || []);
            }
        } else {
            root._obsPickSources = [];
        }
        Qt.callLater(function() { root._suppressObsBrowseCombos = false; });
    }

    function _restoreScrollIfPossible(flickable, y) {
        if (!flickable) return;
        if (y === undefined || y === null) return;
        // Defer until after bindings/layout settle.
        Qt.callLater(function() {
            if (!flickable) return;
            var maxY = Math.max(0, (flickable.contentHeight || 0) - (flickable.height || 0));
            flickable.contentY = Math.max(0, Math.min(y, maxY));
        });
    }

    function _nextUiRevision() {
        rulesUiRevision = ("" + Math.random()).slice(2);
    }

    function _cloneUiTree(tree) {
        try {
            return JSON.parse(JSON.stringify(tree || []));
        } catch (e) {
            return [];
        }
    }

    /** Expand/collapse folder: clone tree, toggle, reassign model (reliable with QML Repeater + QVariantMap). */
    function _commitFolderToggleUi(fid) {
        if (!fid)
            return;
        function toggle(nodes) {
            if (!nodes)
                return false;
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    n.expanded = !n.expanded;
                    return true;
                }
                if (n.kind === "folder") {
                    if (toggle(n.children || []))
                        return true;
                }
            }
            return false;
        }
        var tree = root._cloneUiTree(root.rulesUiTree);
        if (!toggle(tree))
            return;
        root._preserveScroll(function() {
            root.rulesUiTree = tree;
            root._nextUiRevision();
            root._saveUiLayoutOnly();
            root._saveRulesPayload(false);
        });
    }

    function _normalizeUiTree(treeIn) {
        var tree = _cloneUiTree(treeIn);
        if (!tree.length)
            return [];

        function fixFolder(node) {
            if (!node || node.kind !== "folder")
                return node;
            if (node.expanded === undefined || node.expanded === null)
                node.expanded = true;
            node.children = _normalizeUiTree(node.children || []);
            return node;
        }

        var out = [];
        for (var i = 0; i < tree.length; i++) {
            var n = tree[i];
            if (!n)
                continue;
            if (n.kind === "folder") {
                out.push(fixFolder(JSON.parse(JSON.stringify(n))));
                continue;
            }
            if (n.kind === "rule" && n.rule_id)
                out.push({ kind: "rule", rule_id: ("" + n.rule_id) });
        }
        return out;
    }

    function _flattenUiRuleIds(tree) {
        var out = [];
        function walk(nodes) {
            if (!nodes)
                return;
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "rule" && n.rule_id)
                    out.push(("" + n.rule_id));
                else if (n.kind === "folder")
                    walk(n.children);
            }
        }
        walk(tree);
        return out;
    }

    function _rulesIndexById(rid) {
        if (!rid)
            return -1;
        for (var i = 0; i < rulesModel.length; i++) {
            var rr = rulesModel[i];
            if (rr && ("" + rr.id) === ("" + rid))
                return i;
        }
        return -1;
    }

    function _ruleById(rid) {
        var ix = _rulesIndexById(rid);
        if (ix < 0)
            return null;
        return rulesModel[ix];
    }

    function _syncRulesModelOrder() {
        var order = _flattenUiRuleIds(rulesUiTree);
        if (!order.length)
            return;
        var byId = {};
        var i;
        for (i = 0; i < rulesModel.length; i++) {
            var rr = rulesModel[i];
            if (rr && rr.id)
                byId[("" + rr.id)] = rr;
        }
        var next = [];
        var seen = {};
        for (i = 0; i < order.length; i++) {
            var id = order[i];
            if (!id || seen[id])
                continue;
            var obj = byId[id];
            if (obj)
                next.push(obj);
            seen[id] = true;
        }
        for (i = 0; i < rulesModel.length; i++) {
            var r2 = rulesModel[i];
            if (!r2 || !r2.id)
                continue;
            var id2 = "" + r2.id;
            if (!seen[id2])
                next.push(r2);
        }
        rulesModel = next;
    }

    function _mergeUiMissingRules(treeIn, missingIds) {
        var tree = _cloneUiTree(treeIn);
        var flat = _flattenUiRuleIds(tree);
        var seen = {};
        var i;
        for (i = 0; i < flat.length; i++)
            seen[flat[i]] = true;
        var tail = [];
        for (i = 0; i < missingIds.length; i++) {
            var mid = missingIds[i];
            if (!mid || seen[mid])
                continue;
            tail.push({ kind: "rule", rule_id: mid });
            seen[mid] = true;
        }
        return tree.concat(tail);
    }

    function _ruleIdsFromFlatRules(arr) {
        var out = [];
        if (!arr)
            return out;
        for (var i = 0; i < arr.length; i++) {
            if (arr[i] && arr[i].id)
                out.push("" + arr[i].id);
        }
        return out;
    }

    function _generateUiFolderId() {
        return "fld_" + ("" + Math.random()).slice(2) + "_" + ("" + Math.random()).slice(2);
    }

    function _generateRuleId() {
        return "rule_" + ("" + Math.random()).slice(2) + "_" + ("" + Math.random()).slice(2);
    }

    function _saveUiLayoutOnly() {
        if (!actApi || root._rulesPersistBlocked)
            return;
        try {
            actApi.saveRulesUiLayoutJson(platform, accountKey, JSON.stringify({
                                                               schema_version: 1,
                                                               tree: rulesUiTree || []
                                                           }));
        } catch (e0) {
        }
    }


    function _mergeActionsIntoRulesModel() {
        if (root.selectedRule === null || root.selectedIdx < 0)
            return;
        var idx = root.selectedIdx;
        var full;
        try { full = JSON.parse(JSON.stringify(rulesModel)); } catch (e) { return; }
        if (idx < 0 || idx >= full.length)
            return;
        var r = root._normalizeRuleEvents(root._copyRule(full[idx]));
        if (!r)
            return;
        try {
            r.actions = JSON.parse(JSON.stringify(root.actionsModel));
        } catch (e2) {
            r.actions = [];
        }
        if (r.event)
            delete r.event;
        try {
            if (JSON.stringify(full[idx]) === JSON.stringify(r))
                return;
        } catch (e3) {
        }
        full[idx] = r;
        rulesModel = full;
    }

    function _updateActionsModel(aa, scheduleSave) {
        if (root._suppressActionsAutosave)
            return;
        var next;
        try {
            next = JSON.parse(JSON.stringify(aa));
        } catch (e) {
            return;
        }
        try {
            if (JSON.stringify(root.actionsModel) === JSON.stringify(next))
                return;
        } catch (e2) {
        }
        root.actionsModel = next;
        if (scheduleSave !== false)
            root._scheduleCommitSelectedRuleActions();
    }

    function _saveRulesPayload(showToast) {
        if (!actApi || root._rulesPersistBlocked)
            return;
        root._suppressActionsAutosave = true;
        root._flushTriggerEditsFromCombos();
        root._mergeActionsIntoRulesModel();
        var outRules = [];
        for (var i = 0; i < rulesModel.length; i++) {
            var pr = root._ruleToPersistObj(rulesModel[i]);
            if (pr)
                outRules.push(pr);
        }
        var payload = { schema_version: 1, rules: outRules };
        try {
            payload.ui_layout = JSON.parse(JSON.stringify({ schema_version: 1, tree: rulesUiTree || [] }));
        } catch (e1) {
        }
        actApi.saveRulesJson(platform, accountKey, JSON.stringify(payload));
        root._suppressActionsAutosave = false;
        root.hasUnsavedChanges = false;
        if (showToast)
            _notifySaved();
    }

    function _selectedRuleIndexAfterReorder(oldSelIdx, dragIdx, insertBeforeIdx) {
        if (oldSelIdx < 0)
            return oldSelIdx;
        if (dragIdx === insertBeforeIdx || dragIdx + 1 === insertBeforeIdx)
            return oldSelIdx;
        // Moving downward.
        if (dragIdx < insertBeforeIdx) {
            if (oldSelIdx === dragIdx)
                return insertBeforeIdx - 1;
            if (oldSelIdx > dragIdx && oldSelIdx < insertBeforeIdx)
                return oldSelIdx - 1;
            return oldSelIdx;
        }
        // Moving upward.
        if (oldSelIdx === dragIdx)
            return insertBeforeIdx;
        if (oldSelIdx >= insertBeforeIdx && oldSelIdx < dragIdx)
            return oldSelIdx + 1;
        return oldSelIdx;
    }

    function _moveRuleBefore(ruleId, insertBeforeIdx) {
        var dragIdx = _rulesIndexById(ruleId);
        if (dragIdx < 0 || insertBeforeIdx < 0)
            return;
        var copy = rulesModel.slice();
        if (dragIdx === insertBeforeIdx || dragIdx + 1 === insertBeforeIdx)
            return;
        var item = copy.splice(dragIdx, 1)[0];
        var adj = insertBeforeIdx;
        if (dragIdx < insertBeforeIdx)
            adj = insertBeforeIdx - 1;
        copy.splice(adj, 0, item);
        var selOld = selectedIdx;
        rulesModel = copy;
        selectedIdx = _selectedRuleIndexAfterReorder(selOld, dragIdx, insertBeforeIdx);
        root._nextUiRevision();
        root._syncRulesModelOrder();
        root._saveUiLayoutOnly();
        root._save(false);
    }

    function _moveFolderBefore(folderId, beforeRuleId, beforeFolderId) {
        function removeFolder(nodes, fid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    nodes.splice(i, 1);
                    return n;
                }
                if (n.kind === "folder") {
                    var got = removeFolder(n.children || [], fid);
                    if (got)
                        return got;
                }
            }
            return null;
        }

        function insertAt(nodes, idx, node) {
            var j = Math.max(0, Math.min(idx, nodes.length));
            nodes.splice(j, 0, node);
        }

        var tree = _cloneUiTree(rulesUiTree);
        var fnode = removeFolder(tree, folderId);
        if (!fnode)
            return;

        var pos = tree.length;
        if (beforeRuleId && ("" + beforeRuleId).length) {
            for (var u = 0; u < tree.length; u++) {
                var nx = tree[u];
                if (nx && nx.kind === "rule" && ("" + nx.rule_id) === ("" + beforeRuleId)) {
                    pos = u;
                    break;
                }
            }
        } else if (beforeFolderId && ("" + beforeFolderId).length) {
            for (var v = 0; v < tree.length; v++) {
                var ny = tree[v];
                if (ny && ny.kind === "folder" && ("" + ny.id) === ("" + beforeFolderId)) {
                    pos = v;
                    break;
                }
            }
        }

        insertAt(tree, pos, fnode);

        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _dropRuleOntoFolder(ruleId, folderId) {
        function detachRule(nodes, rid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "rule" && ("" + n.rule_id) === rid) {
                    nodes.splice(i, 1);
                    return true;
                }
                if (n.kind === "folder") {
                    if (detachRule(n.children || [], rid))
                        return true;
                }
            }
            return false;
        }

        function appendToFolder(nodes, fid, rid) {
            for (var j = 0; j < nodes.length; j++) {
                var n = nodes[j];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    if (!n.children)
                        n.children = [];
                    n.children.push({ kind: "rule", rule_id: rid });
                    // UX: auto-expand on drop so user sees the result immediately.
                    n.expanded = true;
                    return true;
                }
                if (n.kind === "folder") {
                    if (appendToFolder(n.children || [], fid, rid))
                        return true;
                }
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        if (!detachRule(tree, ruleId))
            return;
        if (!appendToFolder(tree, folderId, ruleId))
            return;
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _dropOntoRootBetween(ruleId, insertBeforeChildId) {
        function detachRule(nodes, rid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "rule" && ("" + n.rule_id) === rid) {
                    nodes.splice(i, 1);
                    return true;
                }
                if (n.kind === "folder") {
                    if (detachRule(n.children || [], rid))
                        return true;
                }
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        if (!detachRule(tree, ruleId))
            return;
        var pos = tree.length;
        if (insertBeforeChildId && ("" + insertBeforeChildId).length) {
            pos = tree.length;
            for (var k = 0; k < tree.length; k++) {
                var nn = tree[k];
                var match = false;
                if (nn && nn.kind === "rule" && ("" + nn.rule_id) === ("" + insertBeforeChildId))
                    match = true;
                else if (nn && nn.kind === "folder" && ("" + nn.id) === ("" + insertBeforeChildId))
                    match = true;
                if (match) {
                    pos = k;
                    break;
                }
            }
        }
        tree.splice(pos, 0, { kind: "rule", rule_id: ruleId });
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _dropOntoFolderBetween(folderId, ruleId, insertBeforeChildId) {
        function detachRule(nodes, rid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "rule" && ("" + n.rule_id) === rid) {
                    nodes.splice(i, 1);
                    return true;
                }
                if (n.kind === "folder") {
                    if (detachRule(n.children || [], rid))
                        return true;
                }
            }
            return false;
        }

        function insertInFolder(nodes, fid, rid, beforeId) {
            for (var j = 0; j < nodes.length; j++) {
                var n = nodes[j];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    if (!n.children)
                        n.children = [];
                    var ch = n.children;
                    var pos = ch.length;
                    if (beforeId && ("" + beforeId).length) {
                        pos = ch.length;
                        for (var t = 0; t < ch.length; t++) {
                            var c = ch[t];
                            if (c && ((c.kind === "rule" && ("" + c.rule_id) === ("" + beforeId))
                                    || (c.kind === "folder" && ("" + c.id) === ("" + beforeId)))) {
                                pos = t;
                                break;
                            }
                        }
                    }
                    ch.splice(pos, 0, { kind: "rule", rule_id: rid });
                    return true;
                }
                if (n.kind === "folder") {
                    if (insertInFolder(n.children || [], fid, rid, beforeId))
                        return true;
                }
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        if (!detachRule(tree, ruleId))
            return;
        if (!insertInFolder(tree, folderId, ruleId, insertBeforeChildId))
            return;
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _moveFolderToParentBefore(folderId, parentFolderId, beforeId) {
        function removeFolder(nodes, fid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === ("" + fid)) {
                    nodes.splice(i, 1);
                    return n;
                }
                if (n.kind === "folder") {
                    var found = removeFolder(n.children || [], fid);
                    if (found)
                        return found;
                }
            }
            return null;
        }

        function insertBefore(nodes, node, bid) {
            var pos = nodes.length;
            if (bid) {
                for (var i = 0; i < nodes.length; i++) {
                    var candidate = nodes[i];
                    if (candidate && ((candidate.kind === "rule" && ("" + candidate.rule_id) === bid)
                            || (candidate.kind === "folder" && ("" + candidate.id) === bid))) {
                        pos = i;
                        break;
                    }
                }
            }
            nodes.splice(pos, 0, node);
            return true;
        }

        function insertInto(nodes, fid, node, bid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid)
                    return insertBefore(n.children || (n.children = []), node, bid);
                if (n.kind === "folder" && insertInto(n.children || [], fid, node, bid))
                    return true;
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        var folder = removeFolder(tree, folderId);
        if (!folder)
            return;
        // A folder cannot be moved into itself or one of its descendants.
        if (parentFolderId && !insertInto(tree, parentFolderId, folder, beforeId))
            return;
        else if (!parentFolderId)
            insertBefore(tree, folder, beforeId);
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _deleteFolderKeepRules(folderId) {
        function liftFolder(nodes, fid) {
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    var kids = n.children ? n.children.slice() : [];
                    nodes.splice.apply(nodes, [i, 1].concat(kids));
                    return true;
                }
                if (n.kind === "folder") {
                    if (liftFolder(n.children || [], fid))
                        return true;
                }
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        if (!liftFolder(tree, folderId))
            return;
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _insertFolderAtRoot(insertBeforeChildId) {
        var tree = _cloneUiTree(rulesUiTree);
        var fid = _generateUiFolderId();
        var name0 = api ? api.loc("actions.folder_default_name") : "New folder";
        var folder = { kind: "folder", id: fid, name: (name0 || "Folder").substring(0, 120), expanded: true, children: [] };
        var pos = tree.length;
        if (insertBeforeChildId && ("" + insertBeforeChildId).length) {
            for (var k = 0; k < tree.length; k++) {
                var nn = tree[k];
                var match = false;
                if (nn && nn.kind === "rule" && ("" + nn.rule_id) === ("" + insertBeforeChildId))
                    match = true;
                else if (nn && nn.kind === "folder" && ("" + nn.id) === ("" + insertBeforeChildId))
                    match = true;
                if (match) {
                    pos = k;
                    break;
                }
            }
        }
        tree.splice(pos, 0, folder);
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._saveUiLayoutOnly();
            root._save(false);
        });
    }

    function _patchUiRemoveRuleId(rid) {
        function strip(nodes) {
            if (!nodes)
                return;
            for (var i = nodes.length - 1; i >= 0; i--) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "rule") {
                    if (("" + n.rule_id) === rid)
                        nodes.splice(i, 1);
                    continue;
                }
                if (n.kind === "folder") {
                    strip(n.children || []);
                }
            }
        }

        var tree = _cloneUiTree(rulesUiTree);
        strip(tree);
        rulesUiTree = tree;
        root._nextUiRevision();
    }

    function _preserveScroll(fn) {
        var leftY = rulesList ? rulesList.contentY : 0;
        var rightF = rightScroll ? rightScroll.contentItem : null;
        var rightY = rightF ? rightF.contentY : 0;
        fn();
        _restoreScrollIfPossible(rulesList, leftY);
        _restoreScrollIfPossible(rightF, rightY);
    }

    function _commitSelectedRuleActions(showToast) {
        actionsAutosaveTimer.stop();
        root._save(!!showToast);
    }

    function _scheduleCommitSelectedRuleActions() {
        if (root._suppressActionsAutosave)
            return;
        actionsAutosaveTimer.restart();
    }

    function _selectRule(idx, rid) {
        actionsAutosaveTimer.stop();
        if (root.selectedIdx >= 0 && idx !== root.selectedIdx)
            root._save(false);
        root.selectedRuleId = rid ? ("" + rid) : "";
        root.selectedIdx = idx;
    }

    readonly property var actionTypeModel: [
        { text: api ? api.loc("actions.play_sound") : "Play sound", value: "play_sound" },
        { text: api ? api.loc("actions.play_random_myinstants_ua") : "Random MyInstants UA", value: "play_random_myinstants_ua" },
        { text: api ? api.loc("actions.write_file") : "Write to file", value: "write_file" },
        { text: api ? api.loc("actions.run_program") : "Run program", value: "run_program" },
        { text: api ? api.loc("actions.simulate_keystrokes") : "Simulate keystrokes", value: "simulate_keystrokes" },
        { text: api ? api.loc("actions.speak_tts") : "Speak text (TTS)", value: "speak_tts" },
        { text: api ? api.loc("actions.show_overlay") : "Show on Actions overlay", value: "show_overlay" },
        { text: api ? api.loc("actions.obs_scene") : "OBS scene", value: "obs_scene" }
    ]

    function _actionTypeIndex(t) {
        var raw = (t || "play_sound");
        var v = (raw === "run_exe") ? "run_program" : raw;
        for (var i = 0; i < actionTypeModel.length; i++) {
            if (actionTypeModel[i].value === v) return i;
        }
        return 0;
    }

    component ConnPillButton: Button {
        id: pillCtl
        property int pillFontSize: 13
        property color colRest: "#1c2434"
        property color colHover: "#263246"
        property color colPress: "#303a50"
        property color borRest: root.cardEdge
        property color borHover: "#3b4458"
        hoverEnabled: true
        font.pixelSize: pillFontSize
        contentItem: Text {
            text: pillCtl.text
            color: root.ink
            font.pixelSize: pillCtl.pillFontSize
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
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

    // Shared Cheremsha button language: filled primary, quiet secondary, compact icon.
    component CheremshaPrimaryButton: Button {
        id: primaryButton
        property string iconName: ""
        property int buttonFontSize: 12
        implicitHeight: 34
        leftPadding: 12
        rightPadding: 12
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: iconName ? root._assetUrl(iconName) : ""
                visible: iconName !== ""
                width: 14
                height: 14
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: primaryButton.text
                color: "white"
                font.pixelSize: primaryButton.buttonFontSize
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            radius: 8
            gradient: Gradient {
                GradientStop { position: 0.0; color: primaryButton.pressed ? "#6d28d9" : (primaryButton.hovered ? "#9d71f7" : "#8b5cf6") }
                GradientStop { position: 1.0; color: primaryButton.pressed ? "#5b21b6" : (primaryButton.hovered ? "#8b5cf6" : "#7c3aed") }
            }
            border.width: 1
            border.color: primaryButton.hovered ? "#c4b5fd" : "#8b54f5"
        }
    }

    component CheremshaSecondaryButton: Button {
        id: secondaryButton
        property string iconName: ""
        property bool danger: false
        property int buttonFontSize: 12
        implicitHeight: 34
        leftPadding: 11
        rightPadding: 11
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Row {
            anchors.centerIn: parent
            spacing: 6
            Image {
                source: iconName ? root._assetUrl(iconName) : ""
                visible: iconName !== ""
                width: 14
                height: 14
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: secondaryButton.text
                color: secondaryButton.danger ? root.dangerRed : root.ink
                font.pixelSize: secondaryButton.buttonFontSize
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        background: Rectangle {
            radius: 8
            color: secondaryButton.pressed ? "#303a50" : (secondaryButton.hovered ? "#263246" : "#161f31")
            border.width: 1
            border.color: secondaryButton.danger
                ? (secondaryButton.hovered ? "#f87171" : "#7f3342")
                : (secondaryButton.hovered ? "#52617a" : "#2a3850")
        }
    }

    component CheremshaLibrarySectionHeader: RowLayout {
        property string iconName: "web_rule.svg"
        property string title: ""
        property string countText: ""
        implicitHeight: 24
        spacing: 6
        Image {
            Layout.preferredWidth: 15
            Layout.preferredHeight: 15
            source: root._assetUrl(parent.iconName)
            fillMode: Image.PreserveAspectFit
            opacity: 0.9
        }
        Text {
            Layout.fillWidth: true
            text: parent.title
            color: root.ink
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            visible: parent.countText !== ""
            text: parent.countText
            color: root.muted
            font.pixelSize: 10
        }
    }

    component CheremshaFilterChip: Button {
        id: filterChip
        property bool active: false
        property int chipFontSize: 11
        implicitHeight: 26
        leftPadding: 10
        rightPadding: 10
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Text {
            text: filterChip.text
            color: filterChip.active ? "white" : root.muted
            font.pixelSize: filterChip.chipFontSize
            font.bold: filterChip.active
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 7
            color: filterChip.active ? "#6d28d9" : (filterChip.hovered ? "#1c2940" : "transparent")
            border.width: 1
            border.color: filterChip.active ? "#8b5cf6" : (filterChip.hovered ? "#52617a" : "#2a3850")
        }
    }

    component CheremshaIconButton: Button {
        id: iconButton
        property string iconName: ""
        property color iconColor: root.ink
        property bool danger: false
        implicitWidth: 30
        implicitHeight: 30
        padding: 0
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        contentItem: Image {
            source: iconButton.iconName ? root._assetUrl(iconButton.iconName) : ""
            width: 14
            height: 14
            anchors.centerIn: parent
            fillMode: Image.PreserveAspectFit
            opacity: iconButton.enabled ? 1.0 : 0.45
        }
        background: Rectangle {
            radius: 7
            color: iconButton.pressed ? "#303a50" : (iconButton.hovered ? "#263246" : "#151e30")
            border.width: 1
            border.color: iconButton.danger
                ? (iconButton.hovered ? "#f87171" : "#7f3342")
                : (iconButton.hovered ? "#52617a" : "#2a3850")
        }
    }

    // Same preference toggle as ConnectionsView.qml `ConnPrefSwitch`.
    component ConnPrefSwitch: Switch {
        id: prefSw
        padding: 0
        implicitWidth: 36
        implicitHeight: 22
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        transformOrigin: Item.Right

        indicator: Rectangle {
            width: prefSw.implicitWidth
            height: prefSw.implicitHeight
            radius: 11
            color: prefSw.checked ? "#134e4a" : "#252d3d"
            border.width: 1
            border.color: prefSw.checked ? "#14b8a6" : "#3b4a63"
            opacity: prefSw.enabled ? 1.0 : 0.55
            Behavior on color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on border.color { ColorAnimation { duration: 140; easing.type: Easing.OutCubic } }

            Rectangle {
                width: 16
                height: 16
                radius: 8
                y: 2
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

    // Keeps the established spacing between rows. DnD feedback is rendered by
    // the root overlay; there is intentionally no native DropArea here.
    component UiRulesDropGap: Item {
        id: gapRoot
        implicitHeight: trailing ? (dndDropZone ? 0 : 14) : 10
        property bool trailing: false
        property bool dndDropZone: false
        property string dndParentFolderId: ""
        property var node: dndDropZone ? { kind: "rule", rule_id: "" } : null
        property var dndArea: dndHitArea
        property string dropBeforeRuleId: ""
        property string dropBeforeFolderId: ""

        Item {
            id: dndHitArea
            visible: gapRoot.dndDropZone
            width: gapRoot.width
            height: gapRoot.dndDropZone ? 24 : 0
        }

        Component.onCompleted: root._registerDndTarget(gapRoot)
        Component.onDestruction: root._unregisterDndTarget(gapRoot)
    }

    component UiRulesRuleRow: Rectangle {
        id: ruleCard
        property var node: null
        property int depth: 0
        property var nextSibling: null
        property string dndParentFolderId: ""
        readonly property var dndArea: ruleCard
        property real dndOffset: root._dndOffsetFor(ruleCard)

        Component.onCompleted: root._registerDndTarget(ruleCard)
        Component.onDestruction: root._dndTargetDestroyed(ruleCard)

        transform: Translate { y: ruleCard.dndOffset }
        Behavior on dndOffset {
            NumberAnimation {
                duration: root.dndAnimationDuration
                easing.type: Easing.OutCubic
            }
        }
        // Opacity is intentionally not animated: the source must disappear in
        // the same frame the preview becomes visible, otherwise both render.
        opacity: root.dndActive && root.dndKind === "rule" && root.dndId === ruleCard.rid ? 0.0 : 1.0

        implicitHeight: ruleMainCol.implicitHeight + 10
        // Search filters the visible list only (never the model / DnD / persistence).
        // Keep the source item alive for MouseArea release/cancel delivery, but
        // make it completely transparent while its one preview is active.
        visible: root._ruleMatchesSearch(ruleObj) && root._ruleMatchesLibraryFilter(ruleObj)
        height: visible ? implicitHeight : 0
        radius: 8
        anchors.left: parent ? parent.left : undefined
        anchors.right: parent ? parent.right : undefined

        property string rid: node && node.rule_id ? ("" + node.rule_id) : ""
        property var ruleObj: rid ? root._ruleById(rid) : null
        property int idxInRules: rid ? root._rulesIndexById(rid) : -1

        color: idxInRules >= 0 && idxInRules === root.selectedIdx ? "#1d2340" : "#111827"
        border.width: idxInRules >= 0 && idxInRules === root.selectedIdx ? 1 : 1
        border.color: idxInRules >= 0 && idxInRules === root.selectedIdx ? root.accentPurple : cardEdge

        MouseArea {
            anchors.fill: parent
            z: -1
            onClicked: {
                if (!rid.length || root.dndActive || root.dndDropPending)
                    return;
                root._selectRule(idxInRules, rid);
            }
        }

        ColumnLayout {
            id: ruleMainCol
            anchors.fill: parent
            anchors.margins: 7
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: 7

                Item {
                    id: dragPad
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 24
                    Layout.alignment: Qt.AlignTop


                    Image {
                        anchors.centerIn: parent
                        source: root._assetUrl("web_drag.svg")
                        width: 14
                        height: 14
                        fillMode: Image.PreserveAspectFit
                        opacity: 0.9
                    }

                    MouseArea {
                        id: ruleDragMa
                        anchors.fill: parent
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: root.dndActive && root.dndSourceTarget === ruleCard
                            ? Qt.ClosedHandCursor : Qt.OpenHandCursor

                        onPressed: function(mouse) {
                            dragPad.forceActiveFocus();
                            var p = dragPad.mapToItem(root, mouse.x, mouse.y);
                            root._dndArm("rule", rid, ruleCard, p.x, p.y);
                        }
                        onPositionChanged: function(mouse) {
                            var p = dragPad.mapToItem(root, mouse.x, mouse.y);
                            root._dndMovePointer(p.x, p.y);
                        }
                        onReleased: function(mouse) {
                            if (root.dndActive && root.dndSourceTarget === ruleCard)
                                root._dndFinish();
                            else
                                root.dndArmed = false;
                        }
                        onCanceled: root._cancelDnd()
                    }

                    activeFocusOnTab: true
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Escape) {
                            root._cancelDnd();
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                                || event.key === Qt.Key_Enter) {
                            if (!root.dndActive && !root.dndDropPending) {
                                var p = dragPad.mapToItem(root, dragPad.width / 2, dragPad.height / 2);
                                root._dndArm("rule", rid, ruleCard, p.x, p.y);
                                root._dndStart(ruleCard);
                            } else if (root.dndActive && root.dndSourceTarget === ruleCard) {
                                root._dndFinish();
                            }
                            event.accepted = true;
                        } else if (root.dndActive && root.dndSourceTarget === ruleCard
                                && event.key === Qt.Key_Up) {
                            root._dndKeyboardMove(-1);
                            event.accepted = true;
                        } else if (root.dndActive && root.dndSourceTarget === ruleCard
                                && event.key === Qt.Key_Down) {
                            root._dndKeyboardMove(1);
                            event.accepted = true;
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 40
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 3

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Image {
                            Layout.preferredWidth: 15
                            Layout.preferredHeight: 15
                            Layout.alignment: Qt.AlignVCenter
                            source: root._assetUrl(root._ruleIconForRow(ruleObj))
                            fillMode: Image.PreserveAspectFit
                            opacity: 0.95
                        }

                        Text {
                            id: ruleTitleLine
                            Layout.fillWidth: true
                            color: ink
                            font.pixelSize: 13
                            font.bold: idxInRules >= 0 && idxInRules === root.selectedIdx
                            wrapMode: Text.NoWrap
                            elide: Text.ElideRight
                            text: root._ruleListTitle(ruleObj || {})
                        }
                    }
                    // Human-readable second line: what the rule reacts to + what it does.
                    // e.g. Слово «привіт» · 1 дія
                    Text {
                        id: ruleSubLine
                        Layout.fillWidth: true
                        leftPadding: 21
                        color: muted
                        font.pixelSize: 11
                        wrapMode: Text.NoWrap
                        elide: Text.ElideRight
                        text: root._ruleLine2(ruleObj || {})
                    }
                }

                ConnPrefSwitch {
                    Layout.alignment: Qt.AlignVCenter
                    checked: ruleObj ? !!ruleObj.enabled : false
                    enabled: ruleObj !== null && idxInRules >= 0
                        && !root.dndActive && !root.dndDropPending
                    onClicked: {
                        if (root.dndActive || root.dndDropPending
                                || ruleObj === null || idxInRules < 0)
                            return;
                        var r2 = root._copyRule(ruleObj);
                        if (r2 == null)
                            return;
                        r2.enabled = checked;
                        root._setRule(idxInRules, r2);
                        root._save(false);
                    }
                }

                // Single compact "…" menu for secondary actions (preview / duplicate / delete).
                // Primary row click = open/edit rule; toggle stays visible for enable/disable.
                Rectangle {
                    id: ruleMoreBtn
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 26
                    radius: 8
                    color: ruleMoreMouse.containsMouse ? "#263246" : "#1c2434"
                    border.width: 1
                    border.color: ruleMoreMouse.containsMouse ? "#3b4458" : cardEdge
                    enabled: idxInRules >= 0 && !root.dndActive && !root.dndDropPending
                    opacity: enabled ? 1.0 : 0.5

                    Image {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        source: root._assetUrl("web_more.svg")
                        fillMode: Image.PreserveAspectFit
                    }

                    MouseArea {
                        id: ruleMoreMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (idxInRules >= 0 && !root.dndActive && !root.dndDropPending)
                                ruleMoreMenu.popup();
                        }
                    }

                    ToolTip.visible: !!(ruleMoreMouse && ruleMoreMouse.containsMouse)
                    ToolTip.delay: 350
                    ToolTip.text: api ? api.loc("actions.rule_more_tt") : "More actions"

                    Menu {
                        id: ruleMoreMenu
                        MenuItem {
                            text: api ? api.loc("actions.rule_preview_tt") : "Test this rule (preview)"
                            enabled: ruleObj !== null && !!ruleObj.id
                            onTriggered: {
                                if (ruleObj === null)
                                    return;
                                var pr = root._ruleToPersistObj(ruleObj);
                                if (!pr)
                                    return;
                                var m = actApi.previewRuleLive(platform, accountKey, pr);
                                root._notifyPreviewToast(m);
                            }
                        }
                        MenuItem {
                            text: api ? api.loc("actions.duplicate_btn") : "Copy"
                            enabled: idxInRules >= 0
                            onTriggered: root._duplicateRuleAt(idxInRules)
                        }
                        MenuSeparator {}
                        MenuItem {
                            text: api ? api.loc("actions.delete") : "Delete"
                            enabled: idxInRules >= 0
                            onTriggered: root._deleteRuleAt(idxInRules)
                        }
                    }
                }
            }
        }


    }

    component UiRulesFolderColumn: ColumnLayout {
        id: folderRoot
        property var node: null
        property int depth: 0
        property var nextSibling: null
        property string dndParentFolderId: ""
        readonly property var dndArea: folderHeader
        property real dndOffset: root._dndOffsetFor(folderRoot)

        Component.onCompleted: root._registerDndTarget(folderRoot)
        Component.onDestruction: root._dndTargetDestroyed(folderRoot)

        transform: Translate { y: folderRoot.dndOffset }
        Behavior on dndOffset {
            NumberAnimation {
                duration: root.dndAnimationDuration
                easing.type: Easing.OutCubic
            }
        }
        // Keep the source handle alive for release/cancel delivery; the entire
        // folder subtree is visually transparent while its preview is active.
        opacity: root.dndActive && root.dndKind === "folder" && root.dndId === folderRoot.fid ? 0.0 : 1.0

        spacing: 6
        anchors.left: parent ? parent.left : undefined
        anchors.right: parent ? parent.right : undefined

        property string fid: node && node.id ? ("" + node.id) : ""
        property bool expanded: !!(node && node.expanded)
        readonly property int childCount: (node && node.children) ? node.children.length : 0
        // Session-only rename edit mode (secondary op, hidden until requested via "…" menu).
        property bool renaming: false

        Rectangle {
            id: folderHeader
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            radius: 0
            color: "transparent"
            border.width: 0

            Rectangle {
                anchors.fill: parent
                radius: folderHeader.radius
                color: root.dndActive && root.dndTargetMode === "folder"
                    && root.dndTargetFolderId === folderRoot.fid ? "#2c6bff33" : "transparent"
                border.width: root.dndActive && root.dndTargetMode === "folder"
                    && root.dndTargetFolderId === folderRoot.fid ? 1 : 0
                border.color: root.accentPurpleSoft
                Behavior on color {
                    ColorAnimation { duration: root.dndAnimationDuration; easing.type: Easing.OutCubic }
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 7

                Item {
                    id: fdDragPad
                    Layout.preferredWidth: 18
                    Layout.fillHeight: true


                    Image {
                        anchors.centerIn: parent
                        source: root._assetUrl("web_drag.svg")
                        width: 14
                        height: 14
                        fillMode: Image.PreserveAspectFit
                        opacity: 0.9
                    }

                    MouseArea {
                        id: folderDragMa
                        anchors.fill: parent
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: root.dndActive && root.dndSourceTarget === folderRoot
                            ? Qt.ClosedHandCursor : Qt.OpenHandCursor

                        onPressed: function(mouse) {
                            fdDragPad.forceActiveFocus();
                            var p = fdDragPad.mapToItem(root, mouse.x, mouse.y);
                            root._dndArm("folder", fid, folderRoot, p.x, p.y);
                        }
                        onPositionChanged: function(mouse) {
                            var p = fdDragPad.mapToItem(root, mouse.x, mouse.y);
                            root._dndMovePointer(p.x, p.y);
                        }
                        onReleased: function(mouse) {
                            if (root.dndActive && root.dndSourceTarget === folderRoot)
                                root._dndFinish();
                            else
                                root.dndArmed = false;
                        }
                        onCanceled: root._cancelDnd()
                    }

                    activeFocusOnTab: true
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Escape) {
                            root._cancelDnd();
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                                || event.key === Qt.Key_Enter) {
                            if (!root.dndActive && !root.dndDropPending) {
                                var p = fdDragPad.mapToItem(root, fdDragPad.width / 2, fdDragPad.height / 2);
                                root._dndArm("folder", fid, folderRoot, p.x, p.y);
                                root._dndStart(folderRoot);
                            } else if (root.dndActive && root.dndSourceTarget === folderRoot) {
                                root._dndFinish();
                            }
                            event.accepted = true;
                        } else if (root.dndActive && root.dndSourceTarget === folderRoot
                                && event.key === Qt.Key_Up) {
                            root._dndKeyboardMove(-1);
                            event.accepted = true;
                        } else if (root.dndActive && root.dndSourceTarget === folderRoot
                                && event.key === Qt.Key_Down) {
                            root._dndKeyboardMove(1);
                            event.accepted = true;
                        }
                    }
                }

                Rectangle {
                    id: folderChevronBtn
                    Layout.preferredWidth: 22
                    Layout.preferredHeight: 22
                    Layout.alignment: Qt.AlignVCenter
                    radius: 5
                    color: folderChevMouse.containsMouse ? "#1c2940" : "transparent"

                    Image {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        source: folderRoot.expanded
                            ? root._assetUrl("chevron-down.svg")
                            : root._assetUrl("chevron-right.svg")
                        fillMode: Image.PreserveAspectFit
                        opacity: 0.9
                    }

                    MouseArea {
                        id: folderChevMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (!root.dndActive && !root.dndDropPending)
                                root._commitFolderToggleUi(fid);
                        }
                    }
                }

                Image {
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                    Layout.alignment: Qt.AlignVCenter
                    source: root._assetUrl("web_folder.svg")
                    fillMode: Image.PreserveAspectFit
                    opacity: 0.95
                }

                // Folder name: plain text by default; rename mode toggled via "…" menu.
                Text {
                    visible: !folderRoot.renaming
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    color: ink
                    font.pixelSize: 13
                    font.bold: true
                    elide: Text.ElideRight
                    text: node ? (node.name || "") : ""

                    MouseArea {
                        anchors.fill: parent
                        onDoubleClicked: {
                            if (!root.dndActive && !root.dndDropPending)
                                folderRoot.renaming = true;
                        }
                    }
                }

                TextField {
                    id: folderRenameField
                    visible: folderRoot.renaming
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    color: ink
                    font.pixelSize: 13
                    maximumLength: 120
                    text: node ? (node.name || "") : ""
                    background: Rectangle {
                        radius: 8
                        color: fieldBg
                        border.width: 1
                        border.color: root.accentPurple
                    }
                    onVisibleChanged: {
                        if (visible) {
                            forceActiveFocus();
                            selectAll();
                        }
                    }
                    onEditingFinished: {
                        folderRoot.renaming = false;
                        root._renameFolder(fid, text);
                    }
                }

                Text {
                    id: countText
                    Layout.alignment: Qt.AlignVCenter
                    visible: folderRoot.childCount > 0
                    text: "(" + folderRoot.childCount + ")"
                    color: muted
                    font.pixelSize: 11
                }

                // Secondary folder ops (rename / delete) live in "…" — clean and uncluttered.
                Rectangle {
                    id: folderMoreBtn
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    radius: 6
                    color: folderMoreMouse.containsMouse ? "#1c2940" : "transparent"
                    border.width: folderMoreMouse.containsMouse ? 1 : 0
                    border.color: "#3b4458"

                    Image {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        source: root._assetUrl("web_more.svg")
                        fillMode: Image.PreserveAspectFit
                    }

                    MouseArea {
                        id: folderMoreMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (!root.dndActive && !root.dndDropPending)
                                folderMoreMenu.popup();
                        }
                    }

                    ToolTip.visible: !!(folderMoreMouse && folderMoreMouse.containsMouse)
                    ToolTip.delay: 350
                    ToolTip.text: api ? api.loc("actions.folder_menu_tt") : "Folder actions"

                    Menu {
                        id: folderMoreMenu
                        MenuItem {
                            text: api ? api.loc("actions.folder_rename") : "Rename"
                            onTriggered: {
                                folderRoot.renaming = true;
                            }
                        }
                        MenuSeparator {}
                        MenuItem {
                            text: api ? api.loc("actions.folder_delete") : "Delete folder"
                            onTriggered: root._deleteFolderKeepRules(fid)
                        }
                    }
                }
            }
        }

        Item {
            id: folderBody
            Layout.fillWidth: true
            Layout.preferredHeight: expanded ? folderInnerCol.implicitHeight : 0
            clip: true

            Rectangle {
                visible: folderRoot.childCount > 0
                x: 16
                y: 0
                width: 1
                height: folderInnerCol.implicitHeight
                color: "#263650"
            }

            Rectangle {
                anchors.fill: folderInnerCol
                anchors.margins: folderRoot.childCount > 0 ? 4 : 0
                radius: 0
                color: "transparent"
                border.width: 0
                visible: false
                z: -1
            }

            Column {
                id: folderInnerCol
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 6

                Repeater {
                    model: (node && node.children) ? node.children : []

                    delegate: UiRulesTreeItem {
                        width: folderInnerCol.width
                        node: modelData
                        depth: folderRoot.depth + 1
                        nextSibling: (index + 1 < ((node && node.children) ? node.children.length : 0))
                            ? node.children[index + 1]
                            : null
                        prevSibling: (node && node.children && index > 0) ? node.children[index - 1] : null
                        parentFolderId: folderRoot.fid
                    }
                }
            }
        }
    }

    Component {
        id: uiRulesRuleRowComp
        UiRulesRuleRow {}
    }

    Component {
        id: uiRulesFolderColumnComp
        UiRulesFolderColumn {}
    }

    component UiRulesTreeItem: ColumnLayout {
        id: treeItemRoot
        property var node: null
        property int depth: 0
        property var nextSibling: null
        property var prevSibling: null
        property string parentFolderId: ""

        spacing: 0
        Layout.fillWidth: true

        UiRulesDropGap {
            Layout.fillWidth: true
            Layout.leftMargin: depth * 16
            visible: !!prevSibling
            dropBeforeRuleId: node && node.kind === "rule" ? ("" + node.rule_id) : ""
            dropBeforeFolderId: node && node.kind === "folder" ? ("" + node.id) : ""
        }

        Loader {
            id: innerRuleLoader
            Layout.fillWidth: true
            Layout.leftMargin: depth * 16
            active: !!node && node.kind !== "folder"
            visible: active
            sourceComponent: uiRulesRuleRowComp

            onLoaded: {
                if (!item || !node)
                    return;
                item.node = node;
                item.depth = depth;
                item.nextSibling = nextSibling;
                item.dndParentFolderId = parentFolderId;
            }
            Connections {
                target: treeItemRoot
                function onNodeChanged() {
                    if (!innerRuleLoader.item || !treeItemRoot.node)
                        return;
                    innerRuleLoader.item.node = treeItemRoot.node;
                    innerRuleLoader.item.depth = treeItemRoot.depth;
                    innerRuleLoader.item.nextSibling = treeItemRoot.nextSibling;
                    innerRuleLoader.item.dndParentFolderId = treeItemRoot.parentFolderId;
                }
                function onParentFolderIdChanged() {
                    if (innerRuleLoader.item)
                        innerRuleLoader.item.dndParentFolderId = treeItemRoot.parentFolderId;
                }
                function onDepthChanged() {
                    if (!innerRuleLoader.item || !treeItemRoot.node)
                        return;
                    innerRuleLoader.item.depth = treeItemRoot.depth;
                }
                function onNextSiblingChanged() {
                    if (!innerRuleLoader.item || !treeItemRoot.node)
                        return;
                    innerRuleLoader.item.nextSibling = treeItemRoot.nextSibling;
                }
            }
        }

        Loader {
            id: innerFolderLoader
            Layout.fillWidth: true
            Layout.leftMargin: depth * 16
            active: !!node && node.kind === "folder"
            visible: active
            sourceComponent: uiRulesFolderColumnComp

            onLoaded: {
                if (!item || !node)
                    return;
                item.node = node;
                item.depth = depth;
                item.nextSibling = nextSibling;
                item.dndParentFolderId = parentFolderId;
            }
            Connections {
                target: treeItemRoot
                function onNodeChanged() {
                    if (!innerFolderLoader.item || !treeItemRoot.node)
                        return;
                    innerFolderLoader.item.node = treeItemRoot.node;
                    innerFolderLoader.item.depth = treeItemRoot.depth;
                    innerFolderLoader.item.nextSibling = treeItemRoot.nextSibling;
                    innerFolderLoader.item.dndParentFolderId = treeItemRoot.parentFolderId;
                }
                function onParentFolderIdChanged() {
                    if (innerFolderLoader.item)
                        innerFolderLoader.item.dndParentFolderId = treeItemRoot.parentFolderId;
                }
                function onDepthChanged() {
                    if (!innerFolderLoader.item || !treeItemRoot.node)
                        return;
                    innerFolderLoader.item.depth = treeItemRoot.depth;
                }
                function onNextSiblingChanged() {
                    if (!innerFolderLoader.item || !treeItemRoot.node)
                        return;
                    innerFolderLoader.item.nextSibling = treeItemRoot.nextSibling;
                }
            }
        }
    }

    // Integer stepper: ConnPill-style − / + and a centered TextField for typing.
    component ConnIntStepper: RowLayout {
        id: stepRoot
        property int fromVal: 1
        property int toVal: 999999
        property int intValue: 1
        signal committed(int v)

        spacing: 8

        function _clamp(n) {
            return Math.max(fromVal, Math.min(toVal, n));
        }

        ConnPillButton {
            text: "−"
            leftPadding: 12
            rightPadding: 12
            topPadding: 6
            bottomPadding: 6
            enabled: stepRoot.intValue > stepRoot.fromVal
            onClicked: stepRoot.committed(stepRoot._clamp(stepRoot.intValue - 1))
        }
        TextField {
            id: stepNumField
            Layout.fillWidth: true
            Layout.minimumWidth: 72
            horizontalAlignment: TextInput.AlignHCenter
            color: root.ink
            font.pixelSize: 13
            inputMethodHints: Qt.ImhDigitsOnly
            validator: IntValidator {
                bottom: stepRoot.fromVal
                top: stepRoot.toVal
            }
            background: Rectangle {
                radius: 8
                color: root.fieldBg
                border.width: 1
                border.color: root.cardEdge
            }
            Component.onCompleted: text = String(stepRoot.intValue)
            Connections {
                target: stepRoot
                function onIntValueChanged() {
                    if (!stepNumField.activeFocus)
                        stepNumField.text = String(stepRoot.intValue);
                }
            }
            onEditingFinished: {
                var raw = (text || "").trim();
                var n = parseInt(raw, 10);
                if (isNaN(n))
                    n = stepRoot.intValue;
                n = stepRoot._clamp(n);
                text = String(n);
                stepRoot.committed(n);
            }
        }
        ConnPillButton {
            text: "+"
            leftPadding: 12
            rightPadding: 12
            topPadding: 6
            bottomPadding: 6
            enabled: stepRoot.intValue < stepRoot.toVal
            onClicked: stepRoot.committed(stepRoot._clamp(stepRoot.intValue + 1))
        }
    }

    component ConnComboBox: ComboBox {
        id: comboBox
        // Default delegate; selection via currentIndexChanged (C++ activated never fires on custom delegate).
        signal picked(int index)
        property var beforePopupOpen: null
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        font.pixelSize: 13
        padding: 10
        contentItem: Text {
            text: comboBox.editable ? (comboBox.editText || "") : comboBox.displayText
            color: root.ink
            font.pixelSize: comboBox.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: root.fieldBg
            border.width: 1
            border.color: comboBox.hovered ? "#3b4458" : root.cardEdge
        }
        onActivated: function (index) {
            comboBox.picked(index);
        }
        popup: Popup {
            y: comboBox.height
            width: comboBox.width
            implicitHeight: contentItem.implicitHeight
            padding: 4
            onAboutToShow: {
                if (comboBox.beforePopupOpen)
                    comboBox.beforePopupOpen();
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: comboBox.popup.visible ? comboBox.delegateModel : null
                currentIndex: comboBox.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
            background: Rectangle {
                radius: 8
                color: "#111827"
                border.width: 1
                border.color: root.cardEdge
            }
        }
    }

    component ConnCheckBox: CheckBox {
        id: chk
        spacing: 8
        font.pixelSize: 13
        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: chk.leftPadding
            y: parent.height / 2 - height / 2
            radius: 4
            color: chk.down ? "#1a2232" : (chk.checked ? "#134e4a" : root.fieldBg)
            border.width: 1
            border.color: chk.checked ? "#14b8a6" : (chk.hovered ? "#3b4458" : root.cardEdge)
            Image {
                anchors.centerIn: parent
                width: 12
                height: 12
                source: root._assetUrl("check.svg")
                fillMode: Image.PreserveAspectFit
                opacity: chk.checked ? 1.0 : 0.0
            }
        }
        contentItem: Text {
            text: chk.text
            font: chk.font
            opacity: chk.enabled ? 1.0 : 0.55
            color: root.ink
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            leftPadding: chk.indicator.width + chk.spacing
        }
    }

    component ConnSlider: Slider {
        id: sl
        property color trackColor: "#14b8a6"
        implicitHeight: 28
        background: Rectangle {
            x: sl.leftPadding
            y: sl.topPadding + sl.availableHeight / 2 - height / 2
            implicitWidth: 200
            implicitHeight: 4
            width: sl.availableWidth
            height: implicitHeight
            radius: 2
            color: "#252d3d"
            Rectangle {
                width: sl.visualPosition * parent.width
                height: parent.height
                color: sl.trackColor
                radius: 2
            }
        }
        handle: Rectangle {
            x: sl.leftPadding + sl.visualPosition * (sl.availableWidth - width)
            y: sl.topPadding + sl.availableHeight / 2 - height / 2
            implicitWidth: 14
            implicitHeight: 14
            radius: 7
            color: sl.pressed ? root.ink : "#cbd5e1"
            border.width: 1
            border.color: sl.hovered ? sl.trackColor : "#3b4a63"
        }
    }

    // _copyRule / _setRule: JSON round-trip so list rows never share one object
    // (e.g. duplicate had re-inserted the same ref; one gift edit touched every row).
    function _copyRule(rule) {
        if (rule == null) return null;
        try { return JSON.parse(JSON.stringify(rule)); } catch (e) { return null; }
    }

    function _cloneOrEmptyRule(src) {
        var o = _copyRule(src);
        if (o) return o;
        return { id: ("" + Math.random()).slice(2), name: "", enabled: true,
            events: [root._chatEvent({
                platform: "all",
                text: "",
                match: "contains",
                case_sensitive: false
            })],
            actions: [] };
    }

    // Never mutate r.event / r.event.params in place: separate rules can share references.
    // Always replace event with a fresh object tree.
    function _chatEvent(p) {
        var plat = "all";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "chat_keyword",
            platform: plat,
            params: {
                text: p.text != null && p.text !== undefined ? p.text : "",
                match: p.match || "contains",
                case_sensitive: !!p.case_sensitive
            }
        };
    }

    function _giftEvent(p) {
        var plat = "tiktok";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "gift_received",
            platform: plat,
            params: {
                gift_id: p.gift_id != null && p.gift_id !== undefined ? p.gift_id : "",
                gift_name: p.gift_name != null && p.gift_name !== undefined ? p.gift_name : "",
                min_count: p.min_count !== undefined && p.min_count !== null ? p.min_count : 1
            }
        };
    }

    function _tiktokAnyGiftEvent(p) {
        var plat = "tiktok";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        var ex = [];
        if (p.exclude_gifts && p.exclude_gifts.length) {
            for (var i = 0; i < p.exclude_gifts.length; i++) {
                if (p.exclude_gifts[i] !== undefined && p.exclude_gifts[i] !== null) {
                    var s = ("" + p.exclude_gifts[i]).trim();
                    if (s !== "")
                        ex.push(s);
                }
            }
        }
        return {
            type: "tiktok_any_gift_received",
            platform: plat,
            params: {
                min_price: p.min_price !== undefined && p.min_price !== null ? p.min_price : 1,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : "",
                exclude_gifts: ex
            }
        };
    }

    function _likesEvent(p) {
        var plat = "tiktok";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "tiktok_likes_received",
            platform: plat,
            params: {
                min_count: p.min_count !== undefined && p.min_count !== null ? p.min_count : 1,
                scope: p.scope || "all_users",
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    function _simpleUserEvent(typ, p) {
        var plat = "tiktok";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: typ,
            platform: plat,
            params: {
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    function _tiktokSharedEvent(p) {
        var plat = "tiktok";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "tiktok_shared",
            platform: plat,
            params: {
                min_count: p.min_count !== undefined && p.min_count !== null ? p.min_count : 1,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    function _twitchCheerEvent(p) {
        var plat = "twitch";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "twitch_cheer",
            platform: plat,
            params: {
                min_bits: p.min_bits !== undefined && p.min_bits !== null ? p.min_bits : 1,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    function _twitchRaidEvent(p) {
        var plat = "twitch";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: "twitch_raid",
            platform: plat,
            params: {
                min_viewers: p.min_viewers !== undefined && p.min_viewers !== null ? p.min_viewers : 1,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    function _youtubeAmountEvent(typ, p) {
        var plat = "youtube";
        if (p.platform != null && ("" + p.platform).trim() !== "")
            plat = ("" + p.platform).trim().toLowerCase();
        return {
            type: typ,
            platform: plat,
            params: {
                min_amount: p.min_amount !== undefined && p.min_amount !== null ? p.min_amount : 0,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
            }
        };
    }

    property var triggerKindModel: []

    function _effectiveTriggerPlatform(ev) {
        if (!ev)
            return "all";
        var p = ev.platform;
        if (typeof p === "string" && p.trim().length)
            return p.trim().toLowerCase();
        var t = (ev.type || "").trim();
        if (t === "chat_keyword")
            return "all";
        if (t.indexOf("twitch_") === 0)
            return "twitch";
        if (t.indexOf("youtube_") === 0)
            return "youtube";
        if (t.indexOf("kick_") === 0)
            return "kick";
        return "tiktok";
    }

    function _platformForEdits() {
        return root._effectiveTriggerPlatform(root.editingTrigger);
    }

    function _triggerPlatformModel() {
        return [
            { text: api ? api.loc("actions.trigger_platform_all") : "All platforms", value: "all" },
            { text: api ? api.loc("actions.trigger_platform_tiktok") : "TikTok", value: "tiktok" },
            { text: api ? api.loc("actions.trigger_platform_twitch") : "Twitch", value: "twitch" },
            { text: api ? api.loc("actions.trigger_platform_youtube") : "YouTube", value: "youtube" },
            { text: api ? api.loc("actions.trigger_platform_kick") : "Kick", value: "kick" }
        ];
    }

    function _kindEntriesForPlatform(plat) {
        var p = (plat || "all").trim().toLowerCase();
        var chat = {
            text: api ? api.loc("actions.event.chat_keyword") : "Chat keyword",
            value: "chat_keyword"
        };
        if (p === "all")
            return [chat];
        if (p === "tiktok") {
            return [
                chat,
                {
                    text: api ? api.loc("actions.event.gift_received") : "Gift received",
                    value: "gift_received"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_any_gift_received") : "Any TikTok gift (by price)",
                    value: "tiktok_any_gift_received"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_likes_received") : "TikTok likes",
                    value: "tiktok_likes_received"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_joined") : "Joined (TikTok)",
                    value: "tiktok_joined"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_followed") : "Followed (TikTok)",
                    value: "tiktok_followed"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_shared") : "Shared (TikTok)",
                    value: "tiktok_shared"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_paid_subscribed") : "Paid sub (TikTok)",
                    value: "tiktok_paid_subscribed"
                },
                {
                    text: api ? api.loc("actions.event.tiktok_first_activity") : "First activity (TikTok)",
                    value: "tiktok_first_activity"
                }
            ];
        }
        if (p === "twitch") {
            return [
                chat,
                {
                    text: api ? api.loc("actions.event.twitch_follow") : "Follow (Twitch)",
                    value: "twitch_follow"
                },
                {
                    text: api ? api.loc("actions.event.twitch_subscribe") : "New subscription (Twitch)",
                    value: "twitch_subscribe"
                },
                {
                    text: api ? api.loc("actions.event.twitch_resub") : "Resub / sub message (Twitch)",
                    value: "twitch_resub"
                },
                {
                    text: api ? api.loc("actions.event.twitch_sub_gift") : "Gift sub (Twitch)",
                    value: "twitch_sub_gift"
                },
                {
                    text: api ? api.loc("actions.event.twitch_cheer") : "Bits / cheer (Twitch)",
                    value: "twitch_cheer"
                },
                {
                    text: api ? api.loc("actions.event.twitch_raid") : "Raid (Twitch)",
                    value: "twitch_raid"
                }
            ];
        }
        if (p === "youtube") {
            return [
                chat,
                {
                    text: api ? api.loc("actions.event.youtube_superchat") : "Super Chat (YouTube)",
                    value: "youtube_superchat"
                },
                {
                    text: api ? api.loc("actions.event.youtube_supersticker") : "Super Sticker (YouTube)",
                    value: "youtube_supersticker"
                },
                {
                    text: api ? api.loc("actions.event.youtube_member") : "New member (YouTube)",
                    value: "youtube_member"
                }
            ];
        }
        if (p === "kick") {
            return [
                chat,
                {
                    text: api ? api.loc("actions.event.kick_follow") : "Follow (Kick)",
                    value: "kick_follow"
                },
                {
                    text: api ? api.loc("actions.event.kick_subscription") : "Subscription (Kick)",
                    value: "kick_subscription"
                },
                {
                    text: api ? api.loc("actions.event.kick_gift_sub") : "Gift sub (Kick)",
                    value: "kick_gift_sub"
                },
                {
                    text: api ? api.loc("actions.event.kick_gift") : "KICKS gifted (Kick)",
                    value: "kick_gift"
                }
            ];
        }
        return [chat];
    }

    function _kindAllowedOnPlatform(kind, plat) {
        var entries = root._kindEntriesForPlatform(plat);
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].value === kind)
                return true;
        }
        return false;
    }

    function _rebuildTriggerKindModelForPlatform(plat) {
        root.triggerKindModel = root._kindEntriesForPlatform(plat);
    }

    function _triggerKindIndex(typ) {
        var t = (typ || "").trim();
        var m = root.triggerKindModel;
        for (var i = 0; i < m.length; i++) {
            if (m[i].value === t)
                return i;
        }
        return 0;
    }

    function _syncPlatformAndKindCombos(ev) {
        if (!ev) {
            root._rebuildTriggerKindModelForPlatform("all");
            if (triggerPlatformCombo)
                triggerPlatformCombo.currentIndex = 0;
            if (triggerKindCombo)
                triggerKindCombo.currentIndex = 0;
            return;
        }
        var tp = root._effectiveTriggerPlatform(ev);
        root._rebuildTriggerKindModelForPlatform(tp);
        if (triggerPlatformCombo) {
            var tpm = root._triggerPlatformModel();
            var pi = 0;
            for (var ti = 0; ti < tpm.length; ti++) {
                if (tpm[ti].value === tp) {
                    pi = ti;
                    break;
                }
            }
            triggerPlatformCombo.currentIndex = pi;
        }
        if (triggerKindCombo)
            triggerKindCombo.currentIndex = root._triggerKindIndex(ev.type);
    }

    function _likesScopeUsesNamedViewer(scope) {
        var s = (scope || "").trim();
        return s === "user_combo" || s === "user_every_n";
    }

    function _likesScopeModel() {
        return [
            { text: api ? api.loc("actions.likes_scope_all") : "All viewers (total)", value: "all_users" },
            { text: api ? api.loc("actions.likes_scope_user_stream") : "Any viewer (stream total)", value: "user_stream" },
            { text: api ? api.loc("actions.likes_scope_user_combo") : "One viewer (one tap combo)", value: "user_combo" },
            {
                text: api ? api.loc("actions.likes_scope_user_every_n") : "One viewer (every N likes)",
                value: "user_every_n"
            }
        ];
    }

    function _likesScopeIndex(scope) {
        var s = (scope || "all_users").trim();
        var m = root._likesScopeModel();
        for (var i = 0; i < m.length; i++) {
            if (m[i].value === s) return i;
        }
        return 0;
    }

    function _normalizeRuleEvents(rule) {
        if (!rule) return null;
        var r = root._copyRule(rule);
        if (!r) return null;
        if (r.events && r.events.length) {
            if (r.event) delete r.event;
            return r;
        }
        if (r.event) {
            r.events = [JSON.parse(JSON.stringify(r.event))];
            delete r.event;
            return r;
        }
        r.events = [root._chatEvent({
            platform: "all",
            text: "",
            match: "contains",
            case_sensitive: false
        })];
        return r;
    }

    function _ruleToPersistObj(rule) {
        var r = root._normalizeRuleEvents(rule);
        if (!r) return null;
        var out = JSON.parse(JSON.stringify(r));
        if (!out.events || !out.events.length)
            out.events = [root._chatEvent({
                platform: "all",
                text: "",
                match: "contains",
                case_sensitive: false
            })];
        if (out.events.length === 1) {
            out.event = out.events[0];
            delete out.events;
        }
        return out;
    }

    function _buildTriggerEventLocal(eventType, platform, ep) {
        var val = (eventType || "chat_keyword").trim();
        var plat = (platform || "all").trim().toLowerCase();
        var p = ep || {};
        if (val === "gift_received")
            return root._giftEvent({
                platform: plat,
                gift_id: p.gift_id || "",
                gift_name: p.gift_name || "",
                min_count: p.min_count || 1
            });
        if (val === "tiktok_any_gift_received")
            return root._tiktokAnyGiftEvent({
                platform: plat,
                min_price: p.min_price || 1,
                user: p.user || "",
                exclude_gifts: p.exclude_gifts || []
            });
        if (val === "tiktok_likes_received")
            return root._likesEvent({
                platform: plat,
                min_count: p.min_count || 1,
                scope: p.scope || "all_users",
                user: p.user || ""
            });
        if (val === "tiktok_shared")
            return root._tiktokSharedEvent({
                platform: plat,
                min_count: p.min_count || 1,
                user: p.user || ""
            });
        if (val === "twitch_cheer")
            return root._twitchCheerEvent({
                platform: plat,
                min_bits: p.min_bits || 1,
                user: p.user || ""
            });
        if (val === "twitch_raid")
            return root._twitchRaidEvent({
                platform: plat,
                min_viewers: p.min_viewers || 1,
                user: p.user || ""
            });
        if (val === "youtube_superchat" || val === "youtube_supersticker")
            return root._youtubeAmountEvent(val, {
                platform: plat,
                min_amount: p.min_amount || 0,
                user: p.user || ""
            });
        if (val === "twitch_follow" || val === "twitch_subscribe" || val === "twitch_resub"
            || val === "twitch_sub_gift" || val === "tiktok_joined" || val === "tiktok_followed"
            || val === "tiktok_paid_subscribed" || val === "tiktok_first_activity"
            || val === "youtube_member" || val === "kick_follow" || val === "kick_subscription"
            || val === "kick_gift_sub" || val === "kick_gift")
            return root._simpleUserEvent(val, { platform: plat, user: p.user || "" });
        return root._chatEvent({
            platform: plat,
            text: p.text || "",
            match: p.match || "contains",
            case_sensitive: !!p.case_sensitive
        });
    }

    function _buildTriggerEventViaApi(eventType, platform, existingEv) {
        var ep = (existingEv && existingEv.params) ? existingEv.params : {};
        if (actApi) {
            try {
                return JSON.parse(actApi.buildTriggerEventJson(eventType, platform, JSON.stringify(ep)));
            } catch (e) {
            }
        }
        return root._buildTriggerEventLocal(eventType, platform, ep);
    }

    function _mergePlatformViaApi(existingEv, newPlatform) {
        if (actApi) {
            try {
                var raw = existingEv ? JSON.stringify(existingEv) : "{}";
                return JSON.parse(actApi.mergeTriggerPlatformJson(raw, newPlatform));
            } catch (e) {
            }
        }
        var cur = existingEv || root._chatEvent({
            platform: "all",
            text: "",
            match: "contains",
            case_sensitive: false
        });
        var typ = (cur.type || "chat_keyword").trim();
        var plat = (newPlatform || "all").trim().toLowerCase();
        var allowed = false;
        var kinds = root._kindEntriesForPlatform(plat);
        for (var i = 0; i < kinds.length; i++) {
            if (kinds[i].value === typ) {
                allowed = true;
                break;
            }
        }
        if (!allowed)
            typ = "chat_keyword";
        return root._buildTriggerEventLocal(typ, plat, cur.params || {});
    }

    function _flushTriggerEditsFromCombos() {
        if (root.selectedRule === null || root._suppressRuleCombos)
            return;
        if (!triggerPlatformCombo || !triggerKindCombo)
            return;
        var tpm = root._triggerPlatformModel();
        var pix = Math.max(0, Math.min(triggerPlatformCombo.currentIndex, tpm.length - 1));
        var plat = tpm[pix].value;
        root._rebuildTriggerKindModelForPlatform(plat);
        var km = root.triggerKindModel;
        if (!km || !km.length)
            return;
        var kix = Math.max(0, Math.min(triggerKindCombo.currentIndex, km.length - 1));
        var val = km[kix].value;
        var cur = root._activeEventForCombos();
        var neu = root._buildTriggerEventViaApi(val, plat, cur);
        if (!neu)
            return;
        var r = root._patchSelectedTrigger(neu);
        if (r == null)
            return;
        root._setRule(root.selectedIdx, r);
    }

    function _patchSelectedTrigger(newEvt) {
        if (root.selectedRule === null) return null;
        var r = root._normalizeRuleEvents(root._copyRule(root.selectedRule));
        if (!r) return null;
        var evs = JSON.parse(JSON.stringify(r.events));
        var ix = Math.max(0, Math.min(root.selectedTriggerIdx, evs.length - 1));
        evs[ix] = newEvt;
        r.events = evs;
        if (r.event) delete r.event;
        return r;
    }

    function _syncTriggerCombos() {
        root._suppressRuleCombos = true;
        var ev = root._activeEventForCombos();
        root._syncPlatformAndKindCombos(ev);
        if (ev && ev.type === "gift_received" && giftRuleCombo) {
            var gi = root._giftOptionIndexForEv(ev);
            if (gi >= 0) {
                giftRuleCombo.currentIndex = gi;
            } else {
                if (giftRuleCombo.count > 0)
                    giftRuleCombo.currentIndex = -1;
                var p = ev.params || {};
                giftRuleCombo.editText = (p.gift_name != null && p.gift_name !== undefined) ? ("" + p.gift_name) : "";
            }
        }
        if (ev && ev.type === "tiktok_likes_received" && likesScopeCombo) {
            var ls = (ev.params && ev.params.scope) || "all_users";
            likesScopeCombo.currentIndex = root._likesScopeIndex(ls);
        }
        ruleCombosSuppressEnd.restart();
    }

    function _oneEventTitle(ev) {
        if (!ev) return "—";
        if (ev.type === "chat_keyword") {
            var kw = (ev.params && ev.params.text) || "";
            return (api ? api.loc("actions.rule_chat_brief") : "Chat") + ": " + kw;
        }
        if (ev.type === "gift_received") {
            var g = (ev.params && ev.params.gift_name) || "";
            return (api ? api.loc("actions.rule_gift_brief") : "Gift") + ": " + g;
        }
        if (ev.type === "tiktok_likes_received") {
            var lp = ev.params || {};
            var mc = lp.min_count != null ? lp.min_count : 1;
            var sc = lp.scope || "all_users";
            return (api ? api.loc("actions.rule_likes_brief") : "Likes") + " · " + mc + " · " + sc;
        }
        if (ev.type === "tiktok_any_gift_received") {
            var ap = ev.params || {};
            var mp = ap.min_price != null ? ap.min_price : 1;
            return (api ? api.loc("actions.event.tiktok_any_gift_received") : "Any gift") + " · ≥" + mp;
        }
        if (ev.type === "tiktok_shared") {
            var sp = ev.params || {};
            var smc = sp.min_count != null ? sp.min_count : 1;
            return (api ? api.loc("actions.event.tiktok_shared") : "Share") + " · ≥" + smc;
        }
        if (ev.type === "tiktok_joined")
            return (api ? api.loc("actions.event.tiktok_joined") : "Joined");
        if (ev.type === "tiktok_followed")
            return (api ? api.loc("actions.event.tiktok_followed") : "Followed");
        if (ev.type === "tiktok_paid_subscribed")
            return (api ? api.loc("actions.event.tiktok_paid_subscribed") : "Paid sub");
        if (ev.type === "tiktok_first_activity")
            return (api ? api.loc("actions.event.tiktok_first_activity") : "First activity");
        if (ev.type === "twitch_follow")
            return (api ? api.loc("actions.event.twitch_follow") : "Follow");
        if (ev.type === "twitch_subscribe")
            return (api ? api.loc("actions.event.twitch_subscribe") : "New sub");
        if (ev.type === "twitch_resub")
            return (api ? api.loc("actions.event.twitch_resub") : "Resub");
        if (ev.type === "twitch_sub_gift")
            return (api ? api.loc("actions.event.twitch_sub_gift") : "Gift sub");
        if (ev.type === "twitch_cheer") {
            var tcp = ev.params || {};
            var mb = tcp.min_bits != null ? tcp.min_bits : 1;
            return (api ? api.loc("actions.event.twitch_cheer") : "Cheer") + " · ≥" + mb + " bits";
        }
        if (ev.type === "twitch_raid") {
            var trp = ev.params || {};
            var mv = trp.min_viewers != null ? trp.min_viewers : 1;
            return (api ? api.loc("actions.event.twitch_raid") : "Raid") + " · ≥" + mv;
        }
        if (ev.type === "youtube_superchat") {
            var ycp = ev.params || {};
            var yca = ycp.min_amount != null ? ycp.min_amount : 0;
            var ycLabel = api ? api.loc("actions.event.youtube_superchat") : "Super Chat";
            return yca > 0 ? (ycLabel + " · ≥" + yca) : ycLabel;
        }
        if (ev.type === "youtube_supersticker") {
            var ysp = ev.params || {};
            var ysa = ysp.min_amount != null ? ysp.min_amount : 0;
            var ysLabel = api ? api.loc("actions.event.youtube_supersticker") : "Super Sticker";
            return ysa > 0 ? (ysLabel + " · ≥" + ysa) : ysLabel;
        }
        if (ev.type === "youtube_member")
            return (api ? api.loc("actions.event.youtube_member") : "New member");
        if (ev.type === "kick_follow")
            return (api ? api.loc("actions.event.kick_follow") : "Follow");
        if (ev.type === "kick_subscription")
            return (api ? api.loc("actions.event.kick_subscription") : "Subscription");
        if (ev.type === "kick_gift_sub")
            return (api ? api.loc("actions.event.kick_gift_sub") : "Gift sub");
        if (ev.type === "kick_gift")
            return (api ? api.loc("actions.event.kick_gift") : "KICKS");
        return ev.type || "—";
    }

    function _syncSelected() {
        var pickId = (selectedRuleId || "").trim();
        var idx = pickId ? _rulesIndexById(pickId) : selectedIdx;
        if (idx < 0 || idx >= rulesModel.length) {
            selectedRule = null;
            selectedIdx = -1;
            selectedRuleId = "";
            actionsModel = [];
            selectedActionIdx = -1;
            root._lastSyncedRuleIdx = -1;
            root._scheduleObsBrowseAutoRefresh();
            return;
        }
        selectedIdx = idx;
        var nextRule = rulesModel[idx];
        if (nextRule && nextRule.id)
            selectedRuleId = "" + nextRule.id;
        var evLen = 0;
        if (nextRule) {
            if (nextRule.events && nextRule.events.length) evLen = nextRule.events.length;
            else if (nextRule.event) evLen = 1;
        }
        if (evLen > 0)
            root.selectedTriggerIdx = Math.max(0, Math.min(root.selectedTriggerIdx, evLen - 1));
        if (idx !== root._lastSyncedRuleIdx) {
            selectedRule = null;
            selectedRule = nextRule;
            try {
                actionsModel = (nextRule && nextRule.actions)
                    ? JSON.parse(JSON.stringify(nextRule.actions)) : [];
            } catch (e) {
                actionsModel = [];
            }
            selectedActionIdx = actionsModel.length ? 0 : -1;
            root._lastSyncedRuleIdx = idx;
        } else {
            selectedRule = nextRule;
        }
        root._scheduleObsBrowseAutoRefresh();
    }

    function _setRule(idx, ruleObj) {
        var full;
        try { full = JSON.parse(JSON.stringify(rulesModel)); }
        catch (e) { return; }
        if (idx < 0 || idx >= full.length) return;
        var one;
        try { one = JSON.parse(JSON.stringify(ruleObj)); }
        catch (e) { return; }
        var prevId = full[idx] && full[idx].id ? ("" + full[idx].id) : "";
        full[idx] = one;
        root._preserveScroll(function() {
            rulesModel = full;
            var nid = one && one.id ? ("" + one.id) : "";
            if (prevId && nid && prevId !== nid) {
                function patchRefs(nodes) {
                    if (!nodes)
                        return;
                    for (var i = 0; i < nodes.length; i++) {
                        var n = nodes[i];
                        if (!n)
                            continue;
                        if (n.kind === "rule" && ("" + n.rule_id) === prevId)
                            n.rule_id = nid;
                        else if (n.kind === "folder")
                            patchRefs(n.children || []);
                    }
                }
                patchRefs(rulesUiTree || []);
                root._nextUiRevision();
                root._saveUiLayoutOnly();
            }
            _syncSelected();
        });
    }

    function _defaultRule() {
        return {
            id: _generateRuleId(),
            name: "",
            enabled: true,
            events: [{ type: "chat_keyword", params: { text: "", match: "contains", case_sensitive: false } }],
            actions: []
        }
    }

    function _giftOptionIndexForEv(ev) {
        if (!ev || ev.type !== "gift_received" || !ev.params)
            return -1;
        var gid = (ev.params.gift_id != null) ? ("" + ev.params.gift_id).trim() : "";
        var gname = (ev.params.gift_name != null) ? ("" + ev.params.gift_name).trim() : "";
        var n = giftOptions.length;
        var i, o, nm;
        if (gid) {
            for (i = 0; i < n; i++) {
                o = giftOptions[i];
                if (o && ("" + (o.id || "")).trim() === gid) return i;
            }
        }
        if (gname) {
            var gl = gname.toLowerCase();
            for (i = 0; i < n; i++) {
                o = giftOptions[i];
                if (o && o.name) {
                    nm = ("" + o.name).toLowerCase();
                    if (nm === gl) return i;
                }
            }
        }
        return -1;
    }

    function _ruleListTitle(r) {
        if (!r) return "—";
        var n = (r.name || "").trim();
        if (n) return n;
        var rr = root._normalizeRuleEvents(r);
        if (!rr || !rr.events || !rr.events.length) return "—";
        if (rr.events.length === 1) {
            var ev = rr.events[0];
            if (ev && ev.type === "chat_keyword") {
                var kw = ev.params && ev.params.text ? ("" + ev.params.text).trim() : "";
                if (kw) return kw.charAt(0).toUpperCase() + kw.substring(1);
            }
            return root._oneEventTitle(ev);
        }
        var parts = [];
        for (var ti = 0; ti < rr.events.length; ti++)
            parts.push(root._oneEventTitle(rr.events[ti]));
        var sep = api ? api.loc("actions.trigger_or_sep") : " | ";
        return parts.join(sep);
    }

    function _ruleListSubtitle(r) {
        if (!r || !r.actions || !r.actions.length)
            return api ? api.loc("actions.rule_no_actions") : "no actions";
        var parts = [];
        for (var i = 0; i < r.actions.length; i++) {
            var a = r.actions[i] || {};
            parts.push(root._actionHumanName(a.type));
        }
        return parts.join(", ");
    }

    function _actionHumanName(t) {
        var v = (t || "").trim();
        if (v === "run_exe") v = "run_program";
        function L(key, fb) { return api ? api.loc(key) : fb; }
        if (v === "play_sound") return L("actions.play_sound", "Програти звук");
        if (v === "play_random_myinstants_ua") return L("actions.play_random_myinstants_ua", "Випадковий звук");
        if (v === "speak_tts") return L("actions.speak_tts", "Озвучити текст");
        if (v === "show_overlay") return L("actions.show_overlay", "Показати в оверлеї");
        if (v === "obs_scene") return L("actions.obs_scene", "Керувати OBS");
        if (v === "write_file") return L("actions.write_file", "Записати у файл");
        if (v === "run_program") return L("actions.run_program", "Запустити програму");
        if (v === "simulate_keystrokes") return L("actions.simulate_keystrokes", "Натиснути клавіші");
        return v || "?";
    }

    // Human-readable "WHEN …" summary for the rule library rows.
    // e.g. 'Чат · Певне слово "привіт"' instead of raw trigger ids.
    function _whenSummary(r) {
        if (!r) return "—";
        var rr = root._normalizeRuleEvents(r);
        if (!rr || !rr.events || !rr.events.length) return "—";
        var parts = [];
        for (var ti = 0; ti < rr.events.length; ti++) {
            (function(ev) {
                var t = (ev && ev.type) ? ("" + ev.type) : "";
                var p = (ev && ev.params) || {};
                var plat = root._effectiveTriggerPlatform(ev);
                var platLabel = "";
                if (plat === "tiktok") platLabel = "TikTok";
                else if (plat === "twitch") platLabel = "Twitch";
                else if (plat === "youtube") platLabel = "YouTube";
                else if (plat === "kick") platLabel = "Kick";
                if (t === "chat_keyword") {
                    var kw = (p.text !== undefined && p.text !== null) ? ("" + p.text).trim() : "";
                    var kindLabel = api ? api.loc("actions.event.chat_keyword") : "Chat keyword";
                    var s = (platLabel ? platLabel + " · " : "Чат · ") + kindLabel;
                    if (kw) s += ' "' + (kw.length > 24 ? kw.substring(0, 24) + "…" : kw) + '"';
                    parts.push(s);
                    return;
                }
                parts.push(root._oneEventTitle(ev));
            })(rr.events[ti]);
        }
        var sep = "  /  ";
        return parts.join(sep);
    }

    function _actionsCountText(r) {
        var n = (r && r.actions) ? r.actions.length : 0;
        if (n === 0) return api ? api.loc("actions.rule_no_actions") : "no actions";
        if (n === 1) return api ? api.loc("actions.rule_one_action") : "1 action";
        var tmpl = api ? api.loc("actions.rule_n_actions") : "%1 actions";
        return ("" + tmpl).replace("%1", "" + n);
    }

    function _shortQuote(s, maxLen) {
        var t = (s !== undefined && s !== null) ? ("" + s).trim() : "";
        if (t.length > maxLen) t = t.substring(0, maxLen) + "…";
        return t;
    }

    // Human-readable single-trigger summary, e.g. Слово «привіт».
    function _humanTrigger(ev) {
        if (!ev) return "—";
        var t = (ev.type || "").trim();
        var p = ev.params || {};
        if (t === "chat_keyword") {
            var kw = root._shortQuote(p.text, 24);
            var tmpl = api ? api.loc("actions.sum_word") : "Word “%1”";
            if (!kw) return api ? api.loc("actions.event.chat_keyword") : "Chat keyword";
            return ("" + tmpl).replace("%1", kw);
        }
        if (t === "gift_received") {
            var gn = (p.gift_name !== undefined && p.gift_name !== null) ? ("" + p.gift_name).trim() : "";
            if (gn) return root._shortQuote(gn, 28);
            return api ? api.loc("actions.event.gift_received") : "Gift received";
        }
        return root._oneEventTitle(ev);
    }

    // Combined second line for rule rows: trigger summary · action count.
    // e.g. Слово «привіт» · 1 дія
    function _ruleLine2(r) {
        if (!r) return "—";
        var rr = root._normalizeRuleEvents(r);
        var trig = "—";
        if (rr && rr.events && rr.events.length) {
            var parts = [];
            for (var i = 0; i < rr.events.length; i++)
                parts.push(root._humanTrigger(rr.events[i]));
            trig = parts.join(" / ");
        }
        return trig + " · " + root._actionsCountText(r);
    }

    function _actionVerb(t) {
        var v = (t || "").trim();
        if (v === "run_exe") v = "run_program";
        function L(key, fb) { return api ? api.loc(key) : fb; }
        if (v === "play_sound") return L("actions.verb_play_sound", "plays a sound");
        if (v === "play_random_myinstants_ua") return L("actions.verb_play_random", "plays a random sound");
        if (v === "speak_tts") return L("actions.verb_speak_tts", "speaks text");
        if (v === "show_overlay") return L("actions.verb_show_overlay", "shows the overlay");
        if (v === "obs_scene") return L("actions.verb_obs", "controls OBS");
        if (v === "write_file") return L("actions.verb_write_file", "writes to a file");
        if (v === "run_program") return L("actions.verb_run_program", "runs a program");
        if (v === "simulate_keystrokes") return L("actions.verb_keystrokes", "presses keys");
        return v || "?";
    }

    function _actionDesc(t) {
        var v = (t || "").trim();
        if (v === "run_exe") v = "run_program";
        function L(key, fb) { return api ? api.loc(key) : fb; }
        if (v === "play_sound") return L("actions.action_desc_play_sound", "Plays an audio file");
        if (v === "play_random_myinstants_ua") return L("actions.action_desc_play_random", "Random sound");
        if (v === "speak_tts") return L("actions.action_desc_speak_tts", "Speaks text aloud");
        if (v === "show_overlay") return L("actions.action_desc_show_overlay", "Shows text on overlay");
        if (v === "obs_scene") return L("actions.action_desc_obs", "Controls the OBS scene");
        if (v === "write_file") return L("actions.action_desc_write_file", "Writes text to a file");
        if (v === "run_program") return L("actions.action_desc_run_program", "Launches a program");
        if (v === "simulate_keystrokes") return L("actions.action_desc_keystrokes", "Simulates key presses");
        return v || "?";
    }

    // Generated rule description for the editor header, e.g.
    // Реагує на слово «привіт» у чаті та програє звук
    function _ruleDescription(r) {
        if (!r) return "";
        var rr = root._normalizeRuleEvents(r);
        var trigText = "";
        if (rr && rr.events && rr.events.length) {
            var ev0 = rr.events[0];
            var t0 = (ev0.type || "").trim();
            var p0 = ev0.params || {};
            if (t0 === "chat_keyword") {
                var kw = root._shortQuote(p0.text, 24) || "…";
                var tmpl = api ? api.loc("actions.desc_word_in_chat") : "the word “%1” in chat";
                trigText = ("" + tmpl).replace("%1", kw);
            } else {
                trigText = root._humanTrigger(ev0);
            }
        }
        var prefix = api ? api.loc("actions.desc_prefix") : "Reacts to ";
        var out = prefix + trigText;
        var acts = (r && r.actions) ? r.actions : [];
        var andWord = api ? api.loc("actions.desc_and") : " and ";
        if (!acts.length) {
            out += api ? api.loc("actions.desc_no_actions") : " (add an action below)";
            return out;
        }
        if (acts.length === 1) {
            out += andWord + root._actionVerb(acts[0].type);
            return out;
        }
        var nTmpl = api ? api.loc("actions.verb_n_actions") : "runs %1 actions";
        out += andWord + ("" + nTmpl).replace("%1", "" + acts.length);
        return out;
    }

    // Rename a folder by id (shared by inline edit + folder menu).
    function _renameFolder(fid, name) {
        var nm = (name || "").trim().substring(0, 120);
        if (!nm.length || !fid.length)
            return false;
        function rename(nodes) {
            if (!nodes)
                return false;
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                if (!n)
                    continue;
                if (n.kind === "folder" && ("" + n.id) === fid) {
                    n.name = nm;
                    return true;
                }
                if (n.kind === "folder") {
                    if (rename(n.children || []))
                        return true;
                }
            }
            return false;
        }
        var tree = root._cloneUiTree(rulesUiTree);
        if (!rename(tree))
            return false;
        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            root._saveUiLayoutOnly();
            root._saveRulesPayload(false);
        });
        return true;
    }

    function _ruleIconForRow(r) {
        var rr = root._normalizeRuleEvents(r);
        var t = (rr && rr.events && rr.events.length) ? ("" + (rr.events[0].type || "")) : "";
        if (t === "gift_received" || t === "tiktok_any_gift_received") return "gift.svg";
        if (t === "tiktok_likes_received") return "web_event_gift.svg";
        if (t.indexOf("superchat") >= 0 || t.indexOf("supersticker") >= 0 || t.indexOf("cheer") >= 0)
            return "donation.svg";
        if (t.indexOf("subscribe") >= 0 || t.indexOf("subscription") >= 0 || t.indexOf("paid_subscribed") >= 0)
            return "web_crown.svg";
        if (t.indexOf("follow") >= 0 || t === "tiktok_joined" || t === "tiktok_shared" || t === "tiktok_first_activity")
            return "users.svg";
        if (t.indexOf("raid") >= 0) return "raid.svg";
        return "chat.svg";
    }

    function _actionIconForType(t) {
        var v = (t || "play_sound").trim();
        if (v === "run_exe") v = "run_program";
        if (v === "play_sound") return "web_volume.svg";
        if (v === "play_random_myinstants_ua") return "web_music.svg";
        if (v === "speak_tts") return "mic.svg";
        if (v === "show_overlay") return "web_camera.svg";
        if (v === "obs_scene") return "web_signal.svg";
        if (v === "write_file") return "copy.svg";
        if (v === "run_program") return "web_arrow_right.svg";
        if (v === "simulate_keystrokes") return "web_key.svg";
        return "web_bolt.svg";
    }

    // Default params for a freshly added action (mirrors the type-switch defaults in the card).
    function _defaultActionParams(t) {
        if (t === "play_sound") return {
            file_path: "",
            volume_percent: 100,
            skip_if_same_playing: false,
            play_immediately: false,
            respect_gift_combo: false
        };
        if (t === "play_random_myinstants_ua") return {
            volume_percent: 100,
            skip_if_same_playing: false,
            play_immediately: false,
            respect_gift_combo: false,
            max_duration_seconds: 0,
            max_page: 1,
            skip_words: ""
        };
        if (t === "write_file") return { file_path: "", text: "", mode: "overwrite" };
        if (t === "run_program") return { program_path: "", arguments: "" };
        if (t === "simulate_keystrokes") return {
            sequence: "",
            hold_ms: 0,
            game_compatibility: false,
            use_interception: false,
            modifier_ctrl: false,
            modifier_alt: false,
            modifier_shift: false
        };
        if (t === "speak_tts") return { text: "" };
        if (t === "show_overlay") return { text: "", seconds: 3 };
        if (t === "obs_scene") return {
            mode: "program_scene",
            canvas_uuid: "",
            scene_name: "",
            source_name: "",
            visible: true,
            revert_previous_state: false,
            revert_delay_seconds: 5
        };
        return {};
    }

    function _clearSelectedRuleActions() {
        if (root.selectedRule === null)
            return;
        var r = root._copyRule(root.selectedRule);
        if (r == null)
            return;
        root.actionsModel = [];
        root.selectedActionIdx = -1;
        r.actions = [];
        root._setRule(root.selectedIdx, r);
        root._markDirty();
        root._save();
    }

    function _moveAction(fromIdx, toIdx) {
        if (root.selectedRule === null || fromIdx < 0 || toIdx < 0)
            return;
        var aa = root.actionsModel.slice();
        if (fromIdx >= aa.length || toIdx >= aa.length)
            return;
        var moved = aa.splice(fromIdx, 1)[0];
        aa.splice(toIdx, 0, moved);
        var r = root._copyRule(root.selectedRule);
        if (r == null)
            return;
        r.actions = aa;
        root.actionsModel = aa;
        root.selectedActionIdx = toIdx;
        root._setRule(root.selectedIdx, r);
        root._markDirty();
        root._save();
    }

    function _addActionOfType(t) {
        if (root.selectedRule === null) return;
        var r = root._copyRule(root.selectedRule);
        if (r == null) return;
        var aa = root.actionsModel.slice();
        var replaceIdx = root.actionPickerReplaceIdx;
        if (replaceIdx >= 0 && replaceIdx < aa.length) {
            aa[replaceIdx] = {
                type: t,
                params: root._defaultActionParams(t)
            };
            root.selectedActionIdx = replaceIdx;
        } else {
            aa.push({ type: t, params: root._defaultActionParams(t) });
            root.selectedActionIdx = aa.length - 1;
        }
        root.actionsModel = aa;
        r.actions = aa;
        root._setRule(root.selectedIdx, r);
        root._markDirty();
        root._save();
        root.showActionPicker = false;
        root.actionPickerReplaceIdx = -1;
        root.actionPickerQuery = "";
    }

    // Action picker model: categorized existing action types only (no invented types).
    function _actionPickerEntries() {
        function label(key, fallback) { return api ? api.loc(key) : fallback; }
        return [
            { group: label("actions.action_group_sound", "Sound"), type: "play_sound",
              title: label("actions.play_sound", "Play sound") },
            { group: label("actions.action_group_sound", "Sound"), type: "play_random_myinstants_ua",
              title: label("actions.play_random_myinstants_ua", "Random MyInstants UA") },
            { group: label("actions.action_group_voice", "Voice & overlay"), type: "speak_tts",
              title: label("actions.speak_tts", "Speak text (TTS)") },
            { group: label("actions.action_group_voice", "Voice & overlay"), type: "show_overlay",
              title: label("actions.show_overlay", "Show on Actions overlay") },
            { group: label("actions.action_group_obs", "OBS"), type: "obs_scene",
              title: label("actions.obs_scene", "OBS scene") },
            { group: label("actions.action_group_system", "System"), type: "write_file",
              title: label("actions.write_file", "Write to file") },
            { group: label("actions.action_group_system", "System"), type: "run_program",
              title: label("actions.run_program", "Run program") },
            { group: label("actions.action_group_system", "System"), type: "simulate_keystrokes",
              title: label("actions.simulate_keystrokes", "Simulate keystrokes") }
        ];
    }

    function _actionPickerFiltered() {
        var q = (root.actionPickerQuery || "").trim().toLowerCase();
        var all = root._actionPickerEntries();
        if (!q) return all;
        var out = [];
        for (var i = 0; i < all.length; i++) {
            var e = all[i];
            if (("" + e.title).toLowerCase().indexOf(q) >= 0
                || ("" + e.group).toLowerCase().indexOf(q) >= 0
                || ("" + e.type).toLowerCase().indexOf(q) >= 0)
                out.push(e);
        }
        return out;
    }

    function _isPinnedRule(r) {
        return !!(r && (r.pinned === true || r.favorite === true || r.is_pinned === true));
    }

    function _topLevelRuleNodes() {
        var out = [];
        var tree = root.rulesUiTree || [];
        for (var i = 0; i < tree.length; i++) {
            if (tree[i] && tree[i].kind === "rule" && tree[i].rule_id)
                out.push(tree[i]);
        }
        return out;
    }

    function _topLevelFolderNodes() {
        var out = [];
        var tree = root.rulesUiTree || [];
        for (var i = 0; i < tree.length; i++) {
            if (tree[i] && tree[i].kind === "folder")
                out.push(tree[i]);
        }
        return out;
    }

    function _pinnedRuleNodes() {
        var out = [];
        var rules = root.rulesModel || [];
        for (var i = 0; i < rules.length; i++) {
            if (_isPinnedRule(rules[i]) && rules[i].id)
                out.push({ kind: "rule", rule_id: "" + rules[i].id });
        }
        return out;
    }

    function _folderCount() {
        function count(nodes) {
            var n = 0;
            for (var i = 0; i < (nodes || []).length; i++) {
                if (!nodes[i]) continue;
                if (nodes[i].kind === "folder") {
                    n++;
                    n += count(nodes[i].children || []);
                }
            }
            return n;
        }
        return count(root.rulesUiTree || []);
    }

    function _unfiledRuleCount() {
        return _topLevelRuleNodes().length;
    }

    function _ruleMatchesLibraryFilter(r) {
        var f = root.libraryFilter || "all";
        if (f === "pinned") return _isPinnedRule(r);
        if (f === "unfiled") {
            var top = _topLevelRuleNodes();
            for (var i = 0; i < top.length; i++)
                if (top[i].rule_id === (r && "" + r.id)) return true;
            return false;
        }
        // The folders filter is applied by the section repeater; keep all
        // children inside those folders visible so the hierarchy remains useful.
        return true;
    }

    function _ruleMatchesSearch(r) {
        var q = (root.ruleSearchText || "").trim().toLowerCase();
        if (!q) return true;
        var hay = [];
        if (r && r.name) hay.push("" + r.name);
        try { hay.push(root._whenSummary(r)); } catch (e0) {}
        try { hay.push(root._ruleLine2(r)); } catch (e1) {}
        try { hay.push(root._ruleListSubtitle(r)); } catch (e2) {}
        return hay.join(" ").toLowerCase().indexOf(q) >= 0;
    }

    function _markDirty() {
        root.hasUnsavedChanges = true;
    }

    function _deleteRuleAt(i) {
        if (i < 0 || i >= rulesModel.length)
            return;
        var killId = rulesModel[i] && rulesModel[i].id ? ("" + rulesModel[i].id) : "";
        var copy = rulesModel.slice();
        copy.splice(i, 1);
        root._preserveScroll(function() {
            rulesModel = copy;
            root._patchUiRemoveRuleId(killId);
            if (("" + root.selectedRuleId) === killId)
                root.selectedRuleId = "";
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._saveRulesPayload(false);
        });
    }

    function _duplicateRuleAt(i) {
        if (i < 0 || i >= rulesModel.length) return;
        root._save(false);
        var srcId = rulesModel[i] && rulesModel[i].id ? ("" + rulesModel[i].id) : "";
        var r = _cloneOrEmptyRule(rulesModel[i]);
        r.id = _generateRuleId();
        var nm = (r.name || "").trim();
        if (nm) {
            var suff = api ? api.loc("actions.rule_name_copy_suffix") : " (copy)";
            r.name = (nm + suff).substring(0, 200);
        }
        var full;
        try { full = JSON.parse(JSON.stringify(rulesModel)); }
        catch (e) { full = rulesModel.slice(); }
        if (!full) full = [];
        full.splice(i + 1, 0, r);
        rulesModel = full;

        function insertAfterRule(nodes, rid, newNode) {
            for (var t = 0; t < nodes.length; t++) {
                var n = nodes[t];
                if (!n)
                    continue;
                if (n.kind === "rule" && ("" + n.rule_id) === rid) {
                    nodes.splice(t + 1, 0, newNode);
                    return true;
                }
                if (n.kind === "folder") {
                    if (insertAfterRule(n.children || [], rid, newNode))
                        return true;
                }
            }
            return false;
        }

        var tree = _cloneUiTree(rulesUiTree);
        var inserted = false;
        if (srcId)
            inserted = insertAfterRule(tree, srcId, { kind: "rule", rule_id: r.id });
        if (!inserted)
            tree.push({ kind: "rule", rule_id: r.id });

        root._preserveScroll(function() {
            rulesUiTree = tree;
            root._nextUiRevision();
            selectedRuleId = "" + r.id;
            selectedIdx = i + 1;
            root._syncRulesModelOrder();
            root._saveUiLayoutOnly();
            root._saveRulesPayload(false);
        });
    }

    function _load() {
        // A reload must never leave a source/preview pair alive.
        root.finishDrag(false);
        if (!actApi) return;
        root._rulesPersistBlocked = true;
        var ok = false;
        try {
            var txt = actApi.loadRulesJson(platform, accountKey);
            var parsed = JSON.parse(txt);
            var raw = parsed.rules || [];
            var norm = [];
            for (var j = 0; j < raw.length; j++) {
                var nr = root._normalizeRuleEvents(raw[j]);
                if (nr) norm.push(nr);
            }
            rulesModel = norm;

            var idsFlat = _ruleIdsFromFlatRules(norm);
            var uiSrc = parsed.ui_layout ? parsed.ui_layout : JSON.parse(actApi.loadRulesUiLayoutJson(platform, accountKey));
            var treeRaw = (uiSrc && uiSrc.tree) ? uiSrc.tree : idsFlat.map(function(id) { return { kind: "rule", rule_id: id }; });
            rulesUiTree = _mergeUiMissingRules(_normalizeUiTree(treeRaw), idsFlat);
            root._syncRulesModelOrder();
            root._nextUiRevision();

            var sel = (selectedRuleId || "").trim();
            if (sel && _rulesIndexById(sel) >= 0)
                selectedIdx = _rulesIndexById(sel);
            else if (rulesModel.length)
                selectedIdx = 0;
            else
                selectedIdx = -1;
            _syncSelected();
            ok = true;
        } catch (e) {
            console.warn("[ActionsView] rules load failed:", e);
            rulesModel = [];
            rulesUiTree = [];
            selectedIdx = -1;
            selectedRuleId = "";
            _syncSelected();
        }
        // Failed load keeps persistence blocked so autosave/UI cannot overwrite good QSettings JSON.
        if (ok) {
            root._rulesPersistBlocked = false;
            root.hasUnsavedChanges = false;
        }
    }

    function _save(showToast) {
        actionsAutosaveTimer.stop();
        root._saveRulesPayload(!!showToast);
    }

    function _reloadGifts() {
        if (!actApi) { giftOptions = []; return; }
        try {
            giftOptions = JSON.parse(actApi.giftOptionsJson(platform, accountKey));
        } catch (e) {
            giftOptions = [];
        }
    }

    function _tryInit() {
        // QML Component.onCompleted can run before MainWindow sets platform/accountKey.
        if (!platform || !accountKey) return;
        _load()
        _reloadGifts()
    }

    Component.onCompleted: {
        _syncTriggerCombos();
        _tryInit();
    }
    onPlatformChanged: {
        _syncTriggerCombos();
        _tryInit();
    }
    onAccountKeyChanged: _tryInit()
    onSelectedIdxChanged: {
        root.selectedTriggerIdx = 0;
        if (selectedIdx >= 0 && selectedIdx < rulesModel.length && rulesModel[selectedIdx] && rulesModel[selectedIdx].id)
            selectedRuleId = "" + rulesModel[selectedIdx].id;
        _syncSelected();
    }
    onRulesModelChanged: _syncSelected()
    onGiftOptionsChanged: {
        var ev = root._activeEventForCombos();
        if (root.selectedRule === null || !ev) return;
        if (ev.type !== "gift_received" || !giftRuleCombo) return;
        root._syncTriggerCombos();
    }
    onSelectedRuleChanged: {
        if (root.selectedRule === null) return;
        root._syncTriggerCombos();
    }
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Rectangle {
            // The library is a panel, not a card around the entire rule tree.
            Layout.preferredWidth: 360
            Layout.minimumWidth: 330
            Layout.maximumWidth: 380
            Layout.fillHeight: true
            radius: 0
            color: "#0b1220"
            border.width: 0

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                width: 1
                color: "#263650"
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 14
                anchors.topMargin: 12
                anchors.bottomMargin: 12
                spacing: 10

                // Library header: title + subtitle (automation-center identity).
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Image {
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        Layout.alignment: Qt.AlignVCenter
                        source: root._assetUrl("web_bolt.svg")
                        fillMode: Image.PreserveAspectFit
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            Layout.fillWidth: true
                            text: api ? api.loc("actions.title") : "Actions"
                            color: ink
                            font.pixelSize: 16
                            font.bold: true
                            wrapMode: Text.Wrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: api ? api.loc("actions.library_subtitle") : "Stream event automation"
                            color: muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // Compact primary action: add rule.
                    CheremshaPrimaryButton {
                        text: api ? api.loc("actions.add_rule") : "Add rule"
                        iconName: "web_plus.svg"
                        Layout.preferredWidth: 150
                        onClicked: {
                            root._save(false);
                            var nr = _defaultRule();
                            // Useful default name so a new rule reads well in the library.
                            var defName = api ? api.loc("actions.new_rule_default_name") : "New rule";
                            nr.name = defName || "New rule";
                            var copy = rulesModel.slice();
                            copy.push(nr);
                            rulesModel = copy;
                            var tree = _cloneUiTree(rulesUiTree);
                            tree.push({ kind: "rule", rule_id: nr.id });
                            root._preserveScroll(function() {
                                rulesUiTree = tree;
                                root._nextUiRevision();
                                selectedRuleId = "" + nr.id;
                                selectedIdx = rulesModel.length - 1;
                                root._syncRulesModelOrder();
                                root._saveUiLayoutOnly();
                                root._saveRulesPayload(false);
                            });
                        }
                    }

                    CheremshaSecondaryButton {
                        text: api ? api.loc("actions.add_folder") : "+ Folder"
                        iconName: "web_folder.svg"
                        Layout.preferredWidth: 105
                        onClicked: root._insertFolderAtRoot("")
                    }
                }

                // Compact search field (filters the visible list only).
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    radius: 8
                    color: fieldBg
                    border.width: 1
                    border.color: cardEdge

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6

                        Image {
                            Layout.preferredWidth: 14
                            Layout.preferredHeight: 14
                            Layout.alignment: Qt.AlignVCenter
                            source: root._assetUrl("web_search.svg")
                            fillMode: Image.PreserveAspectFit
                            opacity: 0.85
                        }

                        TextField {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.search_ph") : "Search rules…"
                            text: root.ruleSearchText
                            font.pixelSize: 12
                            background: Item {}
                            onTextChanged: root.ruleSearchText = text
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    CheremshaFilterChip {
                        text: (api ? api.loc("actions.filter_all") : "Усі") + " (" + (root.rulesModel || []).length + ")"
                        active: root.libraryFilter === "all"
                        onClicked: root.libraryFilter = "all"
                    }
                    CheremshaFilterChip {
                        text: (api ? api.loc("actions.filter_folders") : "Папки") + " (" + root._folderCount() + ")"
                        active: root.libraryFilter === "folders"
                        onClicked: root.libraryFilter = "folders"
                    }
                    CheremshaFilterChip {
                        text: (api ? api.loc("actions.filter_unfiled") : "Без папки") + " (" + root._unfiledRuleCount() + ")"
                        active: root.libraryFilter === "unfiled"
                        onClicked: root.libraryFilter = "unfiled"
                    }
                    Item { Layout.fillWidth: true }
                }

                ScrollView {
                    id: rulesList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    Column {
                        width: Math.max(120, rulesList.availableWidth - 8)
                        spacing: 4

                        CheremshaLibrarySectionHeader {
                            visible: root.libraryFilter === "all" && root._pinnedRuleNodes().length > 0
                            width: parent.width
                            iconName: "pin.svg"
                            title: api ? api.loc("actions.section_pinned") : "Закріплені"
                            countText: "(" + root._pinnedRuleNodes().length + ")"
                        }
                        Repeater {
                            model: root.libraryFilter === "all" ? root._pinnedRuleNodes() : []
                            delegate: UiRulesTreeItem {
                                width: parent.width
                                node: modelData
                                depth: 0
                                nextSibling: (index + 1 < root._pinnedRuleNodes().length) ? root._pinnedRuleNodes()[index + 1] : null
                                prevSibling: index > 0 ? root._pinnedRuleNodes()[index - 1] : null
                            }
                        }

                        Repeater {
                            model: (root.libraryFilter === "all" || root.libraryFilter === "folders")
                                ? root._topLevelFolderNodes() : []
                            delegate: UiRulesTreeItem {
                                width: parent.width
                                node: modelData
                                depth: 0
                                nextSibling: (index + 1 < root._topLevelFolderNodes().length)
                                    ? root._topLevelFolderNodes()[index + 1] : null
                                prevSibling: index > 0 ? root._topLevelFolderNodes()[index - 1] : null
                            }
                        }

                        CheremshaLibrarySectionHeader {
                            visible: (root.libraryFilter === "all" || root.libraryFilter === "unfiled")
                                && root._unfiledRuleCount() > 0
                            width: parent.width
                            iconName: "web_rule.svg"
                            title: api ? api.loc("actions.section_unfiled") : "Без папки"
                            countText: "(" + root._unfiledRuleCount() + ")"
                        }
                        Repeater {
                            model: (root.libraryFilter === "all" || root.libraryFilter === "unfiled")
                                ? root._topLevelRuleNodes() : []
                            delegate: UiRulesTreeItem {
                                width: parent.width
                                node: modelData
                                depth: 0
                                nextSibling: (index + 1 < root._topLevelRuleNodes().length)
                                    ? root._topLevelRuleNodes()[index + 1] : null
                                prevSibling: index > 0 ? root._topLevelRuleNodes()[index - 1] : null
                            }
                        }
                        UiRulesDropGap {
                            id: unfiledTrailingDropGap
                            visible: root.libraryFilter === "all" || root.libraryFilter === "unfiled"
                            width: parent.width
                            trailing: true
                            dndDropZone: root.libraryFilter === "all" || root.libraryFilter === "unfiled"
                        }
                    }
                }
            }
        }

        Rectangle {
            // The editor is an application canvas; only its builder sections are cards.
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 0
            color: "transparent"
            border.width: 0

            ColumnLayout {
                id: editorShell
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                ScrollView {
                    id: rightScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                    // The ScrollView owns the available width; all builder cards fill this content column.
                    width: Math.max(1, rightScroll.availableWidth)
                    spacing: 10

                // Onboarding empty state: shown when no rules exist at all.
                // Never a giant empty editor — explain + primary/secondary creation actions.
                Rectangle {
                    visible: root.selectedIdx < 0 && rulesModel.length === 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: emptyStateCol.implicitHeight + 36
                    radius: 12
                    color: "#111827"
                    border.width: 1
                    border.color: cardEdge

                    ColumnLayout {
                        id: emptyStateCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 8

                        Image {
                            Layout.preferredWidth: 28
                            Layout.preferredHeight: 28
                            Layout.alignment: Qt.AlignHCenter
                            source: root._assetUrl("web_bolt.svg")
                            fillMode: Image.PreserveAspectFit
                        }
                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: api ? api.loc("actions.empty_title") : "Actions automate your stream"
                            color: ink
                            font.pixelSize: 15
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: api ? api.loc("actions.empty_body") : "Create a rule that reacts to chat, gifts, subscriptions and other events automatically."
                            color: muted
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }
                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: 8
                            ConnPillButton {
                                text: api ? api.loc("actions.empty_create_rule") : "+ Create first rule"
                                onClicked: {
                                    var nr = _defaultRule();
                                    var defName = api ? api.loc("actions.new_rule_default_name") : "New rule";
                                    nr.name = defName || "New rule";
                                    var copy = rulesModel.slice();
                                    copy.push(nr);
                                    rulesModel = copy;
                                    var tree = _cloneUiTree(rulesUiTree);
                                    tree.push({ kind: "rule", rule_id: nr.id });
                                    root._preserveScroll(function() {
                                        rulesUiTree = tree;
                                        root._nextUiRevision();
                                        selectedRuleId = "" + nr.id;
                                        selectedIdx = rulesModel.length - 1;
                                        root._syncRulesModelOrder();
                                        root._saveUiLayoutOnly();
                                        root._saveRulesPayload(false);
                                    });
                                }
                            }
                            ConnPillButton {
                                text: api ? api.loc("actions.add_folder") : "+ Folder"
                                onClicked: root._insertFolderAtRoot("")
                            }
                        }
                    }
                }

                Text {
                    visible: root.selectedIdx < 0 && rulesModel.length > 0
                    text: api ? api.loc("actions.pick_rule_hint") : "Pick a rule on the left."
                    color: muted
                    font.pixelSize: 12
                }

                ColumnLayout {
                    visible: root.selectedIdx >= 0
                    Layout.fillWidth: true
                    spacing: 10

                    // Rule identity header: [icon] name + enabled state + natural summary.
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: identityInner.implicitHeight + 20
                        radius: 12
                        color: "#111827"
                        border.width: 1
                        border.color: cardEdge

                        RowLayout {
                            id: identityInner
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Rectangle {
                                Layout.preferredWidth: 38
                                Layout.preferredHeight: 38
                                Layout.alignment: Qt.AlignTop
                                radius: 10
                                color: "#1d2340"
                                border.width: 1
                                border.color: root.accentPurple

                                Image {
                                    anchors.centerIn: parent
                                    width: 20
                                    height: 20
                                    source: root.selectedRule ? root._assetUrl(root._ruleIconForRow(root.selectedRule)) : root._assetUrl("web_rule.svg")
                                    fillMode: Image.PreserveAspectFit
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 5
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        font.pixelSize: 16
                                        font.bold: true
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.rule_name_ph") : "Rule name"
                                        text: root.selectedRule !== null ? (root.selectedRule.name || "") : ""
                                        background: Item {}
                                        onEditingFinished: {
                                            if (root.selectedRule === null) return;
                                            var v = text.trim();
                                            if (v.length > 200) v = v.substring(0, 200);
                                            var r = root._copyRule(root.selectedRule);
                                            if (r == null) return;
                                            r.name = v;
                                            root._setRule(root.selectedIdx, r);
                                            root._markDirty();
                                            root._save();
                                        }
                                    }
                                    Image {
                                        Layout.preferredWidth: 14
                                        Layout.preferredHeight: 14
                                        Layout.alignment: Qt.AlignVCenter
                                        source: root._assetUrl("edit.svg")
                                        fillMode: Image.PreserveAspectFit
                                        opacity: 0.65
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    color: muted
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    text: root.selectedRule ? root._ruleDescription(root.selectedRule) : ""
                                }
                            }

                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: 4

                                ConnPrefSwitch {
                                    Layout.alignment: Qt.AlignHCenter
                                    checked: root.selectedRule ? !!root.selectedRule.enabled : false
                                    enabled: root.selectedRule !== null && root.selectedIdx >= 0
                                    onClicked: {
                                        if (root.selectedRule === null || root.selectedIdx < 0)
                                            return;
                                        var r = root._copyRule(root.selectedRule);
                                        if (r == null)
                                            return;
                                        r.enabled = checked;
                                        root._setRule(root.selectedIdx, r);
                                        root._markDirty();
                                        root._save(false);
                                    }
                                }
                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    color: (root.selectedRule && root.selectedRule.enabled) ? root.okGreen : muted
                                    font.pixelSize: 10
                                    text: (root.selectedRule && root.selectedRule.enabled)
                                        ? (api ? api.loc("actions.rule_enabled") : "Enabled")
                                        : (api ? api.loc("actions.rule_disabled") : "Disabled")
                                }
                            }

                            Item { Layout.fillWidth: true }

                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: 6
                                Text {
                                    visible: !!(root.selectedRule && root.selectedRule.created_at)
                                    text: root.selectedRule && root.selectedRule.created_at
                                        ? "Створено: " + root.selectedRule.created_at : ""
                                    color: muted
                                    font.pixelSize: 10
                                }
                                Text {
                                    visible: !!(root.selectedRule && root.selectedRule.updated_at)
                                    text: root.selectedRule && root.selectedRule.updated_at
                                        ? "Оновлено: " + root.selectedRule.updated_at : ""
                                    color: muted
                                    font.pixelSize: 10
                                }
                                RowLayout {
                                    spacing: 6
                                    CheremshaSecondaryButton {
                                        text: api ? api.loc("actions.duplicate_btn") : "Duplicate"
                                        iconName: "copy.svg"
                                        onClicked: root._duplicateRuleAt(root.selectedIdx)
                                    }
                                    CheremshaSecondaryButton {
                                        text: api ? api.loc("actions.delete") : "Delete"
                                        iconName: "web_trash.svg"
                                        danger: true
                                        onClicked: root._deleteRuleAt(root.selectedIdx)
                                    }
                                }
                            }
                        }
                    }

                    // ============ SECTION 1 — WHEN ============
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: whenInner.implicitHeight + 20
                        radius: 12
                        color: "#121a2e"
                        border.width: 1
                        border.color: root.accentPurple

                        ColumnLayout {
                            id: whenInner
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Image {
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    Layout.alignment: Qt.AlignVCenter
                                    source: root._assetUrl("web_bolt.svg")
                                    fillMode: Image.PreserveAspectFit
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 1
                                    Text {
                                        text: api ? api.loc("actions.when_title") : "WHEN"
                                        color: ink
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                    Text {
                                        text: api ? api.loc("actions.when_subtitle") : "Choose the event that triggers the rule"
                                        color: muted
                                        font.pixelSize: 11
                                    }
                                }
                                ConnPillButton {
                                    visible: root.selectedRule && root.selectedRule.events && root.selectedRule.events.length === 1
                                    Layout.preferredWidth: 68
                                    Layout.minimumWidth: 60
                                    text: "+ АБО"
                                    pillFontSize: 11
                                    hoverEnabled: true
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 350
                                    ToolTip.text: api ? api.loc("actions.add_or_trigger_tt") : "Add alternative trigger (OR)"
                                    onClicked: {
                                        if (root.selectedRule === null) return;
                                        var base = root._normalizeRuleEvents(root._copyRule(root.selectedRule));
                                        if (!base) return;
                                        var evs = JSON.parse(JSON.stringify(base.events));
                                        evs.push(root._chatEvent({
                                            platform: "all",
                                            text: "",
                                            match: "contains",
                                            case_sensitive: false
                                        }));
                                        base.events = evs;
                                        if (base.event) delete base.event;
                                        root.selectedTriggerIdx = evs.length - 1;
                                        root._setRule(root.selectedIdx, base);
                                        root._markDirty();
                                        root._save(false);
                                        root._syncTriggerCombos();
                                    }
                                }
                            }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        visible: root.selectedRule && root.selectedRule.events && root.selectedRule.events.length > 1
                        Text {
                            text: api ? api.loc("actions.triggers_label_when") : "When:"
                            color: muted
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Flickable {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            Layout.maximumHeight: 36
                            Layout.alignment: Qt.AlignVCenter
                            contentWidth: Math.max(width, triggerPillRow.width)
                            contentHeight: 36
                            clip: true
                            flickableDirection: Flickable.HorizontalFlick
                            boundsBehavior: Flickable.StopAtBounds
                            Row {
                                id: triggerPillRow
                                spacing: 8
                                anchors.verticalCenter: parent.verticalCenter
                                Repeater {
                                    model: (root.selectedRule && root.selectedRule.events) ? root.selectedRule.events.length : 0
                                    delegate: ConnPillButton {
                                        text: "" + (index + 1)
                                        font.bold: index === root.selectedTriggerIdx
                                        leftPadding: 12
                                        rightPadding: 12
                                        topPadding: 6
                                        bottomPadding: 6
                                        onClicked: {
                                            root.selectedTriggerIdx = index;
                                            root._syncTriggerCombos();
                                        }
                                    }
                                }
                            }
                        }
                        ConnPillButton {
                            text: "+"
                            Layout.alignment: Qt.AlignVCenter
                            leftPadding: 12
                            rightPadding: 12
                            topPadding: 6
                            bottomPadding: 6
                            onClicked: {
                                if (root.selectedRule === null) return;
                                var base = root._normalizeRuleEvents(root._copyRule(root.selectedRule));
                                if (!base) return;
                                var evs = JSON.parse(JSON.stringify(base.events));
                                evs.push(root._chatEvent({
                                    platform: "all",
                                    text: "",
                                    match: "contains",
                                    case_sensitive: false
                                }));
                                base.events = evs;
                                if (base.event) delete base.event;
                                root.selectedTriggerIdx = evs.length - 1;
                                root._setRule(root.selectedIdx, base);
                                root._save(false);
                                root._syncTriggerCombos();
                            }
                        }
                        ConnPillButton {
                            text: "−"
                            Layout.alignment: Qt.AlignVCenter
                            leftPadding: 12
                            rightPadding: 12
                            topPadding: 6
                            bottomPadding: 6
                            visible: root.selectedRule && root.selectedRule.events && root.selectedRule.events.length > 1
                            onClicked: {
                                if (root.selectedRule === null) return;
                                var base = root._normalizeRuleEvents(root._copyRule(root.selectedRule));
                                if (!base || !base.events || base.events.length <= 1) return;
                                var evs = JSON.parse(JSON.stringify(base.events));
                                var ix = Math.max(0, Math.min(root.selectedTriggerIdx, evs.length - 1));
                                evs.splice(ix, 1);
                                base.events = evs;
                                if (base.event) delete base.event;
                                root.selectedTriggerIdx = Math.max(0, ix - 1);
                                root._setRule(root.selectedIdx, base);
                                root._save(false);
                                root._syncTriggerCombos();
                            }
                        }
                    }

                    // Common trigger controls stay in one horizontal builder row, matching the reference.
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 5
                            Text {
                                text: api ? api.loc("actions.when_platform_label") : "Platform"
                                color: muted
                                font.pixelSize: 11
                            }
                            ConnComboBox {
                        id: triggerPlatformCombo
                        Layout.fillWidth: true
                        model: root._triggerPlatformModel()
                        textRole: "text"
                        valueRole: "value"
                        onPicked: function (idx) {
                            if (root._suppressRuleCombos) return;
                            if (root.selectedRule === null) return;
                            var m = root._triggerPlatformModel();
                            if (idx < 0 || idx >= m.length) return;
                            var newPlat = m[idx].value;
                            root._rebuildTriggerKindModelForPlatform(newPlat);
                            var ev = root._activeEventForCombos();
                            if (!ev) return;
                            var neu = root._mergePlatformViaApi(ev, newPlat);
                            if (!neu) {
                                root._syncTriggerCombos();
                                return;
                            }
                            var r = root._patchSelectedTrigger(neu);
                            if (r == null) return;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                            root._syncTriggerCombos();
                        }
                    }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 5
                            Text {
                                text: api ? api.loc("actions.when_event_label") : "Event type"
                                color: muted
                                font.pixelSize: 11
                            }
                            ConnComboBox {
                        id: triggerKindCombo
                        Layout.fillWidth: true
                        model: root.triggerKindModel
                        textRole: "text"
                        valueRole: "value"
                        beforePopupOpen: function () {
                            if (!triggerPlatformCombo)
                                return;
                            var tpm = root._triggerPlatformModel();
                            var pix = Math.max(0, Math.min(triggerPlatformCombo.currentIndex, tpm.length - 1));
                            root._rebuildTriggerKindModelForPlatform(tpm[pix].value);
                        }
                        onPicked: function (idx) {
                            if (root._suppressRuleCombos) return;
                            if (root.selectedRule === null) return;
                            var km = root.triggerKindModel;
                            if (idx < 0 || idx >= km.length) return;
                            var val = km[idx].value;
                            var tpm = root._triggerPlatformModel();
                            var pix = triggerPlatformCombo ? Math.max(0, Math.min(triggerPlatformCombo.currentIndex, tpm.length - 1)) : 0;
                            var plat = tpm[pix].value;
                            var neu = root._buildTriggerEventViaApi(val, plat, root._activeEventForCombos());
                            if (!neu) {
                                root._syncTriggerCombos();
                                return;
                            }
                            var r = root._patchSelectedTrigger(neu);
                            if (r == null) return;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                            root._syncTriggerCombos();
                        }
                        }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 5

                            // Chat keyword editor
                            ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "chat_keyword"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.keyword") : "Keyword"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.keyword_ph") : "word..."
                            text: root.editingTrigger ? (root.editingTrigger.params.text || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var cur = root._activeEventForCombos();
                                if (!cur || cur.type !== "chat_keyword") return;
                                var ep = cur.params || {};
                                var r = root._patchSelectedTrigger(root._chatEvent({
                                    platform: root._platformForEdits(),
                                    text: text,
                                    match: ep.match,
                                    case_sensitive: ep.case_sensitive
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                            }
                        }
                    }
                    }

                    // Gift editor
                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "gift_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.gift_pick") : "Gift"; color: muted; font.pixelSize: 12 }
                        ConnComboBox {
                            id: giftRuleCombo
                            Layout.fillWidth: true
                            model: giftOptions
                            textRole: "name"
                            valueRole: "id"
                            editable: true
                            delegate: ItemDelegate {
                                width: ListView.view ? ListView.view.width : implicitWidth
                                contentItem: RowLayout {
                                    spacing: 10
                                    Image {
                                        Layout.preferredWidth: 24
                                        Layout.preferredHeight: 24
                                        source: modelData && modelData.image_url ? modelData.image_url : ""
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                        cache: true
                                        visible: source !== ""
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData && modelData.name ? modelData.name : ""
                                        color: root.ink
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: modelData && modelData.price ? (modelData.price + " 🪙") : ""
                                        color: root.muted
                                        font.pixelSize: 12
                                    }
                                }
                            }
                            onPicked: function (idx) {
                                if (root._suppressRuleCombos) return;
                                if (root.selectedRule === null) return;
                                if (idx < 0) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var g = model[idx];
                                var r = root._patchSelectedTrigger(root._giftEvent({
                                    platform: root._platformForEdits(),
                                    gift_id: (g && g.id) || "",
                                    gift_name: (g && g.name) || "",
                                    min_count: ep.min_count
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                            onAccepted: {
                                if (root._suppressRuleCombos) return;
                                // Manual entry fallback: store as gift_name.
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._giftEvent({
                                    platform: root._platformForEdits(),
                                    gift_id: "",
                                    gift_name: editText || "",
                                    min_count: ep.min_count
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.min_count") : "Min count"; color: muted; font.pixelSize: 12 }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999
                            intValue: root.editingTrigger ? (root.editingTrigger.params.min_count || 1) : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._giftEvent({
                                    platform: root._platformForEdits(),
                                    gift_id: ep.gift_id,
                                    gift_name: ep.gift_name,
                                    min_count: v
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    // TikTok any gift (min price) editor
                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "tiktok_any_gift_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.min_price") : "Min price (🪙)"; color: muted; font.pixelSize: 12 }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_price) || 1)
                                : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._tiktokAnyGiftEvent({
                                    platform: root._platformForEdits(),
                                    min_price: v,
                                    user: ep.user || "",
                                    exclude_gifts: ep.exclude_gifts || []
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.user_filter") : "User (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "nickname…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._tiktokAnyGiftEvent({
                                    platform: root._platformForEdits(),
                                    min_price: ep.min_price || 1,
                                    user: text || "",
                                    exclude_gifts: ep.exclude_gifts || []
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }

                        Text {
                            text: (api ? api.loc("actions.exclude_gifts") : "") || "Exclude gifts (do not fire)"
                            color: muted
                            font.pixelSize: 12
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            ConnComboBox {
                                id: tiktokExcludeGiftCombo
                                Layout.fillWidth: true
                                model: root.giftOptions || []
                                textRole: "name"
                                editable: true
                                currentIndex: -1
                                property string placeholderText: (api ? api.loc("actions.exclude_gifts_ph") : "") || "Select a gift or type a name/id…"
                                displayText: currentIndex >= 0 && model && model[currentIndex] && model[currentIndex].name
                                    ? model[currentIndex].name
                                    : editText
                                contentItem: Text {
                                    text: (tiktokExcludeGiftCombo.displayText && ("" + tiktokExcludeGiftCombo.displayText).trim() !== "")
                                        ? tiktokExcludeGiftCombo.displayText
                                        : tiktokExcludeGiftCombo.placeholderText
                                    color: (tiktokExcludeGiftCombo.displayText && ("" + tiktokExcludeGiftCombo.displayText).trim() !== "")
                                        ? root.ink
                                        : root.muted
                                    font.pixelSize: 13
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                    leftPadding: 10
                                    rightPadding: 10
                                }
                                delegate: ItemDelegate {
                                    width: tiktokExcludeGiftCombo.width
                                    contentItem: RowLayout {
                                        spacing: 8
                                        Image {
                                            Layout.preferredWidth: 24
                                            Layout.preferredHeight: 24
                                            source: modelData && modelData.image_url ? modelData.image_url : ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                            cache: true
                                            visible: source !== ""
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData && modelData.name ? modelData.name : ""
                                            color: root.ink
                                            font.pixelSize: 13
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            text: modelData && modelData.price ? (modelData.price + " 🪙") : ""
                                            color: root.muted
                                            font.pixelSize: 12
                                        }
                                    }
                                    background: Rectangle {
                                        radius: 6
                                        color: highlighted ? "#1a2232" : "#111827"
                                    }
                                }
                            }

                            ToolButton {
                                text: "+"
                                Layout.preferredWidth: 44
                                background: Rectangle {
                                    radius: 8
                                    color: fieldBg
                                    border.width: 1
                                    border.color: cardEdge
                                }
                                onClicked: {
                                    if (root.selectedRule === null) return;
                                    var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                    var ex = ep.exclude_gifts || [];
                                    var v = "";
                                    if (tiktokExcludeGiftCombo.currentIndex >= 0 && tiktokExcludeGiftCombo.model
                                            && tiktokExcludeGiftCombo.model[tiktokExcludeGiftCombo.currentIndex]) {
                                        var g = tiktokExcludeGiftCombo.model[tiktokExcludeGiftCombo.currentIndex];
                                        v = (g && g.id) ? ("" + g.id).trim() : (g && g.name) ? ("" + g.name).trim() : "";
                                    }
                                    if (v === "")
                                        v = ("" + (tiktokExcludeGiftCombo.editText || "")).trim();
                                    if (v === "")
                                        return;
                                    var next = [];
                                    for (var i = 0; i < ex.length; i++)
                                        next.push(ex[i]);
                                    var exists = false;
                                    for (var j = 0; j < next.length; j++) {
                                        if (("" + next[j]).trim().toLowerCase() === v.toLowerCase()) {
                                            exists = true;
                                            break;
                                        }
                                    }
                                    if (!exists)
                                        next.push(v);
                                    var r = root._patchSelectedTrigger(root._tiktokAnyGiftEvent({
                                        platform: root._platformForEdits(),
                                        min_price: ep.min_price || 1,
                                        user: ep.user || "",
                                        exclude_gifts: next
                                    }));
                                    if (r == null) return;
                                    root._setRule(root.selectedIdx, r);
                                    root._save();
                                    tiktokExcludeGiftCombo.editText = "";
                                    tiktokExcludeGiftCombo.currentIndex = -1;
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: root.editingTrigger && root.editingTrigger.params && root.editingTrigger.params.exclude_gifts
                                    ? root.editingTrigger.params.exclude_gifts
                                    : []
                                delegate: Rectangle {
                                    radius: 10
                                    color: "#182033"
                                    border.width: 1
                                    border.color: cardEdge
                                    height: 26
                                    width: chipRow.implicitWidth + 18
                                    RowLayout {
                                        id: chipRow
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.left: parent.left
                                        anchors.leftMargin: 8
                                        anchors.right: parent.right
                                        anchors.rightMargin: 8
                                        spacing: 8
                                        Text {
                                            text: ("" + modelData)
                                            color: ink
                                            font.pixelSize: 12
                                            elide: Text.ElideRight
                                        }
                                        ToolButton {
                                            text: "×"
                                            padding: 0
                                            background: Rectangle { color: "transparent" }
                                            contentItem: Text {
                                                text: "×"
                                                color: muted
                                                font.pixelSize: 14
                                                verticalAlignment: Text.AlignVCenter
                                                horizontalAlignment: Text.AlignHCenter
                                            }
                                            onClicked: {
                                                if (root.selectedRule === null) return;
                                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                                var ex = ep.exclude_gifts || [];
                                                var next = [];
                                                for (var i = 0; i < ex.length; i++) {
                                                    if (i === index) continue;
                                                    next.push(ex[i]);
                                                }
                                                var r = root._patchSelectedTrigger(root._tiktokAnyGiftEvent({
                                                    platform: root._platformForEdits(),
                                                    min_price: ep.min_price || 1,
                                                    user: ep.user || "",
                                                    exclude_gifts: next
                                                }));
                                                if (r == null) return;
                                                root._setRule(root.selectedIdx, r);
                                                root._save();
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // TikTok share editor
                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "tiktok_shared"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.min_count") : "Min count"; color: muted; font.pixelSize: 12 }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_count) || 1)
                                : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._tiktokSharedEvent({
                                    platform: root._platformForEdits(),
                                    min_count: v,
                                    user: ep.user || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.user_filter") : "User (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "nickname…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._tiktokSharedEvent({
                                    platform: root._platformForEdits(),
                                    min_count: ep.min_count || 1,
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    // TikTok simple user editor (join/follow/paid-sub/first-activity)
                    ColumnLayout {
                        visible: root.editingTrigger
                            && (root.editingTrigger.type === "tiktok_joined"
                                || root.editingTrigger.type === "tiktok_followed"
                                || root.editingTrigger.type === "tiktok_paid_subscribed"
                                || root.editingTrigger.type === "tiktok_first_activity"
                                || root.editingTrigger.type === "twitch_follow"
                                || root.editingTrigger.type === "twitch_subscribe"
                                || root.editingTrigger.type === "twitch_resub"
                                || root.editingTrigger.type === "twitch_sub_gift"
                                || root.editingTrigger.type === "youtube_member"
                                || root.editingTrigger.type === "kick_follow"
                                || root.editingTrigger.type === "kick_subscription"
                                || root.editingTrigger.type === "kick_gift_sub"
                                || root.editingTrigger.type === "kick_gift")
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: api ? api.loc("actions.user_filter") : "User (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "nickname…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var typ = root.editingTrigger.type || "tiktok_joined";
                                var r = root._patchSelectedTrigger(root._simpleUserEvent(typ, {
                                    platform: root._platformForEdits(),
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "twitch_cheer"
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: api ? api.loc("actions.twitch_min_bits") : "Min bits"
                            color: muted
                            font.pixelSize: 12
                        }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_bits) || 1)
                                : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._twitchCheerEvent({
                                    platform: root._platformForEdits(),
                                    min_bits: v,
                                    user: ep.user || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.user_filter") : "User (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "cheerer…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._twitchCheerEvent({
                                    platform: root._platformForEdits(),
                                    min_bits: ep.min_bits || 1,
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "twitch_raid"
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: api ? api.loc("actions.twitch_min_viewers") : "Min viewers"
                            color: muted
                            font.pixelSize: 12
                        }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_viewers) || 1)
                                : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._twitchRaidEvent({
                                    platform: root._platformForEdits(),
                                    min_viewers: v,
                                    user: ep.user || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.twitch_raider_filter") : "Raider channel (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "channel…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._twitchRaidEvent({
                                    platform: root._platformForEdits(),
                                    min_viewers: ep.min_viewers || 1,
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    // YouTube Super Chat / Super Sticker editor (min amount + optional user)
                    ColumnLayout {
                        visible: root.editingTrigger
                            && (root.editingTrigger.type === "youtube_superchat"
                                || root.editingTrigger.type === "youtube_supersticker")
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: api ? api.loc("actions.youtube_min_amount") : "Min donation amount"
                            color: muted
                            font.pixelSize: 12
                        }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 0
                            toVal: 9999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_amount) || 0)
                                : 0
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var typ = root.editingTrigger.type || "youtube_superchat";
                                var r = root._patchSelectedTrigger(root._youtubeAmountEvent(typ, {
                                    platform: root._platformForEdits(),
                                    min_amount: v,
                                    user: ep.user || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text { text: api ? api.loc("actions.user_filter") : "User (optional)"; color: muted; font.pixelSize: 12 }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.user_filter_ph") : "nickname…"
                            text: root.editingTrigger ? ((root.editingTrigger.params && root.editingTrigger.params.user) || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var typ = root.editingTrigger.type || "youtube_superchat";
                                var r = root._patchSelectedTrigger(root._youtubeAmountEvent(typ, {
                                    platform: root._platformForEdits(),
                                    min_amount: ep.min_amount || 0,
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    // TikTok likes editor
                    ColumnLayout {
                        visible: root.editingTrigger && root.editingTrigger.type === "tiktok_likes_received"
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: api ? api.loc("actions.likes_min_count") : "Likes to trigger"
                            color: muted
                            font.pixelSize: 12
                        }
                        ConnIntStepper {
                            Layout.fillWidth: true
                            fromVal: 1
                            toVal: 999999
                            intValue: root.editingTrigger
                                ? ((root.editingTrigger.params && root.editingTrigger.params.min_count) || 1)
                                : 1
                            onCommitted: function (v) {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var sc0 = ep.scope || "all_users";
                                var r = root._patchSelectedTrigger(root._likesEvent({
                                    platform: root._platformForEdits(),
                                    min_count: v,
                                    scope: sc0,
                                    user: root._likesScopeUsesNamedViewer(sc0) ? (ep.user || "") : ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                        Text {
                            text: api ? api.loc("actions.likes_scope_label") : "Count as"
                            color: muted
                            font.pixelSize: 12
                        }
                        ConnComboBox {
                            id: likesScopeCombo
                            Layout.fillWidth: true
                            model: root._likesScopeModel()
                            textRole: "text"
                            valueRole: "value"
                            onPicked: function (idx) {
                                if (root._suppressRuleCombos) return;
                                if (root.selectedRule === null) return;
                                if (idx < 0) return;
                                var m = root._likesScopeModel();
                                if (idx >= m.length) return;
                                var sc = m[idx].value;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var r = root._patchSelectedTrigger(root._likesEvent({
                                    platform: root._platformForEdits(),
                                    min_count: ep.min_count || 1,
                                    scope: sc,
                                    user: root._likesScopeUsesNamedViewer(sc) ? (ep.user || "") : ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                                root._syncTriggerCombos();
                            }
                        }
                        Text {
                            visible: root.editingTrigger && root.editingTrigger.params
                                && root._likesScopeUsesNamedViewer(root.editingTrigger.params.scope)
                            text: api ? api.loc("actions.likes_user_label") : "Viewer name as in TikTok (optional)"
                            color: muted
                            font.pixelSize: 12
                        }
                        TextField {
                            visible: root.editingTrigger && root.editingTrigger.params
                                && root._likesScopeUsesNamedViewer(root.editingTrigger.params.scope)
                            Layout.fillWidth: true
                            color: ink
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.likes_user_ph") : "nickname…"
                            text: root.editingTrigger ? (root.editingTrigger.params.user || "") : ""
                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                            onEditingFinished: {
                                if (root.selectedRule === null) return;
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
                                var sc1 = ep.scope || "all_users";
                                var r = root._patchSelectedTrigger(root._likesEvent({
                                    platform: root._platformForEdits(),
                                    min_count: ep.min_count || 1,
                                    scope: sc1,
                                    user: root._likesScopeUsesNamedViewer(sc1) ? text : ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: cardEdge; opacity: 0.6 }
                    } // WHEN card ColumnLayout
                    } // WHEN card Rectangle

                    // ============ SECTION 2 — THEN ============
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: thenInner.implicitHeight + 20
                        radius: 12
                        color: "#121a2e"
                        border.width: 1
                        border.color: root.accentTeal

                        ColumnLayout {
                            id: thenInner
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Image {
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    Layout.alignment: Qt.AlignVCenter
                                    source: root._assetUrl("play.svg")
                                    fillMode: Image.PreserveAspectFit
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 1
                                    Text {
                                        text: api ? api.loc("actions.then_title") : "THEN"
                                        color: ink
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                    Text {
                                        text: api ? api.loc("actions.then_subtitle") : "These actions run when the event happens"
                                        color: muted
                                        font.pixelSize: 11
                                    }
                                }
                                CheremshaPrimaryButton {
                                    visible: root.actionsModel && root.actionsModel.length > 0
                                    text: api ? api.loc("actions.add_action_short") : "+ Add action"
                                    iconName: "web_plus.svg"
                                    Layout.preferredWidth: 112
                                    Layout.minimumWidth: 0
                                    Layout.alignment: Qt.AlignVCenter
                                    onClicked: {
                                        root.actionPickerReplaceIdx = -1;
                                        root.showActionPicker = true;
                                    }
                                }
                                CheremshaIconButton {
                                    visible: root.actionsModel && root.actionsModel.length > 0
                                    iconName: "web_more.svg"
                                    Layout.alignment: Qt.AlignVCenter
                                    onClicked: thenMoreMenu.popup()
                                    Menu {
                                        id: thenMoreMenu
                                        MenuItem {
                                            text: api ? (api.loc("actions.clear") || "Clear") : "Clear"
                                            onTriggered: root._clearSelectedRuleActions()
                                        }
                                    }
                                }
                            }

                    // With no actions this is an intentional builder step, not an empty form.
                    Rectangle {
                        visible: !root.actionsModel || root.actionsModel.length === 0
                        Layout.fillWidth: true
                        implicitHeight: emptyActionsCol.implicitHeight + 28
                        radius: 10
                        color: "#0f172a"
                        border.width: 1
                        border.color: cardEdge

                        ColumnLayout {
                            id: emptyActionsCol
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 5

                            CheremshaPrimaryButton {
                                Layout.alignment: Qt.AlignHCenter
                                iconName: "web_plus.svg"
                                text: api ? api.loc("actions.then_empty_cta") : "+ Add first action"
                                onClicked: {
                                    root.actionPickerReplaceIdx = -1;
                                    root.showActionPicker = true;
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: api ? api.loc("actions.then_empty_hint") : "Choose what Cheremsha should do when the rule triggers"
                                color: muted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    ListView {
                        id: actionsList
                        visible: root.actionsModel && root.actionsModel.length > 0
                        Layout.fillWidth: true
                        clip: true
                        interactive: false
                        spacing: 8
                        model: root.actionsModel
                        property int _contentHeightCache: 0
                        implicitHeight: _contentHeightCache
                        onContentHeightChanged: _contentHeightCache = contentHeight
                        // The page ScrollView is the single vertical scroll container.
                        // Expose root API & action types to ListView.view.*
                        property var rootApi: root
                        property var actionTypes: root.actionTypeModel

                        delegate: Rectangle {
                            readonly property var page: actionsList.rootApi

                            function insertKsTag(tag) {
                                if (aType !== "simulate_keystrokes")
                                    return;
                                var aa = page.actionsModel;
                                if (!aa || aIdx < 0 || aIdx >= aa.length)
                                    return;
                                if (!aa[aIdx].params)
                                    aa[aIdx].params = {};
                                var fld = ksStrokeSeq;
                                var pos = fld.cursorPosition;
                                var t0 = fld.text;
                                fld.text = t0.substring(0, pos) + tag + t0.substring(pos);
                                fld.cursorPosition = pos + tag.length;
                                aa[aIdx].params.sequence = fld.text;
                                page._updateActionsModel(aa);
                            }

                            Layout.fillWidth: true
                            width: actionsList.width
                            Layout.minimumWidth: 0
                            radius: 10
                            color: "#111827"
                            border.width: 1
                            border.color: (index === page.selectedActionIdx) ? "#3b4458" : cardEdge

                            readonly property int aIdx: index
                            readonly property string aType: ((modelData && modelData.type) || "play_sound")
                            readonly property string aKind: (aType === "run_exe") ? "run_program" : aType
                            readonly property bool isOpen: index === page.selectedActionIdx
                            // Progressive disclosure for less-frequent sound options (per-card, session-only).
                            property bool playSoundAdvOpen: false
                            property bool playRandomAdvOpen: false
                            // OBS pick lists are global (root._obsPickScenes/_obsPickSources), so do not
                            // tie visibility to selection; selection can lag behind ComboBox popup open.
                            readonly property bool obsBrowseUi: aType === "obs_scene"

                            // ListView delegates must have a reliable implicit height.
                            implicitHeight: cardLayout.implicitHeight + 20
                            height: implicitHeight

                            ColumnLayout {
                                id: cardLayout
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 34
                                        Layout.preferredHeight: 34
                                        Layout.alignment: Qt.AlignTop
                                        radius: 9
                                        color: "#17243a"
                                        border.width: 1
                                        border.color: aType === "play_sound" || aType === "play_random_myinstants_ua"
                                            ? "#0e9f9a" : "#334363"
                                        Image {
                                            anchors.centerIn: parent
                                            width: 18
                                            height: 18
                                            source: page._assetUrl(page._actionIconForType(aType))
                                            fillMode: Image.PreserveAspectFit
                                            opacity: 0.98
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        spacing: 1
                                        Text {
                                            Layout.fillWidth: true
                                            text: page._actionHumanName(aType)
                                            color: ink
                                            font.pixelSize: 13
                                            font.bold: true
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: page._actionDesc(aType)
                                            color: muted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    CheremshaIconButton {
                                        iconName: "chevron-up.svg"
                                        enabled: aIdx > 0
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Перемістити вище"
                                        onClicked: page._moveAction(aIdx, aIdx - 1)
                                    }
                                    CheremshaIconButton {
                                        iconName: "chevron-down.svg"
                                        enabled: aIdx + 1 < page.actionsModel.length
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Перемістити нижче"
                                        onClicked: page._moveAction(aIdx, aIdx + 1)
                                    }
                                    CheremshaIconButton {
                                        iconName: "web_more.svg"
                                        onClicked: actionMoreMenu.popup()
                                        ToolTip.visible: hovered
                                        ToolTip.text: api ? api.loc("actions.rule_more_tt") : "More actions"
                                    }
                                    CheremshaIconButton {
                                        iconName: "web_trash.svg"
                                        danger: true
                                        onClicked: {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var aa = apiRef.actionsModel.slice();
                                            aa.splice(aIdx, 1);
                                            apiRef.actionsModel = aa;
                                            if (page.selectedActionIdx === aIdx) page.selectedActionIdx = -1;
                                            else if (page.selectedActionIdx > aIdx) page.selectedActionIdx = page.selectedActionIdx - 1;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                        ToolTip.visible: hovered
                                        ToolTip.text: api ? api.loc("actions.delete") : "Delete"
                                    }

                                    Menu {
                                        id: actionMoreMenu
                                        MenuItem {
                                            text: "Змінити дію"
                                            onTriggered: {
                                                page.selectedActionIdx = aIdx;
                                                page.actionPickerReplaceIdx = aIdx;
                                                page.actionPickerQuery = "";
                                                page.showActionPicker = true;
                                            }
                                        }
                                    }
                                }

                                // Play sound config
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "play_sound"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_mp3") : "Pick .mp3..."
                                            text: (modelData && modelData.params && modelData.params.file_path) ? modelData.params.file_path : ""
                                            implicitHeight: 36
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: true
                                        }
                                        CheremshaSecondaryButton {
                                            Layout.preferredWidth: 94
                                            Layout.minimumWidth: 86
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            iconName: "web_folder.svg"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;

                                                // Picking a file and/or resetting models can trigger delegate teardown.
                                                // Defer mutations so this click handler can return before the UI rebuilds.
                                                var pickedPath = actApi.pickSoundFile();
                                                if (!pickedPath) return;

                                                var selectedIdx = apiRef.selectedIdx;
                                                var selectedRuleCopy = apiRef._copyRule(apiRef.selectedRule);
                                                if (selectedRuleCopy == null) return;

                                                var actionIndex = aIdx;
                                                var currentActions = apiRef.actionsModel;
                                                if (!currentActions || actionIndex < 0 || actionIndex >= currentActions.length) return;

                                                Qt.callLater(function () {
                                                    // Re-check target still makes sense after any intermediate UI changes.
                                                    if (!apiRef) return;
                                                    if (apiRef.selectedIdx !== selectedIdx) return;

                                                    var aa = apiRef.actionsModel.slice();
                                                    if (actionIndex < 0 || actionIndex >= aa.length) return;

                                                    var ac = apiRef._copyRule(aa[actionIndex]);
                                                    if (ac) aa[actionIndex] = ac;
                                                    aa[actionIndex].params = aa[actionIndex].params || {};
                                                    aa[actionIndex].params.file_path = pickedPath;

                                                    apiRef.actionsModel = aa;
                                                    selectedRuleCopy.actions = aa;
                                                    apiRef._setRule(selectedIdx, selectedRuleCopy);
                                                    apiRef._save();
                                                });
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.play_sound_volume") : "Volume (%)"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        ConnSlider {
                                            id: playSoundVolume
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            from: 0
                                            to: 100
                                            stepSize: 1
                                            value: (modelData && modelData.params && modelData.params.volume_percent !== undefined) ? Number(modelData.params.volume_percent) : 100
                                            onMoved: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.volume_percent = Math.round(value);
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                        Rectangle {
                                            Layout.preferredWidth: 46
                                            Layout.preferredHeight: 24
                                            Layout.alignment: Qt.AlignVCenter
                                            radius: 6
                                            color: "#182033"
                                            border.width: 1
                                            border.color: cardEdge
                                            Text {
                                                anchors.fill: parent
                                                text: Math.round(playSoundVolume.value) + "%"
                                                color: ink
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        id: playSoundSkipDupCb
                                        text: api ? api.loc("actions.play_sound_skip_if_same_playing") : "Skip if this file is already playing or queued"
                                        checked: !!(modelData && modelData.params && modelData.params.skip_if_same_playing)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.skip_if_same_playing === playSoundSkipDupCb.checked) return;
                                            aa[aIdx].params.skip_if_same_playing = playSoundSkipDupCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    // Progressive disclosure: secondary playback rules live here.
                                    ConnPillButton {
                                        // The rule-level Advanced row controls these fields now.
                                        visible: false
                                        text: (api ? api.loc("actions.advanced_params") : "Advanced parameters") + (playSoundAdvOpen ? " −" : " +")
                                        pillFontSize: 11
                                        onClicked: playSoundAdvOpen = !playSoundAdvOpen
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        visible: playSoundAdvOpen || page.thenAdvancedOpen
                                        id: playSoundPlayNowCb
                                        text: api ? api.loc("actions.play_immediately") : "Play immediately (ignore queue)"
                                        checked: !!(modelData && modelData.params && modelData.params.play_immediately)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.play_immediately === playSoundPlayNowCb.checked) return;
                                            aa[aIdx].params.play_immediately = playSoundPlayNowCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        visible: playSoundAdvOpen || page.thenAdvancedOpen
                                        id: playSoundGiftComboCb
                                        text: api ? (api.loc("actions.respect_gift_combo") || "Respect gift combo count") : "Respect gift combo count"
                                        checked: !!(modelData && modelData.params && modelData.params.respect_gift_combo)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.respect_gift_combo === playSoundGiftComboCb.checked) return;
                                            aa[aIdx].params.respect_gift_combo = playSoundGiftComboCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }
                                }

                                // Random MyInstants UA config
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "play_random_myinstants_ua"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.play_sound_volume") : "Volume (%)"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        ConnSlider {
                                            id: playRandomMyinstantsUaVolume
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            from: 0
                                            to: 100
                                            stepSize: 1
                                            value: (modelData && modelData.params && modelData.params.volume_percent !== undefined) ? Number(modelData.params.volume_percent) : 100
                                            onMoved: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.volume_percent = Math.round(value);
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                        Rectangle {
                                            Layout.preferredWidth: 46
                                            Layout.preferredHeight: 24
                                            Layout.alignment: Qt.AlignVCenter
                                            radius: 6
                                            color: "#182033"
                                            border.width: 1
                                            border.color: cardEdge
                                            Text {
                                                anchors.fill: parent
                                                text: Math.round(playRandomMyinstantsUaVolume.value) + "%"
                                                color: ink
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        id: playRandomMyinstantsUaSkipDupCb
                                        text: api ? api.loc("actions.play_sound_skip_if_same_playing") : "Skip if this file is already playing or queued"
                                        checked: !!(modelData && modelData.params && modelData.params.skip_if_same_playing)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.skip_if_same_playing === playRandomMyinstantsUaSkipDupCb.checked) return;
                                            aa[aIdx].params.skip_if_same_playing = playRandomMyinstantsUaSkipDupCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    // Progressive disclosure: secondary random-sound options live here.
                                    ConnPillButton {
                                        // The rule-level Advanced row controls these fields now.
                                        visible: false
                                        text: (api ? api.loc("actions.advanced_params") : "Advanced parameters") + (playRandomAdvOpen ? " −" : " +")
                                        pillFontSize: 11
                                        onClicked: playRandomAdvOpen = !playRandomAdvOpen
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        visible: playRandomAdvOpen || page.thenAdvancedOpen
                                        id: playRandomMyinstantsUaPlayNowCb
                                        text: api ? (api.loc("actions.play_immediately") || "Play immediately (ignore queue)") : "Play immediately (ignore queue)"
                                        checked: !!(modelData && modelData.params && modelData.params.play_immediately)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.play_immediately === playRandomMyinstantsUaPlayNowCb.checked) return;
                                            aa[aIdx].params.play_immediately = playRandomMyinstantsUaPlayNowCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    ConnCheckBox {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        visible: playRandomAdvOpen || page.thenAdvancedOpen
                                        id: playRandomMyinstantsUaGiftComboCb
                                        text: api ? (api.loc("actions.respect_gift_combo") || "Respect gift combo count") : "Respect gift combo count"
                                        checked: !!(modelData && modelData.params && modelData.params.respect_gift_combo)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.respect_gift_combo === playRandomMyinstantsUaGiftComboCb.checked) return;
                                            aa[aIdx].params.respect_gift_combo = playRandomMyinstantsUaGiftComboCb.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    RowLayout {
                                        visible: playRandomAdvOpen || page.thenAdvancedOpen
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.myinstants_skip_words") : "Skip words"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        TextField {
                                            id: playRandomMyinstantsUaSkipWords
                                            Layout.fillWidth: true
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.myinstants_skip_words_ph") : "e.g. meme, loud, siren"
                                            text: (modelData && modelData.params && modelData.params.skip_words !== undefined) ? ("" + modelData.params.skip_words) : ""
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            onActiveFocusChanged: {
                                                page.isActionTextEditing = activeFocus;
                                                if (!activeFocus) page._commitSelectedRuleActions(false);
                                            }
                                            onTextEdited: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.skip_words = text;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    RowLayout {
                                        visible: playRandomAdvOpen || page.thenAdvancedOpen
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.max_duration_seconds") : "Max duration (sec)"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        TextField {
                                            id: playRandomMyinstantsUaMaxDur
                                            Layout.preferredWidth: 120
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: "0"
                                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                                            text: (modelData && modelData.params && modelData.params.max_duration_seconds !== undefined) ? ("" + modelData.params.max_duration_seconds) : "0"
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            onTextEdited: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                var v = parseFloat(text);
                                                if (isNaN(v) || v < 0) v = 0;
                                                aa[aIdx].params.max_duration_seconds = v;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    RowLayout {
                                        visible: playRandomAdvOpen || page.thenAdvancedOpen
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.myinstants_max_page") : "Max page"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        TextField {
                                            id: playRandomMyinstantsUaMaxPage
                                            Layout.preferredWidth: 120
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: "1"
                                            inputMethodHints: Qt.ImhDigitsOnly
                                            text: (modelData && modelData.params && modelData.params.max_page !== undefined) ? ("" + modelData.params.max_page) : "1"
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            onTextEdited: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                var v = parseInt(text);
                                                if (isNaN(v) || v < 1) v = 1;
                                                aa[aIdx].params.max_page = v;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }
                                }

                                // Write file config
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "write_file"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.write_mode") : "Mode"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        ConnComboBox {
                                            Layout.fillWidth: true
                                            model: [
                                                api ? api.loc("actions.write_mode_overwrite") : "Overwrite",
                                                api ? api.loc("actions.write_mode_append") : "Append"
                                            ]
                                            currentIndex: {
                                                var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "overwrite";
                                                return (m === "append") ? 1 : 0;
                                            }
                                            onPicked: function(index) {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.mode = (index === 1) ? "append" : "overwrite";
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_file") : "Pick file..."
                                            text: (modelData && modelData.params && modelData.params.file_path) ? modelData.params.file_path : ""
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: false
                                            onTextChanged: {
                                                // Keep binding updated without rebuilding the full rulesModel
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.file_path = text;
                                                page._updateActionsModel(aa);
                                            }
                                            onActiveFocusChanged: {
                                                if (!activeFocus) page._commitSelectedRuleActions(false);
                                            }
                                        }
                                        ConnPillButton {
                                            Layout.preferredWidth: 94
                                            Layout.minimumWidth: 86
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                // Avoid deleting this delegate while handling the click.
                                                var pickedPath = actApi.pickWriteFile();
                                                if (!pickedPath) return;

                                                var selectedIdx = apiRef.selectedIdx;
                                                var selectedRuleCopy = apiRef._copyRule(apiRef.selectedRule);
                                                if (selectedRuleCopy == null) return;

                                                var actionIndex = aIdx;
                                                var currentActions = apiRef.actionsModel;
                                                if (!currentActions || actionIndex < 0 || actionIndex >= currentActions.length) return;

                                                Qt.callLater(function () {
                                                    if (!apiRef) return;
                                                    if (apiRef.selectedIdx !== selectedIdx) return;

                                                    var aa = apiRef.actionsModel.slice();
                                                    if (actionIndex < 0 || actionIndex >= aa.length) return;

                                                    var ac = apiRef._copyRule(aa[actionIndex]);
                                                    if (ac) aa[actionIndex] = ac;
                                                    aa[actionIndex].params = aa[actionIndex].params || {};
                                                    aa[actionIndex].params.file_path = pickedPath;
                                                    apiRef.actionsModel = aa;

                                                    selectedRuleCopy.actions = aa;
                                                    apiRef._setRule(selectedIdx, selectedRuleCopy);
                                                    apiRef._save();
                                                });
                                            }
                                        }
                                    }

                                    TextArea {
                                        Layout.fillWidth: true
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.write_text_ph") : "Text..."
                                        text: (modelData && modelData.params && modelData.params.text) ? modelData.params.text : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            // Do NOT rebuild the full rulesModel on every keystroke,
                                            // otherwise the delegate is recreated and the field loses focus.
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.text = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            page.isActionTextEditing = activeFocus;
                                            if (!activeFocus) page._commitSelectedRuleActions(false);
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint_file") : "Placeholders (text & file path): giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                }

                                // Run program (cross-platform)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aKind === "run_program"

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_program") : "Pick executable…"
                                            text: {
                                                if (!modelData || !modelData.params) return "";
                                                return modelData.params.program_path || modelData.params.exe_path || "";
                                            }
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: true
                                        }
                                        ConnPillButton {
                                            Layout.preferredWidth: 94
                                            Layout.minimumWidth: 86
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                var p = actApi.pickProgramFile();
                                                if (!p) return;
                                                var r = apiRef._copyRule(apiRef.selectedRule);
                                                if (r == null) return;
                                                var aa = apiRef.actionsModel.slice();
                                                var ac = apiRef._copyRule(aa[aIdx]);
                                                if (ac) aa[aIdx] = ac;
                                                aa[aIdx].params = aa[aIdx].params || {};
                                                aa[aIdx].params.program_path = p;
                                                delete aa[aIdx].params.exe_path;
                                                if (aa[aIdx].type === "run_exe") aa[aIdx].type = "run_program";
                                                apiRef.actionsModel = aa;
                                                r.actions = aa;
                                                apiRef._setRule(apiRef.selectedIdx, r);
                                                apiRef._save();
                                            }
                                        }
                                    }

                                    Text { text: api ? api.loc("actions.program_args") : "Arguments"; color: muted; font.pixelSize: 12 }
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.program_args_ph") : "e.g. --foo bar"
                                        text: (modelData && modelData.params && modelData.params.arguments) ? modelData.params.arguments : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onEditingFinished: {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var aa = apiRef.actionsModel.slice();
                                            var ac = apiRef._copyRule(aa[aIdx]);
                                            if (ac) aa[aIdx] = ac;
                                            aa[aIdx].params = aa[aIdx].params || {};
                                            aa[aIdx].params.arguments = text;
                                            apiRef.actionsModel = aa;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders: giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                }

                                // Simulate keystrokes (Windows SendInput)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "simulate_keystrokes"

                                    Text {
                                        text: api ? api.loc("actions.keystrokes_sequence_label") : "Sequence"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    TextArea {
                                        id: ksStrokeSeq
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 88
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.keystrokes_sequence_ph") : "{END}{F7}"
                                        text: (modelData && modelData.params && modelData.params.sequence !== undefined) ? ("" + modelData.params.sequence) : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                return;
                                            if (!aa[aIdx].params)
                                                aa[aIdx].params = {};
                                            aa[aIdx].params.sequence = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            page.isActionTextEditing = activeFocus;
                                            if (!activeFocus)
                                                page._commitSelectedRuleActions(false);
                                        }
                                    }

                                    Text {
                                        text: api ? api.loc("actions.keystrokes_modifiers") : "Modifiers (for tags only)"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12
                                        ConnCheckBox {
                                            id: ksModCtrl
                                            text: "Ctrl"
                                            checked: !!(modelData && modelData.params && modelData.params.modifier_ctrl)
                                            onCheckedChanged: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                    return;
                                                if (!aa[aIdx].params)
                                                    aa[aIdx].params = {};
                                                if (aa[aIdx].params.modifier_ctrl === ksModCtrl.checked)
                                                    return;
                                                aa[aIdx].params.modifier_ctrl = ksModCtrl.checked;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                        ConnCheckBox {
                                            id: ksModAlt
                                            text: "Alt"
                                            checked: !!(modelData && modelData.params && modelData.params.modifier_alt)
                                            onCheckedChanged: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                    return;
                                                if (!aa[aIdx].params)
                                                    aa[aIdx].params = {};
                                                if (aa[aIdx].params.modifier_alt === ksModAlt.checked)
                                                    return;
                                                aa[aIdx].params.modifier_alt = ksModAlt.checked;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                        ConnCheckBox {
                                            id: ksModShift
                                            text: "Shift"
                                            checked: !!(modelData && modelData.params && modelData.params.modifier_shift)
                                            onCheckedChanged: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                    return;
                                                if (!aa[aIdx].params)
                                                    aa[aIdx].params = {};
                                                if (aa[aIdx].params.modifier_shift === ksModShift.checked)
                                                    return;
                                                aa[aIdx].params.modifier_shift = ksModShift.checked;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    Text {
                                        text: api ? api.loc("actions.keystrokes_insert_hint") : "Insert special keys"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    TabBar {
                                        id: ksKeyTabs
                                        Layout.fillWidth: true
                                        background: Rectangle { color: "transparent" }
                                        TabButton {
                                            text: api ? api.loc("actions.keystrokes_tab_nav") : "Nav"
                                            width: implicitWidth + 16
                                        }
                                        TabButton {
                                            text: api ? api.loc("actions.keystrokes_tab_editing") : "Editing"
                                            width: implicitWidth + 16
                                        }
                                        TabButton {
                                            text: api ? api.loc("actions.keystrokes_tab_fn") : "F-keys"
                                            width: implicitWidth + 16
                                        }
                                        TabButton {
                                            text: api ? api.loc("actions.keystrokes_tab_mouse") : "Mouse"
                                            width: implicitWidth + 16
                                        }
                                    }
                                    StackLayout {
                                        Layout.fillWidth: true
                                        currentIndex: ksKeyTabs.currentIndex
                                        GridLayout {
                                            columns: 4
                                            rowSpacing: 6
                                            columnSpacing: 6
                                            ConnPillButton { pillFontSize: 11; text: "Home"; onClicked: insertKsTag("{HOME}") }
                                            ConnPillButton { pillFontSize: 11; text: "End"; onClicked: insertKsTag("{END}") }
                                            ConnPillButton { pillFontSize: 11; text: "PgUp"; onClicked: insertKsTag("{PGUP}") }
                                            ConnPillButton { pillFontSize: 11; text: "PgDn"; onClicked: insertKsTag("{PGDN}") }
                                            ConnPillButton { pillFontSize: 11; text: "↑"; onClicked: insertKsTag("{UP}") }
                                            ConnPillButton { pillFontSize: 11; text: "↓"; onClicked: insertKsTag("{DOWN}") }
                                            ConnPillButton { pillFontSize: 11; text: "←"; onClicked: insertKsTag("{LEFT}") }
                                            ConnPillButton { pillFontSize: 11; text: "→"; onClicked: insertKsTag("{RIGHT}") }
                                            ConnPillButton { pillFontSize: 11; text: "Ins"; onClicked: insertKsTag("{INSERT}") }
                                            ConnPillButton { pillFontSize: 11; text: "Del"; onClicked: insertKsTag("{DELETE}") }
                                        }
                                        GridLayout {
                                            columns: 4
                                            rowSpacing: 6
                                            columnSpacing: 6
                                            ConnPillButton { pillFontSize: 11; text: "Enter"; onClicked: insertKsTag("{ENTER}") }
                                            ConnPillButton { pillFontSize: 11; text: "Space"; onClicked: insertKsTag("{SPACE}") }
                                            ConnPillButton { pillFontSize: 11; text: "Tab"; onClicked: insertKsTag("{TAB}") }
                                            ConnPillButton { pillFontSize: 11; text: "Esc"; onClicked: insertKsTag("{ESC}") }
                                            ConnPillButton { pillFontSize: 11; text: "Bksp"; onClicked: insertKsTag("{BACKSPACE}") }
                                            ConnPillButton { pillFontSize: 11; text: "Pause"; onClicked: insertKsTag("{PAUSE}") }
                                            ConnPillButton { pillFontSize: 11; text: "Caps"; onClicked: insertKsTag("{CAPSLOCK}") }
                                        }
                                        GridLayout {
                                            columns: 6
                                            rowSpacing: 6
                                            columnSpacing: 6
                                            ConnPillButton { pillFontSize: 11; text: "F1"; onClicked: insertKsTag("{F1}") }
                                            ConnPillButton { pillFontSize: 11; text: "F2"; onClicked: insertKsTag("{F2}") }
                                            ConnPillButton { pillFontSize: 11; text: "F3"; onClicked: insertKsTag("{F3}") }
                                            ConnPillButton { pillFontSize: 11; text: "F4"; onClicked: insertKsTag("{F4}") }
                                            ConnPillButton { pillFontSize: 11; text: "F5"; onClicked: insertKsTag("{F5}") }
                                            ConnPillButton { pillFontSize: 11; text: "F6"; onClicked: insertKsTag("{F6}") }
                                            ConnPillButton { pillFontSize: 11; text: "F7"; onClicked: insertKsTag("{F7}") }
                                            ConnPillButton { pillFontSize: 11; text: "F8"; onClicked: insertKsTag("{F8}") }
                                            ConnPillButton { pillFontSize: 11; text: "F9"; onClicked: insertKsTag("{F9}") }
                                            ConnPillButton { pillFontSize: 11; text: "F10"; onClicked: insertKsTag("{F10}") }
                                            ConnPillButton { pillFontSize: 11; text: "F11"; onClicked: insertKsTag("{F11}") }
                                            ConnPillButton { pillFontSize: 11; text: "F12"; onClicked: insertKsTag("{F12}") }
                                        }
                                        RowLayout {
                                            spacing: 8
                                            ConnPillButton { pillFontSize: 11; text: api ? api.loc("actions.keystrokes_left_click") : "Left click"; onClicked: insertKsTag("{LCLICK}") }
                                            ConnPillButton { pillFontSize: 11; text: api ? api.loc("actions.keystrokes_right_click") : "Right click"; onClicked: insertKsTag("{RCLICK}") }
                                        }
                                    }

                                    Text {
                                        text: api ? api.loc("actions.keystrokes_advanced") : "Advanced"
                                        color: ink
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                    ConnCheckBox {
                                        id: ksInterception
                                        visible: Qt.platform.os === "windows"
                                        text: api ? api.loc("actions.keystrokes_interception") : "Interception driver"
                                        checked: !!(modelData && modelData.params && modelData.params.use_interception)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                return;
                                            if (!aa[aIdx].params)
                                                aa[aIdx].params = {};
                                            if (aa[aIdx].params.use_interception === ksInterception.checked)
                                                return;
                                            aa[aIdx].params.use_interception = ksInterception.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }
                                    Text {
                                        visible: Qt.platform.os === "windows"
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.keystrokes_interception_hint") : ""
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                    ConnCheckBox {
                                        id: ksGameCompat
                                        visible: Qt.platform.os === "windows"
                                        text: api ? api.loc("actions.keystrokes_game_mode") : "Game compatibility"
                                        checked: !!(modelData && modelData.params && modelData.params.game_compatibility)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                return;
                                            if (!aa[aIdx].params)
                                                aa[aIdx].params = {};
                                            if (aa[aIdx].params.game_compatibility === ksGameCompat.checked)
                                                return;
                                            aa[aIdx].params.game_compatibility = ksGameCompat.checked;
                                            page._updateActionsModel(aa);
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: api ? api.loc("actions.keystrokes_hold_ms") : "Hold (ms)"
                                            color: muted
                                            font.pixelSize: 12
                                        }
                                        ConnIntStepper {
                                            Layout.fillWidth: true
                                            fromVal: 0
                                            toVal: 60000
                                            intValue: {
                                                var v = (modelData && modelData.params && modelData.params.hold_ms !== undefined) ? Number(modelData.params.hold_ms) : 0;
                                                if (isNaN(v) || v < 0)
                                                    return 0;
                                                return Math.min(60000, Math.round(v));
                                            }
                                            onCommitted: function (v) {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length)
                                                    return;
                                                if (!aa[aIdx].params)
                                                    aa[aIdx].params = {};
                                                aa[aIdx].params.hold_ms = v;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.keystrokes_placeholders_hint") : "Placeholders…"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.keystrokes_admin_hint") : "Admin hint"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: "#c95c5c"
                                    }
                                }

                                // TTS speak text
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "speak_tts"

                                    Text { text: api ? api.loc("actions.speak_tts_text") : "Text to speak"; color: muted; font.pixelSize: 12 }
                                    TextArea {
                                        Layout.fillWidth: true
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.speak_tts_text_ph") : "phrase…"
                                        text: (modelData && modelData.params && modelData.params.text) ? modelData.params.text : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.text = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            page.isActionTextEditing = activeFocus;
                                            if (!activeFocus) page._commitSelectedRuleActions(false);
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders: giftcount, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                }

                                // Show on Actions overlay
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "show_overlay"

                                    Text { text: api ? api.loc("actions.show_overlay_text") : "Text"; color: muted; font.pixelSize: 12 }
                                    TextArea {
                                        Layout.fillWidth: true
                                        wrapMode: TextArea.Wrap
                                        placeholderText: api ? api.loc("actions.show_overlay_text_ph") : "e.g. {sender} подарував {giftname} x{giftcount}"
                                        text: (modelData && modelData.params && modelData.params.text) ? modelData.params.text : ""
                                        color: ink
                                        placeholderTextColor: muted
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.text = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            page.isActionTextEditing = activeFocus;
                                            if (!activeFocus) page._commitSelectedRuleActions(false);
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        Text { text: api ? api.loc("actions.show_overlay_seconds") : "Seconds"; color: muted; font.pixelSize: 12 }
                                        ConnIntStepper {
                                            Layout.fillWidth: true
                                            fromVal: 0
                                            toVal: 600
                                            intValue: {
                                                var v = (modelData && modelData.params && modelData.params.seconds !== undefined) ? Number(modelData.params.seconds) : 3;
                                                if (isNaN(v) || v < 0)
                                                    return 3;
                                                return Math.min(600, Math.round(v));
                                            }
                                            onCommitted: function (v) {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.seconds = v;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders: giftcount, giftname, sender, platform, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                }

                                // OBS WebSocket: program scene or source visibility
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    visible: aType === "obs_scene"
                                    Component.onCompleted: {
                                        page._obsRefreshFromObs(aIdx, true);
                                    }

                                    Text { text: api ? api.loc("actions.obs_mode") : "Mode"; color: muted; font.pixelSize: 12 }
                                    ConnComboBox {
                                        Layout.fillWidth: true
                                        model: [
                                            {
                                                text: api ? api.loc("actions.obs_mode_program") : "Program scene",
                                                value: "program_scene"
                                            },
                                            {
                                                text: api ? api.loc("actions.obs_mode_source") : "Source visibility",
                                                value: "source_visible"
                                            }
                                        ]
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: {
                                            var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene";
                                            return (m === "source_visible") ? 1 : 0;
                                        }
                                        onPicked: function (idx) {
                                            page.selectedActionIdx = aIdx;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.mode = model[idx].value;
                                            page._updateActionsModel(aa);
                                            if (model[idx].value === "source_visible" && obsBrowseUi)
                                                page._obsReloadSourcesPickList();
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        visible: obsBrowseUi
                                        ConnPillButton {
                                            text: api ? api.loc("actions.obs_refresh_from_obs") : "Load from OBS"
                                            pillFontSize: 12
                                            onClicked: {
                                                page.selectedActionIdx = aIdx;
                                                page._obsRefreshFromObs(aIdx);
                                            }
                                        }
                                    }

                                    Text {
                                        visible: obsBrowseUi
                                        text: api ? api.loc("actions.obs_canvas") : "Canvas"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    ConnComboBox {
                                        Layout.fillWidth: true
                                        visible: obsBrowseUi
                                        model: page._obsPickCanvases
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: {
                                            var m = page._obsPickCanvases;
                                            if (!m || !m.length) return -1;
                                            var cur = (modelData && modelData.params && modelData.params.canvas_uuid !== undefined && modelData.params.canvas_uuid !== null) ? ("" + modelData.params.canvas_uuid) : "";
                                            var ix = page._obsFindComboIndex(m, cur);
                                            return ix >= 0 ? ix : 0;
                                        }
                                        onPicked: function (idx) {
                                            page.selectedActionIdx = aIdx;
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.canvas_uuid = model[idx].value;
                                            page._updateActionsModel(aa);
                                            page._obsReloadScenesPickList();
                                            var pr = aa[aIdx].params || {};
                                            if ((pr.mode || "") === "source_visible")
                                                page._obsReloadSourcesPickList();
                                        }
                                    }

                                    Text {
                                        visible: obsBrowseUi
                                        text: api ? api.loc("actions.obs_scene_pick") : "Scene (from OBS)"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    ConnComboBox {
                                        Layout.fillWidth: true
                                        visible: obsBrowseUi
                                        model: page._obsPickScenes
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: {
                                            var m = page._obsPickScenes;
                                            if (!m || !m.length) return -1;
                                            var cur = (modelData && modelData.params && modelData.params.scene_name) ? ("" + modelData.params.scene_name) : "";
                                            var ix = page._obsFindComboIndex(m, cur);
                                            return ix >= 0 ? ix : 0;
                                        }
                                        onPicked: function (idx) {
                                            page.selectedActionIdx = aIdx;
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.scene_name = model[idx].value;
                                            page._updateActionsModel(aa);
                                            var pr = aa[aIdx].params || {};
                                            if ((pr.mode || "") === "source_visible")
                                                page._obsReloadSourcesPickList();
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        visible: obsBrowseUi && (((modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene") === "source_visible")
                                        text: api ? api.loc("actions.obs_source_pick") : "Source (from OBS)"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    ConnComboBox {
                                        Layout.fillWidth: true
                                        visible: obsBrowseUi && (((modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene") === "source_visible")
                                        model: page._obsPickSources
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: {
                                            var m = page._obsPickSources;
                                            if (!m || !m.length) return -1;
                                            var cur = (modelData && modelData.params && modelData.params.source_name) ? ("" + modelData.params.source_name) : "";
                                            var ix = page._obsFindComboIndex(m, cur);
                                            return ix >= 0 ? ix : 0;
                                        }
                                        onPicked: function (idx) {
                                            page.selectedActionIdx = aIdx;
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.source_name = model[idx].value;
                                            page._updateActionsModel(aa);
                                        }
                                    }

                                    Text {
                                        visible: obsBrowseUi
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.obs_manual_names_hint") : "You can still edit names below (placeholders supported)."
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }

                                    Text { text: api ? api.loc("actions.obs_scene_name") : "Scene name"; color: muted; font.pixelSize: 12 }
                                    TextField {
                                        Layout.fillWidth: true
                                        color: ink
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.obs_scene_name_ph") : "Scene…"
                                        text: (modelData && modelData.params && modelData.params.scene_name) ? modelData.params.scene_name : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.scene_name = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            if (!activeFocus) page._commitSelectedRuleActions(false);
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        visible: {
                                            var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene";
                                            return m === "source_visible";
                                        }
                                        text: api ? api.loc("actions.obs_source_name") : "Source name"
                                        color: muted
                                        font.pixelSize: 12
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        visible: {
                                            var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene";
                                            return m === "source_visible";
                                        }
                                        color: ink
                                        placeholderTextColor: muted
                                        placeholderText: api ? api.loc("actions.obs_source_name_ph") : "Source…"
                                        text: (modelData && modelData.params && modelData.params.source_name) ? modelData.params.source_name : ""
                                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                        onTextChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.source_name = text;
                                            page._updateActionsModel(aa);
                                        }
                                        onActiveFocusChanged: {
                                            if (!activeFocus) page._commitSelectedRuleActions(false);
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        visible: {
                                            var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene";
                                            return m === "source_visible";
                                        }
                                        Text { text: api ? api.loc("actions.obs_visible") : "Visible"; color: muted; font.pixelSize: 12 }
                                        ConnPrefSwitch {
                                            Layout.alignment: Qt.AlignVCenter
                                            checked: {
                                                if (!modelData || !modelData.params) return true;
                                                return modelData.params.visible !== false;
                                            }
                                            // toggled() has no arguments — do not use a callback param (it is undefined).
                                            onToggled: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.visible = checked;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        visible: {
                                            var m = (modelData && modelData.params && modelData.params.mode) ? modelData.params.mode : "program_scene";
                                            return m === "source_visible";
                                        }
                                        ConnCheckBox {
                                            id: obsRevertCb
                                            text: api ? api.loc("actions.obs_revert_checkbox") : "Revert visibility to how it was"
                                            checked: !!(modelData && modelData.params && modelData.params.revert_previous_state)
                                            onCheckedChanged: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                if (aa[aIdx].params.revert_previous_state === obsRevertCb.checked) return;
                                                aa[aIdx].params.revert_previous_state = obsRevertCb.checked;
                                                page._updateActionsModel(aa);
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10
                                            Text {
                                                text: api ? api.loc("actions.obs_revert_after") : "After"
                                                color: muted
                                                font.pixelSize: 12
                                                Layout.alignment: Qt.AlignVCenter
                                            }
                                            ConnIntStepper {
                                                Layout.fillWidth: true
                                                fromVal: 1
                                                toVal: 3600
                                                enabled: !!(modelData && modelData.params && modelData.params.revert_previous_state)
                                                intValue: {
                                                    if (!modelData || !modelData.params) return 5;
                                                    var v = modelData.params.revert_delay_seconds;
                                                    if (v === undefined || v === null || v === "") return 5;
                                                    var n = Number(v);
                                                    if (isNaN(n) || n < 1) return 1;
                                                    if (n > 3600) return 3600;
                                                    return Math.round(n);
                                                }
                                                onCommitted: function (v) {
                                                    var aa = page.actionsModel;
                                                    if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                    if (!aa[aIdx].params) aa[aIdx].params = {};
                                                    aa[aIdx].params.revert_delay_seconds = v;
                                                    page._updateActionsModel(aa);
                                                }
                                            }
                                            Text {
                                                text: api ? api.loc("actions.obs_revert_seconds_suffix") : "s"
                                                color: muted
                                                font.pixelSize: 12
                                                Layout.alignment: Qt.AlignVCenter
                                            }
                                            Item { Layout.fillWidth: true }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: api ? api.loc("actions.obs_revert_seconds_hint") : ""
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 11
                                            color: page.muted
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: api ? api.loc("actions.placeholders_hint") : "Placeholders in names: sender, giftname, …"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        color: page.muted
                                    }
                                }
                            }

                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: page.selectedActionIdx = index
                            }
                        }
                    }

                    // One compact rule-level disclosure control for secondary action parameters.
                    Rectangle {
                        visible: root.actionsModel && root.actionsModel.length > 0
                        Layout.fillWidth: true
                        implicitHeight: advancedRuleRow.implicitHeight + 16
                        radius: 9
                        color: "#101a2b"
                        border.width: 1
                        border.color: cardEdge

                        RowLayout {
                            id: advancedRuleRow
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8
                            Image {
                                Layout.preferredWidth: 16
                                Layout.preferredHeight: 16
                                source: root._assetUrl("gear.svg")
                                fillMode: Image.PreserveAspectFit
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    text: api ? api.loc("actions.advanced_params") : "Advanced parameters"
                                    color: ink
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Text {
                                    text: "Ліміти, фільтри, затримки та інші налаштування"
                                    color: muted
                                    font.pixelSize: 10
                                }
                            }
                            Image {
                                Layout.preferredWidth: 14
                                Layout.preferredHeight: 14
                                rotation: root.thenAdvancedOpen ? 180 : 0
                                source: root._assetUrl("chevron-down.svg")
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.thenAdvancedOpen = !root.thenAdvancedOpen
                        }
                    }

                    // Destructive clear operation is available from the THEN overflow menu.
                    } // THEN card ColumnLayout
                    } // THEN card Rectangle

                } // selected rule editor content
                } // scroll content column
                } // editor ScrollView

                Rectangle {
                    id: bottomSaveBar
                    visible: root.selectedIdx >= 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    radius: 10
                    color: "#0f172a"
                    border.width: 1
                    border.color: cardEdge

                    RowLayout {
                        id: bottomSaveBarInner
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8
                        Text {
                            visible: root.hasUnsavedChanges
                            color: root.accentPurpleSoft
                            font.pixelSize: 11
                            text: api ? api.loc("actions.unsaved_dot") : "Незбережені зміни"
                        }
                        Item { Layout.fillWidth: true }
                        CheremshaSecondaryButton {
                            text: api ? api.loc("actions.cancel_btn") : "Скасувати"
                            iconName: "x.svg"
                            onClicked: {
                                actionsAutosaveTimer.stop();
                                root.hasUnsavedChanges = false;
                                root._load();
                            }
                        }
                        CheremshaPrimaryButton {
                            text: api ? api.loc("actions.save_changes") : "Зберегти зміни"
                            iconName: "check.svg"
                            onClicked: root._commitSelectedRuleActions(true)
                        }
                    }
                }
            }
        }
    }

    // Compact action picker: categorized existing action types, searchable.
    Rectangle {
        anchors.fill: parent
        visible: root.showActionPicker
        color: "#060810aa"
        z: 50

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.showActionPicker = false;
                root.actionPickerReplaceIdx = -1;
                root.actionPickerQuery = "";
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 80, 420)
            height: Math.min(parent.height - 80, pickerCol.implicitHeight + 28)
            radius: 12
            color: "#121620"
            border.width: 1
            border.color: root.accentPurple

            ColumnLayout {
                id: pickerCol
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: api ? api.loc("actions.picker_title") : "Add action"
                    color: ink
                    font.pixelSize: 14
                    font.bold: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    radius: 8
                    color: fieldBg
                    border.width: 1
                    border.color: cardEdge

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6

                        Image {
                            Layout.preferredWidth: 14
                            Layout.preferredHeight: 14
                            source: root._assetUrl("web_search.svg")
                            fillMode: Image.PreserveAspectFit
                            opacity: 0.85
                        }
                        TextField {
                            Layout.fillWidth: true
                            color: ink
                            font.pixelSize: 12
                            placeholderTextColor: muted
                            placeholderText: api ? api.loc("actions.picker_search_ph") : "Search actions…"
                            text: root.actionPickerQuery
                            background: Item {}
                            onTextChanged: root.actionPickerQuery = text
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(320, pickerList.contentHeight + 4)
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    ListView {
                        id: pickerList
                        width: parent.width
                        height: contentHeight
                        interactive: false
                        spacing: 4
                        model: root._actionPickerFiltered()
                        delegate: Rectangle {
                            width: pickerList.width
                            height: 44
                            radius: 8
                            color: pickerMouse.containsMouse ? "#1d2340" : "transparent"
                            border.width: 1
                            border.color: pickerMouse.containsMouse ? root.accentPurple : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                Image {
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    source: root._assetUrl(root._actionIconForType(modelData.type))
                                    fillMode: Image.PreserveAspectFit
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.title
                                        color: ink
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.group
                                        color: muted
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            MouseArea {
                                id: pickerMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root._addActionOfType(modelData.type)
                            }
                        }
                    }
                }
            }
        }
    }

    // One and only one drag representation. The source delegate is hidden
    // while this clipped layer renders the complete floating card.
    Item {
        id: dndOverlayLayer
        visible: root.dndActive
        x: rulesList ? rulesList.mapToItem(root, 0, 0).x : 0
        y: rulesList ? rulesList.mapToItem(root, 0, 0).y : 0
        width: rulesList ? rulesList.width : 0
        height: rulesList ? rulesList.height : 0
        clip: true
        z: 900

        Rectangle {
            id: dndInsertionIndicator
            visible: root.dndTargetMode === "between"
            x: root.dndIndicatorX - dndOverlayLayer.x
            y: root.dndIndicatorY - dndOverlayLayer.y
                + root._dndOffsetFor(root.dndTarget) - height / 2
            width: root.dndIndicatorWidth
            height: 2
            radius: 1
            color: root.accentPurpleSoft
            z: 1
            antialiasing: true
            Behavior on y {
                NumberAnimation {
                    duration: root.dndAnimationDuration
                    easing.type: Easing.OutCubic
                }
            }
            Behavior on width {
                NumberAnimation {
                    duration: root.dndAnimationDuration
                    easing.type: Easing.OutCubic
                }
            }
        }

        Item {
            id: dndFloatingPreview
            visible: root.dndActive
            z: 2
            width: Math.max(1, Math.min(360, dndOverlayLayer.width - 16))
            height: 48
            x: Math.max(8, Math.min(dndOverlayLayer.width - width - 8,
                                    root.dndPointerX - dndOverlayLayer.x + 14))
            y: Math.max(8, Math.min(dndOverlayLayer.height - height - 8,
                                    root.dndPointerY - dndOverlayLayer.y + 14))
            scale: root.reducedMotion ? 1.0 : 1.01
            transformOrigin: Item.TopLeft

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 5
                anchors.leftMargin: 3
                color: "#000000"
                opacity: 0.34
                radius: 9
            }
            Rectangle {
                anchors.fill: parent
                radius: 8
                color: "#151e30"
                border.width: 1
                border.color: root.accentPurpleSoft
                antialiasing: true

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 8
                    Image {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        source: root._assetUrl(root.dndKind === "folder"
                            ? "web_folder.svg"
                            : root._ruleIconForRow(root._ruleById(root.dndId) || {}))
                        fillMode: Image.PreserveAspectFit
                        opacity: 0.95
                    }
                    Text {
                        Layout.fillWidth: true
                        color: root.ink
                        font.pixelSize: 13
                        font.bold: true
                        elide: Text.ElideRight
                        text: root.dndKind === "folder"
                            ? (root.dndSourceTarget && root.dndSourceTarget.node
                                ? (root.dndSourceTarget.node.name || "Folder") : "Folder")
                            : root._ruleListTitle(root._ruleById(root.dndId) || {})
                    }
                    ConnPrefSwitch {
                        visible: root.dndKind === "rule"
                        enabled: false
                        checked: {
                            var previewRule = root._ruleById(root.dndId);
                            return previewRule ? !!previewRule.enabled : false;
                        }
                    }
                    Rectangle {
                        visible: root.dndKind === "rule"
                        Layout.preferredWidth: 30
                        Layout.preferredHeight: 26
                        radius: 8
                        color: "#1c2434"
                        border.width: 1
                        border.color: root.cardEdge
                        Text {
                            anchors.centerIn: parent
                            text: "…"
                            color: root.muted
                            font.pixelSize: 16
                        }
                    }
                }
            }
            Behavior on x { NumberAnimation { duration: root.dndAnimationDuration; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: root.dndAnimationDuration; easing.type: Easing.OutCubic } }
            Behavior on scale { NumberAnimation { duration: root.dndAnimationDuration; easing.type: Easing.OutCubic } }
        }
    }

    // Autosave toast (optional; most saves are silent).
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18
        width: Math.min(parent.width - 36, savedToastText.implicitWidth + 24)
        height: savedToastText.implicitHeight + 16
        radius: 10
        color: "#0f172a"
        border.width: 1
        border.color: "#334155"
        visible: root._savedToastVisible
        opacity: root._savedToastVisible ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: 120 } }

        Text {
            id: savedToastText
            anchors.centerIn: parent
            width: parent.width - 16
            text: api ? api.loc("actions.saved") : "Saved"
            color: root.ink
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 18
        width: Math.min(parent.width - 36, previewToastText.implicitWidth + 24)
        height: previewToastText.implicitHeight + 16
        radius: 10
        color: "#0f172a"
        border.width: 1
        border.color: "#334155"
        visible: root._previewToastVisible
        opacity: root._previewToastVisible ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: 120 } }

        Text {
            id: previewToastText
            anchors.centerIn: parent
            width: parent.width - 16
            text: root._previewToastText
            color: root.ink
            font.pixelSize: 12
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }
}
