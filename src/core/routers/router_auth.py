import re
import json
import time
import aiohttp

from dataclasses import dataclass

from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, Response

from core.globals import LLM_PROXY_ADDRESS
from core.logger import info


CACHE_ITEM_EXPIRATION_TIME = 360


@dataclass
class AuthItem:
    api_key: str
    scope: str
    created_at: str
    user_id: int
    user_email: str


@dataclass
class CacheAuthItem:
    item: AuthItem
    cached_ts: float


def auth_s_left(item: CacheAuthItem):
    return CACHE_ITEM_EXPIRATION_TIME - (time.time() - item.cached_ts)


async def fetch_auth_item(authorization: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{LLM_PROXY_ADDRESS}/auth",
                               headers={"Authorization": authorization}) as response:
            if response.status != 200:
                text = await response.text()
                return {"error": {"message": f"Failed to auth: {text}"}}

            content = await response.json()
            return content


class AuthRouter(APIRouter):
    def __init__(self, auth_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = auth_cache

    async def _check_auth(self, authorization: Header = None) -> Optional[AuthItem]:
        if not authorization:
            return

        match = re.match(r"^Bearer\s+(.+)$", authorization)
        if not match:
            return

        api_key: str = match.group(1)

        if item := self.cache.get(api_key):
            s_left = auth_s_left(item)
            if s_left > 0:
                info(f"cache -> AUTH; exp:{s_left :.1f}s")
                return item.item

        a_item = await fetch_auth_item(authorization)

        if "auth" in a_item:
            item = AuthItem(**a_item["auth"])
            self.cache[api_key] = CacheAuthItem(item=item, cached_ts=time.time())
            info("fetch -> AUTH -> cache")
            return item

        return None

    def _auth_error_response(self):
        return Response(
            status_code=401,
            content=json.dumps({
                "error": {
                    "message": "Invalid authentication",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }),
            media_type="application/json"
        )
