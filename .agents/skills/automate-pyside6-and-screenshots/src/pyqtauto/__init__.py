"""PyQtAuto - Playwright-like automation for PySide6 applications.

This library provides tools for automating and testing PySide6 applications,
similar to how Playwright works for web browsers.

Server (for the application being tested):
    from pyqtauto.server import start_server

    # Auto-start based on PYQTAUTO_ENABLED env var
    start_server()

    # Or force start
    start_server(force=True)

Client (for the test/automation script):
    from pyqtauto import PyQtAutoClient

    with PyQtAutoClient() as client:
        client.click("@name:my_button")
        client.type("@name:my_input", "Hello")
        client.screenshot("screenshot.png")
"""

from .client import CommandError, ConnectionError, PyQtAutoClient, PyQtAutoError
from .protocol import DEFAULT_HOST, DEFAULT_PORT, ENV_ENABLED, ENV_PORT

__version__ = "0.1.0"

__all__ = [
    "PyQtAutoClient",
    "PyQtAutoError",
    "CommandError",
    "ConnectionError",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "ENV_ENABLED",
    "ENV_PORT",
    "__version__",
]
