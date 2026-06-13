from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_TUNNEL_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HOSTNAME_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
    re.IGNORECASE,
)


def normalize_cloudflare_hostname(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    return host


def validate_cloudflare_hostname(hostname: str) -> str:
    host = normalize_cloudflare_hostname(hostname)
    if not host:
        raise ValueError("Cloudflare hostname is empty")
    if not _HOSTNAME_RE.match(host):
        raise ValueError("Cloudflare hostname must look like widgets.example.com")
    return host


def normalize_tunnel_id(value: str) -> str:
    return str(value or "").strip().lower()


def validate_tunnel_id(tunnel_id: str) -> str:
    tid = normalize_tunnel_id(tunnel_id)
    if not tid:
        raise ValueError("Cloudflare tunnel ID is empty")
    if not _TUNNEL_ID_RE.match(tid):
        raise ValueError("Cloudflare tunnel ID must be a UUID")
    return tid


def validate_credentials_file(path: str) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise ValueError("Cloudflare credentials file path is empty")
    creds = Path(raw).expanduser()
    if not creds.is_file():
        raise ValueError(f"Cloudflare credentials file not found: {creds}")
    try:
        payload = json.loads(creds.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Cloudflare credentials file is not valid JSON: {creds}") from e
    if not isinstance(payload, dict):
        raise ValueError("Cloudflare credentials file must contain a JSON object")
    account_tag = str(payload.get("AccountTag") or payload.get("account_tag") or "").strip()
    tunnel_secret = str(payload.get("TunnelSecret") or payload.get("tunnel_secret") or "").strip()
    tunnel_id = str(payload.get("TunnelID") or payload.get("tunnel_id") or "").strip()
    if not account_tag or not tunnel_secret or not tunnel_id:
        raise ValueError(
            "Cloudflare credentials file is missing AccountTag, TunnelSecret, or TunnelID"
        )
    return creds.resolve()


def public_url_for_hostname(hostname: str) -> str:
    return f"https://{validate_cloudflare_hostname(hostname)}"


def write_tunnel_config(
    *,
    tunnel_id: str,
    credentials_file: Path,
    hostname: str,
    local_port: int,
) -> Path:
    tid = validate_tunnel_id(tunnel_id)
    host = validate_cloudflare_hostname(hostname)
    creds = credentials_file
    if not creds.is_file():
        raise ValueError(f"Cloudflare credentials file not found: {creds}")

    config_dir = Path(tempfile.gettempdir()) / "stream-cheremsha" / "cloudflared"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{tid}.yml"
    creds_posix = creds.as_posix()
    body = (
        f"tunnel: {tid}\n"
        f"credentials-file: {creds_posix}\n"
        "ingress:\n"
        f"  - hostname: {host}\n"
        f"    service: http://127.0.0.1:{int(local_port)}\n"
        "  - service: http_status:404\n"
    )
    config_path.write_text(body, encoding="utf-8")
    logger.debug("Wrote cloudflared config: %s", config_path)
    return config_path


def start_cloudflared_process(
    *,
    executable: str,
    config_path: Path | None = None,
    token: str = "",
) -> subprocess.Popen[str]:
    token_value = str(token or "").strip()
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if token_value:
        cmd = [
            executable,
            "tunnel",
            "--no-autoupdate",
            "run",
            "--token",
            token_value,
        ]
    else:
        if config_path is None:
            raise ValueError("Cloudflare config path is required without a tunnel token")
        cmd = [
            executable,
            "tunnel",
            "--no-autoupdate",
            "--config",
            str(config_path),
            "run",
        ]
    logger.info("Starting cloudflared: %s", " ".join(cmd[:4]))
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=create_no_window,
    )


def stop_cloudflared_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def cloudflared_exit_detail(proc: subprocess.Popen[str]) -> str:
    code = proc.returncode
    if code is None:
        return "cloudflared stopped unexpectedly"
    output = ""
    if proc.stdout is not None:
        try:
            output = proc.stdout.read() or ""
        except OSError:
            output = ""
    tail = output.strip().splitlines()[-3:]
    detail = " ".join(line.strip() for line in tail if line.strip())
    if detail:
        return f"cloudflared exited with code {code}: {detail}"
    return f"cloudflared exited with code {code}"
