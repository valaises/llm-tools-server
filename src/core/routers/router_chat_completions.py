import json
import time

import aiohttp

from fastapi.responses import StreamingResponse, JSONResponse

from core.logger import info
from openai_wrappers.types import ChatPost, ChatMessageSystem

from core.chat import limit_messages, remove_trail_tool_calls
from core.globals import LLM_PROXY_ADDRESS
from core.routers.router_auth import AuthRouter
from core.routers.schemas import AUTH_HEADER
from core.tools.tool_context import ToolContext
from core.tools.tools import execute_tools_if_needed
from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository
from mcpl.servers import get_active_servers
from mcpl.wrappers import get_mcpl_tool_props, mcpl_tools_execute
from openai_wrappers.utils import convert_messages_for_openai_format


async def compose_system_message(
        http_session: aiohttp.ClientSession,
        servers
):
    system = "You are a helpful AI assistant."
    # todo: use cache
    mcp_props = await get_mcpl_tool_props(http_session, servers)

    if mcp_props:
        how_to_use_tools = '\n\n'.join([
            p.system_prompt for p in mcp_props if p.system_prompt
        ])
        system = f"{system}\nHow to use TOOLS:\n{how_to_use_tools}"

    return ChatMessageSystem(
        role="system",
        content=system
    )


class ChatCompletionsRouter(AuthRouter):
    def __init__(
            self,
            mcpl_servers_repository: MCPLServersRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._mcpl_servers_repository = mcpl_servers_repository

        self.add_api_route(f"/v1/chat/completions", self._chat_completions, methods=["POST"])

    async def _chat_completions(self, post: ChatPost, authorization = AUTH_HEADER):
        auth = await self._check_auth(authorization)
        if not auth:
            return self._auth_error_response()

        tool_context = ToolContext(
            self.http_session
        )

        servers = await get_active_servers(self._mcpl_servers_repository, auth.user_id)

        messages = post.messages

        if messages and messages[0].role not in ["system", "developer"]:
            system_message = await compose_system_message(self.http_session, servers)
            messages = [system_message, *messages]

        tool_res_messages = await execute_tools_if_needed(tool_context, messages)

        tool_res_messages_mcpl = await mcpl_tools_execute(
            self.http_session, servers, auth.user_id, messages
        )

        tool_res_messages.extend(tool_res_messages_mcpl)
        del tool_res_messages_mcpl
        info(tool_res_messages)

        messages = [
            *messages,
            *tool_res_messages
        ]

        messages = limit_messages(messages)

        remove_trail_tool_calls(messages)

        post.messages = convert_messages_for_openai_format(messages)

        if post.stream is False:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{LLM_PROXY_ADDRESS}/chat/completions",
                        json=post.model_dump(),
                        headers={"Authorization": authorization or ""}
                ) as response:
                    response_data = await response.json()

                    # If we have tool_res_messages, add them to the response
                    if len(tool_res_messages):
                        response_data["tool_res_messages"] = [
                            m.model_dump() for m in tool_res_messages
                        ]

                    return JSONResponse(content=response_data)

        async def streamer():
            prefix, postfix = "data: ", "\n\n"
            if len(tool_res_messages):
                yield prefix + json.dumps({
                    "id": "XXX",
                    "object": "tool_res_messages",
                    "created": time.time(),
                    "model": post.model,
                    "choices": [],

                    "tool_res_messages": [
                        m.model_dump()
                        for m in tool_res_messages
                    ],
                }) + postfix
                info(tool_res_messages)
                tool_res_messages.clear()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{LLM_PROXY_ADDRESS}/chat/completions",
                        json=post.model_dump(),
                        headers={"Authorization": authorization or ""}
                ) as response:
                    async for chunk in response.content:
                        if chunk:
                            yield chunk

        return StreamingResponse(streamer(), media_type="text/event-stream")
