from __future__ import annotations

import asyncio
import logging
import multiprocessing
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from stream_cheremsha.ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Windows/PyInstaller safety for multiprocessing spawn children.
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()
    asyncio.ensure_future(window.run_startup())

    with loop:
        loop.run_forever()
    # Qt is down; still exit the interpreter if native/CUDA threads outlived the loop.
    sys.exit(0)


if __name__ == "__main__":
    main()
