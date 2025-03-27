from typing import Optional, List

import aiohttp
from pydantic import BaseModel

from chat_tools.chat_models import ChatTool, ChatMessage, model_validate_chat_message
from core.logger import error, exception
from mcpl.mcpl_base import mcpl_servers


class ToolProps(BaseModel):
    tool_name: str
    system_prompt: Optional[str] = None
    depends_on: Optional[List[str]] = None


class ToolPropsResponse(BaseModel):
    props: List[ToolProps]


async def get_mcpl_tools(c_session: Optional[aiohttp.ClientSession] = None) -> List[ChatTool]:
    c_session = c_session or aiohttp.ClientSession()

    tools = []
    for server in mcpl_servers():
        tools_url = f"{server.address}/tools"
        try:
            async with c_session as session:
                async with session.get(tools_url) as response:
                    if response.status == 200:
                        server_tools_data = await response.json()
                        server_tools = [ChatTool.model_validate(tool) for tool in server_tools_data["tools"]]
                        tools.extend(server_tools)
                    else:
                        error(f"Failed to fetch tools from {server.name}: {response.status}")
        except Exception as e:
            exception(f"Error fetching tools from {server.name}: {str(e)}")

    return tools


async def get_mcpl_tool_props(c_session: Optional[aiohttp.ClientSession] = None) -> List[ToolProps]:
    c_session = c_session or aiohttp.ClientSession()

    props = []
    for server in mcpl_servers():
        props_url = f"{server.address}/tools-props"
        try:
            async with c_session as session:
                async with session.get(props_url) as response:
                    if response.status == 200:
                        tool_props_data = await response.json()
                        tool_props = ToolPropsResponse.model_validate(tool_props_data)
                        props.extend(tool_props.props)
                    else:
                        error(f"Failed to fetch tool props from {server.name}: {response.status}")
        except Exception as e:
            exception(f"Error fetching tool props from {server.name}: {str(e)}")

    return props


async def mcpl_tools_execute(
        user_id: int,
        messages: List[ChatMessage],
        c_session: Optional[aiohttp.ClientSession] = None
) -> List[ChatMessage]:
    responses = []
    c_session = c_session or aiohttp.ClientSession()

    # todo: execute concurrently
    for server in mcpl_servers():
        execute_url = f"{server.address}/tools-execute"
        try:
            async with c_session as session:
                payload = {
                    "user_id": user_id,
                    "messages": [message.model_dump() for message in messages]
                }
                async with session.post(execute_url, json=payload) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        tool_res_messages = [
                            model_validate_chat_message(msg)
                            for msg in response_data["tool_res_messages"]
                        ]
                        responses.extend(tool_res_messages)
                    else:
                        error(f"Failed to execute tools from {server.name}: {response.status}")
        except Exception as e:
            exception(f"Error executing tools from {server.name}: {str(e)}")

    return responses
