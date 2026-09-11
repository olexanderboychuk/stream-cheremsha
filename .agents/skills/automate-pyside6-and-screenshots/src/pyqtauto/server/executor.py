"""Command executor for PyQtAuto.

This module handles executing commands received from the client,
including UI interactions, widget queries, and screenshots.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
import io
import time
from typing import Any

from PySide6.QtCore import QCoreApplication, QPoint, Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QScrollBar,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from ..protocol import (
    Command,
    CommandType,
    ErrorCode,
    Response,
)
from .finder import ElementFinder
from .introspector import UIIntrospector


class CommandExecutor:
    """Executes commands on the Qt application."""

    def __init__(self, root: QWidget | None = None):
        """Initialize the executor.

        Args:
            root: The root widget for operations. If None, uses active window.
        """
        self._finder = ElementFinder(root)
        self._introspector = UIIntrospector(root)
        self._handlers: dict[str, Callable[[Command], Response]] = {}
        self._register_handlers()

    def set_root(self, root: QWidget | None):
        """Set the root widget."""
        self._finder.set_root(root)
        self._introspector.set_root(root)

    def execute(self, command: Command) -> Response:
        """Execute a command and return the response.

        Args:
            command: The command to execute.

        Returns:
            The response from executing the command.
        """
        start_time = time.time()

        handler = self._handlers.get(command.command)
        if handler is None:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_COMMAND,
                f"Unknown command: {command.command}",
            )

        try:
            response = handler(command)
            response.duration_ms = int((time.time() - start_time) * 1000)
            return response
        except Exception as e:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def _register_handlers(self):
        """Register command handlers."""
        # Introspection
        self._handlers[CommandType.GET_TREE.value] = self._handle_get_tree
        self._handlers[CommandType.FIND.value] = self._handle_find
        self._handlers[CommandType.GET_PROPERTY.value] = self._handle_get_property
        self._handlers[CommandType.LIST_PROPERTIES.value] = self._handle_list_properties

        # Actions
        self._handlers[CommandType.CLICK.value] = self._handle_click
        self._handlers[CommandType.DOUBLE_CLICK.value] = self._handle_double_click
        self._handlers[CommandType.RIGHT_CLICK.value] = self._handle_right_click
        self._handlers[CommandType.TYPE.value] = self._handle_type
        self._handlers[CommandType.KEY.value] = self._handle_key
        self._handlers[CommandType.KEY_SEQUENCE.value] = self._handle_key_sequence
        self._handlers[CommandType.FOCUS.value] = self._handle_focus
        self._handlers[CommandType.HOVER.value] = self._handle_hover
        self._handlers[CommandType.SCROLL.value] = self._handle_scroll

        # State modification
        self._handlers[CommandType.SET_PROPERTY.value] = self._handle_set_property
        self._handlers[CommandType.SET_VALUE.value] = self._handle_set_value
        self._handlers[CommandType.CLEAR.value] = self._handle_clear

        # Verification
        self._handlers[CommandType.SCREENSHOT.value] = self._handle_screenshot
        self._handlers[CommandType.ASSERT.value] = self._handle_assert
        self._handlers[CommandType.EXISTS.value] = self._handle_exists
        self._handlers[CommandType.IS_VISIBLE.value] = self._handle_is_visible
        self._handlers[CommandType.IS_ENABLED.value] = self._handle_is_enabled

        # Synchronization
        self._handlers[CommandType.WAIT.value] = self._handle_wait
        self._handlers[CommandType.WAIT_IDLE.value] = self._handle_wait_idle
        self._handlers[CommandType.SLEEP.value] = self._handle_sleep

        # App control
        self._handlers[CommandType.CLOSE.value] = self._handle_close
        self._handlers[CommandType.QUIT.value] = self._handle_quit

    def _get_widget(
        self, command: Command, param_name: str = "target"
    ) -> tuple[QWidget | None, Response | None]:
        """Get a widget from command params.

        Returns:
            Tuple of (widget, error_response). If widget is None, error_response is set.
        """
        selector = command.params.get(param_name)
        if not selector:
            return None, Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                f"Missing required parameter: {param_name}",
            )

        visible_only = command.options.get("visible_only", True)
        widget = self._finder.find(selector, visible_only=visible_only)

        if widget is None:
            return None, Response.error_response(
                command.id,
                ErrorCode.ELEMENT_NOT_FOUND,
                f"Widget not found: {selector}",
                {"selector": selector},
            )

        return widget, None

    # Introspection handlers

    def _handle_get_tree(self, command: Command) -> Response:
        depth = command.params.get("depth", -1)
        include_invisible = command.params.get("include_invisible", False)
        include_properties = command.params.get("include_properties", True)

        tree = self._introspector.get_tree(
            depth=depth,
            include_invisible=include_invisible,
            include_properties=include_properties,
        )

        if tree is None:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                "No root widget found",
            )

        return Response.success_response(command.id, {"tree": tree})

    def _handle_find(self, command: Command) -> Response:
        selector = command.params.get("query") or command.params.get("selector")
        if not selector:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: query or selector",
            )

        max_results = command.params.get("max_results", 10)
        visible_only = command.params.get("visible_only", True)

        widgets = self._finder.find_all(
            selector, visible_only=visible_only, max_results=max_results
        )

        results = []
        for widget in widgets:
            geo = widget.geometry()
            results.append(
                {
                    "objectName": widget.objectName(),
                    "class": widget.__class__.__name__,
                    "visible": widget.isVisible(),
                    "enabled": widget.isEnabled(),
                    "geometry": {
                        "x": geo.x(),
                        "y": geo.y(),
                        "width": geo.width(),
                        "height": geo.height(),
                    },
                }
            )

        return Response.success_response(
            command.id, {"results": results, "count": len(results)}
        )

    def _handle_get_property(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        prop_name = command.params.get("property")
        if not prop_name:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: property",
            )

        # Try to get property
        value = self._get_widget_property(widget, prop_name)
        if value is None:
            return Response.error_response(
                command.id,
                ErrorCode.PROPERTY_NOT_FOUND,
                f"Property not found: {prop_name}",
            )

        return Response.success_response(command.id, {"value": value})

    def _handle_list_properties(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        # Get all available properties
        props = self._introspector._get_widget_properties(widget)

        # Add common properties
        props["objectName"] = widget.objectName()
        props["visible"] = widget.isVisible()
        props["enabled"] = widget.isEnabled()
        props["focused"] = widget.hasFocus()

        return Response.success_response(command.id, {"properties": props})

    # Action handlers

    def _handle_click(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        button_name = command.params.get("button", "left")

        # For checkboxes and radio buttons, use click() method directly
        # as QTest.mouseClick may miss the clickable area
        if isinstance(widget, QAbstractButton):
            widget.click()
            return Response.success_response(command.id, {"clicked": True})

        # For other widgets, use mouse simulation
        button = self._get_mouse_button(button_name)
        pos = self._get_click_position(widget, command.params.get("pos"))

        try:
            QTest.mouseClick(widget, button, Qt.KeyboardModifier.NoModifier, pos)
        except Exception as e:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                f"Click failed: {e}",
            )

        return Response.success_response(command.id, {"clicked": True})

    def _handle_double_click(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        pos = self._get_click_position(widget, command.params.get("pos"))
        try:
            QTest.mouseDClick(
                widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos
            )
        except Exception as e:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                f"Double-click failed: {e}",
            )

        return Response.success_response(command.id, {"clicked": True})

    def _handle_right_click(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        pos = self._get_click_position(widget, command.params.get("pos"))
        try:
            QTest.mouseClick(
                widget, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, pos
            )
        except Exception as e:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                f"Right-click failed: {e}",
            )

        return Response.success_response(command.id, {"clicked": True})

    def _handle_type(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        text = command.params.get("text", "")
        clear_first = command.params.get("clear_first", True)

        try:
            # For text editors with multiline text, use direct text setting
            # as QTest.keyClicks doesn't handle newlines well
            if isinstance(widget, (QTextEdit, QPlainTextEdit)):
                if clear_first:
                    widget.clear()
                # Insert text at cursor or set directly
                if clear_first:
                    widget.setPlainText(text)
                else:
                    widget.insertPlainText(text)
            elif isinstance(widget, QLineEdit):
                if clear_first:
                    widget.clear()
                # For single line, use keyClicks for realistic simulation
                QTest.keyClicks(widget, text)
            else:
                # Generic widget - try keyClicks
                QTest.keyClicks(widget, text)
        except Exception as e:
            return Response.error_response(
                command.id,
                ErrorCode.INTERNAL_ERROR,
                f"Type failed: {e}",
            )

        return Response.success_response(command.id, {"typed": text})

    def _handle_key(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        key_name = command.params.get("key")
        if not key_name:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: key",
            )

        key = self._get_key(key_name)
        modifiers = self._get_modifiers(command.params.get("modifiers", []))

        QTest.keyClick(widget, key, modifiers)

        return Response.success_response(command.id, {"pressed": key_name})

    def _handle_key_sequence(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        sequence = command.params.get("sequence")
        if not sequence:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: sequence",
            )

        # Parse key sequence (e.g., "Ctrl+S")
        key_seq = QKeySequence(sequence)
        if key_seq.isEmpty():
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                f"Invalid key sequence: {sequence}",
            )

        # Execute the key sequence
        for i in range(key_seq.count()):
            combo = key_seq[i]
            key = Qt.Key(combo.key())
            modifiers = combo.keyboardModifiers()
            QTest.keyClick(widget, key, modifiers)

        return Response.success_response(command.id, {"sequence": sequence})

    def _handle_focus(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        widget.setFocus()
        return Response.success_response(command.id, {"focused": True})

    def _handle_hover(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        pos = self._get_click_position(widget, command.params.get("pos"))
        QTest.mouseMove(widget, pos)

        return Response.success_response(command.id, {"hovered": True})

    def _handle_scroll(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        delta_x = command.params.get("delta_x", 0)
        delta_y = command.params.get("delta_y", 0)
        pos = self._get_click_position(widget, command.params.get("pos"))

        # QTest doesn't have a direct scroll method, use wheel event
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QWheelEvent

        global_pos = widget.mapToGlobal(pos)
        event = QWheelEvent(
            QPointF(pos),
            QPointF(global_pos),
            QPoint(delta_x, delta_y),
            QPoint(delta_x, delta_y),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QCoreApplication.sendEvent(widget, event)

        return Response.success_response(command.id, {"scrolled": True})

    # State modification handlers

    def _handle_set_property(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        prop_name = command.params.get("property")
        value = command.params.get("value")

        if not prop_name:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: property",
            )

        # Try to set property using Qt's property system
        success = widget.setProperty(prop_name, value)
        if not success:
            # Try using setter method
            setter_name = f"set{prop_name[0].upper()}{prop_name[1:]}"
            if hasattr(widget, setter_name):
                getattr(widget, setter_name)(value)
                success = True

        return Response.success_response(command.id, {"set": success})

    def _handle_set_value(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        value = command.params.get("value")

        # Smart value setting based on widget type
        if isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            widget.setPlainText(str(value))
        elif isinstance(widget, QComboBox):
            if isinstance(value, int):
                widget.setCurrentIndex(value)
            else:
                widget.setCurrentText(str(value))
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, (QSlider, QScrollBar)):
            widget.setValue(int(value))
        elif isinstance(widget, (QCheckBox, QRadioButton)):
            widget.setChecked(bool(value))
        elif isinstance(widget, QTabWidget):
            widget.setCurrentIndex(int(value))
        else:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                f"Cannot set value on widget of type {widget.__class__.__name__}",
            )

        return Response.success_response(command.id, {"value": value})

    def _handle_clear(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
            widget.clear()
        elif isinstance(widget, QComboBox) and widget.isEditable():
            widget.clearEditText()
        else:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                f"Cannot clear widget of type {widget.__class__.__name__}",
            )

        return Response.success_response(command.id, {"cleared": True})

    # Verification handlers

    def _handle_screenshot(self, command: Command) -> Response:
        target = command.params.get("target")
        filename = command.params.get("filename")
        format_type = command.params.get("format", "png")

        if target:
            widget = self._finder.find(target)
            if widget is None:
                return Response.error_response(
                    command.id,
                    ErrorCode.ELEMENT_NOT_FOUND,
                    f"Widget not found: {target}",
                )
        else:
            widget = self._finder.get_root()
            if widget is None:
                return Response.error_response(
                    command.id,
                    ErrorCode.INTERNAL_ERROR,
                    "No root widget found",
                )

        # Capture screenshot
        pixmap = widget.grab()

        if filename:
            # Save to file
            success = pixmap.save(filename, format_type.upper())
            if not success:
                return Response.error_response(
                    command.id,
                    ErrorCode.SCREENSHOT_FAILED,
                    f"Failed to save screenshot to {filename}",
                )
            return Response.success_response(
                command.id,
                {
                    "saved": filename,
                    "width": pixmap.width(),
                    "height": pixmap.height(),
                },
            )
        else:
            # Return as base64
            buffer = io.BytesIO()
            pixmap.save(buffer, format_type.upper())
            image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return Response.success_response(
                command.id,
                {
                    "image": image_data,
                    "format": format_type,
                    "width": pixmap.width(),
                    "height": pixmap.height(),
                },
            )

    def _handle_assert(self, command: Command) -> Response:
        widget, error = self._get_widget(command)
        if error:
            return error

        prop_name = command.params.get("property")
        operator = command.params.get("operator", "==")
        expected = command.params.get("expected")

        actual = self._get_widget_property(widget, prop_name)

        passed = self._compare_values(actual, expected, operator)

        return Response.success_response(
            command.id,
            {
                "passed": passed,
                "actual": actual,
                "expected": expected,
                "operator": operator,
            },
        )

    def _handle_exists(self, command: Command) -> Response:
        selector = command.params.get("target")
        if not selector:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: target",
            )

        widget = self._finder.find(selector, visible_only=False)
        exists = widget is not None

        return Response.success_response(command.id, {"exists": exists})

    def _handle_is_visible(self, command: Command) -> Response:
        selector = command.params.get("target")
        if not selector:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: target",
            )

        widget = self._finder.find(selector, visible_only=False)
        exists = widget is not None
        visible = widget.isVisible() if widget else False

        return Response.success_response(
            command.id, {"exists": exists, "visible": visible}
        )

    def _handle_is_enabled(self, command: Command) -> Response:
        selector = command.params.get("target")
        if not selector:
            return Response.error_response(
                command.id,
                ErrorCode.INVALID_PARAMS,
                "Missing required parameter: target",
            )

        widget = self._finder.find(selector, visible_only=False)
        exists = widget is not None
        enabled = widget.isEnabled() if widget else False

        return Response.success_response(
            command.id, {"exists": exists, "enabled": enabled}
        )

    # Synchronization handlers

    def _handle_wait(self, command: Command) -> Response:
        selector = command.params.get("target")
        condition = command.params.get("condition", "visible")
        timeout_ms = command.params.get("timeout_ms", 5000)
        poll_interval_ms = command.params.get("poll_interval_ms", 50)

        start_time = time.time()
        timeout_sec = timeout_ms / 1000.0
        poll_interval_sec = poll_interval_ms / 1000.0

        while time.time() - start_time < timeout_sec:
            widget = (
                self._finder.find(selector, visible_only=False)
                if selector
                else self._finder.get_root()
            )

            if self._check_condition(widget, condition):
                return Response.success_response(command.id, {"condition_met": True})

            # Process events to keep UI responsive
            QCoreApplication.processEvents()
            time.sleep(poll_interval_sec)

        return Response.error_response(
            command.id,
            ErrorCode.TIMEOUT,
            f"Condition '{condition}' not met within {timeout_ms}ms",
        )

    def _handle_wait_idle(self, command: Command) -> Response:
        timeout_ms = command.params.get("timeout_ms", 5000)

        # Process all pending events multiple times to ensure queue is drained
        # PySide6 doesn't have hasPendingEvents, so we process events
        # for a reasonable number of iterations
        iterations = min(10, max(1, timeout_ms // 50))

        for _ in range(iterations):
            QCoreApplication.processEvents()
            time.sleep(0.01)

        return Response.success_response(command.id, {"idle": True})

    def _handle_sleep(self, command: Command) -> Response:
        ms = command.params.get("ms", 1000)
        time.sleep(ms / 1000.0)
        return Response.success_response(command.id, {"slept_ms": ms})

    # App control handlers

    def _handle_close(self, command: Command) -> Response:
        target = command.params.get("target")

        if target:
            widget = self._finder.find(target)
            if widget is None:
                return Response.error_response(
                    command.id,
                    ErrorCode.ELEMENT_NOT_FOUND,
                    f"Widget not found: {target}",
                )
            widget.close()
        else:
            widget = self._finder.get_root()
            if widget:
                widget.close()

        return Response.success_response(command.id, {"closed": True})

    def _handle_quit(self, command: Command) -> Response:
        app = QApplication.instance()
        if app:
            # Schedule quit for after response is sent
            QTimer.singleShot(100, app.quit)

        return Response.success_response(command.id, {"quitting": True})

    # Helper methods

    def _get_mouse_button(self, button_name: str) -> Qt.MouseButton:
        buttons = {
            "left": Qt.MouseButton.LeftButton,
            "right": Qt.MouseButton.RightButton,
            "middle": Qt.MouseButton.MiddleButton,
        }
        return buttons.get(button_name.lower(), Qt.MouseButton.LeftButton)

    def _get_click_position(self, widget: QWidget, pos: dict | None) -> QPoint:
        if pos:
            return QPoint(pos.get("x", 0), pos.get("y", 0))
        # Default to center
        rect = widget.rect()
        return rect.center()

    def _get_key(self, key_name: str) -> Qt.Key:
        # Map common key names to Qt.Key
        key_map = {
            "enter": Qt.Key.Key_Return,
            "return": Qt.Key.Key_Return,
            "tab": Qt.Key.Key_Tab,
            "escape": Qt.Key.Key_Escape,
            "esc": Qt.Key.Key_Escape,
            "backspace": Qt.Key.Key_Backspace,
            "delete": Qt.Key.Key_Delete,
            "space": Qt.Key.Key_Space,
            "up": Qt.Key.Key_Up,
            "down": Qt.Key.Key_Down,
            "left": Qt.Key.Key_Left,
            "right": Qt.Key.Key_Right,
            "home": Qt.Key.Key_Home,
            "end": Qt.Key.Key_End,
            "pageup": Qt.Key.Key_PageUp,
            "pagedown": Qt.Key.Key_PageDown,
        }

        key_lower = key_name.lower()
        if key_lower in key_map:
            return key_map[key_lower]

        # Try to get from Qt.Key by name
        try:
            return getattr(Qt.Key, f"Key_{key_name}")
        except AttributeError:
            # Single character
            if len(key_name) == 1:
                return Qt.Key(ord(key_name.upper()))

        return Qt.Key.Key_unknown

    def _get_modifiers(self, modifiers: list[str]) -> Qt.KeyboardModifiers:
        result = Qt.KeyboardModifier.NoModifier
        for mod in modifiers:
            mod_lower = mod.lower()
            if mod_lower in ("ctrl", "control"):
                result |= Qt.KeyboardModifier.ControlModifier
            elif mod_lower in ("shift",):
                result |= Qt.KeyboardModifier.ShiftModifier
            elif mod_lower in ("alt",):
                result |= Qt.KeyboardModifier.AltModifier
            elif mod_lower in ("meta", "cmd", "command"):
                result |= Qt.KeyboardModifier.MetaModifier
        return result

    def _get_widget_property(self, widget: QWidget, prop_name: str) -> Any:
        """Get a property value from a widget."""
        # Common properties
        if prop_name == "text":
            if hasattr(widget, "text"):
                return widget.text()
            elif hasattr(widget, "toPlainText"):
                return widget.toPlainText()
            elif hasattr(widget, "currentText"):
                return widget.currentText()
        elif prop_name == "value":
            if hasattr(widget, "value"):
                return widget.value()
        elif prop_name == "checked":
            if hasattr(widget, "isChecked"):
                return widget.isChecked()
        elif prop_name == "visible":
            return widget.isVisible()
        elif prop_name == "enabled":
            return widget.isEnabled()
        elif prop_name == "focused":
            return widget.hasFocus()
        elif prop_name == "objectName":
            return widget.objectName()

        # Try Qt property system
        value = widget.property(prop_name)
        if value is not None:
            return value

        # Try getter method
        if hasattr(widget, prop_name):
            attr = getattr(widget, prop_name)
            if callable(attr):
                return attr()
            return attr

        return None

    def _compare_values(self, actual: Any, expected: Any, operator: str) -> bool:
        """Compare values using the specified operator."""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<":
            return actual < expected
        elif operator == "<=":
            return actual <= expected
        elif operator == "contains":
            return expected in str(actual)
        return False

    def _check_condition(self, widget: QWidget | None, condition: str) -> bool:
        """Check if a widget meets the specified condition."""
        if condition == "exists":
            return widget is not None
        elif condition == "not_exists":
            return widget is None
        elif condition == "visible":
            return widget is not None and widget.isVisible()
        elif condition == "not_visible":
            return widget is None or not widget.isVisible()
        elif condition == "enabled":
            return widget is not None and widget.isEnabled()
        elif condition == "disabled":
            return widget is not None and not widget.isEnabled()
        elif condition == "focused":
            return widget is not None and widget.hasFocus()
        elif condition.startswith("property:"):
            # property:name=value
            if widget is None:
                return False
            parts = condition[9:].split("=", 1)
            if len(parts) == 2:
                prop_name, expected = parts
                actual = self._get_widget_property(widget, prop_name)
                return str(actual) == expected
        return False
