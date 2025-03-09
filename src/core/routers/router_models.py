import aiohttp
from fastapi import APIRouter, Response, Header

from core.globals import LLM_PROXY_ADDRESS


class ModelsRouter(APIRouter):
    def __init__(self):
        super().__init__()

        self.add_api_route("/v1/models", self._models, methods=["GET"])
        self.add_api_route("/v1/models/{model}", self._model_info, methods=["GET"])

    async def _models(self, authorization: str = Header(None)):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LLM_PROXY_ADDRESS}/models",
                                   headers={"Authorization": authorization}) as response:
                content = await response.read()
                return Response(content=content, status_code=response.status,
                                media_type=response.headers.get("content-type"))

    async def _model_info(self, model: str, authorization: str = Header(None)):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LLM_PROXY_ADDRESS}/models/{model}",
                                   headers={"Authorization": authorization}) as response:
                content = await response.read()
                return Response(content=content, status_code=response.status,
                                media_type=response.headers.get("content-type"))
