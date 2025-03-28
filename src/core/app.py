from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from core.repositories.files_repository import FilesRepository
from core.routers.router_caps import CapsRouter
from core.routers.router_chat_completions import ChatCompletionsRouter
from core.routers.router_files import FilesRouter
from core.routers.router_models import ModelsRouter


__all__ = ["App"]


class App(FastAPI):
    def __init__(
            self,
            files_repository: FilesRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.auth_cache = {}
        self.files_repository = files_repository
        
        self._setup_middlewares()
        self.add_event_handler("startup", self._startup_events)

        for router in self._routers():
            self.include_router(router)

    def _setup_middlewares(self):
        self.add_middleware(
            CORSMiddleware, # type: ignore[arg-type]
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.add_middleware(NoCacheMiddleware) # type: ignore[arg-type]

    async def _startup_events(self):
        pass

    def _routers(self):
        return [
            CapsRouter(self.auth_cache),
            ChatCompletionsRouter(self.auth_cache),
            FilesRouter(
                self.auth_cache,
                self.files_repository,
            ),

            ModelsRouter()
        ]

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache"
        return response
