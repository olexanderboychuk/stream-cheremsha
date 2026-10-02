from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

UPDATER_FILENAME = "CheremshaUpdater.exe"
# Standalone Nuitka layout ships the updater as a folder (no self-extracting
# one-file stub, which trips Defender ML heuristics). Legacy installs may still
# carry the single-file build next to the main exe.
UPDATER_DIST_DIRNAMES = ("CheremshaUpdater.dist", "updater.dist")
_TEMP_ROOT_NAME = "CheremshaUpdater"
_STALE_SECONDS = 7 * 24 * 60 * 60


def _cleanup_stale_updaters(root: Path, *, now: float | None = None) -> None:
    if not root.is_dir():
        return
    cutoff = (time.time() if now is None else now) - _STALE_SECONDS
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child)
        except OSError:
            logger.debug("Unable to remove stale updater directory: %s", child)


def resolve_packaged_updater(app_dir: Path) -> tuple[Path, str] | None:
    """Locate the packaged updater next to the installed app.

    Returns ``(exe_path, kind)`` where kind is ``"file"`` (legacy one-file
    binary) or ``"dist"`` (standalone folder). ``None`` when not packaged.
    """
    single = app_dir / UPDATER_FILENAME
    if single.is_file():
        return single, "file"
    for dirname in UPDATER_DIST_DIRNAMES:
        candidate = app_dir / dirname / UPDATER_FILENAME
        if candidate.is_file():
            return candidate, "dist"
    return None


def build_updater_args(
    *,
    url: str,
    sha256: str,
    version: str,
    install_dir: Path,
    app: Path,
    parent_pid: int,
    locale: str,
    require_signature: bool = False,
    expected_publisher: str = "",
    work_dir: Path | None = None,
    ready_file: Path | None = None,
) -> list[str]:
    args = [
        "--url",
        url,
        "--sha256",
        sha256,
        "--version",
        version,
        "--install-dir",
        str(install_dir),
        "--app",
        str(app),
        "--parent-pid",
        str(parent_pid),
        "--locale",
        locale,
    ]
    if require_signature:
        args.extend(["--require-signature", "--expected-publisher", expected_publisher])
    if work_dir is not None:
        args.extend(["--work-dir", str(work_dir)])
    if ready_file is not None:
        args.extend(["--ready-file", str(ready_file)])
    return args


def start_updater(
    *,
    url: str,
    sha256: str,
    version: str,
    install_dir: Path,
    app: Path,
    locale: str,
    require_signature: bool = False,
    expected_publisher: str = "",
) -> subprocess.Popen[bytes]:
    """Start an independent updater, copying the production binary outside the install dir."""
    temp_root = Path(tempfile.gettempdir()) / _TEMP_ROOT_NAME
    temp_root.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_updaters(temp_root)

    run_dir = temp_root / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    ready_file = run_dir / "updater.ready"
    args = build_updater_args(
        url=url,
        sha256=sha256,
        version=version,
        install_dir=install_dir,
        app=app,
        parent_pid=os.getpid(),
        locale=locale,
        require_signature=require_signature,
        expected_publisher=expected_publisher,
        work_dir=run_dir,
        ready_file=ready_file,
    )

    packaged = resolve_packaged_updater(app.parent)
    staged_from_install_dir = packaged is not None
    if packaged is not None:
        source, kind = packaged
        if kind == "dist":
            staged_dist = run_dir / source.parent.name
            shutil.copytree(source.parent, staged_dist)
            executable = staged_dist / UPDATER_FILENAME
        else:
            executable = run_dir / UPDATER_FILENAME
            shutil.copy2(source, executable)
        command = [str(executable), *args]
        cwd = run_dir
    elif app.name.lower() == "cheremsha.exe":
        shutil.rmtree(run_dir, ignore_errors=True)
        raise FileNotFoundError(f"Packaged updater not found under: {app.parent}")
    else:
        # Development-only path; production builds always package the updater.
        command = [sys.executable, "-m", "stream_cheremsha.updates.updater", *args]
        cwd = run_dir

    try:
        if sys.platform.startswith("win"):
            detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    close_fds=True,
                    creationflags=detached | subprocess.CREATE_BREAKAWAY_FROM_JOB,
                )
            except OSError:
                # Some parent jobs disallow breakaway. A detached GUI child still survives a
                # normal Cheremsha shutdown, so retry without that optional protection.
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    close_fds=True,
                    creationflags=detached,
                )
        else:
            process = subprocess.Popen(command, cwd=str(cwd), close_fds=True)
    except (OSError, ValueError):
        if staged_from_install_dir:
            shutil.rmtree(cwd, ignore_errors=True)
        raise
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if ready_file.is_file():
            logger.info("Updater started: pid=%s target_version=%s", process.pid, version)
            return process
        if process.poll() is not None:
            break
        time.sleep(0.05)

    if process.poll() is None:
        process.terminate()
    shutil.rmtree(run_dir, ignore_errors=True)
    raise RuntimeError("Updater did not become ready")
