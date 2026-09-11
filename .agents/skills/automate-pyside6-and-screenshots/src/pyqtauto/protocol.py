"""Protocol definitions for pyqtauto client-server communication.

This module defines the JSON-based protocol used for communication between
the pyqtauto client and server running inside a PySide6 application.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any


class CommandType(str, Enum):
    """Supported command types."""

    # Introspection
    GET_TREE = "get_tree"
    FIND = "find"
    GET_PROPERTY = "get_property"
    LIST_PROPERTIES = "list_properties"

    # Actions
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"
    KEY_SEQUENCE = "key_sequence"
    FOCUS = "focus"
    HOVER = "hover"
    SCROLL = "scroll"

    # State modification
    SET_PROPERTY = "set_property"
    SET_VALUE = "set_value"
    CLEAR = "clear"

    # Verification
    SCREENSHOT = "screenshot"
    ASSERT = "assert"
    EXISTS = "exists"
    IS_VISIBLE = "is_visible"
    IS_ENABLED = "is_enabled"

    # Synchronization
    WAIT = "wait"
    WAIT_IDLE = "wait_idle"
    SLEEP = "sleep"

    # App control
    CLOSE = "close"
    QUIT = "quit"


class ErrorCode(str, Enum):
    """Error codes for command responses."""

    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_VISIBLE = "ELEMENT_NOT_VISIBLE"
    ELEMENT_NOT_ENABLED = "ELEMENT_NOT_ENABLED"
    PROPERTY_NOT_FOUND = "PROPERTY_NOT_FOUND"
    INVALID_SELECTOR = "INVALID_SELECTOR"
    INVALID_COMMAND = "INVALID_COMMAND"
    INVALID_PARAMS = "INVALID_PARAMS"
    TIMEOUT = "TIMEOUT"
    SCREENSHOT_FAILED = "SCREENSHOT_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class Command:
    """A command to be executed by the server."""

    id: str
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str | bytes) -> Command:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        d = json.loads(data)
        return cls(
            id=d.get("id", ""),
            command=d.get("command", ""),
            params=d.get("params", {}),
            options=d.get("options", {}),
        )


@dataclass
class ErrorInfo:
    """Error details for failed commands."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """Response from the server after executing a command."""

    id: str
    success: bool
    result: dict[str, Any] | None = None
    error: ErrorInfo | None = None
    duration_ms: int = 0

    def to_json(self) -> str:
        d = {
            "id": self.id,
            "success": self.success,
            "duration_ms": self.duration_ms,
        }
        if self.result is not None:
            d["result"] = self.result
        if self.error is not None:
            d["error"] = {
                "code": self.error.code,
                "message": self.error.message,
                "details": self.error.details,
            }
        return json.dumps(d)

    @classmethod
    def from_json(cls, data: str | bytes) -> Response:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        d = json.loads(data)
        error = None
        if "error" in d:
            error = ErrorInfo(
                code=d["error"].get("code", ""),
                message=d["error"].get("message", ""),
                details=d["error"].get("details", {}),
            )
        return cls(
            id=d.get("id", ""),
            success=d.get("success", False),
            result=d.get("result"),
            error=error,
            duration_ms=d.get("duration_ms", 0),
        )

    @classmethod
    def success_response(
        cls, id: str, result: dict[str, Any], duration_ms: int = 0
    ) -> Response:
        return cls(id=id, success=True, result=result, duration_ms=duration_ms)

    @classmethod
    def error_response(
        cls,
        id: str,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        duration_ms: int = 0,
    ) -> Response:
        return cls(
            id=id,
            success=False,
            error=ErrorInfo(code=code.value, message=message, details=details or {}),
            duration_ms=duration_ms,
        )


# Selector types
SELECTOR_BY_NAME = "@name:"
SELECTOR_BY_CLASS = "@class:"
SELECTOR_BY_TEXT = "@text:"
SELECTOR_BY_ACCESSIBLE = "@accessible:"


@dataclass
class WidgetInfo:
    """Information about a widget in the tree."""

    object_name: str
    class_name: str
    role: str
    visible: bool
    enabled: bool
    focused: bool
    geometry: dict[str, int]
    path: str
    text: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    children: list[WidgetInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "objectName": self.object_name,
            "class": self.class_name,
            "role": self.role,
            "visible": self.visible,
            "enabled": self.enabled,
            "focused": self.focused,
            "geometry": self.geometry,
            "path": self.path,
        }
        if self.text is not None:
            d["text"] = self.text
        if self.properties:
            d["properties"] = self.properties
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


# Default configuration
DEFAULT_PORT = 9876
DEFAULT_HOST = "localhost"
ENV_PORT = "PYQTAUTO_PORT"
ENV_ENABLED = "PYQTAUTO_ENABLED"


# Widget role mappings
ROLE_MAPPINGS = {
    "QPushButton": "button",
    "QToolButton": "button",
    "QCheckBox": "checkbox",
    "QRadioButton": "radio",
    "QComboBox": "combobox",
    "QLineEdit": "lineedit",
    "QTextEdit": "textarea",
    "QPlainTextEdit": "textarea",
    "QSpinBox": "spinbox",
    "QDoubleSpinBox": "spinbox",
    "QSlider": "slider",
    "QScrollBar": "scrollbar",
    "QLabel": "label",
    "QMainWindow": "window",
    "QDialog": "dialog",
    "QWidget": "widget",
    "QFrame": "frame",
    "QTabWidget": "tabwidget",
    "QTabBar": "tabbar",
    "QListWidget": "list",
    "QListView": "list",
    "QTableWidget": "table",
    "QTableView": "table",
    "QTreeWidget": "tree",
    "QTreeView": "tree",
    "QMenuBar": "menubar",
    "QMenu": "menu",
    "QToolBar": "toolbar",
    "QStatusBar": "statusbar",
    "QGroupBox": "group",
    "QProgressBar": "progressbar",
}


def infer_role(class_name: str) -> str:
    """Infer a semantic role from the Qt class name."""
    return ROLE_MAPPINGS.get(class_name, "widget")
