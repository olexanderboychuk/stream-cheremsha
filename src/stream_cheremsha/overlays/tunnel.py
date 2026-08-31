from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pyngrok import ngrok

from stream_cheremsha.overlays.cloudflare_tunnel import (
    cloudflared_exit_detail,
    public_url_for_hostname,
    start_cloudflared_process,
    stop_cloudflared_process,
    validate_cloudflare_hostname,
)
from stream_cheremsha.overlays.ngrok_domain import (
    fetch_ngrok_dev_domain,
    normalize_ngrok_domain,
    validate_ngrok_domain,
)
from stream_cheremsha.overlays.tunnel_types import TunnelProvider

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TunnelState:
    provider: TunnelProvider = TunnelProvider.NONE
    public_url: str = ""
    status: str = "idle"  # idle | starting | active | error
    message: str = ""


def _local_port(local_url: str) -> int:
    parsed = urlparse(str(local_url or "").strip())
    if parsed.port is not None:
        return int(parsed.port)
    if parsed.scheme == "https":
        return 443
    return 80


def _resolve_ngrok_domain(*, authtoken: str, configured_domain: str) -> str:
    configured = normalize_ngrok_domain(configured_domain)
    if configured:
        return validate_ngrok_domain(configured)
    discovered = fetch_ngrok_dev_domain(authtoken)
    if discovered:
        return validate_ngrok_domain(discovered)
    raise RuntimeError(
        "ngrok domain is required for a stable public URL. "
        "Open https://dashboard.ngrok.com/domains, copy your *.ngrok-free.dev domain, "
        "and paste it in Widgets → Public URL settings."
    )


def _ngrok_connect(port: int, authtoken: str, domain: str) -> tuple[Any, str]:
    token = str(authtoken or "").strip()
    if not token:
        raise RuntimeError(
            "ngrok authtoken is required. Get one at https://dashboard.ngrok.com/get-started/your-authtoken"
        )
    ngrok.set_auth_token(token)
    hostname = _resolve_ngrok_domain(authtoken=token, configured_domain=domain)
    tunnel = ngrok.connect(port, "http", bind_tls=True, domain=hostname)
    url = str(getattr(tunnel, "public_url", "") or "").rstrip("/")
    if not url:
        raise RuntimeError("ngrok did not return a public URL")
    host = (urlparse(url).hostname or "").lower()
    if host and host != hostname:
        logger.warning("ngrok returned %s but requested domain %s", host, hostname)
    return tunnel, url


def _ngrok_disconnect(tunnel: Any | None) -> None:
    if tunnel is not None:
        public_url = str(getattr(tunnel, "public_url", "") or "").strip()
        if public_url:
            ngrok.disconnect(public_url)
    ngrok.kill()


