"""Element finder for PyQtAuto.

This module provides functionality to find widgets by various selectors
such as object name, class name, text content, or hierarchical paths.
"""

from __future__ import annotations

from collections.abc import Callable
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from ..protocol import (
    SELECTOR_BY_ACCESSIBLE,
    SELECTOR_BY_CLASS,
    SELECTOR_BY_NAME,
    SELECTOR_BY_TEXT,
)


class ElementFinder:
    """Finds widgets by various selectors."""

    def __init__(self, root: QWidget | None = None):
        """Initialize the finder.

        Args:
            root: The root widget to search from. If None, searches all windows.
        """
        self._root = root
        self._cache: dict[str, QWidget | None] = {}

    def get_root(self) -> QWidget | None:
        """Get the root widget for searching."""
        if self._root is not None:
            return self._root

        app = QApplication.instance()
        if app is None:
            return None

        active = app.activeWindow()
        if active is not None:
            return active

        top_level = app.topLevelWidgets()
        for widget in top_level:
            if widget.isVisible():
                return widget

        return top_level[0] if top_level else None

    def set_root(self, root: QWidget | None):
        """Set the root widget for searching."""
        self._root = root
        self.clear_cache()

    def clear_cache(self):
        """Clear the widget cache."""
        self._cache.clear()

    def find(self, selector: str, visible_only: bool = True) -> QWidget | None:
        """Find a widget by selector.

        Selector types:
            - @name:objectName - Find by objectName
            - @class:ClassName - Find by class name
            - @text:text - Find by text content
            - @accessible:name - Find by accessible name
            - path/to/widget - Find by hierarchical path

        Args:
            selector: The selector string.
            visible_only: Only return visible widgets.

        Returns:
            The found widget, or None if not found.
        """
        cache_key = f"{selector}:{visible_only}"
        if cache_key in self._cache:
            widget = self._cache[cache_key]
            # Validate cached widget still exists and matches criteria
            if widget is not None and widget.isVisible() if visible_only else True:
                return widget
            # Cache miss, remove stale entry
            del self._cache[cache_key]

        widget = self._find_impl(selector, visible_only)
        self._cache[cache_key] = widget
        return widget

    def find_all(
        self, selector: str, visible_only: bool = True, max_results: int = 100
    ) -> list[QWidget]:
        """Find all widgets matching the selector.

        Args:
            selector: The selector string.
            visible_only: Only return visible widgets.
            max_results: Maximum number of results.

        Returns:
            List of matching widgets.
        """
        return self._find_all_impl(selector, visible_only, max_results)

    def _find_impl(self, selector: str, visible_only: bool) -> QWidget | None:
        """Internal implementation of find."""
        root = self.get_root()
        if root is None:
            return None

        # Parse selector type
        if selector.startswith(SELECTOR_BY_NAME):
            name = selector[len(SELECTOR_BY_NAME) :]
            return self._find_by_name(root, name, visible_only)

        elif selector.startswith(SELECTOR_BY_CLASS):
            class_name = selector[len(SELECTOR_BY_CLASS) :]
            return self._find_by_class(root, class_name, visible_only)

        elif selector.startswith(SELECTOR_BY_TEXT):
            text = selector[len(SELECTOR_BY_TEXT) :]
            return self._find_by_text(root, text, visible_only)

        elif selector.startswith(SELECTOR_BY_ACCESSIBLE):
            name = selector[len(SELECTOR_BY_ACCESSIBLE) :]
            return self._find_by_accessible(root, name, visible_only)

        else:
            # Assume hierarchical path
            return self._find_by_path(root, selector, visible_only)

    def _find_all_impl(
        self, selector: str, visible_only: bool, max_results: int
    ) -> list[QWidget]:
        """Internal implementation of find_all."""
        root = self.get_root()
        if root is None:
            return []

        if selector.startswith(SELECTOR_BY_NAME):
            name = selector[len(SELECTOR_BY_NAME) :]
            return self._find_all_matching(
                root, lambda w: w.objectName() == name, visible_only, max_results
            )

        elif selector.startswith(SELECTOR_BY_CLASS):
            class_name = selector[len(SELECTOR_BY_CLASS) :]
            return self._find_all_matching(
                root,
                lambda w: w.__class__.__name__ == class_name,
                visible_only,
                max_results,
            )

        elif selector.startswith(SELECTOR_BY_TEXT):
            text = selector[len(SELECTOR_BY_TEXT) :]
            return self._find_all_matching(
                root,
                lambda w: self._widget_has_text(w, text),
                visible_only,
                max_results,
            )

        elif selector.startswith(SELECTOR_BY_ACCESSIBLE):
            name = selector[len(SELECTOR_BY_ACCESSIBLE) :]
            return self._find_all_matching(
                root, lambda w: w.accessibleName() == name, visible_only, max_results
            )

        return []

    def _find_by_name(
        self, root: QWidget, name: str, visible_only: bool
    ) -> QWidget | None:
        """Find widget by objectName."""
        # First check root itself
        if root.objectName() == name:
            if not visible_only or root.isVisible():
                return root

        # Then search children
        widget = root.findChild(QWidget, name)
        if widget is not None:
            if not visible_only or widget.isVisible():
                return widget

        # Search all top-level windows if not found
        app = QApplication.instance()
        if app and self._root is None:
            for window in app.topLevelWidgets():
                if window == root:
                    continue
                if window.objectName() == name:
                    if not visible_only or window.isVisible():
                        return window
                widget = window.findChild(QWidget, name)
                if widget is not None:
                    if not visible_only or widget.isVisible():
                        return widget

        return None

    def _find_by_class(
        self, root: QWidget, class_name: str, visible_only: bool
    ) -> QWidget | None:
        """Find widget by class name."""
        return self._find_first_matching(
            root, lambda w: w.__class__.__name__ == class_name, visible_only
        )

    def _find_by_text(
        self, root: QWidget, text: str, visible_only: bool
    ) -> QWidget | None:
        """Find widget by text content."""
        return self._find_first_matching(
            root, lambda w: self._widget_has_text(w, text), visible_only
        )

    def _find_by_accessible(
        self, root: QWidget, name: str, visible_only: bool
    ) -> QWidget | None:
        """Find widget by accessible name."""
        return self._find_first_matching(
            root, lambda w: w.accessibleName() == name, visible_only
        )

    def _find_by_path(
        self, root: QWidget, path: str, visible_only: bool
    ) -> QWidget | None:
        """Find widget by hierarchical path.

        Path format: parent/child/grandchild or parent/child[index]
        Special: * matches any intermediate widget
        """
        parts = path.split("/")
        if not parts:
            return None

        current: QWidget | None = root

        # Check if first part matches root
        first = parts[0]
        if first and first != "*":
            name, index = self._parse_path_part(first)
            if not self._matches_path_part(current, name):
                # First part doesn't match root, search from root
                current = self._find_child_by_path_part(root, first, visible_only)
                if current is None:
                    return None
            parts = parts[1:]

        # Follow path
        for part in parts:
            if not part:
                continue
            if current is None:
                return None

            if part == "*":
                # Wildcard - skip to next part
                continue

            current = self._find_child_by_path_part(current, part, visible_only)

        if visible_only and current is not None and not current.isVisible():
            return None

        return current

    def _parse_path_part(self, part: str) -> tuple[str, int | None]:
        """Parse a path part like 'name[2]' into (name, index)."""
        match = re.match(r"^(.+)\[(\d+)\]$", part)
        if match:
            return match.group(1), int(match.group(2))
        return part, None

    def _matches_path_part(self, widget: QWidget, name: str) -> bool:
        """Check if widget matches path part (name or class)."""
        return widget.objectName() == name or widget.__class__.__name__ == name

    def _find_child_by_path_part(
        self, parent: QWidget, part: str, visible_only: bool
    ) -> QWidget | None:
        """Find a child widget by path part."""
        name, index = self._parse_path_part(part)

        matches: list[QWidget] = []
        for child in parent.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        ):
            if self._matches_path_part(child, name):
                if not visible_only or child.isVisible():
                    matches.append(child)

        if not matches:
            return None

        if index is not None:
            return matches[index] if index < len(matches) else None

        return matches[0]

    def _find_first_matching(
        self,
        root: QWidget,
        predicate: Callable[[QWidget], bool],
        visible_only: bool,
    ) -> QWidget | None:
        """Find first widget matching predicate using DFS."""
        if visible_only and not root.isVisible():
            return None

        if predicate(root):
            return root

        for child in root.findChildren(QWidget):
            if visible_only and not child.isVisible():
                continue
            if predicate(child):
                return child

        return None

    def _find_all_matching(
        self,
        root: QWidget,
        predicate: Callable[[QWidget], bool],
        visible_only: bool,
        max_results: int,
    ) -> list[QWidget]:
        """Find all widgets matching predicate using DFS."""
        results: list[QWidget] = []

        if visible_only and not root.isVisible():
            return results

        if predicate(root):
            results.append(root)

        for child in root.findChildren(QWidget):
            if len(results) >= max_results:
                break
            if visible_only and not child.isVisible():
                continue
            if predicate(child):
                results.append(child)

        return results

    def _widget_has_text(self, widget: QWidget, text: str) -> bool:
        """Check if widget contains the specified text."""
        # Try various text methods
        if hasattr(widget, "text"):
            try:
                if widget.text() == text:
                    return True
            except Exception:
                pass

        if hasattr(widget, "toPlainText"):
            try:
                if widget.toPlainText() == text:
                    return True
            except Exception:
                pass

        if hasattr(widget, "currentText"):
            try:
                if widget.currentText() == text:
                    return True
            except Exception:
                pass

        if hasattr(widget, "title"):
            try:
                if widget.title() == text:
                    return True
            except Exception:
                pass

        return False
