from __future__ import annotations

from typing import Any

import httpx

DONATIK_API_BASE = "https://api.donatik.io"


async def fetch_donations(
    token: str,
    from_date: str,
    to_date: str,
    *,
    page: int = 1,
    per_page: int = 500,
    timeout: float = 45.0,
) -> tuple[list[dict[str, Any]], int]:
    """GET /donations — returns (data rows, total count)."""
    params: dict[str, str] = {
        "token": token.strip(),
        "fromDate": from_date.strip(),
        "toDate": to_date.strip(),
        "page": str(max(1, page)),
        "perPage": str(max(1, min(per_page, 500))),
    }
    url = f"{DONATIK_API_BASE.rstrip('/')}/donations"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        msg = "Donatik: response is not a JSON object"
        raise ValueError(msg)
    raw_data = body.get("data")
    rows: list[dict[str, Any]] = raw_data if isinstance(raw_data, list) else []
    total_raw = body.get("total", 0)
    try:
        total = int(total_raw)
    except (TypeError, ValueError):
        total = 0
    return rows, total
