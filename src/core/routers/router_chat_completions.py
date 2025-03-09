import aiohttp

from fastapi import Header, APIRouter
from fastapi.responses import StreamingResponse

from core.globals import LLM_PROXY_ADDRESS
from core.routers.chat_models import ChatPost


class ChatCompletionsRouter(APIRouter):
    def __init__(self):
        super().__init__()

        self.add_api_route(f"/v1/chat/completions", self._chat_completions, methods=["POST"])

    async def _chat_completions(self, post: ChatPost, authorization: str = Header(None)):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{LLM_PROXY_ADDRESS}/chat/completions",
                    json=post.model_dump(),
                    headers={"Authorization": authorization}
            ) as response:
                return StreamingResponse(response.content.iter_any(), media_type="text/event-stream")
