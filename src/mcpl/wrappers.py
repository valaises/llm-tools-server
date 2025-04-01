import asyncio
from itertools import chain
from typing import Optional, List

import aiohttp
from pydantic import BaseModel

from chat_tools.chat_models import ChatTool, ChatMessage, model_validate_chat_message
from core.logger import error, exception
from mcpl.repositories.repo_mcpl_servers import MCPLServer


class ToolProps(BaseModel):
    tool_name: str
    system_prompt: Optional[str] = None
    depends_on: Optional[List[str]] = None


class ToolPropsResponse(BaseModel):
    props: List[ToolProps]


async def get_mcpl_tools(
        c_session: aiohttp.ClientSession,
        servers: List[MCPLServer]
) -> List[ChatTool]:
    """
    Fetch chat tools from multiple MCPL servers concurrently.

    Args:
        c_session: The aiohttp ClientSession to use for requests.
                  The caller is responsible for managing the session's lifecycle.
        servers: List of MCPL servers to fetch tools from.

    Returns:
        A list of ChatTool objects from all servers.
    """

    async def fetch_from_server(server: MCPLServer) -> List[ChatTool]:
        tools_url = f"{server.address}/tools"
        try:
            async with c_session.get(tools_url) as response:
                if response.status == 200:
                    server_tools_data = await response.json()
                    return [ChatTool.model_validate(tool) for tool in server_tools_data["tools"]]
                else:
                    error(f"Failed to fetch tools from {server.address}: {response.status}")
                    return []
        except Exception as e:
            exception(f"Error fetching tools from {server.address}: {str(e)}")
            return []

    # Execute all requests concurrently
    results = await asyncio.gather(*[fetch_from_server(server) for server in servers])

    return list(chain.from_iterable(results))


async def get_mcpl_tool_props(
        c_session: aiohttp.ClientSession,
        servers: List[MCPLServer]
) -> List[ToolProps]:
    """
    Fetch tool properties from multiple MCPL servers concurrently.

    Args:
        c_session: The aiohttp ClientSession to use for requests.
                  The caller is responsible for managing the session's lifecycle.
        servers: List of MCPL servers to fetch tool properties from.

    Returns:
        A list of ToolProps objects from all servers.
    """

    async def fetch_from_server(server: MCPLServer) -> List[ToolProps]:
        props_url = f"{server.address}/tools-props"
        try:
            async with c_session.get(props_url) as response:
                if response.status == 200:
                    tool_props_data = await response.json()
                    tool_props = ToolPropsResponse.model_validate(tool_props_data)
                    return tool_props.props
                else:
                    error(f"Failed to fetch tool props from {server.address}: {response.status}")
                    return []
        except Exception as e:
            exception(f"Error fetching tool props from {server.address}: {str(e)}")
            return []

    # Execute all requests concurrently
    results = await asyncio.gather(*[fetch_from_server(server) for server in servers])

    return list(chain.from_iterable(results))


async def mcpl_tools_execute(
        c_session: aiohttp.ClientSession,
        servers: List[MCPLServer],
        user_id: int,
        messages: List[ChatMessage]
) -> List[ChatMessage]:
    """
    Execute tools on multiple MCPL servers concurrently.

    Args:
        c_session: The aiohttp ClientSession to use for requests.
                  The caller is responsible for managing the session's lifecycle.
        servers: List of MCPL servers to execute tools on.
        user_id: The user ID to associate with the tool execution.
        messages: List of chat messages to process.

    Returns:
        A list of chat messages containing the tool responses.
    """

    async def execute_on_server(server: MCPLServer) -> List[ChatMessage]:
        execute_url = f"{server.address}/tools-execute"
        try:
            payload = {
                "user_id": user_id,
                "messages": [message.model_dump() for message in messages]
            }
            async with c_session.post(execute_url, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return [
                        model_validate_chat_message(msg)
                        for msg in response_data["tool_res_messages"]
                    ]
                else:
                    error(f"Failed to execute tools from {server.address}: {response.status}")
                    return []
        except Exception as e:
            exception(f"Error executing tools from {server.address}: {str(e)}")
            return []

    # Execute all requests concurrently
    results = await asyncio.gather(*[execute_on_server(server) for server in servers])

    return list(chain.from_iterable(results))
