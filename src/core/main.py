import signal

import asyncio
import threading

import uvloop
import uvicorn

from core.args import parse_args
from core.globals import BASE_DIR
from core.logger import init_logger, info, warn
from core.app import App
from core.repositories.files_repository import FilesRepository

from doc_search.extactor.worker import spawn_worker as spawn_worker_doc_search


class Server(uvicorn.Server):
    """Custom uvicorn Server with graceful shutdown"""

    def __init__(
            self,
            app,
            host: str,
            port: int,
            doc_s_stop: threading.Event,
            doc_s_thread: threading.Thread,
    ):
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            timeout_keep_alive=600,
            log_config=None
        )
        super().__init__(config)
        self.doc_s_stop = doc_s_stop
        self.doc_s_thread = doc_s_thread

    async def shutdown(self, sockets=None):
        """Graceful shutdown with stats worker cleanup"""

        if self.doc_s_stop and self.doc_s_thread:
            self.doc_s_stop.set()
            self.doc_s_thread.join(timeout=5)
            if self.doc_s_thread.is_alive():
                warn("doc_s_thread didn't finish in time")

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
    doc_s_stop, doc_s_thread = spawn_worker_doc_search(files_repository)

    app = App(
        files_repository,
        docs_url="/docs",
        redoc_url=None
    )

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    server = Server(
        app=app,
        host=args.host,
        port=args.port,
        doc_s_stop=doc_s_stop,
        doc_s_thread=doc_s_thread,
    )

    setup_signal_handlers(server)

    server.run()
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
