from typing import List

from fastapi import status
from pydantic import BaseModel

from chat_tools.chat_models import ChatTool

from core.logger import error
from core.routers.router_auth import AuthRouter
from core.routers.schemas import RESPONSES, error_constructor, ErrorResponse, AUTH_HEADER
from core.tools.tools import get_tools_list
from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository
from mcpl.servers import get_active_servers
from mcpl.wrappers import get_mcpl_tools


class ToolsResponse(BaseModel):
    tools: List[ChatTool]


class CapsRouter(AuthRouter):
    def __init__(
            self,
            mcpl_servers_repository: MCPLServersRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._mcpl_servers_repository = mcpl_servers_repository

        self.add_api_route(
            "/v1/tools",
            self._tools,
            methods=["GET"],
            response_model=ToolsResponse,
            status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "Successful response with a list of tools",
                    "model": ToolsResponse
                },
                500: {
                    "description": "Failed to retrieve tools due to an internal server error",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "message": "An error occurred while retrieving tools: Internal server error",
                                    "type": "caps_error",
                                    "code": "tools_retrieval_failed"
                                }
                            }
                        }
                    }
                },
                **RESPONSES["auth_failed"]
            }
        )

    async def _tools(self, authorization = AUTH_HEADER):
        """
        Get available tools for the authenticated user.

        This endpoint returns a list of tools that are available to the authenticated user,
        including both standard tools and any MCPL-specific tools associated with the user's servers.

        - **authorization**: Bearer token for authentication (Bearer XXX) (required)

        Returns:
            A ToolsResponse object containing the list of available tools

        Raises:
        ```
        - 401: If authentication fails
        - 500: If an error occurs while retrieving tools
        ```
        """
        try:
            auth = await self._check_auth(authorization)
            if not auth:
                return self._auth_error_response()

            servers = await get_active_servers(self._mcpl_servers_repository, auth.user_id)
            mcpl_tools = await get_mcpl_tools(self.http_session, servers)

            return ToolsResponse(
                tools=[
                    *get_tools_list(),
                    *mcpl_tools,
                ]
            )
        except Exception as e:
            error(f"Error retrieving tools: {str(e)}")
            return error_constructor(
                message=f"An error occurred while retrieving tools: {e}",
                error_type="caps_error",
                code="tools_retrieval_failed",
                status_code=500,
            )
