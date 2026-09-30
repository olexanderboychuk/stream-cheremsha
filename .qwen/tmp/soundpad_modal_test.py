"""Functional regression test for SoundpadView modal save paths.

Loads the real SoundpadView.qml offscreen with a mock spApi and drives:
  A) add-modal flow   -> _saveAddSound() (was ReferenceError at line 234)
  B) add error path   -> rejected file keeps modal open, sets addErrorMsg
  C) edit-modal flow  -> _saveEditSound() (same cross-scope bug class)
  D) hotkey modal     -> captureZone focus Connections (cross-scope before fix)

Any QML ReferenceError printed to stderr fails the run.
"""

from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QUrl, Slot  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression  # noqa: E402

REPO = "/home/oleksandrboichuk/Dev/Self/stream-cheremsha"
QML_DIR = os.environ.get("SOUNDPAD_TEST_QML_DIR",
                         os.path.join(REPO, "src", "stream_cheremsha", "qml"))
VIEW_QML = os.path.join(QML_DIR, "SoundpadView.qml")


class MockSpApi(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.add_calls: list[tuple] = []
        self.update_calls: list[tuple] = []
        self.assign_calls: list[tuple] = []
        self.reject_next_add = False
        self._sounds = [
            {
                "id": "sp-1",
                "name": "Old",
                "category": "Custom",
                "volume": 0.8,
                "cooldown_sec": 5.0,
                "playback_mode": "restart",
                "enabled": True,
                "hotkey": "",
                "playing": False,
                "broken": False,
                "waveform_peaks": [],
                "duration_sec": 1.0,
            }
        ]

    @Slot(str, str, str, str, float, str, result=str)
    def addSound(self, fileUrl: str, name: str, category: str, hotkey: str, volume: float, mode: str) -> str:
        self.add_calls.append((fileUrl, name, category, hotkey, volume, mode))
        if self.reject_next_add:
            self.reject_next_add = False
            return ""
        return "sp-new"

    @Slot(str, str, result=bool)
    def updateSoundJson(self, sound_id: str, patch_json: str) -> bool:
        self.update_calls.append((sound_id, json.loads(patch_json)))
        return True

    @Slot(result=str)
    def soundsJson(self) -> str:
        return json.dumps(self._sounds, ensure_ascii=False)

    @Slot(str, str, result=str)
    def assignHotkey(self, sound_id: str, combo: str) -> str:
        self.assign_calls.append((sound_id, combo))
        return "ok"

    @Slot(str, result=bool)
    def clearHotkey(self, sound_id: str) -> bool:
        return True

    @Slot(str, result=str)
    def hotkeyOwnerName(self, combo: str) -> str:
        return "Old" if combo == "F1" else ""

    @Slot(result=str)
    def pickAudioFile(self) -> str:
        return ""

    @Slot(result=str)
    def globalStateJson(self) -> str:
        return json.dumps({"volume": 1.0, "monitor": False, "stream_out": False, "output_device": ""})

    @Slot(result=str)
    def outputDevices(self) -> str:
        return "[]"

    @Slot(str, result=bool)
    def removeSound(self, sound_id: str) -> bool:
        return True

    @Slot(str, result=str)
    def duplicateSound(self, sound_id: str) -> str:
        return ""

    @Slot(str)
    def playSound(self, sound_id: str) -> None:
        pass

    @Slot(str)
    def stopSound(self, sound_id: str) -> None:
        pass

    @Slot(float)
    def setGlobalVolume(self, v: float) -> None:
        pass

    @Slot(bool)
    def setMonitor(self, b: bool) -> None:
        pass

    @Slot(bool)
    def setStreamOut(self, b: bool) -> None:
        pass

    @Slot(str)
    def setOutputDevice(self, desc: str) -> None:
        pass

    @Slot(str)
    def importDroppedUrls(self, urls_json: str) -> str:
        return "[]"


def walk(obj):
    yield obj
    for c in obj.children():
        yield from walk(c)


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlEngine()
    engine.addImportPath(QML_DIR)
    api = MockSpApi()
    engine.rootContext().setContextProperty("spApi", api)

    comp = QQmlComponent(engine, QUrl.fromLocalFile(VIEW_QML))
    if comp.isError():
        print("FAIL: component load error:", comp.errorString())
        return 1

    view = comp.create()
    if view is None:
        print("FAIL: create() returned None")
        return 1

    ctx = engine.rootContext()

    def qeval(js: str):
        expr = QQmlExpression(ctx, view, js)
        result = expr.evaluate()
        if expr.hasError():
            raise AssertionError(
                f"QML expression error in {js!r}: {expr.error()} "
                f"@ {expr.sourceFile()}:{expr.lineNumber()}")
        return result

    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        status = "ok  " if cond else "FAIL"
        print(f"[{status}] {label}" + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(label)

    # ---- A) add-modal flow -------------------------------------------------
    qeval("openAddModal('file:///tmp/fake.mp3')")
    check("A1 modal opens", bool(view.property("showAddModal")))
    check("A2 draft name = file stem", view.property("addDraftName") == "fake",
          f"got {view.property('addDraftName')!r}")

    # field -> root direction: find the add TextField (placeholder 'Airhorn'),
    # type into it, expect onTextChanged to push into root.addDraftName.
    add_field = None
    for o in walk(view):
        if o.metaObject().indexOfProperty("placeholderText") >= 0 and \
           str(o.property("placeholderText")) == "Airhorn":
            add_field = o
            break
    check("A3 add name field found", add_field is not None)
    if add_field is not None:
        # root -> field direction (binding)
        qeval("addDraftName = 'Buzzer'")
        app.processEvents()
        check("A4 root->field binding", str(add_field.property("text")) == "Buzzer",
              f"got {add_field.property('text')!r}")
        # field -> root direction (handler)
        add_field.setProperty("text", "Airhorn")
        app.processEvents()
        check("A5 field->root handler", view.property("addDraftName") == "Airhorn",
              f"got {view.property('addDraftName')!r}")

    qeval("_saveAddSound()")
    check("A6 addSound called once", len(api.add_calls) == 1, f"calls={api.add_calls}")
    if api.add_calls:
        url, name, cat, hk, vol, mode = api.add_calls[0]
        check("A7 args correct",
              url == "file:///tmp/fake.mp3" and name == "Airhorn" and cat == "Меми"
              and hk == "" and abs(float(vol) - 1.0) < 1e-9 and mode == "restart",
              f"got {api.add_calls[0]!r}")
    check("A8 modal closed after save", not bool(view.property("showAddModal")))

    # ---- B) add error path --------------------------------------------------
    api.reject_next_add = True
    qeval("openAddModal('file:///tmp/bad.mp3')")
    qeval("_saveAddSound()")
    check("B1 modal stays open on reject", bool(view.property("showAddModal")))
    check("B2 addErrorMsg set", str(view.property("addErrorMsg")) != "")

    # ---- C) edit-modal flow -------------------------------------------------
    qeval("openEditModal('sp-1')")
    check("C1 edit modal opens", bool(view.property("showEditModal")))
    check("C2 draft loaded from sound", view.property("editName") == "Old"
          and abs(float(view.property("editVolume")) - 0.8) < 1e-9,
          f"name={view.property('editName')!r} vol={view.property('editVolume')!r}")

    # simulate user edits through the real field handlers where possible
    edit_field = None
    for o in walk(view):
        if o.metaObject().indexOfProperty("placeholderText") >= 0 and \
           str(o.property("placeholderText")) == "":
            # candidate: a TextField without placeholder; must live under the
            # 'Редагувати звук' modal (ancestor with dimOpacity + that title)
            p = o.parent()
            while p is not None:
                if p.metaObject().indexOfProperty("dimOpacity") >= 0 and \
                   str(p.property("title")) == "Редагувати звук":
                    edit_field = o
                    break
                p = p.parent()
            if edit_field is not None:
                break
    check("C3 edit name field found", edit_field is not None)
    if edit_field is not None:
        edit_field.setProperty("text", "New Name")
        app.processEvents()
        check("C4 edit field->root handler", view.property("editName") == "New Name",
              f"got {view.property('editName')!r}")

    qeval("_saveEditSound()")
    check("C5 updateSoundJson called once", len(api.update_calls) == 1, f"calls={api.update_calls}")
    if api.update_calls:
        sid, patch = api.update_calls[0]
        expected = {
            "name": "New Name",
            "category": "Custom",
            "volume": 0.8,
            "cooldown_sec": 5.0,
            "playback_mode": "restart",
            "enabled": True,
        }
        check("C6 patch correct", sid == "sp-1" and patch == expected, f"got {sid!r} {patch!r}")
    check("C7 edit modal closed after save", not bool(view.property("showEditModal")))

    # ---- E) add-dialog hotkey/mode drafts ------------------------------------
    qeval("addHotkeyDraft = 'F1'; _refreshAddConflict()")
    check("E1 conflict owner shown", view.property("addConflictOwner") == "Old",
          f"got {view.property('addConflictOwner')!r}")
    qeval("addHotkeyDraft = ''; _refreshAddConflict()")
    check("E2 conflict cleared", view.property("addConflictOwner") == "")
    check("E3 mode default restart", view.property("addDraftMode") == "restart",
          f"got {view.property('addDraftMode')!r}")
    qeval("addDraftMode = 'hold'")
    check("E4 mode draft set", view.property("addDraftMode") == "hold")
    qeval("openAddModal('file:///tmp/fake2.mp3')")
    check("E5 mode reset on open", view.property("addDraftMode") == "restart"
          and view.property("addListening") is False
          and view.property("addConflictOwner") == "")

    # ---- D) hotkey modal focus path -----------------------------------------
    qeval("hotkeyTargetId = 'sp-1'; showHotkeyModal = true")
    app.processEvents()
    check("D1 hotkey modal opens", bool(view.property("showHotkeyModal")))
    qeval("showHotkeyModal = false")
    print()
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S): {failures}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    # Capture stderr (fd 2) for the whole run; QML JS errors land there.
    saved = os.dup(2)
    r, w = os.pipe()
    code = 1
    try:
        os.dup2(w, 2)
        code = main()
    finally:
        os.dup2(saved, 2)
        os.close(w)  # close write end so the read below sees EOF

    err_text = ""
    with os.fdopen(r, "r", encoding="utf-8") as buf:
        err_text = buf.read()

    if "ReferenceError" in err_text or "TypeError" in err_text:
        print("---- QML runtime errors captured on stderr ----")
        print(err_text)
        code = 1
    elif err_text.strip():
        # informational only
        pass
    sys.exit(code)
