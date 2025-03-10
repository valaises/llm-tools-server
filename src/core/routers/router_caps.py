import json

from fastapi import Header, APIRouter, Response

from core.tools.tools import get_tools_list


class CapsRouter(APIRouter):
    def __init__(self):
        super().__init__()

        self.add_api_route("/v1/tools", self._tools, methods=["GET"])

    def _tools(self, _authorization: str = Header(None)):
        data = get_tools_list()

        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json"
        )
