"""PyQtAuto Client - Remote control client for PySide6 applications.

This module provides a client for sending automation commands to a
PySide6 application running the PyQtAuto server.

Usage:
    from pyqtauto.client import PyQtAutoClient

    with PyQtAutoClient(port=9876) as client:
        # Get widget tree
        tree = client.get_tree()

        # Click a button
        client.click("@name:my_button")

        # Type text
        client.type("@name:my_input", "Hello World")

        # Take screenshot
        client.screenshot("screenshot.png")
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import socket
from typing import Any
import uuid

from .protocol import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    Command,
    CommandType,
    Response,
)


class PyQtAutoError(Exception):
    """Base exception for PyQtAuto errors."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ConnectionError(PyQtAutoError):
    """Connection error."""

    pass


class CommandError(PyQtAutoError):
    """Command execution error."""

    pass


class PyQtAutoClient:
    """Client for controlling PySide6 applications remotely.

    This client communicates with a PyQtAuto server running inside a
    PySide6 application via JSON over TCP sockets.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = 30.0,
    ):
        """Initialize the client.

        Args:
            host: The server host.
            port: The server port.
            timeout: Socket timeout in seconds.
        """
        self._host = host
        self._port = port
        self._timeout = timeout

    def __enter__(self) -> PyQtAutoClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def _send_command(self, command: Command) -> Response:
        """Send a command and receive the response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((self._host, self._port))

            # Send command
            command_json = command.to_json()
            sock.sendall(command_json.encode("utf-8"))

            # Receive response
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Check for complete JSON
                try:
                    json.loads(data.decode("utf-8"))
                    break
                except json.JSONDecodeError:
                    continue

            sock.close()

            if not data:
                raise ConnectionError("CONNECTION_CLOSED", "Server closed connection")

            return Response.from_json(data)

        except TimeoutError as e:
            raise ConnectionError(
                "TIMEOUT", f"Connection timeout after {self._timeout}s"
            ) from e
        except OSError as e:
            raise ConnectionError("SOCKET_ERROR", str(e)) from e

    def _execute(
        self,
        command_type: str,
        params: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a command and return the result."""
        command = Command(
            id=str(uuid.uuid4()),
            command=command_type,
            params=params or {},
            options=options or {},
        )

        response = self._send_command(command)

        if not response.success:
            error = response.error
            raise CommandError(
                error.code if error else "UNKNOWN",
                error.message if error else "Unknown error",
                error.details if error else {},
            )

        return response.result or {}

    # Introspection methods

    def get_tree(
        self,
        depth: int = -1,
        include_invisible: bool = False,
        include_properties: bool = True,
    ) -> dict[str, Any]:
        """Get the widget tree.

        Args:
            depth: Maximum depth to traverse. -1 for unlimited.
            include_invisible: Include invisible widgets.
            include_properties: Include widget properties.

        Returns:
            The widget tree as a dictionary.
        """
        return self._execute(
            CommandType.GET_TREE.value,
            {
                "depth": depth,
                "include_invisible": include_invisible,
                "include_properties": include_properties,
            },
        )["tree"]

    def find(
        self,
        selector: str,
        max_results: int = 10,
        visible_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Find widgets matching a selector.

        Args:
            selector: The selector string.
            max_results: Maximum number of results.
            visible_only: Only return visible widgets.

        Returns:
            List of matching widget info.
        """
        result = self._execute(
            CommandType.FIND.value,
            {
                "query": selector,
                "max_results": max_results,
                "visible_only": visible_only,
            },
        )
        return result.get("results", [])

    def get_property(self, target: str, property_name: str) -> Any:
        """Get a property value from a widget.

        Args:
            target: The widget selector.
            property_name: The property name.

        Returns:
            The property value.
        """
        return self._execute(
            CommandType.GET_PROPERTY.value,
            {"target": target, "property": property_name},
        )["value"]

    def list_properties(self, target: str) -> dict[str, Any]:
        """List all properties of a widget.

        Args:
            target: The widget selector.

        Returns:
            Dictionary of property names to values.
        """
        return self._execute(
            CommandType.LIST_PROPERTIES.value,
            {"target": target},
        )["properties"]

    # Action methods

    def click(
        self,
        target: str,
        button: str = "left",
        pos: dict[str, int] | None = None,
    ) -> bool:
        """Click a widget.

        Args:
            target: The widget selector.
            button: Mouse button ("left", "right", "middle").
            pos: Optional click position {x, y} relative to widget.

        Returns:
            True if successful.
        """
        params = {"target": target, "button": button}
        if pos:
            params["pos"] = pos
        return self._execute(CommandType.CLICK.value, params)["clicked"]

    def double_click(self, target: str, pos: dict[str, int] | None = None) -> bool:
        """Double-click a widget.

        Args:
            target: The widget selector.
            pos: Optional click position {x, y} relative to widget.

        Returns:
            True if successful.
        """
        params = {"target": target}
        if pos:
            params["pos"] = pos
        return self._execute(CommandType.DOUBLE_CLICK.value, params)["clicked"]

    def right_click(self, target: str, pos: dict[str, int] | None = None) -> bool:
        """Right-click a widget.

        Args:
            target: The widget selector.
            pos: Optional click position {x, y} relative to widget.

        Returns:
            True if successful.
        """
        params = {"target": target}
        if pos:
            params["pos"] = pos
        return self._execute(CommandType.RIGHT_CLICK.value, params)["clicked"]

    def type(
        self,
        target: str,
        text: str,
        clear_first: bool = True,
    ) -> str:
        """Type text into a widget.

        Args:
            target: The widget selector.
            text: The text to type.
            clear_first: Clear existing text first.

        Returns:
            The typed text.
        """
        return self._execute(
            CommandType.TYPE.value,
            {"target": target, "text": text, "clear_first": clear_first},
        )["typed"]

    def key(
        self,
        target: str,
        key: str,
        modifiers: list[str] | None = None,
    ) -> str:
        """Press a key on a widget.

        Args:
            target: The widget selector.
            key: The key name (e.g., "Enter", "Tab", "A").
            modifiers: List of modifiers (e.g., ["ctrl", "shift"]).

        Returns:
            The pressed key.
        """
        return self._execute(
            CommandType.KEY.value,
            {"target": target, "key": key, "modifiers": modifiers or []},
        )["pressed"]

    def key_sequence(self, target: str, sequence: str) -> str:
        """Press a key sequence on a widget.

        Args:
            target: The widget selector.
            sequence: The key sequence (e.g., "Ctrl+S", "Ctrl+Shift+N").

        Returns:
            The pressed sequence.
        """
        return self._execute(
            CommandType.KEY_SEQUENCE.value,
            {"target": target, "sequence": sequence},
        )["sequence"]

    def focus(self, target: str) -> bool:
        """Set focus to a widget.

        Args:
            target: The widget selector.

        Returns:
            True if successful.
        """
        return self._execute(CommandType.FOCUS.value, {"target": target})["focused"]

    def hover(self, target: str, pos: dict[str, int] | None = None) -> bool:
        """Hover over a widget.

        Args:
            target: The widget selector.
            pos: Optional position {x, y} relative to widget.

        Returns:
            True if successful.
        """
        params = {"target": target}
        if pos:
            params["pos"] = pos
        return self._execute(CommandType.HOVER.value, params)["hovered"]

    def scroll(
        self,
        target: str,
        delta_x: int = 0,
        delta_y: int = 0,
        pos: dict[str, int] | None = None,
    ) -> bool:
        """Scroll a widget.

        Args:
            target: The widget selector.
            delta_x: Horizontal scroll amount.
            delta_y: Vertical scroll amount.
            pos: Optional position {x, y} for scroll event.

        Returns:
            True if successful.
        """
        params = {"target": target, "delta_x": delta_x, "delta_y": delta_y}
        if pos:
            params["pos"] = pos
        return self._execute(CommandType.SCROLL.value, params)["scrolled"]

    # State modification methods

    def set_property(self, target: str, property_name: str, value: Any) -> bool:
        """Set a property on a widget.

        Args:
            target: The widget selector.
            property_name: The property name.
            value: The value to set.

        Returns:
            True if successful.
        """
        return self._execute(
            CommandType.SET_PROPERTY.value,
            {"target": target, "property": property_name, "value": value},
        )["set"]

    def set_value(self, target: str, value: Any) -> Any:
        """Set the value of a widget (smart setter).

        This method automatically handles different widget types:
        - QLineEdit/QTextEdit: Sets text
        - QComboBox: Sets index (int) or text (str)
        - QSpinBox/QSlider: Sets numeric value
        - QCheckBox/QRadioButton: Sets checked state

        Args:
            target: The widget selector.
            value: The value to set.

        Returns:
            The set value.
        """
        return self._execute(
            CommandType.SET_VALUE.value,
            {"target": target, "value": value},
        )["value"]

    def clear(self, target: str) -> bool:
        """Clear a widget's content.

        Args:
            target: The widget selector.

        Returns:
            True if successful.
        """
        return self._execute(CommandType.CLEAR.value, {"target": target})["cleared"]

    # Verification methods

    def screenshot(
        self,
        filename: str | Path | None = None,
        target: str | None = None,
        format: str = "png",
    ) -> dict[str, Any]:
        """Take a screenshot.

        Args:
            filename: Optional filename to save the screenshot.
            target: Optional widget selector (defaults to root window).
            format: Image format ("png", "jpg").

        Returns:
            Dictionary with "image" (base64), "width", "height" if no filename,
            or "saved", "width", "height" if filename is provided.
        """
        params = {"format": format}
        if target:
            params["target"] = target
        if filename:
            params["filename"] = str(filename)

        result = self._execute(CommandType.SCREENSHOT.value, params)

        # If we got base64 data and a filename was provided, save it
        if "image" in result and filename:
            image_data = base64.b64decode(result["image"])
            Path(filename).write_bytes(image_data)
            result["saved"] = str(filename)

        return result

    def screenshot_to_file(
        self,
        filename: str | Path,
        target: str | None = None,
        format: str = "png",
    ) -> str:
        """Take a screenshot and save it to a file.

        Args:
            filename: The filename to save the screenshot.
            target: Optional widget selector (defaults to root window).
            format: Image format ("png", "jpg").

        Returns:
            The saved filename.
        """
        result = self.screenshot(filename=filename, target=target, format=format)
        return result.get("saved", str(filename))

    def screenshot_to_bytes(
        self,
        target: str | None = None,
        format: str = "png",
    ) -> bytes:
        """Take a screenshot and return the image data.

        Args:
            target: Optional widget selector (defaults to root window).
            format: Image format ("png", "jpg").

        Returns:
            The image data as bytes.
        """
        result = self.screenshot(target=target, format=format)
        return base64.b64decode(result["image"])

    def assert_property(
        self,
        target: str,
        property_name: str,
        operator: str,
        expected: Any,
    ) -> bool:
        """Assert a property value.

        Args:
            target: The widget selector.
            property_name: The property name.
            operator: Comparison operator ("==", "!=", ">", ">=", "<", "<=",
                "contains").
            expected: The expected value.

        Returns:
            True if assertion passed.
        """
        result = self._execute(
            CommandType.ASSERT.value,
            {
                "target": target,
                "property": property_name,
                "operator": operator,
                "expected": expected,
            },
        )
        return result["passed"]

    def exists(self, target: str) -> bool:
        """Check if a widget exists.

        Args:
            target: The widget selector.

        Returns:
            True if the widget exists.
        """
        return self._execute(CommandType.EXISTS.value, {"target": target})["exists"]

    def is_visible(self, target: str) -> bool:
        """Check if a widget is visible.

        Args:
            target: The widget selector.

        Returns:
            True if the widget exists and is visible.
        """
        result = self._execute(CommandType.IS_VISIBLE.value, {"target": target})
        return result.get("visible", False)

    def is_enabled(self, target: str) -> bool:
        """Check if a widget is enabled.

        Args:
            target: The widget selector.

        Returns:
            True if the widget exists and is enabled.
        """
        result = self._execute(CommandType.IS_ENABLED.value, {"target": target})
        return result.get("enabled", False)

    # Synchronization methods

    def wait(
        self,
        target: str,
        condition: str = "visible",
        timeout_ms: int = 5000,
        poll_interval_ms: int = 50,
    ) -> bool:
        """Wait for a condition to be met.

        Args:
            target: The widget selector.
            condition: The condition to wait for:
                - "exists": Widget exists
                - "not_exists": Widget doesn't exist
                - "visible": Widget is visible
                - "not_visible": Widget is hidden
                - "enabled": Widget is enabled
                - "disabled": Widget is disabled
                - "focused": Widget has focus
                - "property:name=value": Property equals value
            timeout_ms: Maximum wait time in milliseconds.
            poll_interval_ms: Poll interval in milliseconds.

        Returns:
            True if condition was met.
        """
        result = self._execute(
            CommandType.WAIT.value,
            {
                "target": target,
                "condition": condition,
                "timeout_ms": timeout_ms,
                "poll_interval_ms": poll_interval_ms,
            },
        )
        return result.get("condition_met", False)

    def wait_idle(self, timeout_ms: int = 5000) -> bool:
        """Wait for the Qt event queue to be empty.

        Args:
            timeout_ms: Maximum wait time in milliseconds.

        Returns:
            True when idle.
        """
        return self._execute(
            CommandType.WAIT_IDLE.value,
            {"timeout_ms": timeout_ms},
        )["idle"]

    def sleep(self, ms: int) -> int:
        """Sleep for a specified time.

        Note: Prefer using wait() or wait_idle() over sleep() for
        more reliable synchronization.

        Args:
            ms: Time to sleep in milliseconds.

        Returns:
            The time slept in milliseconds.
        """
        return self._execute(CommandType.SLEEP.value, {"ms": ms})["slept_ms"]

    # App control methods

    def close(self, target: str | None = None) -> bool:
        """Close a window.

        Args:
            target: Optional widget selector. Closes root window if not specified.

        Returns:
            True if successful.
        """
        params = {}
        if target:
            params["target"] = target
        return self._execute(CommandType.CLOSE.value, params)["closed"]

    def quit(self) -> bool:
        """Quit the application.

        Returns:
            True if quit signal was sent.
        """
        return self._execute(CommandType.QUIT.value)["quitting"]

    # Convenience methods

    def wait_and_click(
        self,
        target: str,
        timeout_ms: int = 5000,
        button: str = "left",
    ) -> bool:
        """Wait for a widget to be visible and click it.

        Args:
            target: The widget selector.
            timeout_ms: Maximum wait time.
            button: Mouse button.

        Returns:
            True if successful.
        """
        self.wait(target, "visible", timeout_ms)
        return self.click(target, button)

    def type_and_submit(
        self,
        target: str,
        text: str,
        submit_key: str = "Return",
        clear_first: bool = True,
    ) -> None:
        """Type text and press submit key.

        Args:
            target: The widget selector.
            text: The text to type.
            submit_key: The key to press after typing.
            clear_first: Clear existing text first.
        """
        self.type(target, text, clear_first)
        self.key(target, submit_key)

    def select_combo_item(self, target: str, item: str | int) -> Any:
        """Select an item in a combo box.

        Args:
            target: The combo box selector.
            item: The item text or index.

        Returns:
            The selected value.
        """
        return self.set_value(target, item)

    def check(self, target: str, checked: bool = True) -> Any:
        """Check or uncheck a checkbox/radio button.

        Args:
            target: The widget selector.
            checked: Whether to check or uncheck.

        Returns:
            The new state.
        """
        return self.set_value(target, checked)

    def get_text(self, target: str) -> str:
        """Get the text content of a widget.

        Args:
            target: The widget selector.

        Returns:
            The text content.
        """
        return self.get_property(target, "text")
