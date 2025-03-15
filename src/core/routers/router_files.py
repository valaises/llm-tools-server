import os
import uuid
import hashlib
from datetime import datetime

from pathlib import Path

import aiofiles

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from core.globals import UPLOADS_DIR
from core.logger import exception, info
from core.repositories.files_repository import FilesRepository, FileItem
from core.routers.router_auth import AuthRouter


class FilesRouter(AuthRouter):
    def __init__(
            self,
            auth_cache,
            files_repository: FilesRepository
    ):
        super().__init__(auth_cache=auth_cache)
        self._files_repository = files_repository

        self.add_api_route("/v1/files/list", self._files_list, methods=["GET"])
        self.add_api_route("/v1/files/upload", self._files_upload, methods=["POST"])

    async def _files_list(self, authorization: str = Header(None)):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        info(f"searching files for user_id: {auth.user_id}")
        files = await self._files_repository.get_user_files(auth.user_id)

        content = {
            "files": [f.model_dump(mode='json') for f in files]
        }

        return JSONResponse(
            status_code=200,
            content=content
        )

    async def _files_upload(self, request: Request, authorization: str = Header(None)):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        file_name = request.headers.get('X-File-Name')
        file_role = request.headers.get('X-File-Role', 'document')

        if not file_name:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "X-File-Name header is either missing or empty"}
            )

        # Create a unique hash based on the original filename and a random UUID
        random_hash = hashlib.sha256(f"{file_name}{uuid.uuid4()}".encode()).hexdigest()

        # Keep the original file extension if it exists
        original_extension = Path(file_name).suffix
        hashed_filename = f"{random_hash}{original_extension}"

        file_path = Path(UPLOADS_DIR) / hashed_filename

        temp_file_path = file_path.with_suffix(file_path.suffix + '.tmp')

        if temp_file_path.exists():
            os.remove(temp_file_path)

        temp_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(temp_file_path, 'wb') as f:
                async for chunk in request.stream():
                    await f.write(chunk)

            os.rename(temp_file_path, file_path)

            file_item = FileItem(
                file_name=hashed_filename,
                file_name_orig=file_name,
                file_ext=original_extension,
                file_role=file_role,
                file_size=os.path.getsize(file_path),
                user_id=auth.user_id,
                created_at=datetime.now(),
            )
            info(file_item)

            if not await self._files_repository.create_file(file_item):
                raise Exception("Failed to save file information to database")

            return JSONResponse(
                content={
                    "status": "success",
                    "file_name": file_name,
                    "stored_as": hashed_filename
                },
                media_type="application/json"
            )

        except Exception as e:
            exception("exception")
            if temp_file_path.exists():
                os.remove(temp_file_path)

            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)}
            )