class OverlayTunnel:
    def __init__(self) -> None:
        self._state = TunnelState()
        self._ngrok_tunnel: Any | None = None
        self._ngrok_domain_used = ""
        self._cloudflared_proc: Any | None = None
        self._cloudflared_config_path: Path | None = None

    def state(self) -> TunnelState:
        return self._state

    def ngrok_domain_used(self) -> str:
        return self._ngrok_domain_used

    async def start(
        self,
        *,
        provider: TunnelProvider | str,
        local_url: str,
        ngrok_authtoken: str = "",
        ngrok_domain: str = "",
        custom_url: str = "",
        cloudflare_hostname: str = "",
        cloudflare_tunnel_token: str = "",
        cloudflared_executable: str = "",
    ) -> str:
        await self.stop()
        try:
            resolved = TunnelProvider(str(provider))
        except ValueError as e:
            raise ValueError(f"Unknown tunnel provider: {provider}") from e

        if resolved == TunnelProvider.NONE:
            self._state = TunnelState(provider=TunnelProvider.NONE)
            return ""

        if resolved == TunnelProvider.CUSTOM:
            url = str(custom_url or "").strip().rstrip("/")
            if not url:
                self._state = TunnelState(
                    provider=resolved,
                    status="error",
                    message="Custom URL is empty",
                )
                raise ValueError("Custom tunnel URL is empty")
            self._state = TunnelState(provider=resolved, public_url=url, status="active")
            return url

        self._state = TunnelState(provider=resolved, status="starting")

        try:
            if resolved == TunnelProvider.NGROK:
                public_url = await self._start_ngrok(local_url, ngrok_authtoken, ngrok_domain)
            elif resolved == TunnelProvider.CLOUDFLARE:
                public_url = await self._start_cloudflare(
                    local_url,
                    hostname=cloudflare_hostname,
                    tunnel_token=cloudflare_tunnel_token,
                    cloudflared_executable=cloudflared_executable,
                )
            else:
                raise ValueError(f"Unsupported tunnel provider: {resolved}")
        except (OSError, RuntimeError, ValueError) as e:
            await self._cleanup_resources()
            self._state = TunnelState(provider=resolved, status="error", message=str(e))
            raise

        self._state = TunnelState(provider=resolved, public_url=public_url, status="active")
        logger.info("Overlay tunnel active (%s): %s", resolved.value, public_url)
        return public_url

    async def stop(self) -> None:
        await self._cleanup_resources()
        self._state = TunnelState()
        self._ngrok_domain_used = ""

    async def _cleanup_resources(self) -> None:
        ngrok_tunnel = self._ngrok_tunnel
        self._ngrok_tunnel = None
        if ngrok_tunnel is not None:
            try:
                await asyncio.to_thread(_ngrok_disconnect, ngrok_tunnel)
            except (OSError, RuntimeError) as e:
                logger.warning("ngrok shutdown failed: %s", e)

        cloudflared_proc = self._cloudflared_proc
        self._cloudflared_proc = None
        self._cloudflared_config_path = None
        if cloudflared_proc is not None:
            try:
                await asyncio.to_thread(stop_cloudflared_process, cloudflared_proc)
            except OSError as e:
                logger.warning("cloudflared shutdown failed: %s", e)

    async def _start_ngrok(self, local_url: str, authtoken: str, domain: str) -> str:
        port = _local_port(local_url)

        def _connect() -> tuple[Any, str, str]:
            tunnel, public_url = _ngrok_connect(port, authtoken, domain)
            host = normalize_ngrok_domain(str(getattr(tunnel, "public_url", "") or public_url))
            if not host:
                host = normalize_ngrok_domain(public_url)
            return tunnel, public_url, host

        tunnel, public_url, domain_used = await asyncio.to_thread(_connect)
        self._ngrok_tunnel = tunnel
        self._ngrok_domain_used = domain_used
        return public_url

    async def _start_cloudflare(
        self,
        local_url: str,
        *,
        hostname: str,
        tunnel_token: str,
        cloudflared_executable: str,
    ) -> str:
        host = validate_cloudflare_hostname(hostname)
        public_url = public_url_for_hostname(host)
        logger.info(
            "Cloudflare tunnel token mode for %s (dashboard ingress should target %s)",
            host,
            local_url,
        )
        exe = str(cloudflared_executable or "").strip()
        if not exe:
            raise RuntimeError("Cloudflare tunnel support is disabled")

        token = str(tunnel_token or "").strip()
        if not token:
            raise RuntimeError(
                "Cloudflare tunnel token is required. "
                "Copy it from Zero Trust → Networks → Tunnels → your tunnel → Install connector."
            )

        def _connect() -> tuple[Any, Path | None]:
            proc = start_cloudflared_process(executable=exe, token=token)
            if proc.poll() is not None:
                raise RuntimeError(cloudflared_exit_detail(proc))
            return proc, None

        proc, config_path = await asyncio.to_thread(_connect)
        self._cloudflared_proc = proc
        self._cloudflared_config_path = config_path
        return public_url
