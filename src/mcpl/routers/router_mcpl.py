from fastapi import status
from typing import List
from pydantic import BaseModel, Field

from core.globals import DEFAULT_MCPL_SERVERS
from core.logger import error, exception
from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository, MCPLServer
from core.routers.router_auth import AuthRouter
from core.routers.schemas import RESPONSES, error_constructor, ErrorResponse, AUTH_HEADER


class MCPLServerItem(BaseModel):
    address: str = Field(..., description="Server address (IP:port or domain:port)")
    is_active: bool = Field(True, description="Whether the server is active")


class MCPLServersListResponse(BaseModel):
    servers: List[MCPLServerItem] = Field(..., description="List of user's MCPL servers")


class MCPLServersUpdateRequest(BaseModel):
    servers: List[MCPLServerItem] = Field(..., description="List of MCPL servers to save")


class MCPLServersUpdateResponse(BaseModel):
    status: str = Field(..., description="Status of the update operation")
    message: str = Field(..., description="Message describing the result")
    servers: List[MCPLServerItem] = Field(..., description="Updated list of user's MCPL servers")


class MCPLRouter(AuthRouter):
    def __init__(
            self,
            mcpl_servers_repository: MCPLServersRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._mcpl_servers_repository = mcpl_servers_repository

        self.add_api_route(
            "/v1/mcpl-servers-list",
            self._mcpl_servers_list,
            methods=["GET"],
            response_model=MCPLServersListResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "Successful response with a list of user's MCPL servers",
                    "model": MCPLServersListResponse
                },
                500: {
                    "description": "Failed to retrieve servers due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "An error occurred while retrieving servers: Internal server error",
                                    "type": "mcpl_error",
                                    "code": "servers_retrieval_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

        self.add_api_route(
            "/v1/mcpl-servers-update",
            self._mcpl_servers_update,
            methods=["POST"],
            response_model=MCPLServersUpdateResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "Successful update of user's MCPL servers",
                    "model": MCPLServersUpdateResponse
                },
                500: {
                    "description": "Failed to update servers due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "Failed to update servers: Internal server error",
                                    "type": "mcpl_error",
                                    "code": "servers_update_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

    async def _mcpl_servers_list(self, authorization = AUTH_HEADER):
        """
        Get the list of MCPL servers for the authenticated user.

        This endpoint returns a list of MCPL servers associated with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)

        Returns:
            A MCPLServersListResponse object containing the list of user's MCPL servers

        Raises:
        ```
        - 401: If authentication fails
        - 500: If an error occurs while retrieving servers
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            servers = await self._mcpl_servers_repository.get_user_servers(auth.user_id)
            default_servers = [
                MCPLServer(user_id=-1, address=s, is_active=True) for s in DEFAULT_MCPL_SERVERS
            ]
            servers.extend(default_servers)

            return MCPLServersListResponse(
                servers=[MCPLServerItem(address=s.address, is_active=s.is_active) for s in servers]
            )
        except Exception as e:
            error(f"Error retrieving MCPL servers: {str(e)}")
            return error_constructor(
                message=f"An error occurred while retrieving servers: {e}",
                error_type="mcpl_error",
                code="servers_retrieval_failed",
                status_code=500,
            )

    async def _mcpl_servers_update(self, request: MCPLServersUpdateRequest, authorization = AUTH_HEADER):
        """
        Update the list of MCPL servers for the authenticated user.

        This endpoint updates the list of MCPL servers associated with the authenticated user.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)
        - **request**: A MCPLServersUpdateRequest object containing the list of servers to save

        Returns:
            A MCPLServersUpdateResponse object containing the status, message, and updated list of servers

        Raises:
        ```
        - 401: If authentication fails
        - 500: If an error occurs while updating servers
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            # Convert the request items to MCPLServer objects
            mcpl_servers = [
                MCPLServer(
                    user_id=auth.user_id,
                    address=server.address if server.address.endswith("/v1") else (server.address.rstrip("/") + "/v1"),
                    is_active=server.is_active
                ) for server in request.servers
            ]

            # Update all servers for the user
            success = await self._mcpl_servers_repository.update_user_servers(auth.user_id, mcpl_servers)

            if not success:
                return error_constructor(
                    message="Failed to update servers: Database operation failed",
                    error_type="mcpl_error",
                    code="servers_update_failed",
                    status_code=500,
                )

            # Get the updated servers to return in the response
            updated_servers = await self._mcpl_servers_repository.get_user_servers(auth.user_id)

            return MCPLServersUpdateResponse(
                status="success",
                message="Servers updated successfully",
                servers=[MCPLServerItem(address=s.address, is_active=s.is_active) for s in updated_servers]
            )

        except Exception as e:
            exception(f"Error updating MCPL servers: {str(e)}")
            return error_constructor(
                message=f"Failed to update servers: {str(e)}",
                error_type="mcpl_error",
                code="servers_update_failed",
                status_code=500,
            )
