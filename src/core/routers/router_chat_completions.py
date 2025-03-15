import json
import time

import aiohttp

from fastapi import Header
from fastapi.responses import StreamingResponse

from core.chat import limit_messages, remove_trail_tool_calls
from core.globals import LLM_PROXY_ADDRESS
from core.chat_models import ChatPost
from core.routers.router_auth import AuthRouter
from core.tools.tools import execute_tools_if_needed


class ChatCompletionsRouter(AuthRouter):
    def __init__(self, auth_cache):
        super().__init__(auth_cache=auth_cache)

        self.add_api_route(f"/v1/chat/completions", self._chat_completions, methods=["POST"])

    async def _chat_completions(self, post: ChatPost, authorization: str = Header(None)):
        if not await self._check_auth(authorization):
            return self._auth_error_response()

        messages = post.messages

        tool_res_messages = execute_tools_if_needed(messages)
        messages = [*messages, *tool_res_messages]

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

                    "tool_res_messages": [m.model_dump() for m in tool_res_messages],
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
