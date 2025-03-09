import signal

import asyncio
import uvloop
import uvicorn

from core.args import parse_args
from core.logger import init_logger, info
from core.app import App


class Server(uvicorn.Server):
    """Custom uvicorn Server with graceful shutdown"""

    def __init__(self, app, host: str, port: int):
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



    app = App(
        docs_url=None,
        redoc_url=None
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
