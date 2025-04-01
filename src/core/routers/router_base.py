
from fastapi import APIRouter
from scalar_fastapi import get_scalar_api_reference


class BaseRouter(APIRouter):
    def __init__(self):
        super().__init__()

        self.add_api_route("/docs", self._scalar, methods=["GET"], include_in_schema=False)

    async def _scalar(self):
        return get_scalar_api_reference(
            openapi_url="/api/v1/openapi.json",
            title="Sensible API Ref",
        )
