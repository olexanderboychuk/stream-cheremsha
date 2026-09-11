# PyQtAuto

A Playwright-like automation library for PySide6 applications. Enables remote control, testing, and screenshot capture of Qt desktop applications through a simple JSON-over-TCP protocol.

## Features

- **Zero-config server**: Embed in any PySide6 app with 2 lines of code
- **Remote control**: Python API and CLI for automation
- **Widget selectors**: Find widgets by name, class, text, or path
- **Full interaction**: Click, type, key press, scroll, hover, focus
- **Screenshots**: Capture app or specific widgets as PNG/JPG
- **Verification**: Assert properties, check visibility/enabled state
- **Synchronization**: Wait for conditions, idle state detection

## Installation

```bash
# As a dependency
uv add pyqtauto

# For development
uv add --dev pyqtauto
```

Or as a local source dependency in `pyproject.toml`:

```toml
[tool.uv.sources]
pyqtauto = { path = "/path/to/pyqtauto" }
```

## Quick Start

### 1. Add server to your PySide6 app

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from pyqtauto.server import start_server

def main():
    app = QApplication(sys.argv)

    # Start automation server (checks PYQTAUTO_ENABLED env var)
    start_server()  # or start_server(force=True) to always enable

    window = QMainWindow()
    window.setObjectName("main_window")  # Important for selectors!
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### 2. Write automation script

```python
from pyqtauto import PyQtAutoClient

with PyQtAutoClient(port=9876) as client:
    # Wait for app to be ready
    client.wait_idle()

    # Interact with widgets
    client.type("@name:email_input", "test@example.com")
    client.click("@name:submit_button")

    # Verify results
    client.wait("@name:success_label", "visible")
    client.screenshot_to_file("result.png")

    # Read widget state
    text = client.get_text("@name:status_label")
    print(f"Status: {text}")
```

### 3. Or use the CLI

```bash
# Get widget tree
pyqtauto tree

# Click a button
pyqtauto click "@name:submit_btn"

# Type text
pyqtauto type "@name:input" "Hello World"

# Take screenshot
pyqtauto screenshot output.png

# Interactive shell
pyqtauto shell
```

## Widget Selectors

Always set `objectName` on widgets you want to automate:

```python
button = QPushButton("Click Me")
button.setObjectName("submit_btn")  # Use as "@name:submit_btn"
```

| Selector | Example | Description |
|----------|---------|-------------|
| `@name:` | `@name:submit_btn` | Find by objectName (recommended) |
| `@class:` | `@class:QPushButton` | Find first widget of class |
| `@text:` | `@text:Submit` | Find by text content |
| `path` | `main/form/button` | Hierarchical path |

## API Reference

### Actions

```python
client.click("@name:button")           # Left click
client.double_click("@name:item")      # Double click
client.right_click("@name:widget")     # Context menu
client.type("@name:input", "text")     # Type text
client.key("@name:input", "Return")    # Press key
client.key_sequence("@name:input", "Ctrl+S")  # Key combo
client.focus("@name:widget")           # Set focus
client.set_value("@name:checkbox", True)      # Smart setter
```

### Verification

```python
client.exists("@name:widget")          # Check existence
client.is_visible("@name:widget")      # Check visibility
client.is_enabled("@name:widget")      # Check enabled state
client.get_text("@name:label")         # Get text content
client.get_property("@name:spin", "value")    # Get property
client.screenshot_to_file("shot.png")  # Capture screenshot
```

### Synchronization

```python
client.wait("@name:button", "visible", timeout_ms=5000)
client.wait("@name:spinner", "not_visible")
client.wait_idle()                     # Wait for event queue
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYQTAUTO_ENABLED` | - | Set to `1` to enable server |
| `PYQTAUTO_PORT` | `9876` | Server port |

## Demo

Run the included demo:

```bash
# Terminal 1: Start demo app
python tests/qtappdemo.py

# Terminal 2: Run automation
python tests/qtcontroldemo.py
```

## Claude Code Integration

PyQtAuto includes a [Claude Code skill](https://code.claude.com/docs/en/skills) that teaches Claude how to automate and test your PySide6 applications. To install it:

**For a single project:**

```bash
mkdir -p .claude/skills/automate-pyside6-and-screenshots
cp /path/to/pyqtauto/SKILL.md .claude/skills/automate-pyside6-and-screenshots/
```

**For all your projects (personal skill):**

```bash
mkdir -p ~/.claude/skills/automate-pyside6-and-screenshots
cp /path/to/pyqtauto/SKILL.md ~/.claude/skills/automate-pyside6-and-screenshots/
```

Once installed, Claude can automatically use PyQtAuto when you ask it to test or automate your PySide6 application, or you can invoke it directly with `/automate-pyside6-and-screenshots`.
