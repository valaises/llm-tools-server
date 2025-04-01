import aiohttp
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from core.repositories.files_repository import FilesRepository
from core.routers.router_base import BaseRouter
from core.routers.router_caps import CapsRouter
from core.routers.router_chat_completions import ChatCompletionsRouter
from core.routers.router_files import FilesRouter
from core.routers.router_models import ModelsRouter

__all__ = ["App"]

from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository
from mcpl.routers.router_mcpl import MCPLRouter


class App(FastAPI):
    def __init__(
            self,
            files_repository: FilesRepository,
            mcpl_repository: MCPLServersRepository,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.auth_cache = {}
        self.files_repository = files_repository
        self.mcpl_repository = mcpl_repository

        self._setup_middlewares()
        self.add_event_handler("startup", self._startup_events)
        self.add_event_handler("shutdown", self._shutdown_events)

    def _setup_middlewares(self):
        self.add_middleware(
            CORSMiddleware,  # type: ignore[arg-type]
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.add_middleware(NoCacheMiddleware)  # type: ignore[arg-type]

    async def _startup_events(self):
        self.http_session = aiohttp.ClientSession()
        # Include routers after http_session is initialized
        for router in self._routers():
            self.include_router(router)

    async def _shutdown_events(self):
        if hasattr(self, 'http_session'):
            await self.http_session.close()

    def _routers(self):
        return [
            BaseRouter(),
            MCPLRouter(
                self.mcpl_repository,
                self.auth_cache,
                self.http_session,
            ),
            CapsRouter(
                self.mcpl_repository,
                self.auth_cache,
                self.http_session,
            ),
            ChatCompletionsRouter(
                self.mcpl_repository,
                self.auth_cache,
                self.http_session,
            ),
            FilesRouter(
                self.files_repository,
                self.auth_cache,
                self.http_session,
            ),
            ModelsRouter(
                self.auth_cache,
                self.http_session,
            )
        ]


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache"
        return response
