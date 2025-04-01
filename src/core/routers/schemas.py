import json

from pydantic import BaseModel
from fastapi import Header, Response


class ErrorDetail(BaseModel):
    message: str
    type: str
    code: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


AUTH_HEADER = Header(
    None,
    description="Bearer token for authentication",
    example="Bearer XXX"
)


RESPONSES = {
    "auth_failed": {
        401: {
            "description": "Authentication failed",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "Invalid authentication",
                            "type": "invalid_request_error",
                            "code": "invalid_api_key"
                        }
                    }
                }
            }
        }
    },
    "not_an_admin": {
        403: {
            "description": "User does not have admin privileges",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "message": "User does not have admin privileges",
                            "type": "permission_denied_error",
                            "code": "not_authorized"
                        }
                    }
                }
            }
        }
    }
}


def error_constructor(message: str, error_type: str, code: str, status_code: int) -> Response:
    """
    Example:
        message="Invalid authentication",
        type="invalid_request_error",
        code="invalid_api_key"
        status_code=401
    """
    error_response = ErrorResponse(
        error=ErrorDetail(
            message=message,
            type=error_type,
            code=code
        )
    )
    return Response(
        status_code=status_code,
        content=json.dumps(error_response.model_dump()),
        media_type="application/json"
    )
