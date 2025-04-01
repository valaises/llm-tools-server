import signal

import asyncio

import uvloop
import uvicorn

from core.args import parse_args
from core.globals import BASE_DIR
from core.logger import init_logger, info
from core.app import App
from core.repositories.files_repository import FilesRepository
from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository


class Server(uvicorn.Server):
    """Custom uvicorn Server with graceful shutdown"""

    def __init__(
            self,
            app,
            host: str,
            port: int,
    ):
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            timeout_keep_alive=600,
            log_config=None
        )
        super().__init__(config)

    async def shutdown(self, sockets=None):
        """Graceful shutdown with stats worker cleanup"""

        # Shutdown uvicorn
        await super().shutdown(sockets=sockets)


def setup_signal_handlers(server: Server):
    """Setup handlers for signals"""
    def handle_exit(signum, frame):
        info(f"Received exit signal {signal.Signals(signum).name}")
        asyncio.create_task(server.shutdown())

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)


def main():
    args = parse_args()
    init_logger(args.DEBUG)
    info("Logger initialized")

    db_dir = BASE_DIR / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    files_repository = FilesRepository(db_dir / "files.db")
    mcpl_repository = MCPLServersRepository(db_dir / "mcpl_servers.db")

    app = App(
        files_repository,
        mcpl_repository,

        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json"
    )

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    server = Server(
        app=app,
        host=args.host,
        port=args.port,
    )

    setup_signal_handlers(server)

    server.run()
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
