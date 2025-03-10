from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from core.routers.router_caps import CapsRouter
from core.routers.router_chat_completions import ChatCompletionsRouter
from core.routers.router_models import ModelsRouter


__all__ = ["App"]


class App(FastAPI):
    def __init__(
            self,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._setup_middlewares()
        self.add_event_handler("startup", self._startup_events)

        for router in self._routers():
            self.include_router(router)

    def _setup_middlewares(self):
        self.add_middleware(
            CORSMiddleware, # type: ignore[arg-type]
            allow_origins=[
                "http://localhost:5173",
                "http://localhost:5174",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.add_middleware(NoCacheMiddleware) # type: ignore[arg-type]

    async def _startup_events(self):
        pass

    def _routers(self):
        return [
            CapsRouter(),
            ModelsRouter(),
            ChatCompletionsRouter(),
        ]

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache"
        return response
