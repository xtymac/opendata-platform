"""CKAN Cookie Authentication Module"""

import httpx
from typing import Optional, Tuple
from fastapi import Request

from sync_service.logger import get_logger

log = get_logger("cms_ckan_sync.auth")


async def verify_ckan_cookie(request: Request, ckan_url: str) -> Tuple[bool, Optional[dict]]:
    """
    Verify CKAN session cookie by calling CKAN API.

    Args:
        request: FastAPI request object
        ckan_url: CKAN instance URL

    Returns:
        (is_valid, user_info) - user_info contains sysadmin field if valid
    """
    # Get CKAN session cookie
    ckan_cookie = request.cookies.get("ckan")
    if not ckan_cookie:
        log.debug("No CKAN cookie found in request")
        return False, None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{ckan_url}/api/action/user_show",
                params={"id": "me"},
                cookies={"ckan": ckan_cookie},
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    user_info = data.get("result", {})
                    log.info(f"CKAN cookie auth successful for user: {user_info.get('name')}")
                    return True, user_info
                else:
                    log.debug(f"CKAN API returned success=false: {data.get('error')}")
            else:
                log.debug(f"CKAN API returned status {resp.status_code}")

    except httpx.TimeoutException:
        log.warning("CKAN cookie verification timed out")
    except httpx.RequestError as e:
        log.warning(f"CKAN cookie verification request failed: {e}")
    except Exception as e:
        log.error(f"Unexpected error during CKAN cookie verification: {e}")

    return False, None
