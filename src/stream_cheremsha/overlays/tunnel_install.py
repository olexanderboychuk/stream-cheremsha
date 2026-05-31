from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg as _winreg

from stream_cheremsha.overlays.tunnel_types import TunnelProvider

logger = logging.getLogger(__name__)

_WINGET_PACKAGES: dict[TunnelProvider, str] = {
    TunnelProvider.NGROK: "Ngrok.Ngrok",
}

_NGROK_CANDIDATE_DIRS = (
    lambda: Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ngrok",
    lambda: Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "ngrok",
    lambda: Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
)


def winget_executable() -> str | None:
    return shutil.which("winget")


def is_winget_available() -> bool:
    return winget_executable() is not None


def winget_package_id(provider: TunnelProvider | str) -> str | None:
    try:
        resolved = TunnelProvider(str(provider))
    except ValueError:
        return None
    return _WINGET_PACKAGES.get(resolved)


def provider_needs_cli(provider: TunnelProvider | str) -> bool:
    try:
        resolved = TunnelProvider(str(provider))
    except ValueError:
        return False
    return resolved == TunnelProvider.NGROK


def refresh_windows_path() -> None:
    if sys.platform != "win32":
        return

    chunks: list[str] = []
    for hive, subkey in (
        (_winreg.HKEY_CURRENT_USER, "Environment"),
        (
            _winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    ):
        try:
            with _winreg.OpenKey(hive, subkey) as key:
                value, _kind = _winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())
    if chunks:
        os.environ["PATH"] = ";".join(chunks)


def _find_exe_in_dirs(name: str, dir_factories: tuple) -> str | None:
    for factory in dir_factories:
        base = factory()
        if not str(base):
            continue
        if not base.is_dir():
            continue
        direct = base / f"{name}.exe"
        if direct.is_file():
            return str(direct)
        try:
            for hit in base.rglob(f"{name}.exe"):
                if hit.is_file():
                    return str(hit)
        except OSError:
            continue
    return None


def find_ngrok_executable() -> str | None:
    hit = shutil.which("ngrok")
    if hit:
        return hit
    return _find_exe_in_dirs("ngrok", _NGROK_CANDIDATE_DIRS)


def is_tunnel_cli_installed(provider: TunnelProvider | str) -> bool:
    try:
        resolved = TunnelProvider(str(provider))
    except ValueError:
        return True
    if resolved == TunnelProvider.NGROK:
        return find_ngrok_executable() is not None
    return True


def install_prompt_labels(provider: TunnelProvider | str, *, locale: str) -> tuple[str, str]:
    uk = locale != "en"
    try:
        resolved = TunnelProvider(str(provider))
    except ValueError:
        return ("Install", "Install tunnel tool?")

    if resolved == TunnelProvider.NGROK:
        if uk:
            return (
                "Встановити ngrok?",
                "ngrok не знайдено в PATH. Встановити ngrok через winget?",
            )
        return (
            "Install ngrok?",
            "ngrok was not found in PATH. Install ngrok via winget?",
        )
    return ("Install", "Install tunnel tool?")


def missing_cli_status_message(provider: TunnelProvider | str, *, locale: str) -> str:
    uk = locale != "en"
    try:
        resolved = TunnelProvider(str(provider))
    except ValueError:
        return "Tool not installed" if not uk else "Інструмент не встановлено"
    if resolved == TunnelProvider.NGROK:
        return (
            "ngrok не встановлено — увімкніть тунель знову для встановлення через winget"
            if uk
            else "ngrok is not installed — toggle the tunnel again to install via winget"
        )
    return "Tool not installed" if not uk else "Інструмент не встановлено"


async def install_tunnel_tool_via_winget(provider: TunnelProvider | str) -> tuple[bool, str]:
    pkg = winget_package_id(provider)
    if not pkg:
        return False, f"Unsupported provider: {provider}"

    winget = winget_executable()
    if not winget:
        return False, "winget is not available on this system"

    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = await asyncio.create_subprocess_exec(
        winget,
        "install",
        "--id",
        pkg,
        "-e",
        "--accept-package-agreements",
        "--accept-source-agreements",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=create_no_window,
    )
    out_bytes = b""
    assert proc.stdout is not None
    while True:
        chunk = await proc.stdout.read(65536)
        if not chunk:
            break
        out_bytes += chunk
        logger.debug("winget: %s", chunk.decode("utf-8", errors="replace").rstrip())

    code = await proc.wait()
    output = out_bytes.decode("utf-8", errors="replace").strip()
    refresh_windows_path()

    if code != 0:
        detail = output.splitlines()[-1] if output else f"exit code {code}"
        return False, detail

    if not is_tunnel_cli_installed(provider):
        return False, "Installation finished but the executable is still not in PATH"

    return True, ""
