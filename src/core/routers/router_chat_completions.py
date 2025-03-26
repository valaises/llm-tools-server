import json
import time

import aiohttp

from fastapi import Header
from fastapi.responses import StreamingResponse

from core.chat import limit_messages, remove_trail_tool_calls
from core.globals import LLM_PROXY_ADDRESS
from core.chat_models import ChatPost, ChatMessageSystem
from core.logger import info
from core.routers.router_auth import AuthRouter
from core.tools.tools import execute_tools_if_needed
from mcpl.wrappers import get_mcpl_tool_props, mcpl_tools_execute


async def compose_system_message():
    system = "You are a helpful AI assistant."
    # todo: use cache
    mcp_props = await get_mcpl_tool_props()

    if mcp_props:
        how_to_use_tools = '\n\n'.join([
            p.system_prompt for p in mcp_props if p.system_prompt
        ])
        system = f"{system}\nHow to use TOOLS:\n{how_to_use_tools}"

    return ChatMessageSystem(role="system", content=system)


class ChatCompletionsRouter(AuthRouter):
    def __init__(self, auth_cache):
        super().__init__(auth_cache=auth_cache)

        self.add_api_route(f"/v1/chat/completions", self._chat_completions, methods=["POST"])

    async def _chat_completions(self, post: ChatPost, authorization: str = Header(None)):
        if not await self._check_auth(authorization):
            return self._auth_error_response()

        messages = post.messages

        if messages and messages[0].role not in ["system", "developer"]:
            system_message = await compose_system_message()
            messages = [system_message, *messages]

        tool_res_messages = execute_tools_if_needed(messages)
        tool_res_messages_mcpl = await mcpl_tools_execute(1, messages)

        messages = [*messages, *tool_res_messages, *tool_res_messages_mcpl]

        messages = limit_messages(messages)

        remove_trail_tool_calls(messages)

        post.messages = messages

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
                        for m in [*tool_res_messages, *tool_res_messages_mcpl]
                    ],
                }) + postfix
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
