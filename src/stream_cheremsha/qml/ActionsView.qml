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

    // Provided by MainWindow when opening the editor.
    property string platform: ""
    property string accountKey: ""

    readonly property color base: "#0a0b0e"
    readonly property color cardBase: "#121620"
    readonly property color cardEdge: "#2a3142"
    readonly property color ink: "#e8eaed"
    readonly property color muted: "#8b95a5"
    readonly property color fieldBg: "#0c0f16"

    Rectangle { anchors.fill: parent; color: base }

    property var rulesModel: []
    property var rulesUiTree: []
    property string rulesUiRevision: ""
    property string selectedRuleId: ""
    property int selectedIdx: -1
    property bool dndDebug: false
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
        var evs = selectedRule.events;
        if (!evs || !evs.length) {
            if (selectedRule.event)
                return selectedRule.event;
            return null;
        }
        var ix = Math.max(0, Math.min(selectedTriggerIdx, evs.length - 1));
        return evs[ix];
    }

    // Same resolution as editingTrigger but as a function: safe to call in the same
    // handler tick as selectedTriggerIdx changes (bindings are not flushed yet).
    function _activeEventForCombos() {
        if (root.selectedRule === null)
            return null;
        var evs = root.selectedRule.events;
        if (!evs || !evs.length) {
            if (root.selectedRule.event)
                return root.selectedRule.event;
            return null;
        }
        var ix = Math.max(0, Math.min(root.selectedTriggerIdx, evs.length - 1));
        return evs[ix];
    }

    property bool isActionTextEditing: false
    // true while we set event/gift comboboxes from the rule; blocks onActivated/onAccepted
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
            root._commitSelectedRuleActions(false);
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
            root._obsPickCanvases = [];
            root._obsPickScenes = [];
            root._obsPickSources = [];
            return;
        }
        var aa = root.actionsModel;
        if (!aa || ix >= aa.length) {
            root._obsPickCanvases = [];
            root._obsPickScenes = [];
            root._obsPickSources = [];
            return;
        }
        var row = aa[ix];
        if (!row || ("" + (row.type || "")).trim() !== "obs_scene") {
            root._obsPickCanvases = [];
            root._obsPickScenes = [];
            root._obsPickSources = [];
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

        if (mode === "source_visible") {
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

    function _dropPayload(drop) {
        // Qt versions differ in how drag mime maps to DropArea.drop.text.
        // Try drop.text first, then fall back to mimeData.
        var raw = "";
        try {
            raw = (drop && drop.text) ? ("" + drop.text) : "";
        } catch (e0) {
            raw = "";
        }
        if (dndDebug) {
            console.log("[ActionsView] drop.text.len=", (raw || "").length);
        }
        if (!raw || !raw.trim().length) {
            try {
                if (drop && drop.mimeData) {
                    if (drop.mimeData.text && ("" + drop.mimeData.text).trim().length) {
                        raw = "" + drop.mimeData.text;
                    } else if (drop.mimeData.dataAsString) {
                        raw = "" + (drop.mimeData.dataAsString("text/plain") || "");
                        if (!raw || !raw.trim().length)
                            raw = "" + (drop.mimeData.dataAsString("text") || "");
                    }
                }
            } catch (e1) {
                raw = raw || "";
            }
        }
        if (dndDebug) {
            console.log("[ActionsView] parsed-raw.len=", (raw || "").length, "raw.head=", (raw || "").slice(0, 80));
        }
        if (!raw || !raw.trim().length)
            return null;
        try {
            return JSON.parse(raw);
        } catch (e2) {
            if (dndDebug)
                console.log("[ActionsView] JSON.parse failed");
            return null;
        }
    }

    function _saveRulesPayload(showToast) {
        if (!actApi || root._rulesPersistBlocked)
            return;
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
                            if (c && c.kind === "rule" && ("" + c.rule_id) === ("" + beforeId)) {
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
        if (selectedRule === null) return;
        var r;
        var a;
        try { r = JSON.parse(JSON.stringify(selectedRule)); } catch (e) { return; }
        try { a = JSON.parse(JSON.stringify(actionsModel)); } catch (e2) { a = []; }
        r.actions = a;
        root._preserveScroll(function() {
            _setRule(selectedIdx, r);
            _save(!!showToast);
        });
    }

    function _scheduleCommitSelectedRuleActions() {
        actionsAutosaveTimer.restart();
    }

    readonly property var actionTypeModel: [
        { text: api ? api.loc("actions.play_sound") : "Play sound", value: "play_sound" },
        { text: api ? api.loc("actions.play_random_myinstants_ua") : "Random MyInstants UA", value: "play_random_myinstants_ua" },
        { text: api ? api.loc("actions.write_file") : "Write to file", value: "write_file" },
        { text: api ? api.loc("actions.run_program") : "Run program", value: "run_program" },
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

    component UiRulesDropGap: Item {
        id: gapRoot
        height: trailing ? 14 : 10
        property bool trailing: false
        property string dropBeforeRuleId: ""
        property string dropBeforeFolderId: ""

        DropArea {
            anchors.fill: parent

            Rectangle {
                anchors.fill: parent
                radius: 4
                color: parent.containsDrag ? "#2c6bff55" : "transparent"
            }

            onDropped: function(drop) {
                var payload = root._dropPayload(drop);
                if (!payload || payload.scope !== "actions-rules")
                    return;

                if (trailing) {
                    if (payload.kind === "rule")
                        root._dropOntoRootBetween(payload.rule_id, "");
                    else if (payload.kind === "folder")
                        root._moveFolderBefore(payload.folder_id, "", "");
                    drop.acceptProposedAction();
                    return;
                }

                if (payload.kind === "rule")
                    root._dropOntoRootBetween(payload.rule_id, dropBeforeRuleId);
                else if (payload.kind === "folder")
                    root._moveFolderBefore(payload.folder_id, dropBeforeRuleId, dropBeforeFolderId);
                drop.acceptProposedAction();
            }
        }
    }

    component UiRulesRuleRow: Rectangle {
        id: ruleCard
        property var node: null
        property int depth: 0
        property var nextSibling: null

        height: 58
        radius: 10
        x: depth * 14
        width: Math.max(120, parent.width - depth * 14)

        property string rid: node && node.rule_id ? ("" + node.rule_id) : ""
        property var ruleObj: rid ? root._ruleById(rid) : null
        property int idxInRules: rid ? root._rulesIndexById(rid) : -1

        color: idxInRules >= 0 && idxInRules === root.selectedIdx ? "#1a2232" : "#111827"
        border.width: 1
        border.color: cardEdge

        MouseArea {
            anchors.fill: parent
            z: -1
            onClicked: {
                if (!rid.length)
                    return;
                root.selectedRuleId = rid;
                root.selectedIdx = idxInRules;
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            Item {
                id: dragPad
                Layout.preferredWidth: 28
                Layout.fillHeight: true

                // NOTE: don't bind Drag.active (can create binding loops on some Qt builds).
                Drag.supportedActions: Qt.MoveAction
                Drag.proposedAction: Qt.MoveAction
                Drag.hotSpot: Qt.point(width / 2, height / 2)
                Drag.dragType: Drag.Automatic
                Drag.mimeData: {
                    "text/plain": JSON.stringify({
                        scope: "actions-rules",
                        kind: "rule",
                        rule_id: rid
                    }),
                    "text": JSON.stringify({
                        scope: "actions-rules",
                        kind: "rule",
                        rule_id: rid
                    })
                }

                Text {
                    anchors.centerIn: parent
                    text: "⠿"
                    color: muted
                    font.pixelSize: 14
                }

                MouseArea {
                    id: ruleDragMa
                    anchors.fill: parent
                    hoverEnabled: true
                    preventStealing: true
                    cursorShape: Qt.OpenHandCursor
                    property real pressX: 0
                    property real pressY: 0
                    property bool armed: false

                    onPressed: function(mouse) {
                        pressX = mouse.x;
                        pressY = mouse.y;
                        armed = true;
                        dragPad.Drag.active = false;
                        cursorShape = Qt.OpenHandCursor;
                    }
                    onPositionChanged: function(mouse) {
                        if (!armed)
                            return;
                        var dx = Math.abs(mouse.x - pressX);
                        var dy = Math.abs(mouse.y - pressY);
                        if (dx + dy >= 10) {
                            dragPad.Drag.hotSpot = Qt.point(pressX, pressY);
                            dragPad.Drag.active = true;
                            cursorShape = Qt.ClosedHandCursor;
                        }
                    }
                    onReleased: function(mouse) {
                        armed = false;
                        dragPad.Drag.active = false;
                        cursorShape = Qt.OpenHandCursor;
                    }
                    onCanceled: function() {
                        armed = false;
                        dragPad.Drag.active = false;
                        cursorShape = Qt.OpenHandCursor;
                    }
                }
            }

            Switch {
                checked: ruleObj ? !!ruleObj.enabled : false
                enabled: ruleObj !== null && idxInRules >= 0
                onClicked: {
                    if (ruleObj === null || idxInRules < 0)
                        return;
                    var r = root._copyRule(ruleObj);
                    if (r == null)
                        return;
                    r.enabled = checked;
                    root._setRule(idxInRules, r);
                    root._save(false);
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 80
                Layout.alignment: Qt.AlignVCenter
                implicitHeight: ruleTitleLine.implicitHeight + 2 + ruleSubLine.implicitHeight

                Text {
                    id: ruleTitleLine
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    color: ink
                    font.pixelSize: 13
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    text: root._ruleListTitle(ruleObj || {})
                }
                Text {
                    id: ruleSubLine
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: ruleTitleLine.bottom
                    anchors.topMargin: 2
                    color: muted
                    font.pixelSize: 11
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    text: root._ruleListSubtitle(ruleObj || {})
                }
            }

            ConnPillButton {
                text: "▶"
                pillFontSize: 12
                enabled: ruleObj !== null && !!ruleObj.id
                onClicked: {
                    if (ruleObj === null)
                        return;
                    var pr = root._ruleToPersistObj(ruleObj);
                    if (!pr)
                        return;
                    var m = actApi.previewRuleLive(platform, accountKey, pr);
                    root._notifyPreviewToast(m);
                }
            }

            ConnPillButton {
                text: api ? api.loc("actions.duplicate_btn") : "Copy"
                pillFontSize: 12
                enabled: idxInRules >= 0
                onClicked: root._duplicateRuleAt(idxInRules)
            }

            ConnPillButton {
                text: api ? api.loc("actions.delete") : "Delete"
                enabled: idxInRules >= 0
                onClicked: {
                    var killId = rid;
                    var copy = rulesModel.slice();
                    copy.splice(idxInRules, 1);
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
            }
        }

        DropArea {
            anchors.fill: parent

            Rectangle {
                anchors.fill: parent
                radius: ruleCard.radius
                color: parent.containsDrag ? "#2c6bff33" : "transparent"
                border.width: parent.containsDrag ? 1 : 0
                border.color: "#4d8dff"
            }

            onDropped: function(drop) {
                var payload = root._dropPayload(drop);
                if (!payload || payload.scope !== "actions-rules")
                    return;
                if (payload.kind !== "rule")
                    return;
                root._moveRuleBefore(payload.rule_id, idxInRules);
                drop.acceptProposedAction();
            }
        }
    }

    component UiRulesFolderColumn: Column {
        id: folderRoot
        property var node: null
        property int depth: 0
        property var nextSibling: null

        spacing: 6
        x: depth * 14
        width: Math.max(120, parent.width - depth * 14)

        property string fid: node && node.id ? ("" + node.id) : ""
        property bool expanded: !!(node && node.expanded)
        readonly property int childCount: (node && node.children) ? node.children.length : 0

        Rectangle {
            id: folderHeader
            width: parent.width
            height: 44
            radius: 10
            color: "#141b29"
            border.width: 1
            border.color: cardEdge

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Item {
                    id: fdDragPad
                    Layout.preferredWidth: 28
                    Layout.fillHeight: true

                    // NOTE: don't bind Drag.active (can create binding loops on some Qt builds).
                    Drag.supportedActions: Qt.MoveAction
                    Drag.proposedAction: Qt.MoveAction
                    Drag.hotSpot: Qt.point(width / 2, height / 2)
                    Drag.dragType: Drag.Automatic
                    Drag.mimeData: {
                        "text/plain": JSON.stringify({
                            scope: "actions-rules",
                            kind: "folder",
                            folder_id: fid
                        }),
                        "text": JSON.stringify({
                            scope: "actions-rules",
                            kind: "folder",
                            folder_id: fid
                        })
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "⠿"
                        color: muted
                        font.pixelSize: 14
                    }

                    MouseArea {
                        id: folderDragMa
                        anchors.fill: parent
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: Qt.OpenHandCursor
                        property real pressX: 0
                        property real pressY: 0
                        property bool armed: false

                        onPressed: function(mouse) {
                            pressX = mouse.x;
                            pressY = mouse.y;
                            armed = true;
                            fdDragPad.Drag.active = false;
                            cursorShape = Qt.OpenHandCursor;
                        }
                        onPositionChanged: function(mouse) {
                            if (!armed)
                                return;
                            var dx = Math.abs(mouse.x - pressX);
                            var dy = Math.abs(mouse.y - pressY);
                            if (dx + dy >= 10) {
                                fdDragPad.Drag.hotSpot = Qt.point(pressX, pressY);
                                fdDragPad.Drag.active = true;
                                cursorShape = Qt.ClosedHandCursor;
                            }
                        }
                        onReleased: function(mouse) {
                            armed = false;
                            fdDragPad.Drag.active = false;
                            cursorShape = Qt.OpenHandCursor;
                        }
                        onCanceled: function() {
                            armed = false;
                            fdDragPad.Drag.active = false;
                            cursorShape = Qt.OpenHandCursor;
                        }
                    }
                }

                Text {
                    text: folderRoot.expanded ? "▾" : "▸"
                    color: ink
                    font.pixelSize: 14
                    Layout.alignment: Qt.AlignVCenter
                }

                TextField {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 80
                    color: ink
                    font.pixelSize: 13
                    maximumLength: 120
                    text: node ? (node.name || "") : ""
                    background: Rectangle {
                        radius: 8
                        color: fieldBg
                        border.width: 1
                        border.color: cardEdge
                    }
                    onEditingFinished: {
                        var nm = text.trim().substring(0, 120);
                        if (!nm.length || !fid.length)
                            return;

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
                            return;
                        root._preserveScroll(function() {
                            rulesUiTree = tree;
                            root._nextUiRevision();
                            root._saveUiLayoutOnly();
                            root._saveRulesPayload(false);
                        });
                    }
                }

                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    radius: 10
                    color: "#0f1420"
                    border.width: 1
                    border.color: cardEdge
                    visible: folderRoot.childCount > 0
                    implicitHeight: 22
                    implicitWidth: countText.implicitWidth + 14
                    Text {
                        id: countText
                        anchors.centerIn: parent
                        text: "" + folderRoot.childCount
                        color: muted
                        font.pixelSize: 12
                    }
                }

                ConnPillButton {
                    text: api ? api.loc("actions.folder_delete") : "Delete folder"
                    pillFontSize: 11
                    leftPadding: 10
                    rightPadding: 10
                    topPadding: 4
                    bottomPadding: 4
                    onClicked: root._deleteFolderKeepRules(fid)
                }
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                z: -1
                onClicked: {
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

                    var tree = root._cloneUiTree(rulesUiTree);
                    if (!toggle(tree))
                        return;
                    root._preserveScroll(function() {
                        rulesUiTree = tree;
                        root._nextUiRevision();
                        root._saveUiLayoutOnly();
                        root._saveRulesPayload(false);
                    });
                }
            }

            DropArea {
                anchors.fill: parent

                Rectangle {
                    anchors.fill: parent
                    radius: folderHeader.radius
                    color: parent.containsDrag ? "#2c6bff33" : "transparent"
                    border.width: parent.containsDrag ? 1 : 0
                    border.color: "#4d8dff"
                }

                onDropped: function(drop) {
                    var payload = root._dropPayload(drop);
                    if (!payload || payload.scope !== "actions-rules")
                        return;
                    if (payload.kind !== "rule")
                        return;
                    root._dropRuleOntoFolder(payload.rule_id, fid);
                    drop.acceptProposedAction();
                }
            }
        }

        Item {
            id: folderBody
            width: parent.width
            height: expanded ? folderInnerCol.implicitHeight : 0
            clip: true

            Behavior on height {
                NumberAnimation {
                    duration: 220
                    easing.type: Easing.OutCubic
                }
            }

            Rectangle {
                anchors.fill: folderInnerCol
                anchors.margins: folderRoot.childCount > 0 ? 4 : 0
                radius: 10
                color: "#111827"
                border.width: folderRoot.childCount > 0 ? 1 : 0
                border.color: cardEdge
                visible: folderRoot.childCount > 0
                z: -1
            }

            Column {
                id: folderInnerCol
                width: parent.width
                spacing: 8

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

    component UiRulesTreeItem: Column {
        id: treeItemRoot
        property var node: null
        property int depth: 0
        property var nextSibling: null
        property var prevSibling: null

        spacing: 0
        width: parent.width

        UiRulesDropGap {
            width: parent.width
            visible: !!prevSibling
            dropBeforeRuleId: node && node.kind === "rule" ? ("" + node.rule_id) : ""
            dropBeforeFolderId: node && node.kind === "folder" ? ("" + node.id) : ""
        }

        Loader {
            id: innerRuleLoader
            width: parent.width
            active: !!node && node.kind !== "folder"
            visible: active
            sourceComponent: uiRulesRuleRowComp

            onLoaded: {
                if (!item || !node)
                    return;
                item.node = node;
                item.depth = depth;
                item.nextSibling = nextSibling;
            }
            Connections {
                target: treeItemRoot
                function onNodeChanged() {
                    if (!innerRuleLoader.item || !treeItemRoot.node)
                        return;
                    innerRuleLoader.item.node = treeItemRoot.node;
                    innerRuleLoader.item.depth = treeItemRoot.depth;
                    innerRuleLoader.item.nextSibling = treeItemRoot.nextSibling;
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
            width: parent.width
            active: !!node && node.kind === "folder"
            visible: active
            sourceComponent: uiRulesFolderColumnComp

            onLoaded: {
                if (!item || !node)
                    return;
                item.node = node;
                item.depth = depth;
                item.nextSibling = nextSibling;
            }
            Connections {
                target: treeItemRoot
                function onNodeChanged() {
                    if (!innerFolderLoader.item || !treeItemRoot.node)
                        return;
                    innerFolderLoader.item.node = treeItemRoot.node;
                    innerFolderLoader.item.depth = treeItemRoot.depth;
                    innerFolderLoader.item.nextSibling = treeItemRoot.nextSibling;
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
        id: cb
        hoverEnabled: true
        font.pixelSize: 13
        padding: 10
        contentItem: Text {
            text: cb.displayText
            color: root.ink
            font.pixelSize: cb.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: root.fieldBg
            border.width: 1
            border.color: cb.hovered ? "#3b4458" : root.cardEdge
        }
        delegate: ItemDelegate {
            width: ListView.view ? ListView.view.width : implicitWidth
            contentItem: Text {
                text: cb.textRole ? (modelData[cb.textRole] || "") : (modelData || "")
                color: root.ink
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 6
                color: highlighted ? "#1a2232" : "#111827"
            }
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
        return {
            type: "tiktok_any_gift_received",
            platform: plat,
            params: {
                min_price: p.min_price !== undefined && p.min_price !== null ? p.min_price : 1,
                user: p.user != null && p.user !== undefined ? ("" + p.user) : ""
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
            { text: api ? api.loc("actions.trigger_platform_youtube") : "YouTube", value: "youtube" }
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
            root._scheduleObsBrowseAutoRefresh();
            return;
        }
        selectedIdx = idx;
        // Force a change notification even if the rule reference is unchanged.
        selectedRule = null;
        selectedRule = rulesModel[idx];
        if (selectedRule && selectedRule.id)
            selectedRuleId = "" + selectedRule.id;
        var evLen = 0;
        if (selectedRule) {
            if (selectedRule.events && selectedRule.events.length) evLen = selectedRule.events.length;
            else if (selectedRule.event) evLen = 1;
        }
        if (evLen > 0)
            root.selectedTriggerIdx = Math.max(0, Math.min(root.selectedTriggerIdx, evLen - 1));
        try {
            actionsModel = (selectedRule && selectedRule.actions)
                ? JSON.parse(JSON.stringify(selectedRule.actions)) : [];
        } catch (e) {
            actionsModel = [];
        }
        selectedActionIdx = actionsModel.length ? 0 : -1;
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
        if (rr.events.length === 1) return root._oneEventTitle(rr.events[0]);
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
        for (var i = 0; i < r.actions.length; i++)
            parts.push(r.actions[i].type || "?");
        return parts.join(", ");
    }

    function _duplicateRuleAt(i) {
        if (i < 0 || i >= rulesModel.length) return;
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
        if (ok)
            root._rulesPersistBlocked = false;
    }

    function _save(showToast) {
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
            // Wider so rule rows clear the list scrollbar; was 340.
            Layout.preferredWidth: 396
            Layout.fillHeight: true
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: api ? api.loc("actions.title") : "Actions"
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    ConnPillButton {
                        text: api ? api.loc("actions.add_rule") : "Add rule"
                        onClicked: {
                            var nr = _defaultRule();
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

                    Item { Layout.fillWidth: true }

                    ConnPillButton {
                        text: api ? api.loc("actions.save") : "Save"
                        onClicked: root._commitSelectedRuleActions(true)
                    }
                }

                ScrollView {
                    id: rulesList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                    Column {
                        width: Math.max(120, rulesList.availableWidth - 22)
                        spacing: 8

                        UiRulesDropGap {
                            width: parent.width
                            dropBeforeRuleId: (rulesUiTree && rulesUiTree.length && rulesUiTree[0].kind === "rule") ? ("" + rulesUiTree[0].rule_id) : ""
                            dropBeforeFolderId: (rulesUiTree && rulesUiTree.length && rulesUiTree[0].kind === "folder") ? ("" + rulesUiTree[0].id) : ""
                        }

                        Repeater {
                            model: rulesUiTree || []

                            delegate: UiRulesTreeItem {
                                width: parent.width
                                node: modelData
                                depth: 0
                                nextSibling: (index + 1 < (rulesUiTree || []).length) ? rulesUiTree[index + 1] : null
                                prevSibling: index > 0 ? rulesUiTree[index - 1] : null
                            }
                        }

                        UiRulesDropGap {
                            width: parent.width
                            trailing: true
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 14
            color: cardBase
            border.width: 1
            border.color: cardEdge
            ScrollView {
                id: rightScroll
                anchors.fill: parent
                anchors.margins: 14
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                ColumnLayout {
                    // Narrower than viewport so row controls (e.g. +/−) and combo arrows clear the scrollbar.
                    width: Math.max(1, rightScroll.availableWidth - 22)
                    spacing: 10

                Text {
                    text: api ? api.loc("actions.edit") : "Edit"
                    color: ink
                    font.pixelSize: 16
                    font.bold: true
                }

                Text {
                    visible: root.selectedIdx < 0
                    text: api ? api.loc("actions.pick_rule_hint") : "Pick a rule on the left."
                    color: muted
                    font.pixelSize: 12
                }

                ColumnLayout {
                    visible: root.selectedIdx >= 0
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: api ? api.loc("actions.rule_name") : "Name"; color: muted; font.pixelSize: 12 }
                    TextField {
                        Layout.fillWidth: true
                        color: ink
                        placeholderTextColor: muted
                        placeholderText: api ? api.loc("actions.rule_name_ph") : "e.g. Rose → OBS"
                        text: root.selectedRule !== null ? (root.selectedRule.name || "") : ""
                        background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                        onEditingFinished: {
                            if (root.selectedRule === null) return;
                            var v = text.trim();
                            if (v.length > 200) v = v.substring(0, 200);
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            r.name = v;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text {
                            text: api ? api.loc("actions.triggers") : "Triggers"
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

                    Text {
                        text: api ? api.loc("actions.trigger_platform_label") : "Trigger platform"
                        color: muted
                        font.pixelSize: 12
                    }
                    ConnComboBox {
                        id: triggerPlatformCombo
                        Layout.fillWidth: true
                        model: root._triggerPlatformModel()
                        textRole: "text"
                        valueRole: "value"
                        onActivated: function (idx) {
                            if (root._suppressRuleCombos) return;
                            if (root.selectedRule === null) return;
                            var m = root._triggerPlatformModel();
                            if (idx < 0 || idx >= m.length) return;
                            var newPlat = m[idx].value;
                            var ev = root._activeEventForCombos();
                            if (!ev) return;
                            var curKind = (ev.type || "").trim();
                            var neu;
                            if (root._kindAllowedOnPlatform(curKind, newPlat)) {
                                neu = JSON.parse(JSON.stringify(ev));
                                neu.platform = newPlat;
                            } else {
                                neu = root._chatEvent({
                                    platform: newPlat,
                                    text: "",
                                    match: "contains",
                                    case_sensitive: false
                                });
                            }
                            var r = root._patchSelectedTrigger(neu);
                            if (r == null) return;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                            root._syncTriggerCombos();
                        }
                    }
                    Text {
                        text: api ? api.loc("actions.trigger_kind_label") : "Event type"
                        color: muted
                        font.pixelSize: 12
                    }
                    ConnComboBox {
                        id: triggerKindCombo
                        Layout.fillWidth: true
                        model: root.triggerKindModel
                        textRole: "text"
                        valueRole: "value"
                        onActivated: function (idx) {
                            if (root._suppressRuleCombos) return;
                            if (root.selectedRule === null) return;
                            var km = root.triggerKindModel;
                            if (idx < 0 || idx >= km.length) return;
                            var val = km[idx].value;
                            var tpm = root._triggerPlatformModel();
                            var pix = triggerPlatformCombo ? Math.max(0, Math.min(triggerPlatformCombo.currentIndex, tpm.length - 1)) : 0;
                            var plat = tpm[pix].value;
                            var neu = val === "gift_received"
                                ? root._giftEvent({
                                    platform: plat,
                                    gift_id: "",
                                    gift_name: "",
                                    min_count: 1
                                })
                                : val === "tiktok_any_gift_received"
                                ? root._tiktokAnyGiftEvent({
                                    platform: plat,
                                    min_price: 1,
                                    user: ""
                                })
                                : val === "tiktok_likes_received"
                                ? root._likesEvent({
                                    platform: plat,
                                    min_count: 1,
                                    scope: "all_users",
                                    user: ""
                                })
                                : val === "tiktok_shared"
                                ? root._tiktokSharedEvent({
                                    platform: plat,
                                    min_count: 1,
                                    user: ""
                                })
                                : (val === "twitch_follow" || val === "twitch_subscribe"
                                    || val === "twitch_resub" || val === "twitch_sub_gift")
                                ? root._simpleUserEvent(val, { platform: plat, user: "" })
                                : val === "twitch_cheer"
                                ? root._twitchCheerEvent({
                                    platform: plat,
                                    min_bits: 1,
                                    user: ""
                                })
                                : val === "twitch_raid"
                                ? root._twitchRaidEvent({
                                    platform: plat,
                                    min_viewers: 1,
                                    user: ""
                                })
                                : val === "tiktok_joined" || val === "tiktok_followed"
                                    || val === "tiktok_paid_subscribed" || val === "tiktok_first_activity"
                                ? root._simpleUserEvent(val, { platform: plat, user: "" })
                                : root._chatEvent({
                                    platform: plat,
                                    text: "",
                                    match: "contains",
                                    case_sensitive: false
                                });
                            var r = root._patchSelectedTrigger(neu);
                            if (r == null) return;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                            root._syncTriggerCombos();
                        }
                    }

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
                                var ep = (root.editingTrigger && root.editingTrigger.params) || {};
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
                            onActivated: function (idx) {
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
                                var r = root._patchSelectedTrigger(root._tiktokAnyGiftEvent({
                                    platform: root._platformForEdits(),
                                    min_price: ep.min_price || 1,
                                    user: text || ""
                                }));
                                if (r == null) return;
                                root._setRule(root.selectedIdx, r);
                                root._save();
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
                                || root.editingTrigger.type === "twitch_sub_gift")
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
                            onActivated: function (idx) {
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
                    Text { text: api ? api.loc("actions.actions") : "Actions"; color: ink; font.pixelSize: 14; font.bold: true }

                    ListView {
                        id: actionsList
                        Layout.fillWidth: true
                        width: parent.width
                        clip: true
                        interactive: true
                        spacing: 10
                        model: root.actionsModel
                        implicitHeight: contentHeight
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                        // Expose root API & action types to delegate via ListView.view.*
                        property var rootApi: root
                        property var actionTypes: root.actionTypeModel

                        delegate: Rectangle {
                            readonly property var page: actionsList.rootApi

                            Layout.fillWidth: true
                            width: actionsList.width
                            radius: 10
                            color: "#111827"
                            border.width: 1
                            border.color: (index === page.selectedActionIdx) ? "#3b4458" : cardEdge

                            readonly property int aIdx: index
                            readonly property string aType: ((modelData && modelData.type) || "play_sound")
                            readonly property string aKind: (aType === "run_exe") ? "run_program" : aType
                            readonly property bool isOpen: index === page.selectedActionIdx
                            readonly property bool obsBrowseUi: aType === "obs_scene" && isOpen

                            // ListView delegates must have a reliable implicit height.
                            implicitHeight: cardLayout.implicitHeight + 20
                            height: implicitHeight

                            ColumnLayout {
                                id: cardLayout
                                x: 10
                                y: 10
                                width: Math.max(1, parent.width - 20)
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    ConnComboBox {
                                        Layout.preferredWidth: 200
                                        Layout.fillWidth: true
                                        model: actionsList.actionTypes
                                        textRole: "text"
                                        valueRole: "value"
                                        currentIndex: actionsList.rootApi._actionTypeIndex(aType)
                                        onActivated: function (idx) {
                                            var apiRef = actionsList.rootApi;
                                            if (apiRef.selectedRule === null) return;
                                            var r = apiRef._copyRule(apiRef.selectedRule);
                                            if (r == null) return;
                                            var t = model[idx].value;
                                            var aa = apiRef.actionsModel.slice();
                                            var ac = apiRef._copyRule(aa[aIdx]);
                                            if (ac) aa[aIdx] = ac;
                                            aa[aIdx].type = t;
                                            if (t === "play_sound") aa[aIdx].params = {
                                                file_path: "",
                                                volume_percent: 100,
                                                skip_if_same_playing: false
                                            };
                                            if (t === "play_random_myinstants_ua") aa[aIdx].params = {
                                                volume_percent: 100,
                                                skip_if_same_playing: false,
                                                max_duration_seconds: 0,
                                                max_page: 1
                                            };
                                            if (t === "write_file") aa[aIdx].params = { file_path: "", text: "", mode: "overwrite" };
                                            if (t === "run_program") aa[aIdx].params = { program_path: "", arguments: "" };
                                            if (t === "speak_tts") aa[aIdx].params = { text: "" };
                                            if (t === "show_overlay") aa[aIdx].params = { text: "", seconds: 3 };
                                            if (t === "obs_scene") aa[aIdx].params = {
                                                mode: "program_scene",
                                                canvas_uuid: "",
                                                scene_name: "",
                                                source_name: "",
                                                visible: true,
                                                revert_previous_state: false,
                                                revert_delay_seconds: 5
                                            };
                                            apiRef.actionsModel = aa;
                                            r.actions = aa;
                                            apiRef._setRule(apiRef.selectedIdx, r);
                                            apiRef._save();
                                        }
                                    }

                                    ConnPillButton {
                                        text: api ? api.loc("actions.delete") : "Delete"
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
                                            color: ink
                                            placeholderTextColor: muted
                                            placeholderText: api ? api.loc("actions.pick_mp3") : "Pick .mp3..."
                                            text: (modelData && modelData.params && modelData.params.file_path) ? modelData.params.file_path : ""
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            readOnly: true
                                        }
                                        ConnPillButton {
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                var p = actApi.pickSoundFile();
                                                if (!p) return;
                                                var r = apiRef._copyRule(apiRef.selectedRule);
                                                if (r == null) return;
                                                var aa = apiRef.actionsModel.slice();
                                                var ac = apiRef._copyRule(aa[aIdx]);
                                                if (ac) aa[aIdx] = ac;
                                                aa[aIdx].params = aa[aIdx].params || {};
                                                aa[aIdx].params.file_path = p;
                                                apiRef.actionsModel = aa;
                                                r.actions = aa;
                                                apiRef._setRule(apiRef.selectedIdx, r);
                                                apiRef._save();
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
                                        Slider {
                                            id: playSoundVolume
                                            Layout.fillWidth: true
                                            from: 0
                                            to: 100
                                            stepSize: 1
                                            value: (modelData && modelData.params && modelData.params.volume_percent !== undefined) ? Number(modelData.params.volume_percent) : 100
                                            onMoved: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.volume_percent = Math.round(value);
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
                                            }
                                        }
                                    }

                                    CheckBox {
                                        id: playSoundSkipDupCb
                                        text: api ? api.loc("actions.play_sound_skip_if_same_playing") : "Skip if this file is already playing or queued"
                                        checked: !!(modelData && modelData.params && modelData.params.skip_if_same_playing)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.skip_if_same_playing === playSoundSkipDupCb.checked) return;
                                            aa[aIdx].params.skip_if_same_playing = playSoundSkipDupCb.checked;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                        Slider {
                                            id: playRandomMyinstantsUaVolume
                                            Layout.fillWidth: true
                                            from: 0
                                            to: 100
                                            stepSize: 1
                                            value: (modelData && modelData.params && modelData.params.volume_percent !== undefined) ? Number(modelData.params.volume_percent) : 100
                                            onMoved: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.volume_percent = Math.round(value);
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
                                            }
                                        }
                                    }

                                    CheckBox {
                                        id: playRandomMyinstantsUaSkipDupCb
                                        text: api ? api.loc("actions.play_sound_skip_if_same_playing") : "Skip if this file is already playing or queued"
                                        checked: !!(modelData && modelData.params && modelData.params.skip_if_same_playing)
                                        onCheckedChanged: {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            if (aa[aIdx].params.skip_if_same_playing === playRandomMyinstantsUaSkipDupCb.checked) return;
                                            aa[aIdx].params.skip_if_same_playing = playRandomMyinstantsUaSkipDupCb.checked;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
                                        }
                                    }

                                    RowLayout {
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
                                            inputMethodHints: Qt.ImhDigitsOnly
                                            text: (modelData && modelData.params && modelData.params.max_duration_seconds !== undefined) ? ("" + modelData.params.max_duration_seconds) : "0"
                                            background: Rectangle { radius: 8; color: fieldBg; border.width: 1; border.color: cardEdge }
                                            onTextEdited: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                var v = parseFloat(text);
                                                if (isNaN(v) || v < 0) v = 0;
                                                aa[aIdx].params.max_duration_seconds = v;
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
                                            }
                                        }
                                    }

                                    RowLayout {
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
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
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
                                            onActivated: function(index) {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.mode = (index === 1) ? "append" : "overwrite";
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextField {
                                            Layout.fillWidth: true
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
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
                                            }
                                            onActiveFocusChanged: {
                                                if (!activeFocus) page._commitSelectedRuleActions(false);
                                            }
                                        }
                                        ConnPillButton {
                                            text: api ? api.loc("actions.browse") : "Browse…"
                                            onClicked: {
                                                var apiRef = actionsList.rootApi;
                                                if (apiRef.selectedRule === null) return;
                                                var p = actApi.pickWriteFile();
                                                if (!p) return;
                                                var r = apiRef._copyRule(apiRef.selectedRule);
                                                if (r == null) return;
                                                var aa = apiRef.actionsModel.slice();
                                                var ac = apiRef._copyRule(aa[aIdx]);
                                                if (ac) aa[aIdx] = ac;
                                                aa[aIdx].params = aa[aIdx].params || {};
                                                aa[aIdx].params.file_path = p;
                                                apiRef.actionsModel = aa;
                                                r.actions = aa;
                                                apiRef._setRule(apiRef.selectedIdx, r);
                                                apiRef._save();
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
                                            page.actionsModel = aa; // keep binding updated without cloning everything
                                            page._scheduleCommitSelectedRuleActions();
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
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                        SpinBox {
                                            from: 0
                                            to: 600
                                            value: (modelData && modelData.params && modelData.params.seconds !== undefined) ? Number(modelData.params.seconds) : 3
                                            editable: true
                                            Layout.preferredWidth: 160
                                            onValueModified: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                aa[aIdx].params.seconds = value;
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
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
                                        onActivated: function (idx) {
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.mode = model[idx].value;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                            onClicked: page._obsRefreshFromObs(aIdx)
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
                                        onActivated: function (idx) {
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.canvas_uuid = model[idx].value;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                        onActivated: function (idx) {
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.scene_name = model[idx].value;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                        onActivated: function (idx) {
                                            if (page._suppressObsBrowseCombos) return;
                                            if (idx < 0) return;
                                            var aa = page.actionsModel;
                                            if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                            if (!aa[aIdx].params) aa[aIdx].params = {};
                                            aa[aIdx].params.source_name = model[idx].value;
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                            page.actionsModel = aa;
                                            page._scheduleCommitSelectedRuleActions();
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
                                        Switch {
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
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
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
                                        CheckBox {
                                            id: obsRevertCb
                                            text: api ? api.loc("actions.obs_revert_checkbox") : "Revert visibility to how it was"
                                            checked: !!(modelData && modelData.params && modelData.params.revert_previous_state)
                                            onCheckedChanged: {
                                                var aa = page.actionsModel;
                                                if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                if (!aa[aIdx].params) aa[aIdx].params = {};
                                                if (aa[aIdx].params.revert_previous_state === obsRevertCb.checked) return;
                                                aa[aIdx].params.revert_previous_state = obsRevertCb.checked;
                                                page.actionsModel = aa;
                                                page._scheduleCommitSelectedRuleActions();
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
                                            SpinBox {
                                                id: obsRevertSec
                                                from: 1
                                                to: 3600
                                                editable: true
                                                implicitWidth: 140
                                                enabled: !!(modelData && modelData.params && modelData.params.revert_previous_state)
                                                value: {
                                                    if (!modelData || !modelData.params) return 5;
                                                    var v = modelData.params.revert_delay_seconds;
                                                    if (v === undefined || v === null || v === "") return 5;
                                                    var n = Number(v);
                                                    if (isNaN(n) || n < 1) return 1;
                                                    if (n > 3600) return 3600;
                                                    return Math.round(n);
                                                }
                                                onValueModified: {
                                                    var aa = page.actionsModel;
                                                    if (!aa || aIdx < 0 || aIdx >= aa.length) return;
                                                    if (!aa[aIdx].params) aa[aIdx].params = {};
                                                    aa[aIdx].params.revert_delay_seconds = obsRevertSec.value;
                                                    page.actionsModel = aa;
                                                    page._scheduleCommitSelectedRuleActions();
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

                    ConnPillButton {
                        text: api ? api.loc("actions.add_action") : "+ Add action"
                        pillFontSize: 12
                        onClicked: {
                            if (root.selectedRule === null) return;
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            var aa = root.actionsModel.slice();
                            aa.push({
                                type: "play_sound",
                                params: { file_path: "", volume_percent: 100, skip_if_same_playing: false }
                            });
                            root.actionsModel = aa;
                            root.selectedActionIdx = aa.length - 1;
                            r.actions = aa;
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    ConnPillButton {
                        text: api ? (api.loc("actions.clear") || "Clear") : "Clear"
                        pillFontSize: 12
                        onClicked: {
                            if (root.selectedRule === null) return;
                            var r = root._copyRule(root.selectedRule);
                            if (r == null) return;
                            root.actionsModel = [];
                            root.selectedActionIdx = -1;
                            r.actions = [];
                            root._setRule(root.selectedIdx, r);
                            root._save();
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
                }
            }
        }
    }

    // Simple toast "Saved" notification (only for explicit Save button).
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

