from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def split_command_line_arguments(arguments: str) -> list[str]:
    raw = (arguments or "").strip()
    if not raw:
        return []
    # Windows: backslashes in paths; POSIX mode would break common cases.
    return shlex.split(raw, posix=sys.platform != "win32")


def validate_program_path(path: str) -> Path:
    p = Path((path or "").strip())
    if not p:
        raise ValueError("program_path is required")
    rp = p.resolve()
    if not rp.is_file():
        raise FileNotFoundError(str(rp))
    if sys.platform != "win32" and not os.access(rp, os.X_OK):
        raise PermissionError(f"not executable: {rp}")
    return rp


async def launch_program(program_path: str, arguments: str = "") -> None:
    exe = validate_program_path(program_path)
    argv = [str(exe), *split_command_line_arguments(arguments)]

    kwargs: dict[str, object] = {
        "stdin": asyncio.subprocess.DEVNULL,
        "stdout": asyncio.subprocess.DEVNULL,
        "stderr": asyncio.subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = int(subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
    else:
        kwargs["start_new_session"] = True

    proc = await asyncio.create_subprocess_exec(*argv, **kwargs)

    async def _reap() -> None:
        rc = await proc.wait()
        if rc != 0:
            logger.info("launch_program finished: %s exit_code=%s", exe, rc)

    asyncio.create_task(_reap())
