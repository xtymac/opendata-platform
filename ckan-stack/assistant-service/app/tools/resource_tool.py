"""CKAN resource metadata helper."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict

import httpx

logger = None  # configured externally

CKAN_BASE_URL = os.getenv("CKAN_BASE_URL", "http://ckan:5000")
CACHE_TTL = 60  # seconds
_RESOURCE_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}


def configure_logger(shared_logger) -> None:
    global logger
    logger = shared_logger


async def fetch_resource(resource_id: str) -> Dict[str, Any]:
    resource_id = (resource_id or "").strip()
    if not resource_id:
        raise ValueError("resource_id is required")

    now = time.time()
    cached = _RESOURCE_CACHE.get(resource_id)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    url = f"{CKAN_BASE_URL.rstrip('/')}/api/3/action/resource_show"

    try:
        async with httpx.AsyncClient(timeout=5.0) as session:
            response = await session.get(url, params={"id": resource_id})
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.warning("resource_show failed for %s: %s", resource_id, exc)
        raise RuntimeError(f"Failed to fetch resource metadata for {resource_id}") from exc

    if not payload.get("success"):
        raise RuntimeError(f"resource_show returned success=false for {resource_id}")

    result = payload["result"]
    _RESOURCE_CACHE[resource_id] = (now, result)
    return result
