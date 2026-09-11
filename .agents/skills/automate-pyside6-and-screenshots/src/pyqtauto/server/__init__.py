"""PyQtAuto Server - Automation server for PySide6 applications.

This module provides a server that can be embedded in any PySide6 application
to enable remote automation and testing.

Usage:
    from pyqtauto.server import start_server, AutomationServer

    # Auto-start based on environment variable
    start_server()

    # Or manual control
    server = AutomationServer(port=9876)
    server.start()
"""

from .executor import CommandExecutor
from .finder import ElementFinder
from .introspector import UIIntrospector
from .server import AutomationServer, start_server

__all__ = [
    "AutomationServer",
    "start_server",
    "UIIntrospector",
    "CommandExecutor",
    "ElementFinder",
]
