import os

from pathlib import Path
from typing import Optional

import aiofiles

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.globals import UPLOADS_DIR
from core.routers.router_auth import AuthRouter


class KnowledgeItem(BaseModel):
    file_name: str
    type: str
    format: Optional[str] = None


class KnowledgeRouter(AuthRouter):
    def __init__(self, auth_cache):
        super().__init__(auth_cache=auth_cache)

        self.add_api_route("/v1/knowledge/list", self._knowledge_list, methods=["GET"])
        self.add_api_route("/v1/knowledge/upload", self._knowledge_item_upload, methods=["POST"])

    async def _knowledge_list(self, authorization: str = Header(None)):
        if not await self._check_auth(authorization):
            return self._auth_error_response()

        content = {
            "knowledge": []
        }
        return JSONResponse(
            status_code=200,
            content=content
        )

    async def _knowledge_item_upload(self, request: Request, authorization: str = Header(None)):
        if not await self._check_auth(authorization):
            return self._auth_error_response()

        file_name = request.headers.get('X-File-Name')
        if not file_name:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "X-File-Name header is either missing or empty"}
            )

        file_path = Path(UPLOADS_DIR) / file_name

        if file_path.exists():
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "File already exists"}
            )

        temp_file_path = file_path.with_suffix(file_path.suffix + '.tmp')

        if temp_file_path.exists():
            os.remove(temp_file_path)

        temp_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(temp_file_path, 'wb') as f:
                async for chunk in request.stream():
                    await f.write(chunk)

            os.rename(temp_file_path, file_path)

            return JSONResponse(
                content={"status": "success", "file_name": file_name},
                media_type="application/json"
            )

        except Exception as e:
            if temp_file_path.exists():
                os.remove(temp_file_path)

            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)}
            )
