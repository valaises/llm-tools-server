from fastapi import Response

from core.globals import LLM_PROXY_ADDRESS
from core.routers.router_auth import AuthRouter
from core.routers.schemas import AUTH_HEADER


class ModelsRouter(AuthRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_api_route("/v1/models", self._models, methods=["GET"])
        self.add_api_route("/v1/models/{model}", self._model_info, methods=["GET"])

    async def _models(self, authorization = AUTH_HEADER):
        async with self.http_session.get(f"{LLM_PROXY_ADDRESS}/models",
                               headers={"Authorization": authorization}) as response:
            content = await response.read()
            return Response(content=content, status_code=response.status,
                            media_type=response.headers.get("content-type"))

    async def _model_info(self, model: str, authorization = AUTH_HEADER):
        async with self.http_session.get(f"{LLM_PROXY_ADDRESS}/models/{model}",
                               headers={"Authorization": authorization}) as response:
            content = await response.read()
            return Response(content=content, status_code=response.status,
                            media_type=response.headers.get("content-type"))
