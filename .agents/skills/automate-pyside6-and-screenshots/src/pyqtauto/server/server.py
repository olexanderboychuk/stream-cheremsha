"""PyQtAuto Server - Main server implementation.

This module provides the automation server that can be embedded in any
PySide6 application to enable remote control and testing.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import socket
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from ..protocol import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENV_ENABLED,
    ENV_PORT,
    Command,
    ErrorCode,
    Response,
)
from .executor import CommandExecutor


class AutomationServer(QObject):
    """Automation server for PySide6 applications.

    The server runs a socket listener in a background thread and uses
    Qt signals to dispatch commands to the main UI thread for execution.

    Usage:
        server = AutomationServer(port=9876)
        server.start()

        # Or with a specific root widget
        server = AutomationServer(root=my_widget)
        server.start()
    """

    # Signal emitted when a command is received (with client socket for response)
    _command_received = Signal(str, object)

    def __init__(
        self,
        root: QWidget | None = None,
        host: str = DEFAULT_HOST,
        port: int | None = None,
        parent: QObject | None = None,
    ):
        """Initialize the automation server.

        Args:
            root: The root widget for automation. If None, uses active window.
            host: The host to bind to.
            port: The port to listen on. If None, uses env var or default.
            parent: The parent QObject.
        """
        super().__init__(parent)

        self._host = host
        self._port = port or int(os.environ.get(ENV_PORT, DEFAULT_PORT))
        self._executor = CommandExecutor(root)
        self._server_socket: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None

        # Connect signal to handler
        self._command_received.connect(self._handle_command)

    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port

    @property
    def host(self) -> str:
        """Get the server host."""
        return self._host

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running

    def set_root(self, root: QWidget | None):
        """Set the root widget for automation."""
        self._executor.set_root(root)

    def start(self):
        """Start the automation server."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the automation server."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _server_loop(self):
        """Main server loop running in background thread."""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)

            print(f"PyQtAuto server listening on {self._host}:{self._port}")

            while self._running:
                try:
                    client_socket, addr = self._server_socket.accept()
                    # Handle client in a separate thread
                    threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,),
                        daemon=True,
                    ).start()
                except TimeoutError:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"Server error: {e}")
                    break

        except Exception as e:
            print(f"Failed to start server: {e}")
        finally:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass

    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection."""
        try:
            client_socket.settimeout(30.0)

            # Receive data
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Check for complete JSON
                try:
                    json.loads(data.decode("utf-8"))
                    break
                except json.JSONDecodeError:
                    continue

            if not data:
                return

            # Emit signal to process command in main thread
            # We use a blocking mechanism to wait for the response
            response_holder = {"response": None, "done": threading.Event()}

            def on_response(response_json: str):
                response_holder["response"] = response_json
                response_holder["done"].set()

            # Store callback for this request
            self._response_callback = on_response
            self._command_received.emit(data.decode("utf-8"), on_response)

            # Wait for response (with timeout)
            if response_holder["done"].wait(timeout=60.0):
                response_json = response_holder["response"]
                if response_json:
                    client_socket.sendall(response_json.encode("utf-8"))
            else:
                # Timeout
                error_response = Response.error_response(
                    "",
                    ErrorCode.TIMEOUT,
                    "Command execution timeout",
                )
                client_socket.sendall(error_response.to_json().encode("utf-8"))

        except Exception as e:
            try:
                error_response = Response.error_response(
                    "",
                    ErrorCode.INTERNAL_ERROR,
                    str(e),
                )
                client_socket.sendall(error_response.to_json().encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass

    def _handle_command(self, command_json: str, callback: Callable[[str], None]):
        """Handle a command in the main thread."""
        try:
            command = Command.from_json(command_json)
            response = self._executor.execute(command)
            callback(response.to_json())
        except Exception as e:
            error_response = Response.error_response(
                "",
                ErrorCode.INTERNAL_ERROR,
                str(e),
            )
            callback(error_response.to_json())


# Global server instance
_server: AutomationServer | None = None


def start_server(
    root: QWidget | None = None,
    host: str = DEFAULT_HOST,
    port: int | None = None,
    force: bool = False,
) -> AutomationServer | None:
    """Start the automation server if enabled.

    The server is started if:
    - force=True, OR
    - The PYQTAUTO_ENABLED environment variable is set to "1", "true", or "yes"

    Args:
        root: The root widget for automation.
        host: The host to bind to.
        port: The port to listen on.
        force: Force start regardless of environment variable.

    Returns:
        The server instance, or None if not started.
    """
    global _server

    if _server is not None and _server.is_running:
        return _server

    # Check if enabled
    enabled = force or os.environ.get(ENV_ENABLED, "").lower() in ("1", "true", "yes")
    if not enabled:
        return None

    _server = AutomationServer(root=root, host=host, port=port)
    _server.start()

    return _server


def get_server() -> AutomationServer | None:
    """Get the global server instance."""
    return _server


def stop_server():
    """Stop the global server instance."""
    global _server
    if _server is not None:
        _server.stop()
        _server = None
