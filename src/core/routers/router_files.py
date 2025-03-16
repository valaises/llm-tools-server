import os
import uuid
import hashlib

from urllib.parse import unquote
from datetime import datetime

from pathlib import Path

import aiofiles

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel, Field

from core.globals import UPLOADS_DIR
from core.logger import exception
from core.repositories.files_repository import FilesRepository, FileItem
from core.routers.router_auth import AuthRouter


class FileDeleteRequest(BaseModel):
    file_name: str


class FileUpdateRequest(BaseModel):
    file_name: str = Field(..., description="The name of the file to update")
    file_name_orig: Optional[str] = Field(None, description="New original file name")
    file_role: Optional[str] = Field(None, description="New file role")
    file_type: Optional[str] = Field(None, description="New file type")
    processing_status: Optional[str] = Field(None, description="New processing status")


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
        self.add_api_route("/v1/files/delete", self._files_delete, methods=["POST"])
        self.add_api_route("/v1/files/update", self._files_update, methods=["POST"])

    async def _files_list(self, authorization: str = Header(None)):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

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
        file_name = unquote(file_name)

        # Create a unique hash based on the original filename and a random UUID
        random_hash = hashlib.sha256(f"{file_name}{uuid.uuid4()}".encode()).hexdigest()  # type: ignore

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

    async def _files_delete(self, request: FileDeleteRequest, authorization: str = Header(None)):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        try:
            file_name = request.file_name

            # Get user files to verify ownership
            user_files = await self._files_repository.get_user_files(auth.user_id)
            file_exists = any(file.file_name == file_name for file in user_files)

            if not file_exists:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "File not found or you don't have permission to delete it"}
                )

            # Delete from database
            if not await self._files_repository.delete_file(file_name):
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "Failed to delete file from database"}
                )

            # Delete the actual file
            file_path = Path(UPLOADS_DIR) / file_name
            if file_path.exists():
                os.remove(file_path)

            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "File deleted successfully"}
            )

        except Exception as e:
            exception(f"Error deleting file: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Failed to delete file: {str(e)}"}
            )

    async def _files_update(self, request: FileUpdateRequest, authorization: str = Header(None)):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        try:
            file_name = request.file_name

            # Get user files to verify ownership and get current file data
            user_files = await self._files_repository.get_user_files(auth.user_id)
            file_to_update = next((file for file in user_files if file.file_name == file_name), None)

            if not file_to_update:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "File not found or you don't have permission to update it"}
                )

            # Update only the fields provided in the request
            if request.file_name_orig is not None:
                file_to_update.file_name_orig = request.file_name_orig

            if request.file_role is not None:
                file_to_update.file_role = request.file_role

            if request.file_type is not None:
                file_to_update.file_type = request.file_type

            if request.processing_status is not None:
                file_to_update.processing_status = request.processing_status

            # Update the file in the database
            if not await self._files_repository.update_file(file_name, file_to_update):
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "Failed to update file information"}
                )

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "File updated successfully",
                    "file": file_to_update.model_dump(mode='json')
                }
            )

        except Exception as e:
            exception(f"Error updating file: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Failed to update file: {str(e)}"}
            )
