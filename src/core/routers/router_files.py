import os
import uuid
import hashlib

from urllib.parse import unquote
from datetime import datetime
from pathlib import Path

import aiofiles

from fastapi import Request, status
from typing import Optional, List
from pydantic import BaseModel, Field

from core.globals import UPLOADS_DIR
from core.logger import exception, error
from core.repositories.files_repository import FilesRepository, FileItem
from core.routers.router_auth import AuthRouter
from core.routers.schemas import RESPONSES, error_constructor, ErrorResponse, AUTH_HEADER


class FileItemResponse(BaseModel):
    file_name: str = Field(..., description="Unique file identifier")
    file_name_orig: str = Field(..., description="Original file name")
    file_ext: str = Field(..., description="File extension")
    file_role: str = Field(..., description="Role of the file (e.g., document)")
    file_type: Optional[str] = Field(None, description="Type of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    processing_status: Optional[str] = Field(None, description="Processing status of the file")
    created_at: datetime = Field(..., description="Timestamp when the file was created")


class FilesListResponse(BaseModel):
    files: List[FileItemResponse] = Field(..., description="List of user's files")


class FileUploadResponse(BaseModel):
    status: str = Field(..., description="Status of the upload operation")
    file_name: str = Field(..., description="Original file name")
    stored_as: str = Field(..., description="Stored file name (hashed)")


class FileDeleteRequest(BaseModel):
    file_name: str = Field(..., description="The name of the file to delete")


class FileDeleteResponse(BaseModel):
    status: str = Field(..., description="Status of the delete operation")
    message: str = Field(..., description="Message describing the result")


class FileUpdateRequest(BaseModel):
    file_name: str = Field(..., description="The name of the file to update")
    file_name_orig: Optional[str] = Field(None, description="New original file name")
    file_role: Optional[str] = Field(None, description="New file role")
    file_type: Optional[str] = Field(None, description="New file type")
    processing_status: Optional[str] = Field(None, description="New processing status")


class FileUpdateResponse(BaseModel):
    status: str = Field(..., description="Status of the update operation")
    message: str = Field(..., description="Message describing the result")
    file: FileItemResponse = Field(..., description="Updated file information")


class FilesRouter(AuthRouter):
    def __init__(
            self,
            files_repository: FilesRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._files_repository = files_repository

        self.add_api_route(
            "/v1/files/list",
            self._files_list,
            methods=["GET"],
            response_model=FilesListResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "Successful response with a list of user's files",
                    "model": FilesListResponse
                },
                500: {
                    "description": "Failed to retrieve files due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "An error occurred while retrieving files: Internal server error",
                                    "type": "files_error",
                                    "code": "files_retrieval_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

        self.add_api_route(
            "/v1/files/upload",
            self._files_upload,
            methods=["POST"],
            response_model=FileUploadResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "File uploaded successfully",
                    "model": FileUploadResponse
                },
                400: {
                    "description": "Bad request, missing required headers",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "X-File-Name header is either missing or empty",
                                    "type": "files_error",
                                    "code": "invalid_request"
                                }
                            }
                        }
                    }
                },
                500: {
                    "description": "Failed to upload file due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "Failed to upload file: Internal server error",
                                    "type": "files_error",
                                    "code": "file_upload_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

        self.add_api_route(
            "/v1/files/delete",
            self._files_delete,
            methods=["POST"],
            response_model=FileDeleteResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "File deleted successfully",
                    "model": FileDeleteResponse
                },
                404: {
                    "description": "File not found or user doesn't have permission",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "File not found or you don't have permission to delete it",
                                    "type": "files_error",
                                    "code": "file_not_found"
                                }
                            }
                        }
                    }
                },
                500: {
                    "description": "Failed to delete file due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "Failed to delete file: Internal server error",
                                    "type": "files_error",
                                    "code": "file_deletion_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

        self.add_api_route(
            "/v1/files/update",
            self._files_update,
            methods=["POST"],
            response_model=FileUpdateResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "File updated successfully",
                    "model": FileUpdateResponse
                },
                404: {
                    "description": "File not found or user doesn't have permission",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "File not found or you don't have permission to update it",
                                    "type": "files_error",
                                    "code": "file_not_found"
                                }
                            }
                        }
                    }
                },
                500: {
                    "description": "Failed to update file due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "Failed to update file: Internal server error",
                                    "type": "files_error",
                                    "code": "file_update_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

    async def _files_list(self, authorization = AUTH_HEADER):
        """
        Get the list of files for the authenticated user.

        This endpoint returns a list of files associated with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)

        Returns:
            A FilesListResponse object containing the list of user's files

        Raises:
        ```
        - 401: If authentication fails
        - 500: If an error occurs while retrieving files
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            files = await self._files_repository.get_user_files(auth.user_id)

            return FilesListResponse(
                files=[FileItemResponse(**f.model_dump(mode='json')) for f in files]
            )
        except Exception as e:
            error(f"Error retrieving files: {str(e)}")
            return error_constructor(
                message=f"An error occurred while retrieving files: {e}",
                error_type="files_error",
                code="files_retrieval_failed",
                status_code=500,
            )

    async def _files_upload(self, request: Request, authorization = AUTH_HEADER):
        """
        Upload a file for the authenticated user.

        This endpoint allows uploading a file and associates it with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)
        - **X-File-Name**: Header containing the original file name (required)
        - **X-File-Role**: Header containing the file role (optional, defaults to 'document')

        Returns:
            A FileUploadResponse object containing the upload status and file information

        Raises:
        ```
        - 400: If required headers are missing
        - 401: If authentication fails
        - 500: If an error occurs during file upload
        ```
        """
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        file_name = request.headers.get('X-File-Name')
        file_role = request.headers.get('X-File-Role', 'document')

        if not file_name:
            return error_constructor(
                message="X-File-Name header is either missing or empty",
                error_type="files_error",
                code="invalid_request",
                status_code=400,
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

            return FileUploadResponse(
                status="success",
                file_name=file_name,
                stored_as=hashed_filename
            )

        except Exception as e:
            exception(f"Error uploading file: {str(e)}")
            if temp_file_path.exists():
                os.remove(temp_file_path)

            return error_constructor(
                message=f"Failed to upload file: {str(e)}",
                error_type="files_error",
                code="file_upload_failed",
                status_code=500,
            )

    async def _files_delete(self, request: FileDeleteRequest, authorization = AUTH_HEADER):
        """
        Delete a file for the authenticated user.

        This endpoint deletes a file associated with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)
        - **request**: A FileDeleteRequest object containing the name of the file to delete

        Returns:
            A FileDeleteResponse object containing the deletion status and message

        Raises:
        ```
        - 401: If authentication fails
        - 404: If the file is not found or the user doesn't have permission
        - 500: If an error occurs during file deletion
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            file_name = request.file_name

            # Get user files to verify ownership
            user_files = await self._files_repository.get_user_files(auth.user_id)
            file_exists = any(file.file_name == file_name for file in user_files)

            if not file_exists:
                return error_constructor(
                    message="File not found or you don't have permission to delete it",
                    error_type="files_error",
                    code="file_not_found",
                    status_code=404,
                )

            # Delete from database
            if not await self._files_repository.delete_file(file_name):
                return error_constructor(
                    message="Failed to delete file from database",
                    error_type="files_error",
                    code="file_deletion_failed",
                    status_code=500,
                )

            # Delete the actual file
            file_path = Path(UPLOADS_DIR) / file_name
            if file_path.exists():
                os.remove(file_path)

            return FileDeleteResponse(
                status="success",
                message="File deleted successfully"
            )

        except Exception as e:
            exception(f"Error deleting file: {str(e)}")
            return error_constructor(
                message=f"Failed to delete file: {str(e)}",
                error_type="files_error",
                code="file_deletion_failed",
                status_code=500,
            )

    async def _files_update(self, request: FileUpdateRequest, authorization = AUTH_HEADER):
        """
        Update file information for the authenticated user.

        This endpoint updates information for a file associated with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)
        - **request**: A FileUpdateRequest object containing the file information to update

        Returns:
            A FileUpdateResponse object containing the update status, message, and updated file information

        Raises:
        ```
        - 401: If authentication fails
        - 404: If the file is not found or the user doesn't have permission
        - 500: If an error occurs during file update
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            file_name = request.file_name

            # Get user files to verify ownership and get current file data
            user_files = await self._files_repository.get_user_files(auth.user_id)
            file_to_update = next((file for file in user_files if file.file_name == file_name), None)

            if not file_to_update:
                return error_constructor(
                    message="File not found or you don't have permission to update it",
                    error_type="files_error",
                    code="file_not_found",
                    status_code=404,
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
                return error_constructor(
                    message="Failed to update file information",
                    error_type="files_error",
                    code="file_update_failed",
                    status_code=500,
                )

            return FileUpdateResponse(
                status="success",
                message="File updated successfully",
                file=FileItemResponse(**file_to_update.model_dump(mode='json'))
            )

        except Exception as e:
            exception(f"Error updating file: {str(e)}")
            return error_constructor(
                message=f"Failed to update file: {str(e)}",
                error_type="files_error",
                code="file_update_failed",
                status_code=500,
            )
