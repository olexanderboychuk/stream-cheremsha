"""Widget introspection for PyQtAuto.

This module provides functionality to introspect the widget tree of a
PySide6 application, extracting information about each widget's properties,
state, and hierarchy.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QWidget,
)

from ..protocol import WidgetInfo, infer_role


class UIIntrospector:
    """Introspects the widget tree of a PySide6 application."""

    def __init__(self, root: QWidget | None = None):
        """Initialize the introspector.

        Args:
            root: The root widget to introspect. If None, uses the active window.
        """
        self._root = root

    def get_root(self) -> QWidget | None:
        """Get the root widget for introspection."""
        if self._root is not None:
            return self._root

        app = QApplication.instance()
        if app is None:
            return None

        # Try active window first
        active = app.activeWindow()
        if active is not None:
            return active

        # Fall back to top-level widgets
        top_level = app.topLevelWidgets()
        for widget in top_level:
            if widget.isVisible():
                return widget

        return top_level[0] if top_level else None

    def set_root(self, root: QWidget | None):
        """Set the root widget for introspection."""
        self._root = root

    def get_tree(
        self,
        root: QWidget | None = None,
        depth: int = -1,
        include_invisible: bool = False,
        include_properties: bool = True,
    ) -> dict[str, Any] | None:
        """Get the widget tree as a dictionary.

        Args:
            root: The root widget. If None, uses the default root.
            depth: Maximum depth to traverse. -1 for unlimited.
            include_invisible: Include invisible widgets.
            include_properties: Include widget properties.

        Returns:
            A dictionary representing the widget tree, or None if no root.
        """
        widget = root or self.get_root()
        if widget is None:
            return None

        info = self._introspect_widget(
            widget,
            path=widget.objectName() or widget.__class__.__name__,
            depth=depth,
            include_invisible=include_invisible,
            include_properties=include_properties,
        )
        return info.to_dict() if info else None

    def _introspect_widget(
        self,
        widget: QWidget,
        path: str,
        depth: int,
        include_invisible: bool,
        include_properties: bool,
        current_depth: int = 0,
    ) -> WidgetInfo | None:
        """Recursively introspect a widget and its children."""
        if not include_invisible and not widget.isVisible():
            return None

        class_name = widget.__class__.__name__
        geo = widget.geometry()

        info = WidgetInfo(
            object_name=widget.objectName() or "",
            class_name=class_name,
            role=infer_role(class_name),
            visible=widget.isVisible(),
            enabled=widget.isEnabled(),
            focused=widget.hasFocus(),
            geometry={
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height(),
            },
            path=path,
        )

        # Extract text if available
        text = self._get_widget_text(widget)
        if text is not None:
            info.text = text

        # Extract type-specific properties
        if include_properties:
            info.properties = self._get_widget_properties(widget)

        # Recursively process children
        if depth != 0:
            children = []
            for child in widget.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
            ):
                child_path = f"{path}/{child.objectName() or child.__class__.__name__}"
                child_info = self._introspect_widget(
                    child,
                    path=child_path,
                    depth=depth - 1 if depth > 0 else -1,
                    include_invisible=include_invisible,
                    include_properties=include_properties,
                    current_depth=current_depth + 1,
                )
                if child_info:
                    children.append(child_info)
            info.children = children

        return info

    def _get_widget_text(self, widget: QWidget) -> str | None:
        """Extract text content from a widget."""
        if isinstance(widget, (QPushButton, QCheckBox, QRadioButton)):
            return widget.text()
        elif isinstance(widget, QLabel):
            return widget.text()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            return widget.toPlainText()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QGroupBox):
            return widget.title()
        elif isinstance(widget, QTabWidget):
            idx = widget.currentIndex()
            return widget.tabText(idx) if idx >= 0 else None
        return None

    def _get_widget_properties(self, widget: QWidget) -> dict[str, Any]:
        """Extract type-specific properties from a widget."""
        props: dict[str, Any] = {}

        if isinstance(widget, QLineEdit):
            props["placeholderText"] = widget.placeholderText()
            props["readOnly"] = widget.isReadOnly()
            props["maxLength"] = widget.maxLength()
            props["echoMode"] = widget.echoMode().name

        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            props["readOnly"] = widget.isReadOnly()

        elif isinstance(widget, (QCheckBox, QRadioButton)):
            props["checked"] = widget.isChecked()
            props["checkable"] = widget.isCheckable()

        elif isinstance(widget, QPushButton):
            props["checkable"] = widget.isCheckable()
            props["checked"] = widget.isChecked()
            props["flat"] = widget.isFlat()
            props["default"] = widget.isDefault()

        elif isinstance(widget, QComboBox):
            props["currentIndex"] = widget.currentIndex()
            props["count"] = widget.count()
            props["editable"] = widget.isEditable()
            items = [widget.itemText(i) for i in range(min(widget.count(), 100))]
            props["items"] = items

        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            props["value"] = widget.value()
            props["minimum"] = widget.minimum()
            props["maximum"] = widget.maximum()
            props["singleStep"] = widget.singleStep()

        elif isinstance(widget, (QSlider, QScrollBar)):
            props["value"] = widget.value()
            props["minimum"] = widget.minimum()
            props["maximum"] = widget.maximum()
            props["orientation"] = widget.orientation().name

        elif isinstance(widget, QTabWidget):
            props["currentIndex"] = widget.currentIndex()
            props["count"] = widget.count()
            tabs = [widget.tabText(i) for i in range(widget.count())]
            props["tabs"] = tabs

        elif isinstance(widget, QListWidget):
            props["count"] = widget.count()
            props["currentRow"] = widget.currentRow()

        elif isinstance(widget, QTableWidget):
            props["rowCount"] = widget.rowCount()
            props["columnCount"] = widget.columnCount()

        elif isinstance(widget, QTreeWidget):
            props["topLevelItemCount"] = widget.topLevelItemCount()

        elif isinstance(widget, QProgressBar):
            props["value"] = widget.value()
            props["minimum"] = widget.minimum()
            props["maximum"] = widget.maximum()
            props["format"] = widget.format()

        return props
