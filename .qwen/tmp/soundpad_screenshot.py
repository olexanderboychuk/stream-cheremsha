#!/usr/bin/env python3
"""Capture a screenshot of the redesigned Soundpad UI."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import Qt, QUrl, QObject, Slot, Property, Signal
import json

# Create a mock spApi object for the screenshot (no real audio)
class MockSpApi(QObject):
    soundsChanged = Signal()
    
    @Slot(result=str)
    def soundsJson(self):
        # Return some sample sounds to show the grid layout
        return json.dumps([
            {"id": "s1", "name": "Airhorn", "category": "Реакції", "hotkey": "F1", 
             "duration_sec": 2.0, "volume": 1.0, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.3, 0.6, 0.4, 0.8, 0.5, 0.7, 0.9, 0.4], "playing": False},
            {"id": "s2", "name": "Bruh", "category": "Меми", "hotkey": "F2", 
             "duration_sec": 1.5, "volume": 0.8, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.5, 0.3, 0.7, 0.4, 0.6, 0.8, 0.3, 0.5], "playing": False},
            {"id": "s3", "name": "Vine Boom", "category": "Меми", "hotkey": "F3", 
             "duration_sec": 1.2, "volume": 1.0, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.8, 0.9, 0.7, 0.5, 0.6, 0.4, 0.3, 0.2], "playing": False},
            {"id": "s4", "name": "Sad Violin", "category": "Музика", "hotkey": "F4", 
             "duration_sec": 7.0, "volume": 0.9, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.6, 0.4], "playing": False},
            {"id": "s5", "name": "Clap", "category": "Реакції", "hotkey": "F5", 
             "duration_sec": 1.0, "volume": 1.0, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2], "playing": False},
            {"id": "s6", "name": "Wow", "category": "Меми", "hotkey": "F6", 
             "duration_sec": 1.8, "volume": 0.7, "cooldown_sec": 0, "enabled": True,
             "waveform_peaks": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.7, 0.5], "playing": False},
        ])
    
    @Slot(result=str)
    def outputDevices(self):
        return json.dumps(["Default", "AD103 High Definition"])
    
    @Slot(str)
    def setOutputDevice(self, device): pass
    
    @Slot(float)
    def setGlobalVolume(self, vol): pass
    
    @Slot(bool)
    def setMonitor(self, on): pass
    
    @Slot(bool)
    def setStreamOut(self, on): pass
    
    @Slot(str, result=str)
    def addSound(self, url, name, cat, hk, vol): return ""
    
    @Slot(str)
    def removeSound(self, sid): pass
    
    @Slot(str, str)
    def assignHotkey(self, sid, combo): pass
    
    @Slot(str)
    def clearHotkey(self, sid): pass
    
    @Slot(str)
    def playSound(self, sid): pass
    
    @Slot(str)
    def stopSound(self, sid): pass
    
    @Slot(result=str)
    def globalStateJson(self):
        return json.dumps({"volume": 0.78, "monitor": True, "stream_out": True, "output_device": ""})

def main():
    app = QApplication(sys.argv)
    
    # Create mock spApi and set as context property
    mock_api = MockSpApi()
    
    # Load the SoundpadView QML with proper import path
    qml_path = Path(__file__).parent.parent.parent / "src/stream_cheremsha/qml/SoundpadView.qml"
    
    widget = QQuickWidget()
    widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
    widget.engine().addImportPath(str(Path(__file__).parent.parent.parent / "src/stream_cheremsha/qml"))
    widget.rootContext().setContextProperty("spApi", mock_api)
    widget.setSource(QUrl.fromLocalFile(str(qml_path)))
    
    # Wait for loading
    app.processEvents()
    
    # Check if loaded successfully
    root = widget.rootObject()
    if not root:
        print("Failed to load QML - no root object")
        return 1
    
    print(f"Root object: {root}")
    
    # Set a reasonable size for the screenshot (show grid with multiple cards)
    widget.resize(1200, 800)
    app.processEvents()
    
    # Capture screenshot
    output_path = Path(__file__).parent / "soundpad_redesign.png"
    widget.grab().save(str(output_path), "PNG")
    print(f"Screenshot saved to: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
