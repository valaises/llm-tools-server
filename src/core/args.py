from argparse import ArgumentParser
from dataclasses import dataclass


from core.logger import init_logger


__all__ = ["Args", "parse_args"]


@dataclass
class Args:
    host: str
    port: int
    DEBUG: bool


def parse_args() -> Args:
    init_logger(True)
    parser = ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=7012, type=int)
    parser.add_argument("--DEBUG", default=False, action="store_true")

    args = parser.parse_args()

    return Args(
        DEBUG=args.DEBUG,
        host=args.host,
        port=args.port,
    )
