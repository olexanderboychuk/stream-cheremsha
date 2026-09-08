import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    width: 800
    height: 600
    visible: true
    title: "Layout Fix Test"
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 20
        padding: 20
        
        Text {
            text: "Testing GAMEPLAY / BEHAVIOR Section Layout"
            font.pixelSize: 18
            color: "white"
        }
        
        // Test the WidgetEditorSection with multiple controls
        WidgetEditorSection {
            title: "Gameplay / Behavior"
            description: "Rules, sources, timing, and widget behavior."
            icon: "≡"
            expanded: true
            
            // Simulate some behavior settings
            WidgetEditorControl {
                label: "Enable Auto-Start"
                description: "Automatically start the widget when stream begins"
                type: "toggle"
                field: "auto_start"
                value: false
            }
            
            WidgetEditorControl {
                label: "Cooldown Period"
                description: "Seconds between widget activations"
                type: "number"
                field: "cooldown"
                value: 30
                minimum: 5
                maximum: 300
            }
            
            WidgetEditorControl {
                label: "Max Participants"
                description: "Maximum number of participants allowed"
                type: "number"
                field: "max_participants"
                value: 10
                minimum: 1
                maximum: 50
            }
            
            WidgetEditorControl {
                label: "Notification Sound"
                description: "Sound played when widget activates"
                type: "select"
                field: "notification_sound"
                value: "default"
                options: ["none", "default", "alert1", "alert2"]
                optionLabels: ["None", "Default", "Alert 1", "Alert 2"]
            }
            
            WidgetEditorControl {
                label: "Custom CSS Class"
                description: "Additional CSS classes for styling"
                type: "text"
                field: "css_class"
                value: ""
            }
        }
    }
    
    background: Rectangle { color: "#0f172a" }
}