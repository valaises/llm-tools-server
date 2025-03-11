
import aiohttp

from fastapi import Header, APIRouter
from fastapi.responses import StreamingResponse

from core.chat import limit_messages, remove_trail_tool_calls
from core.globals import LLM_PROXY_ADDRESS
from core.chat_models import ChatPost
from core.logger import info
from core.tools.tools import execute_tools_if_needed


class ChatCompletionsRouter(APIRouter):
    def __init__(self):
        super().__init__()

        self.add_api_route(f"/v1/chat/completions", self._chat_completions, methods=["POST"])

    async def _chat_completions(self, post: ChatPost, authorization: str = Header(None)):
        messages = post.messages

        tool_res_messages = execute_tools_if_needed(messages)
        messages = [*messages, *tool_res_messages]

        messages = limit_messages(messages)

        remove_trail_tool_calls(messages)

        async def streamer():
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
