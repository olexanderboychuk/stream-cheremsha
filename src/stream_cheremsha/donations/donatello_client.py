from __future__ import annotations

from typing import Any

import httpx

DONATELLO_API_BASE = "https://donatello.to/api/v1"


async def fetch_donatello_donates(
    token: str,
    *,
    page: int = 0,
    size: int = 50,
    timeout: float = 45.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """GET /donates with ``X-Token`` — returns (content rows, pagination meta)."""
    url = f"{DONATELLO_API_BASE.rstrip('/')}/donates"
    headers = {"X-Token": token.strip()}
    params: dict[str, int] = {"page": max(0, page), "size": max(1, min(size, 100))}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        msg = "Donatello: response is not a JSON object"
        raise ValueError(msg)
    raw_content = body.get("content")
    rows: list[dict[str, Any]] = raw_content if isinstance(raw_content, list) else []

    def _int(key: str, default: int = 0) -> int:
        v = body.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    meta: dict[str, Any] = {
        "page": _int("page", 0),
        "size": _int("size", params["size"]),
        "pages": max(0, _int("pages", 0)),
        "total": max(0, _int("total", 0)),
        "first": bool(body.get("first", True)),
        "last": bool(body.get("last", True)),
    }
    return rows, meta
