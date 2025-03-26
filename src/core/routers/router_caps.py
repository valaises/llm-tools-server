import json

from fastapi import Header, Response

from core.routers.router_auth import AuthRouter
from core.tools.tools import get_tools_list
from mcpl.wrappers import get_mcpl_tools


class CapsRouter(AuthRouter):
    def __init__(self, auth_cache):
        super().__init__(auth_cache=auth_cache)

        self.add_api_route("/v1/tools", self._tools, methods=["GET"])

    async def _tools(self, authorization: str = Header(None)):
        if not await self._check_auth(authorization):
            return self._auth_error_response()

        mcpl_tools = await get_mcpl_tools()

        content = {
            "tools": [t.model_dump() for t in [
                *get_tools_list(),
                *mcpl_tools
            ]]
        }

        return Response(
            content=json.dumps(content, indent=2),
            media_type="application/json"
        )
